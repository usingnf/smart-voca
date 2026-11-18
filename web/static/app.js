// 2026-11-18 - 클로드 스마트 보카 - 웹 화면 시작과 메뉴 이동 (해시 기준 라우팅, 계정 선택 확인)
// 파일 위치: web/static/app.js

"use strict";

(function () {
  const SV_ = window.SV;
  SV_.cleanup = [];

  const MENU = [
    { section: "학습" },
    { key: "memorize", label: "▣  암기" },
    { key: "test", label: "✎  시험" },
    { key: "assignment", label: "☑  과제" },
    { key: "search", label: "⌕  유사 의미 검색" },
    { section: "관리" },
    { key: "add", label: "＋  단어 추가" },
    { key: "report", label: "▤  보고서" },
    { key: "options", label: "⚙  옵션" },
    { key: "account", label: "◉  계정 관리" },
  ];

  SV_.updateWho = function () {
    const who = document.getElementById("who");
    who.textContent = SV_.state.username ? `사용 중인 계정: ${SV_.state.username}` : "계정을 선택하세요";
  };

  function buildMenu() {
    const menu = document.getElementById("menu");
    menu.replaceChildren(...MENU.map((item) => {
      if (item.section) {
        return SV_.el("div", { class: "menu-section", text: item.section });
      }
      return SV_.el("a", { class: "menu-item", href: `#${item.key}`, "data-page": item.key, text: item.label });
    }));
  }

  function highlightMenu(page) {
    document.querySelectorAll(".menu-item").forEach((link) => {
      link.classList.toggle("active", link.dataset.page === page);
    });
  }

  function currentPage() {
    return location.hash.replace("#", "") || (SV_.state.username ? "memorize" : "account");
  }

  async function route() {
    // 이전 화면에서 등록한 키보드 동작 등을 먼저 정리한다.
    SV_.cleanup.splice(0).forEach((cleanupFn) => cleanupFn());
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    const page = currentPage();
    highlightMenu(page);

    if (!SV_.state.username && page !== "account") {
      SV_.render([
        SV_.card([
          SV_.el("h2", { text: "계정을 먼저 선택하세요" }),
          SV_.el("p", { text: "기존 계정을 고르거나 새 계정을 만들면 학습 기록이 그 계정에 저장됩니다." }),
          SV_.el("div", { class: "row end" }, [SV_.button("계정 선택하러 가기", () => { location.hash = "#account"; }, "primary")]),
        ]),
      ]);
      return;
    }
    const handler = SV_.pages[page];
    if (!handler) {
      location.hash = SV_.state.username ? "#memorize" : "#account";
      return;
    }
    try {
      await handler();
    } catch (error) {
      SV_.fail(error);
    }
  }

  // 명세서 3.11: 마지막 계정을 기억하지 않는다. 화면을 새로 열면 계정을 다시 고른다.
  async function init() {
    const [meta, settings] = await Promise.all([SV_.api("/api/meta"), SV_.api("/api/settings")]);
    SV_.state.meta = meta;
    SV_.applySettings(settings);
    document.getElementById("footer").textContent =
      `데이터 폴더: ${meta.data_dir} · 단어 ${meta.word_count}개 · 이 PC에서만 접속할 수 있습니다`;
    buildMenu();
    SV_.updateWho();
    window.addEventListener("hashchange", route);
    if (!location.hash) {
      location.hash = SV_.state.username ? "#memorize" : "#account";
    }
    await route();
  }

  init().catch((error) => {
    document.getElementById("view").replaceChildren(
      SV_.el("p", { class: "error", text: `화면을 불러오지 못했습니다: ${error.message}` }),
    );
  });
})();
