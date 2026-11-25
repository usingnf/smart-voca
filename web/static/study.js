// 2026-11-18 - 클로드 스마트 보카 - 웹 화면: 암기, 시험(문항 풀이·채점), 과제
// 파일 위치: web/static/study.js

"use strict";

(function () {
  const SV_ = window.SV;
  const OX_TRUE = "O";
  const OX_FALSE = "X";

  // ----- 시험 문항 풀이와 결과 -----

  // 문항을 하나씩 풀게 하고, 제출하면 서버에서 채점한 결과를 보여 준다.
  // opts: { abortable, assignment, onDone, onRetest }
  SV_.runQuiz = function (quiz, opts = {}) {
    const answers = new Array(quiz.total).fill("");
    let index = 0;

    function saveCurrentInput() {
      const input = document.getElementById("answer-input");
      if (input) {
        answers[index] = input.value.trim();
      }
    }

    function drawQuestion() {
      const question = quiz.questions[index];
      const percent = Math.round((index / quiz.total) * 100);
      const progress = SV_.el("div", { class: "progress" }, [
        SV_.el("div", { class: "progress-label", text: `${index + 1} / ${quiz.total} 문항` }),
        SV_.el("div", { class: "progress-track" }, [
          SV_.el("div", { class: "progress-fill", style: `width:${percent}%` }),
        ]),
      ]);

      const answerArea = SV_.el("div", { class: "answer-area" }, [renderAnswerInput(question)]);
      const isLast = index === quiz.total - 1;
      const prevButton = SV_.button("이전", () => {
        saveCurrentInput();
        index -= 1;
        drawQuestion();
      }, "ghost");
      prevButton.disabled = index === 0;
      const nextButton = isLast
        ? SV_.button("제출하고 채점", submitAnswers, "primary")
        : SV_.button("다음", () => {
          saveCurrentInput();
          index += 1;
          drawQuestion();
        }, "primary");
      const navRow = SV_.el("div", { class: "row between" }, [prevButton, nextButton]);

      const leaveButton = opts.abortable
        ? SV_.button("그만두기", leaveQuiz, "danger ghost")
        : null;

      SV_.render([
        SV_.el("h2", { text: opts.title || quiz.title }),
        progress,
        SV_.card([
          SV_.el("p", { class: "prompt", text: question.prompt }),
          answerArea,
        ]),
        navRow,
        leaveButton ? SV_.el("div", { class: "row end" }, [leaveButton]) : null,
      ].filter(Boolean));
      const input = document.getElementById("answer-input");
      if (input) {
        input.focus();
        input.addEventListener("keydown", (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            nextButton.click();
          }
        });
      }
    }

    function renderAnswerInput(question) {
      const current = answers[index];
      if (question.kind === "단답형") {
        return SV_.el("input", {
          id: "answer-input",
          class: "text-input",
          type: "text",
          placeholder: "정답을 입력하세요",
          value: current,
          autocomplete: "off",
        });
      }
      if (question.kind === "4지선다형") {
        return SV_.el("div", { class: "choices" }, question.choices.map((choice) =>
          SV_.el("button", {
            type: "button",
            class: `choice ${current === choice ? "selected" : ""}`.trim(),
            text: choice,
            onclick: () => {
              answers[index] = choice;
              drawQuestion();
            },
          })));
      }
      // OX형
      return SV_.el("div", { class: "choices ox" }, [OX_TRUE, OX_FALSE].map((mark) =>
        SV_.el("button", {
          type: "button",
          class: `choice ox-choice ${current === mark ? "selected" : ""}`.trim(),
          text: mark === OX_TRUE ? "O  (맞음)" : "X  (틀림)",
          onclick: () => {
            answers[index] = mark;
            drawQuestion();
          },
        })));
    }

    async function submitAnswers() {
      saveCurrentInput();
      const unanswered = answers.filter((answer) => !answer).length;
      if (unanswered > 0 && !window.confirm(`아직 답하지 않은 문항이 ${unanswered}개 있습니다. 그래도 제출할까요?`)) {
        return;
      }
      try {
        const result = await SV_.api(`/api/quiz/${quiz.quiz_id}/grade`, {
          method: "POST",
          body: { answers },
        });
        showResult(result);
      } catch (error) {
        SV_.fail(error);
      }
    }

    async function leaveQuiz() {
      const message = opts.assignment
        ? "그만두면 오늘 과제는 미이수로 기록되고 단어가 다음 날 복습으로 넘어갑니다. 그만둘까요?"
        : "그만두면 이 시험은 기록되지 않습니다. 그만둘까요?";
      if (!window.confirm(message)) {
        return;
      }
      try {
        await SV_.api(`/api/quiz/${quiz.quiz_id}/abort`, { method: "POST" });
      } catch (error) {
        SV_.fail(error);
      }
      if (opts.onDone) {
        opts.onDone({ aborted: true });
      }
    }

    function showResult(result) {
      const wrongRows = result.results.filter((row) => !row.is_correct);
      const percent = Math.round(result.score * 100);
      let verdict = null;
      if (result.passed !== null && result.passed !== undefined) {
        verdict = SV_.el("p", {
          class: `verdict ${result.passed ? "ok" : "bad"}`,
          text: result.passed
            ? `과제를 완수했습니다! (기준 ${Math.round(result.pass_rate * 100)}% 이상)`
            : `아쉽지만 기준(${Math.round(result.pass_rate * 100)}%)에 못 미쳤습니다. 과제는 미이수입니다.`,
        });
      }
      const rows = result.results.map((row) => SV_.el("li", { class: row.is_correct ? "row-ok" : "row-bad" }, [
        SV_.el("strong", { text: row.word }),
        SV_.el("span", { class: "muted", text: `  ${row.direction} · ${row.kind}` }),
        SV_.el("div", { text: `내 답: ${row.user_answer || "(없음)"}` }),
        row.is_correct ? null : SV_.el("div", { text: `정답: ${row.expected_text}` }),
      ].filter(Boolean)));

      const buttons = [];
      if (opts.onRetest && wrongRows.length > 0) {
        buttons.push(SV_.button("오답만 다시 풀기", () => opts.onRetest(), "primary"));
      }
      buttons.push(SV_.button("처음으로", () => opts.onDone && opts.onDone({ aborted: false }), "ghost"));

      SV_.render([
        SV_.el("h2", { text: `채점 결과: ${percent}점 (${result.results.length - wrongRows.length}/${result.results.length} 정답)` }),
        verdict,
        SV_.el("ul", { class: "result-list" }, rows),
        SV_.el("div", { class: "row end" }, buttons),
      ].filter(Boolean));
    }

    drawQuestion();
  };

  // ----- 암기 -----

  SV_.pages.memorize = function () {
    const settings = SV_.state.settings;
    let entry = null;
    let opened = false;
    const favoritesCheck = SV_.el("input", { type: "checkbox", id: "memo-fav" });
    // 기본값은 오늘 과제 단어만 보기다. 체크를 풀면 전체 단어에서 고른다.
    const todayCheck = SV_.el("input", { type: "checkbox", id: "memo-today", checked: true });
    const notice = SV_.el("p", { class: "notice" });
    const main = SV_.el("div", { class: "memo-main" });
    const askEnglish = settings.memorize_direction !== "한글→영어";

    async function loadNext() {
      try {
        const data = await SV_.api(`/api/memorize/next?${SV_.query({ favorites_only: favoritesCheck.checked, today_only: todayCheck.checked })}`);
        entry = data.word;
        opened = false;
        notice.textContent = data.notice || "";
        drawCard();
      } catch (error) {
        SV_.fail(error);
      }
    }

    async function openAnswer() {
      if (opened) {
        return;
      }
      opened = true;
      try {
        await SV_.api("/api/memorize/open", { method: "POST", body: { username: SV_.state.username, word: entry.word } });
      } catch (error) {
        SV_.fail(error);
      }
      drawCard();
    }

    async function toggleFavorite() {
      try {
        const data = await SV_.api(`/api/favorites/${encodeURIComponent(entry.word)}`, {
          method: "POST",
          body: { username: SV_.state.username },
        });
        entry.favorite = data.favorite;
        drawCard();
      } catch (error) {
        SV_.fail(error);
      }
    }

    function speak(word) {
      if (!window.speechSynthesis) {
        SV_.toast("이 브라우저는 음성 읽기를 지원하지 않습니다.", "error");
        return;
      }
      const utterance = new SpeechSynthesisUtterance(word);
      utterance.lang = "en-US";
      window.speechSynthesis.speak(utterance);
    }

    function drawCard() {
      if (!entry) {
        return;
      }
      const question = askEnglish ? entry.word : entry.meanings.join(", ");
      const answerText = askEnglish ? entry.meanings.join(", ") : entry.word;
      const details = [];
      if (opened) {
        if (entry.english_gloss) {
          details.push(SV_.el("p", { class: "muted", text: `영문 뜻: ${entry.english_gloss}` }));
        }
        if (entry.synonyms.length) {
          details.push(SV_.el("p", { text: `유의어: ${entry.synonyms.join(", ")}` }));
        }
        if (entry.example) {
          details.push(SV_.el("p", { class: "example", text: `예문: ${entry.example}` }));
        }
        details.push(SV_.el("p", { class: "muted", text: `품사: ${SV_.posLabel(entry.pos)}${entry.custom ? " · 직접 추가한 단어" : ""}` }));
      }

      const starLabel = entry.favorite ? "★ 즐겨찾기 해제" : "☆ 즐겨찾기";
      main.replaceChildren(
        SV_.card([
          SV_.el("div", { class: "memo-question", text: question }),
          opened
            ? SV_.el("div", { class: "memo-answer", text: answerText })
            : SV_.el("p", { class: "muted", text: "뜻을 보려면 '뜻 보기'를 누르세요 (Enter)" }),
          ...details,
        ], "memo-card"),
        SV_.el("div", { class: "row wrap" }, [
          opened
            ? SV_.button("다음 단어 (Enter)", loadNext, "primary")
            : SV_.button("뜻 보기 (Enter)", openAnswer, "primary"),
          SV_.button(starLabel, toggleFavorite, "ghost"),
          SV_.button("🔊 발음", () => speak(entry.word), "ghost"),
        ]),
      );
    }

    function onKey(event) {
      if (event.target && ["INPUT", "TEXTAREA"].includes(event.target.tagName) && event.target !== favoritesCheck && event.target !== todayCheck) {
        return;
      }
      if (event.key === "Enter" && entry) {
        event.preventDefault();
        if (opened) {
          loadNext();
        } else {
          openAnswer();
        }
      }
    }
    document.addEventListener("keydown", onKey);
    SV_.cleanup.push(() => document.removeEventListener("keydown", onKey));

    favoritesCheck.addEventListener("change", loadNext);
    todayCheck.addEventListener("change", loadNext);
    SV_.render([
      SV_.el("h2", { text: "암기" }),
      SV_.el("label", { class: "check" }, [todayCheck, " 오늘 과제 단어만 보기 (그날의 단어 암기)"]),
      SV_.el("label", { class: "check" }, [favoritesCheck, " 즐겨찾기 단어만 보기"]),
      notice,
      main,
    ]);
    loadNext();
  };

  // ----- 시험 설정과 시작 -----

  SV_.pages.test = function () {
    const meta = SV_.state.meta;
    const settings = SV_.state.settings;
    const countSelect = SV_.el("select", { id: "exam-count" }, optionRange(meta.exam_count));
    countSelect.value = String(settings.exam_count);
    const directionSelect = SV_.el("select", { id: "exam-direction" },
      meta.directions.map((item) => SV_.el("option", { value: item, text: item })));
    directionSelect.value = settings.exam_direction;
    const kindChecks = meta.kinds.map((kind) => checkBox("kind", kind, settings.exam_kinds.includes(kind)));
    const posChecks = meta.pos_order.map((key) => checkBox("pos", key, settings.exam_pos_keys.includes(key), SV_.posLabel(key)));
    const favoriteCheck = checkBox("fav", "favorites", settings.exam_favorites_only, "즐겨찾기 단어만 출제");
    const error = SV_.el("p", { class: "error" });

    function selectedValues(name) {
      return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map((node) => node.value);
    }

    async function start() {
      const kinds = selectedValues("kind");
      const posKeys = selectedValues("pos");
      const direction = directionSelect.value;
      const count = Number(countSelect.value);
      const favoritesOnly = favoriteCheck.querySelector("input").checked;
      error.textContent = "";
      if (!kinds.length) {
        error.textContent = "문제 유형을 하나 이상 고르세요.";
        return;
      }
      if (!posKeys.length) {
        error.textContent = "출제할 품사를 하나 이상 고르세요.";
        return;
      }
      try {
        const quiz = await SV_.api("/api/test/quiz", {
          method: "POST",
          body: { username: SV_.state.username, count, kinds, pos_keys: posKeys, direction, favorites_only: favoritesOnly },
        });
        await rememberSetup({ count, kinds, posKeys, direction, favoritesOnly });
        SV_.runQuiz(quiz, {
          title: "시험",
          abortable: true,
          onDone: () => SV_.pages.test(),
          onRetest: () => startWrongRetest(kinds, direction),
        });
      } catch (apiError) {
        error.textContent = apiError.message;
      }
    }

    async function startWrongRetest(kinds, direction) {
      try {
        const quiz = await SV_.api("/api/test/wrong", {
          method: "POST",
          body: { username: SV_.state.username, kinds, direction },
        });
        SV_.runQuiz(quiz, {
          title: "오답 재시험",
          abortable: true,
          onDone: () => SV_.pages.test(),
          onRetest: () => startWrongRetest(kinds, direction),
        });
      } catch (apiError) {
        SV_.fail(apiError);
      }
    }

    SV_.render([
      SV_.el("h2", { text: "시험" }),
      SV_.card([
        SV_.el("div", { class: "form-row" }, [SV_.el("label", { text: "문항 수" }), countSelect]),
        SV_.el("div", { class: "form-row" }, [SV_.el("label", { text: "시험 방향" }), directionSelect]),
        SV_.el("div", { class: "form-row" }, [SV_.el("label", { text: "문제 유형" }), SV_.el("div", { class: "checks" }, kindChecks)]),
        SV_.el("div", { class: "form-row" }, [SV_.el("label", { text: "품사" }), SV_.el("div", { class: "checks" }, posChecks)]),
        SV_.el("div", { class: "form-row" }, [SV_.el("label", { text: "조건" }), SV_.el("div", { class: "checks" }, [favoriteCheck])]),
        error,
        SV_.el("div", { class: "row end" }, [
          SV_.button("오답만 다시 풀기", () => startWrongRetest(selectedValues("kind"), directionSelect.value), "ghost"),
          SV_.button("시험 시작", start, "primary"),
        ]),
      ]),
    ]);
  };

  // 선택한 시험 조건을 설정에 남겨 다음에도 그대로 쓰게 한다 (데스크톱 앱과 같은 동작).
  async function rememberSetup(setup) {
    try {
      const saved = await SV_.api("/api/settings", {
        method: "PUT",
        body: {
          exam_count: setup.count,
          exam_kinds: setup.kinds,
          exam_pos_keys: setup.posKeys,
          exam_direction: setup.direction,
          exam_favorites_only: setup.favoritesOnly,
        },
      });
      return saved;
    } catch (error) {
      return null;
    }
  }

  function optionRange(range) {
    const options = [];
    for (let value = range.min; value <= range.max; value += range.step) {
      options.push(SV_.el("option", { value: String(value), text: `${value}문항` }));
    }
    return options;
  }

  function checkBox(name, value, checked, label) {
    const input = SV_.el("input", { type: "checkbox", name, value, checked: checked || null });
    if (name === "fav") {
      input.removeAttribute("name");
    }
    return SV_.el("label", { class: "check" }, [input, " ", label || value]);
  }

  // ----- 과제 -----

  SV_.pages.assignment = async function () {
    SV_.render(SV_.el("p", { class: "muted", text: "과제를 불러오는 중입니다…" }));
    try {
      const data = await SV_.api(`/api/assignment?${SV_.query()}`);
      const statusText = { pending: "진행 중", completed: "완수", missed: "미이수" }[data.status] || data.status;
      const scoreText = data.score === null || data.score === undefined ? "-" : `${Math.round(data.score * 100)}%`;
      const wordRows = data.words.map((word) => SV_.el("li", {}, [
        SV_.el("strong", { text: word.word }),
        SV_.el("span", { class: "muted", text: `  ${word.pos_label} · ${word.meanings.join(", ")}` }),
      ]));
      const startButton = data.pending
        ? SV_.button("과제 시험 시작", () => startAssignment(), "primary")
        : null;
      SV_.render([
        SV_.el("h2", { text: "오늘의 영단어 과제" }),
        SV_.card([
          SV_.el("p", { text: `${data.day_number}일차  ·  날짜: ${data.date}  ·  상태: ${statusText}  ·  점수: ${scoreText}` }),
          SV_.el("p", { class: "muted", text: `암기한 단어 ${data.memorized_count} / ${data.total_count}` }),
          SV_.el("p", { class: "muted", text: `복습 ${data.review_count}개 + 신규 ${data.new_count}개 · 정답률 80% 이상이면 완수` }),
        ]),
        SV_.card([SV_.el("ul", { class: "word-list" }, wordRows)]),
        startButton ? SV_.el("div", { class: "row end" }, [startButton]) : null,
      ].filter(Boolean));
    } catch (error) {
      SV_.render(SV_.el("p", { class: "error", text: error.message }));
    }
  };

  async function startAssignment() {
    try {
      const quiz = await SV_.api("/api/assignment/quiz", {
        method: "POST",
        body: { username: SV_.state.username },
      });
      SV_.runQuiz(quiz, {
        title: "과제 시험",
        assignment: true,
        abortable: true,
        onDone: () => SV_.pages.assignment(),
      });
    } catch (error) {
      SV_.fail(error);
    }
  }
})();
