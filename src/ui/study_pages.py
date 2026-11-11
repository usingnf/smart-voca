#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 암기, 단어 추가·편집·삭제, 유사 의미 검색 화면
# 파일 위치: src/ui/study_pages.py

import html
import re

from PyQt6.QtCore import QEvent, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import POS_DEFAULT_ORDER
from online_dict import ATTRIBUTION_TEXT, MSG_NO_KEY, OnlineDictError, search_english_translations
from quiz import DIRECTION_EN_TO_KO, DIRECTION_KO_TO_EN
from speech import speak_word
from ui.theme import mark_font_level
from vocab import POS_LABELS, join_list, search_by_english, search_by_meaning, split_list

WORD_PATTERN = re.compile(r"^[A-Za-z][A-Za-z '\-]{0,39}$")


def page_title(text):
    """화면 제목. 글꼴 크기는 글꼴 단계로 지정해 옵션의 글꼴 크기를 따라간다."""
    label = QLabel(text)
    mark_font_level(label, "title")
    return label


def make_table(headers):
    """교대 행 색상과 읽기 전용 설정을 가진 표를 만든다."""
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    return table


def fill_pos_combo(combo):
    for key in POS_DEFAULT_ORDER:
        combo.addItem(POS_LABELS[key], key)


class MemorizePage(QWidget):
    """암기 화면. 영어 또는 한글을 먼저 보고, [열기]를 누르면 대응하는 답과 예문이 열린다.

    시험이 아니므로 채점과 오답률에는 넣지 않는다. 열어 본 기록만 남긴다.
    """

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.current = None
        self._answer_shown = False

        self.direction_combo = QComboBox()
        self.direction_combo.addItems([DIRECTION_EN_TO_KO, DIRECTION_KO_TO_EN])
        self.direction_combo.currentIndexChanged.connect(self.refresh_question)
        self.direction_combo.setToolTip("영어→한글: 영단어를 보고 뜻을 엽니다. 한글→영어: 뜻을 보고 단어를 엽니다.")
        self.favorites_only = QCheckBox("즐겨찾기 단어만")
        self.favorites_only.toggled.connect(self.next_word)
        self.favorites_only.setToolTip("★로 표시한 단어만 보여 줍니다. 즐겨찾기가 없으면 전체 단어를 보여 줍니다.")
        self.question_label = QLabel()
        mark_font_level(self.question_label, "large")
        self.answer_label = QLabel()
        mark_font_level(self.answer_label, "emphasis")
        self.example_label = QLabel()
        self.example_label.setWordWrap(True)
        self.example_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notice_label = QLabel()
        self.notice_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.favorite_button = QPushButton("★ 즐겨찾기")
        self.favorite_button.clicked.connect(self.toggle_favorite)
        self.favorite_button.setToolTip("이 단어를 즐겨찾기에 넣거나 뺍니다.")
        speak_button = QPushButton("발음 듣기")
        speak_button.clicked.connect(self.speak_current)
        speak_button.setToolTip("영어 단어를 소리 내어 읽어 줍니다.")
        open_button = QPushButton("열기")
        open_button.clicked.connect(self.open_answer)
        open_button.setToolTip("단축키: Space 또는 Enter. 열린 뒤에는 다음 단어로 넘어갑니다.")
        next_button = QPushButton("다음 단어")
        next_button.clicked.connect(self.next_word)
        next_button.setToolTip("단축키: →")

        # 단축키는 이 화면에 있을 때만 동작한다. Space·Enter는 열기, 열고 난 뒤에는 다음 단어.
        for key in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(self.open_or_next)
        arrow_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        arrow_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        arrow_shortcut.activated.connect(self.next_word)

        top_row = QHBoxLayout()
        top_row.addWidget(self.direction_combo)
        top_row.addWidget(self.favorites_only)
        top_row.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(page_title("암기"))
        layout.addLayout(top_row)
        layout.addStretch()
        layout.addWidget(self.question_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.answer_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.example_label)
        layout.addWidget(self.notice_label)
        layout.addStretch()
        buttons = QHBoxLayout()
        buttons.addWidget(open_button)
        buttons.addWidget(speak_button)
        buttons.addWidget(self.favorite_button)
        buttons.addWidget(next_button)
        layout.addLayout(buttons)

        self.next_word()

    def apply_settings(self, settings):
        self.direction_combo.setCurrentText(settings.memorize_direction)

    def _candidates(self):
        """출제 후보와 안내 문구를 함께 돌려준다. 즐겨찾기가 없으면 전체 단어로 바꾸고 그 사실을 알린다."""
        if self.favorites_only.isChecked():
            favorite_pool = self.session.favorite_pool()
            if favorite_pool:
                return list(favorite_pool.values()), ""
            return list(self.session.pool.values()), "즐겨찾기 단어가 없어 전체 단어에서 보여 줍니다."
        return list(self.session.pool.values()), ""

    def next_word(self):
        candidates, notice = self._candidates()
        self.notice_label.setText(notice)
        self.current = self.session.rng.choice(candidates)
        self.refresh_question()

    def open_or_next(self):
        """Space·Enter: 아직 안 열었으면 열고, 이미 열었으면 다음 단어로 간다."""
        if self._answer_shown:
            self.next_word()
        else:
            self.open_answer()

    def refresh_question(self):
        self._answer_shown = False
        self.answer_label.setText("")
        self.example_label.setText("")
        if self.current is None:
            return
        if self.direction_combo.currentText() == DIRECTION_EN_TO_KO:
            self.question_label.setText(self.current.word)
        else:
            self.question_label.setText(self.current.meanings[0])
        self._refresh_favorite_button()

    def _refresh_favorite_button(self):
        marked = self.current is not None and self.session.is_favorite(self.current.word)
        self.favorite_button.setText("★ 즐겨찾기 해제" if marked else "☆ 즐겨찾기")

    def toggle_favorite(self):
        if self.current is None:
            return
        self.session.toggle_favorite(self.current.word)
        self._refresh_favorite_button()

    def speak_current(self):
        if self.current is not None:
            speak_word(self.current.word)

    def open_answer(self):
        if self.current is None:
            return
        if self.direction_combo.currentText() == DIRECTION_EN_TO_KO:
            answer = join_list(self.current.meanings)
        else:
            answer = self.current.word
        self.answer_label.setText(answer)
        self.example_label.setText(self.current.example or "예문 없음")
        self._answer_shown = True
        self.session.record_memorize(self.current.word)


