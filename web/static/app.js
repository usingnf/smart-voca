// 2026-11-26 - 클로드 스마트 보카 - 웹 화면 시작과 메뉴 이동 (해시 기준 라우팅, 로그인 확인, 로그인 전에는 메뉴 숨김)
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
    { key: "community", label: "◎  다른 계정 보기" },
    { key: "options", label: "⚙  옵션" },
    { key: "account", label: "◉  내 계정" },
  ];

  // 상단 표시줄: 로그인한 계정과 로그아웃 단추 (로그인 전에는 안내 문구만)
  SV_.updateWho = function () {
    const who = document.getElementById("who");
    if (SV_.state.username) {
      const label = SV_.state.isGuest ? "게스트 계정" : `${SV_.state.username} 로 로그인 중`;
      who.replaceChildren(
        SV_.el("span", { text: label }),
        SV_.button("로그아웃", () => SV_.logout(), "ghost"),
      );
    } else {
      who.textContent = "로그인이 필요합니다";
    }
    document.querySelector(".layout").classList.toggle("signed-out", !SV_.state.username);
  };

  // 로그인 성공 뒤: 계정 정보를 저장하고 암기 화면으로 간다.
  SV_.afterLogin = function (data) {
    SV_.state.username = data.username;
    SV_.state.isPublic = Boolean(data.is_public);
    SV_.state.isGuest = Boolean(data.is_guest);
    SV_.updateWho();
    location.hash = "#memorize";
  };

  // 로그아웃하거나 계정을 지운 뒤: 로그인 화면으로 간다.
  SV_.signedOut = function () {
    SV_.state.username = null;
    SV_.state.isPublic = false;
    SV_.state.isGuest = false;
    SV_.updateWho();
    location.hash = "#login";
  };

  SV_.logout = async function () {
    try {
      await SV_.api("/api/auth/logout", { method: "POST" });
    } catch (error) {
      // 쿠키를 지우는 데 실패해도 화면에서는 로그아웃 상태로 본다.
    }
    SV_.signedOut();
  };

  // 세션이 끝나면 (다른 탭에서 로그아웃하거나 키가 바뀐 경우) 로그인 화면으로 보낸다.
  SV_.onUnauthorized = function () {
    SV_.state.username = null;
    SV_.updateWho();
    location.hash = "#login";
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
    return location.hash.replace("#", "") || (SV_.state.username ? "memorize" : "login");
  }

  async function route() {
    // 이전 화면에서 등록한 키보드 동작 등을 먼저 정리한다.
    SV_.cleanup.splice(0).forEach((cleanupFn) => cleanupFn());
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    const page = currentPage();

    // 로그인 화면은 메뉴 없이 보여 준다. 이미 로그인했다면 암기 화면으로 보낸다.
    if (page === "login") {
      highlightMenu("");
      if (SV_.state.username) {
        location.hash = "#memorize";
        return;
      }
      SV_.pages.login();
      return;
    }
    // 로그인하지 않았으면 로그인 화면으로 보낸다 (명세서 3.22).
    if (!SV_.state.username) {
      location.hash = "#login";
      return;
    }

    highlightMenu(page);
    const handler = SV_.pages[page];
    if (!handler) {
      location.hash = "#memorize";
      return;
    }
    try {
      await handler();
    } catch (error) {
      SV_.fail(error);
    }
  }

  async function init() {
    const [meta, settings] = await Promise.all([SV_.api("/api/meta"), SV_.api("/api/settings")]);
    SV_.state.meta = meta;
    SV_.applySettings(settings);
    document.getElementById("footer").textContent =
      `데이터 폴더: ${meta.data_dir} · 단어 ${meta.word_count}개 · 이 PC에서만 접속할 수 있습니다`;
    buildMenu();

    // 화면을 열면 세션 쿠키로 로그인 상태를 확인한다. 로그인하지 않았으면 401이 와서 로그인 화면으로 간다.
    try {
      const me = await SV_.api("/api/auth/me");
      SV_.state.username = me.username;
      SV_.state.isPublic = Boolean(me.is_public);
      SV_.state.isGuest = Boolean(me.is_guest);
    } catch (error) {
      SV_.state.username = null;
    }
    SV_.updateWho();
    window.addEventListener("hashchange", route);
    if (!location.hash) {
      location.hash = SV_.state.username ? "#memorize" : "#login";
    }
    await route();
  }

  init().catch((error) => {
    document.getElementById("view").replaceChildren(
      SV_.el("p", { class: "error", text: `화면을 불러오지 못했습니다: ${error.message}` }),
    );
  });
})();
