// 2026-11-18 - 클로드 스마트 보카 - 웹 화면: 단어 추가, 검색(온라인 보조 포함), 보고서, 계정, 옵션
// 파일 위치: web/static/manage.js

"use strict";

(function () {
  const SV_ = window.SV;

  // ----- 단어 추가 -----

  SV_.pages.add = function () {
    const wordInput = SV_.el("input", { type: "text", id: "add-word", placeholder: "예: abacus", autocomplete: "off" });
    const posSelect = SV_.el("select", { id: "add-pos" },
      SV_.state.meta.pos_order.map((key) => SV_.el("option", { value: key, text: SV_.posLabel(key) })));
    const meaningInput = SV_.el("input", { type: "text", id: "add-meaning", placeholder: "뜻을 쉼표로 구분 (예: 수판, 산판)" });
    const message = SV_.el("p", { class: "notice", "aria-live": "polite" });

    async function save() {
      const meanings = SV_.splitList(meaningInput.value);
      try {
        const result = await SV_.api("/api/words", {
          method: "POST",
          body: { username: SV_.state.username, word: wordInput.value.trim(), pos: posSelect.value, meanings },
        });
        message.className = "notice ok";
        message.textContent = result.merged
          ? `'${result.word}'은(는) 이미 있는 단어라 입력한 뜻을 합쳤습니다.`
          : `'${result.word}' 저장 완료 (${meanings.join(", ")})`;
        wordInput.value = "";
        meaningInput.value = "";
        wordInput.focus();
      } catch (error) {
        message.className = "notice error";
        message.textContent = error.message;
      }
    }

    meaningInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        save();
      }
    });

    const fileInput = SV_.el("input", { type: "file", id: "import-file", accept: ".csv,text/csv" });
    const importMessage = SV_.el("p", { class: "notice", "aria-live": "polite" });
    const importErrors = SV_.el("ul", { class: "muted", id: "import-errors" });

    async function importFile() {
      const file = fileInput.files[0];
      importErrors.replaceChildren();
      if (!file) {
        importMessage.className = "notice error";
        importMessage.textContent = "CSV 파일을 먼저 고르세요.";
        return;
      }
      try {
        const text = await file.text();
        const result = await SV_.api("/api/words/import", {
          method: "POST",
          body: { username: SV_.state.username, text },
        });
        importMessage.className = "notice ok";
        const invalidText = result.invalid ? `, 형식 오류 ${result.invalid}줄` : "";
        importMessage.textContent =
          `${result.added}개 추가, ${result.skipped}개 건너뜀(이미 있는 단어 또는 파일 안 중복)${invalidText}`;
        result.errors.forEach((item) => importErrors.appendChild(SV_.el("li", { text: `${item.line}줄: ${item.reason}` })));
        fileInput.value = "";
      } catch (error) {
        importMessage.className = "notice error";
        importMessage.textContent = error.message;
      }
    }

    SV_.render([
      SV_.el("h2", { text: "단어 추가" }),
      SV_.card([
        SV_.el("div", { class: "form-row" }, [SV_.el("label", { text: "영단어" }), wordInput]),
        SV_.el("div", { class: "form-row" }, [SV_.el("label", { text: "품사" }), posSelect]),
        SV_.el("div", { class: "form-row" }, [SV_.el("label", { text: "한글 뜻" }), meaningInput]),
        SV_.el("p", { class: "muted", text: "영문자, 공백, 하이픈, 작은따옴표만 쓸 수 있습니다. 같은 단어가 있으면 뜻을 합칩니다." }),
        message,
        SV_.el("div", { class: "row end" }, [SV_.button("저장", save, "primary")]),
      ]),
      SV_.card([
        SV_.el("h3", { text: "CSV 가져오기" }),
        SV_.el("p", { class: "muted", text: "영단어,뜻 두 칸짜리 UTF-8 CSV입니다. 첫 줄 머리글(영단어,뜻)은 있어도 되고 없어도 됩니다. 품사는 '기타'로 들어갑니다. 이미 있는 단어는 건너뜁니다." }),
        SV_.el("div", { class: "form-row" }, [SV_.el("label", { text: "파일" }), fileInput]),
        importMessage,
        importErrors,
        SV_.el("div", { class: "row end" }, [SV_.button("가져오기", importFile, "primary")]),
      ]),
    ]);
    wordInput.focus();
  };

  // ----- 검색 -----

  SV_.pages.search = function () {
    const queryInput = SV_.el("input", { type: "text", id: "search-q", placeholder: "영어 단어 또는 한글 뜻" });
    const modeSelect = SV_.el("select", { id: "search-mode" }, [
      SV_.el("option", { value: "english", text: "영어 단어로 찾기" }),
      SV_.el("option", { value: "meaning", text: "한글 뜻으로 찾기" }),
    ]);
    const resultBox = SV_.el("div", { class: "search-results" });
    const onlineBox = SV_.el("div", { class: "online-box" });

    async function search() {
      const query = queryInput.value.trim();
      if (!query) {
        resultBox.replaceChildren(SV_.el("p", { class: "muted", text: "검색어를 입력하세요." }));
        onlineBox.replaceChildren();
        return;
      }
      try {
        const found = await SV_.api(`/api/words/search?${SV_.query({ q: query, mode: modeSelect.value })}`);
        if (!found.length) {
          resultBox.replaceChildren(SV_.el("p", { class: "muted", text: "찾는 단어가 없습니다." }));
        } else {
          resultBox.replaceChildren(...found.map(renderEntry));
        }
        onlineBox.replaceChildren();
        if (SV_.isHangul(query)) {
          onlineBox.replaceChildren(SV_.button("온라인 영어 번역 찾기 (보조)", () => onlineSearch(query), "ghost"));
        }
      } catch (error) {
        SV_.fail(error);
      }
    }

    async function onlineSearch(query) {
      onlineBox.replaceChildren(SV_.el("p", { class: "muted", text: "온라인에서 찾는 중입니다…" }));
      try {
        const data = await SV_.api(`/api/online-search?${SV_.query({ q: query })}`);
        const parts = [];
        if (data.message) {
          parts.push(SV_.el("p", { class: "notice", text: data.message }));
        }
        if (data.results.length) {
          parts.push(SV_.el("ul", { class: "word-list" }, data.results.map((item) => SV_.el("li", {}, [
            SV_.el("strong", { text: item.word }),
            SV_.el("span", { class: "muted", text: `  ${item.english.join(", ")}` }),
          ]))));
        }
        parts.push(SV_.el("p", { class: "attribution", text: SV_.state.meta.attribution }));
        onlineBox.replaceChildren(...parts);
      } catch (error) {
        SV_.fail(error);
      }
    }

    queryInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        search();
      }
    });

    SV_.render([
      SV_.el("h2", { text: "유사 의미 검색" }),
      SV_.card([
        SV_.el("div", { class: "row wrap" }, [queryInput, modeSelect, SV_.button("검색", search, "primary")]),
      ]),
      resultBox,
      onlineBox,
    ]);
    queryInput.focus();
  };

  function renderEntry(entry) {
    const lines = [
      SV_.el("div", { class: "entry-head" }, [
        SV_.el("strong", { text: entry.word }),
        SV_.el("span", { class: "tag", text: SV_.posLabel(entry.pos) }),
        entry.custom ? SV_.el("span", { class: "tag soft", text: "직접 추가" }) : null,
      ].filter(Boolean)),
      SV_.el("div", { text: entry.meanings.join(", ") }),
    ];
    if (entry.synonyms.length) {
      lines.push(SV_.el("div", { class: "muted", text: `유의어: ${entry.synonyms.join(", ")}` }));
    } else {
      lines.push(SV_.el("div", { class: "muted", text: "유의어 없음" }));
    }
    if (entry.example) {
      lines.push(SV_.el("div", { class: "example", text: `예문: ${entry.example}` }));
    }
    return SV_.el("article", { class: "card entry" }, lines);
  }

  // ----- 보고서 -----

  SV_.pages.report = async function () {
    const meta = SV_.state.meta;
    const periodSelect = SV_.el("select", { id: "report-period" },
      meta.period_options.map((item) => SV_.el("option", { value: item, text: item })));
    const startInput = SV_.el("input", { type: "date", id: "report-start" });
    const endInput = SV_.el("input", { type: "date", id: "report-end" });
    const customBox = SV_.el("div", { class: "row wrap" }, [startInput, " ~ ", endInput]);
    customBox.hidden = true;
    const body = SV_.el("div", { class: "report-body" });

    periodSelect.addEventListener("change", () => {
      customBox.hidden = periodSelect.value !== "기간 선택";
      load();
    });
    startInput.addEventListener("change", load);
    endInput.addEventListener("change", load);

    async function load() {
      const extra = { period: periodSelect.value };
      if (periodSelect.value === "기간 선택") {
        if (!startInput.value || !endInput.value) {
          body.replaceChildren(SV_.el("p", { class: "muted", text: "시작일과 끝일을 고르세요." }));
          return;
        }
        extra.start = startInput.value;
        extra.end = endInput.value;
      }
      try {
        const report = await SV_.api(`/api/report?${SV_.query(extra)}`);
        body.replaceChildren(...renderReport(report));
      } catch (error) {
        body.replaceChildren(SV_.el("p", { class: "error", text: error.message }));
      }
    }

    SV_.render([
      SV_.el("h2", { text: "보고서" }),
      SV_.card([
        SV_.el("div", { class: "row wrap" }, [
          SV_.el("label", { text: "기간" }), periodSelect,
          SV_.el("a", {
            class: "btn ghost",
            href: `api/history/export?${SV_.query()}`,
            text: "이력 CSV 내려받기",
          }),
        ]),
        customBox,
      ]),
      body,
    ]);
    load();
  };

  function renderReport(report) {
    const pct = (value) => (value === null || value === undefined ? "-" : `${Math.round(value * 100)}%`);
    const cards = SV_.el("div", { class: "stat-grid" }, [
      statCard("과제 완수율", pct(report.completion_rate)),
      statCard("암기한 단어", `${report.memorized}개`),
      statCard("시험 정답률", pct(report.accuracy)),
      statCard("시험 문항 수", `${report.test_total}문항`),
    ]);
    const maxRate = 1;
    const bars = SV_.el("div", { class: "bars" }, report.daily.map((day) => {
      const height = day.rate === null ? 0 : Math.round((day.rate / maxRate) * 100);
      return SV_.el("div", { class: "bar-col", title: day.rate === null ? "시험 없음" : pct(day.rate) }, [
        SV_.el("div", { class: "bar", style: `height:${height}%` }),
        SV_.el("div", { class: "bar-label", text: day.label }),
      ]);
    }));
    // 표는 좁은 화면에서 칸 안에서만 가로 스크롤되도록 한 겹 감싼다.
    const wrongTable = report.top_wrong.length
      ? SV_.el("div", { class: "table-scroll" }, [
        SV_.el("table", { class: "table" }, [
          SV_.el("thead", {}, [SV_.el("tr", {}, ["단어", "출제", "오답", "오답률"].map((text) => SV_.el("th", { text })))]),
          SV_.el("tbody", {}, report.top_wrong.map((row) => SV_.el("tr", {}, [
            SV_.el("td", { text: row.word }),
            SV_.el("td", { text: String(row.asked) }),
            SV_.el("td", { text: String(row.wrong) }),
            SV_.el("td", { text: pct(row.rate) }),
          ]))),
        ]),
      ])
      : SV_.el("p", { class: "muted", text: "오답 기록이 없습니다." });

    return [
      cards,
      SV_.card([SV_.el("h3", { text: "회차별 정답률 (최근 20회)" }), runBars(report.runs)]),
      SV_.card([SV_.el("h3", { text: "최근 14일 시험 정답률" }), bars]),
      SV_.card([SV_.el("h3", { text: "오답이 많은 단어" }), wrongTable]),
    ];
  }

  // 회차(시험 한 번)별 정답률 막대. 회차 번호는 시험을 치른 순서다 (VOCA-FR-032).
  function runBars(runs) {
    if (!runs.length) {
      return SV_.el("p", { class: "muted", text: "아직 치른 시험이 없습니다." });
    }
    return SV_.el("div", { class: "bars" }, runs.map((run) => {
      const height = run.rate === null ? 0 : Math.round(run.rate * 100);
      return SV_.el("div", { class: "bar-col", title: `${run.label} · ${run.at} · ${run.rate === null ? "-" : pct(run.rate)}` }, [
        SV_.el("div", { class: "bar", style: `height:${height}%` }),
        SV_.el("div", { class: "bar-label", text: run.label }),
      ]);
    }));
  }

  function statCard(label, value) {
    return SV_.el("div", { class: "stat" }, [
      SV_.el("div", { class: "stat-label", text: label }),
      SV_.el("div", { class: "stat-value", text: value }),
    ]);
  }

  // ----- 옵션 -----

  SV_.pages.options = function () {
    const meta = SV_.state.meta;
    const settings = SV_.state.settings;
    const themeSelect = SV_.el("select", { id: "opt-theme" },
      meta.themes.map((item) => SV_.el("option", { value: item, text: item })));
    themeSelect.value = settings.theme;
    const fontInput = SV_.el("input", { type: "range", id: "opt-font", min: "9", max: "16", value: String(settings.font_size) });
    const fontLabel = SV_.el("span", { text: `${settings.font_size}px` });
    fontInput.addEventListener("input", () => { fontLabel.textContent = `${fontInput.value}px`; });
    const memorizeSelect = SV_.el("select", { id: "opt-memo-dir" }, [
      SV_.el("option", { value: "영어→한글", text: "영어 → 한글" }),
      SV_.el("option", { value: "한글→영어", text: "한글 → 영어" }),
    ]);
    memorizeSelect.value = settings.memorize_direction;
    const onlineCheck = SV_.el("input", { type: "checkbox", id: "opt-online", checked: settings.online_lookup_enabled || null });
    const keyInput = SV_.el("input", {
      type: "password",
      id: "opt-key",
      placeholder: settings.krdict_api_key_set ? "저장되어 있음 (바꾸려면 새로 입력)" : "인증키를 입력하세요",
      autocomplete: "off",
    });
    const message = SV_.el("p", { class: "notice", "aria-live": "polite" });

    async function save() {
      const body = {
        theme: themeSelect.value,
        font_size: Number(fontInput.value),
        memorize_direction: memorizeSelect.value,
        online_lookup_enabled: onlineCheck.checked,
      };
      if (keyInput.value.trim()) {
        body.krdict_api_key = keyInput.value.trim();
      }
      try {
        await SV_.api("/api/settings", { method: "PUT", body });
        SV_.applySettings(await SV_.api("/api/settings"));
        message.className = "notice ok";
        message.textContent = "옵션을 저장했습니다.";
        keyInput.value = "";
      } catch (error) {
        message.className = "notice error";
        message.textContent = error.message;
      }
    }

    async function clearKey() {
      if (!window.confirm("저장된 온라인 검색 인증키를 지울까요?")) {
        return;
      }
      try {
        await SV_.api("/api/settings", { method: "PUT", body: { krdict_api_key: "" } });
        SV_.applySettings(await SV_.api("/api/settings"));
        SV_.toast("인증키를 지웠습니다.");
        SV_.pages.options();
      } catch (error) {
        SV_.fail(error);
      }
    }

    SV_.render([
      SV_.el("h2", { text: "옵션" }),
      SV_.card([
        SV_.el("div", { class: "form-row" }, [SV_.el("label", { text: "화면 테마" }), themeSelect]),
        SV_.el("div", { class: "form-row" }, [SV_.el("label", { text: "글꼴 크기" }), SV_.el("div", { class: "row" }, [fontInput, fontLabel])]),
        SV_.el("div", { class: "form-row" }, [SV_.el("label", { text: "암기 방향" }), memorizeSelect]),
        SV_.el("div", { class: "form-row" }, [SV_.el("label", { text: "온라인 검색" }), SV_.el("label", { class: "check" }, [onlineCheck, " 한글 검색 때 영어 번역 보조 검색 사용"])]),
        SV_.el("div", { class: "form-row" }, [SV_.el("label", { text: "검색 인증키" }), keyInput]),
        SV_.el("p", { class: "muted", text: "인증키는 이 PC의 설정 파일에만 저장되며 화면에 다시 표시되지 않습니다." }),
        message,
        SV_.el("div", { class: "row end" }, [
          SV_.button("인증키 지우기", clearKey, "danger ghost"),
          SV_.button("저장", save, "primary"),
        ]),
      ]),
    ]);
  };
})();