class AddWordPage(QWidget):
    """단어 추가·편집·삭제 화면. 사용자가 추가한 단어를 표에서 골라 뜻을 고치거나 지울 수 있다."""

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.editing_word = None

        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("영단어 (예: resilient)")
        self.pos_combo = QComboBox()
        fill_pos_combo(self.pos_combo)
        self.meaning_input = QLineEdit()
        self.meaning_input.setPlaceholderText("한글 뜻 (쉼표로 여러 개 입력 가능)")
        self.message_label = QLabel()
        self.mode_label = QLabel()
        self.duplicate_hint = QLabel()
        self.duplicate_hint.setStyleSheet("color: #e65100; font-weight: bold;")
        self.word_input.textChanged.connect(self._update_duplicate_hint)

        add_button = QPushButton("추가")
        add_button.clicked.connect(self.add_word)
        add_button.setToolTip("입력한 단어와 뜻을 저장합니다. 이미 있는 단어면 뜻을 합칩니다.")
        self.save_button = QPushButton("수정 저장")
        self.save_button.clicked.connect(self.save_edit)
        self.save_button.setToolTip("표에서 고른 단어의 뜻·품사를 수정합니다.")
        clear_button = QPushButton("입력 초기화")
        clear_button.clicked.connect(self.clear_form)
        self.delete_button = QPushButton("선택 단어 삭제")
        self.delete_button.clicked.connect(self.delete_selected)
        self.delete_button.setToolTip("표에서 고른 단어를 지웁니다.")

        self.custom_table = make_table(["단어", "품사", "한글 뜻"])
        self.custom_table.itemSelectionChanged.connect(self.load_selected)

        form = QHBoxLayout()
        form.addWidget(self.word_input)
        form.addWidget(self.pos_combo)
        buttons = QHBoxLayout()
        buttons.addWidget(add_button)
        buttons.addWidget(self.save_button)
        buttons.addWidget(clear_button)
        buttons.addWidget(self.delete_button)

        layout = QVBoxLayout(self)
        layout.addWidget(page_title("단어 추가"))
        layout.addLayout(form)
        layout.addWidget(self.duplicate_hint)
        layout.addWidget(self.meaning_input)
        layout.addLayout(buttons)
        layout.addWidget(self.mode_label)
        layout.addWidget(self.message_label)
        layout.addWidget(QLabel("내가 추가한 단어 (표를 누르면 수정할 수 있습니다)"))
        layout.addWidget(self.custom_table)

        self.refresh_table()
        self._set_editing(None)

    def _set_editing(self, word):
        self.editing_word = word
        self.word_input.setReadOnly(word is not None)
        self.save_button.setEnabled(word is not None)
        self.delete_button.setEnabled(word is not None)
        self.mode_label.setText(f"수정 중: {word}" if word else "새 단어 입력 중")

    def refresh_table(self):
        words = sorted(self.session.custom.values(), key=lambda entry: entry.word)
        self.custom_table.setRowCount(len(words))
        for row_index, entry in enumerate(words):
            self.custom_table.setItem(row_index, 0, QTableWidgetItem(entry.word))
            self.custom_table.setItem(row_index, 1, QTableWidgetItem(POS_LABELS.get(entry.pos, entry.pos)))
            self.custom_table.setItem(row_index, 2, QTableWidgetItem(join_list(entry.meanings)))

    def load_selected(self):
        rows = self.custom_table.selectionModel().selectedRows()
        if not rows:
            return
        word = self.custom_table.item(rows[0].row(), 0).text()
        entry = self.session.custom.get(word)
        if entry is None:
            return
        self.word_input.setText(word)
        index = self.pos_combo.findData(entry.pos) if entry.pos in POS_LABELS else -1
        self.pos_combo.setCurrentIndex(max(index, 0))
        self.meaning_input.setText(join_list(entry.meanings))
        self._set_editing(word)
        self.message_label.setText("")
        self._update_duplicate_hint()

    def _update_duplicate_hint(self, *_args):
        """새 단어를 입력하는 중에 이미 있는 단어이면 칸 아래에 미리 알린다. 저장 시 경고 창은 그대로 뜬다."""
        word = self.word_input.text().strip().lower()
        if self.editing_word is not None or not word:
            self.duplicate_hint.setText("")
            return
        if self.session.exists_word(word):
            self.duplicate_hint.setText(f"'{word}'은(는) 이미 있는 단어입니다. 추가하면 뜻이 합쳐집니다.")
        else:
            self.duplicate_hint.setText("")

    def clear_form(self):
        self.custom_table.clearSelection()
        self.word_input.clear()
        self.meaning_input.clear()
        self.pos_combo.setCurrentIndex(0)
        self._set_editing(None)
        self.message_label.setText("")
        self._update_duplicate_hint()

    def _read_form(self):
        word = self.word_input.text().strip().lower()
        meanings = split_list(self.meaning_input.text())
        pos = self.pos_combo.currentData()
        if not WORD_PATTERN.match(word):
            self.message_label.setText("영단어는 영문자, 공백, 하이픈, 작은따옴표만 쓸 수 있습니다.")
            return None
        if not meanings:
            self.message_label.setText("한글 뜻을 한 개 이상 입력하세요.")
            return None
        return word, pos, meanings

    def add_word(self):
        form = self._read_form()
        if form is None:
            return
        word, pos, meanings = form
        if self.session.exists_word(word):
            QMessageBox.warning(self, "이미 있는 단어",
                                f"'{word}'은(는) 이미 있는 단어입니다. 입력한 뜻을 합칩니다.")
        self.session.add_word(word, pos, meanings)
        self.message_label.setText(f"'{word}' 저장 완료 ({join_list(meanings)})")
        self.refresh_table()
        self.clear_form()
        # 연속 입력을 위해 단어 칸으로 포커스를 돌린다.
        self.word_input.setFocus()

    def save_edit(self):
        if self.editing_word is None:
            return
        form = self._read_form()
        if form is None:
            return
        _, pos, meanings = form
        self.session.update_custom_word(self.editing_word, pos, meanings)
        self.message_label.setText(f"'{self.editing_word}' 수정 저장 완료")
        self.refresh_table()
        self.clear_form()

    def delete_selected(self):
        if self.editing_word is None:
            return
        answer = QMessageBox.warning(
            self, "단어 삭제",
            f"'{self.editing_word}'을(를) 삭제합니다. 기본 단어와 같은 단어라면 기본 뜻으로 돌아갑니다.\n"
            "이 작업은 되돌릴 수 없습니다. 계속하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        word = self.editing_word
        self.session.delete_custom_word(word)
        self.message_label.setText(f"'{word}' 삭제 완료")
        self.refresh_table()
        self.clear_form()


class OnlineLookupWorker(QThread):
    """온라인 검색을 백그라운드에서 실행한다. 끝나면 (검색어, 결과 목록, 오류 메시지)를 보낸다."""

    lookup_done = pyqtSignal(str, object, str)

    def __init__(self, query, api_key):
        super().__init__()
        self.query = query
        self.api_key = api_key

    def run(self):
        try:
            results = search_english_translations(self.query, self.api_key)
            self.lookup_done.emit(self.query, results, "")
        except OnlineDictError as error:
            self.lookup_done.emit(self.query, [], str(error))


ONLINE_DEBOUNCE_MS = 600
# 온라인 조회 시간 제한(5초)보다 조금 길게 기다린다.
ONLINE_SHUTDOWN_WAIT_MS = 6000


class SearchPage(QWidget):
    """유사 의미 검색 화면. 입력하는 즉시 찾고, 행을 고르면 상세 정보를 보여 준다.

    검색 대상은 voca.csv 단어와 사용자가 추가한 단어다.
    한글 검색어는 온라인 한영 번역(FR-12)을 보조로 함께 보여 준다. 온라인 결과가 없어도 로컬 결과는 그대로 나온다.
    """

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.entries = []
        self.api_key = ""
        self.online_enabled = True
        self.online_cache = {}
        self.online_workers = []

        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("영어 단어 또는 한글 뜻 (입력하면 바로 검색됩니다)")
        self.query_input.textChanged.connect(self.search)
        self.query_input.setToolTip("Enter 또는 ↓ 키로 결과 표로 이동합니다. 표에서 Esc를 누르면 다시 입력 칸으로 돌아옵니다.")
        self.query_input.installEventFilter(self)
        self.result_table = make_table(["단어", "한글 뜻", "유의어"])
        self.result_table.itemSelectionChanged.connect(self.show_detail)
        self.result_table.installEventFilter(self)
        self.detail_label = QLabel("행을 고르면 뜻, 영문 풀이, 예문을 보여 줍니다.")
        self.detail_label.setWordWrap(True)
        self.online_label = QLabel()
        self.online_label.setWordWrap(True)
        self.message_label = QLabel()

        self.online_timer = QTimer(self)
        self.online_timer.setSingleShot(True)
        self.online_timer.setInterval(ONLINE_DEBOUNCE_MS)
        self.online_timer.timeout.connect(self.start_online_lookup)

        layout = QVBoxLayout(self)
        layout.addWidget(page_title("유사 의미 검색"))
        layout.addWidget(self.query_input)
        layout.addWidget(self.result_table)
        layout.addWidget(self.detail_label)
        layout.addWidget(self.online_label)
        layout.addWidget(self.message_label)

    def eventFilter(self, watched, event):
        """입력 칸에서 Enter·↓를 누르면 결과 표의 첫 행으로, 표에서 Esc를 누르면 입력 칸으로 옮긴다."""
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if watched is self.query_input and key in (Qt.Key.Key_Down, Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self.entries:
                    self.result_table.setFocus()
                    self.result_table.selectRow(0)
                    return True
            if watched is self.result_table and key == Qt.Key.Key_Escape:
                self.query_input.setFocus()
                return True
        return super().eventFilter(watched, event)

    def set_online_settings(self, enabled, api_key):
        """설정의 온라인 사용 여부와 인증키를 반영한다. 키가 바뀌면 온라인 캐시를 비운다."""
        if api_key != self.api_key:
            self.api_key = api_key
            self.online_cache.clear()
        self.online_enabled = enabled
        if not enabled:
            self.online_timer.stop()
            self.online_label.setText("")
        elif self.query_input.text().strip():
            self.update_online_area(self.query_input.text().strip())

    def search(self):
        query = self.query_input.text().strip()
        self.online_timer.stop()
        if not query:
            self.entries = []
            self.result_table.setRowCount(0)
            self.detail_label.setText("행을 고르면 뜻, 영문 풀이, 예문을 보여 줍니다.")
            self.online_label.setText("")
            self.message_label.setText("검색어를 입력하세요.")
            return
        if query.isascii():
            self.entries = search_by_english(self.session.pool, query)
        else:
            self.entries = search_by_meaning(self.session.pool, query)

        self.result_table.setRowCount(len(self.entries))
        for row_index, entry in enumerate(self.entries):
            values = [entry.word, join_list(entry.meanings), join_list(entry.synonyms) or "유의어 없음"]
            for column_index, value in enumerate(values):
                self.result_table.setItem(row_index, column_index, QTableWidgetItem(value))
        self.message_label.setText("" if self.entries else
                                   "검색 결과가 없습니다. (voca.csv 단어와 추가한 단어만 검색합니다)")
        self.update_online_area(query)

    def update_online_area(self, query):
        """한글 검색어만 온라인 조회 대상이다. 캐시가 있으면 바로 보여 주고, 없으면 잠시 뒤 조회한다."""
        if query.isascii() or not self.online_enabled:
            self.online_label.setText("")
            return
        if not self.api_key:
            self.online_label.setText(f"[온라인 참고] {MSG_NO_KEY}")
            return
        if query in self.online_cache:
            self.show_online_result(*self.online_cache[query])
            return
        self.online_label.setText("[온라인 참고] 조회 중...")
        self.online_timer.start()

    def start_online_lookup(self):
        query = self.query_input.text().strip()
        if (not self.online_enabled or not query or query.isascii()
                or query in self.online_cache or not self.api_key):
            return
        self.online_workers = [worker for worker in self.online_workers if worker.isRunning()]
        worker = OnlineLookupWorker(query, self.api_key)
        worker.lookup_done.connect(self.on_online_lookup_done)
        self.online_workers.append(worker)
        worker.start()

    def on_online_lookup_done(self, query, results, error_message):
        # 오류(네트워크, 한도 초과 등)는 일시적일 수 있으므로 캐시하지 않는다. 같은 검색어를 다시 입력하면 재조회한다.
        if not error_message:
            self.online_cache[query] = (results, error_message)
        if query == self.query_input.text().strip():
            self.show_online_result(results, error_message)

    def shutdown(self):
        """창을 닫을 때 호출한다. 실행 중인 온라인 조회가 끝날 때까지 기다려, 스레드가 살아 있는 채로 파괴되지 않게 한다."""
        self.online_timer.stop()
        for worker in self.online_workers:
            if worker.isRunning():
                worker.wait(ONLINE_SHUTDOWN_WAIT_MS)
        self.online_workers = []

    def show_online_result(self, results, error_message):
        if error_message:
            self.online_label.setText(f"[온라인 참고] {error_message}")
            return
        if not results:
            self.online_label.setText("[온라인 참고] 온라인 사전에 영어 번역이 없습니다.")
            return
        lines = [f"{item.word} ({item.pos or '품사 없음'}): {', '.join(item.english)}" for item in results[:5]]
        lines.append(ATTRIBUTION_TEXT)
        self.online_label.setText("[온라인 참고 · 한국어기초사전]<br>" + "<br>".join(html.escape(line) for line in lines))

    def show_detail(self):
        rows = self.result_table.selectionModel().selectedRows()
        if not rows or rows[0].row() >= len(self.entries):
            return
        entry = self.entries[rows[0].row()]
        esc = html.escape
        pos_text = POS_LABELS.get(entry.pos, entry.pos) if entry.pos else "품사 없음"
        lines = [
            f"<b>{esc(entry.word)}</b>  ({esc(pos_text)})",
            f"한글 뜻: {esc(join_list(entry.meanings))}",
            f"영문 풀이: {esc(entry.english_gloss or '없음')}",
            f"유의어: {esc(join_list(entry.synonyms) or '없음')}",
            f"예문: {esc(entry.example or '없음')}",
            f"출처: {esc(entry.source or '없음')}",
        ]
        self.detail_label.setText("<br>".join(lines))
