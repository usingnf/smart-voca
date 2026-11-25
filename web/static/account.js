// 2026-11-26 - 클로드 스마트 보카 - 웹 화면: 내 계정(공개 설정, 기록 초기화, 계정 삭제)과 다른 계정 보기(공개 계정 진척 통계, 읽기 전용)
// 파일 위치: web/static/account.js

"use strict";

(function () {
  const SV_ = window.SV;

  function pct(value) {
    return value === null || value === undefined ? "-" : `${Math.round(value * 100)}%`;
  }

  // ----- 내 계정 -----

  SV_.pages.account = function () {
    const visibility = SV_.el("input", { type: "checkbox", id: "my-public" });
    visibility.checked = Boolean(SV_.state.isPublic);
    const message = SV_.el("p", { class: "notice", "aria-live": "polite" });

    async function changeVisibility() {
      try {
        const data = await SV_.api("/api/auth/visibility", { method: "PUT", body: { is_public: visibility.checked } });
        SV_.state.isPublic = data.is_public;
        message.className = "notice ok";
        message.textContent = data.is_public ? "다른 계정 보기에 공개합니다." : "비공개로 바꿨습니다.";
      } catch (error) {
        visibility.checked = !visibility.checked;
        SV_.fail(error);
      }
    }
    visibility.addEventListener("change", changeVisibility);

    async function resetRecords() {
      const name = SV_.state.username;
      if (!window.confirm(`'${name}' 계정의 오답률, 이력, 과제 기록을 모두 지울까요? 추가한 단어는 남습니다.`)) {
        return;
      }
      try {
        await SV_.api(`/api/users/${encodeURIComponent(name)}/reset`, { method: "POST" });
        SV_.toast("기록을 초기화했습니다.");
      } catch (error) {
        SV_.fail(error);
      }
    }

    async function removeAccount() {
      const name = SV_.state.username;
      const typed = window.prompt(`계정 '${name}'과 모든 기록을 삭제합니다. 되돌릴 수 없습니다.\n계정 이름을 그대로 입력하면 삭제합니다.`);
      if (typed !== name) {
        if (typed !== null) {
          SV_.toast("계정 이름이 맞지 않아 삭제하지 않았습니다.", "error");
        }
        return;
      }
      try {
        await SV_.api(`/api/users/${encodeURIComponent(name)}`, { method: "DELETE" });
        SV_.toast("계정을 삭제했습니다.");
        await SV_.logout();
      } catch (error) {
        SV_.fail(error);
      }
    }

    SV_.render([
      SV_.el("h2", { text: "내 계정" }),
      SV_.card([
        SV_.el("p", { text: `로그인한 계정: ${SV_.state.username}${SV_.state.isGuest ? " (게스트)" : ""}` }),
        SV_.state.isGuest
          ? SV_.el("p", { class: "muted", text: "게스트 계정은 공개할 수 없습니다. 로그아웃하면 다시 들어갈 수 없습니다." })
          : SV_.el("label", { class: "check" }, [visibility, " 다른 계정 보기에 공개 (이름과 진척 통계가 다른 사용자에게 보입니다)"]),
        message,
      ]),
      SV_.card([
        SV_.el("h3", { text: "기록과 계정" }),
        SV_.el("div", { class: "row" }, [
          SV_.button("기록 초기화", resetRecords, "ghost"),
          SV_.button("계정 삭제", removeAccount, "danger ghost"),
          SV_.button("로그아웃", () => SV_.logout(), "ghost"),
        ]),
      ]),
    ]);
  };

  // ----- 다른 계정 보기 (읽기 전용) -----

  function statCard(label, value) {
    return SV_.el("div", { class: "stat" }, [
      SV_.el("div", { class: "stat-label", text: label }),
      SV_.el("div", { class: "stat-value", text: value }),
    ]);
  }

  function statCards(item) {
    return SV_.el("div", { class: "stats" }, [
      statCard("현재 일차", item.day ? `${item.day}일차` : "-"),
      statCard("암기한 단어", `${item.memorized} / ${item.total}`),
      statCard("과제 완수율", pct(item.completion_rate)),
      statCard("시험 정답률", pct(item.test_accuracy)),
    ]);
  }

  function showDetail(key) {
    SV_.render(SV_.el("p", { class: "muted", text: "계정 정보를 불러오는 중입니다…" }));
    SV_.api(`/api/community/users/${encodeURIComponent(key)}`).then((item) => {
      SV_.render([
        SV_.el("h2", { text: `${item.username}${item.is_me ? " (나)" : ""}` }),
        SV_.card([
          statCards(item),
          SV_.el("p", { class: "muted", text: "읽기 전용입니다. 이 계정의 단어와 기록 목록은 보이지 않습니다." }),
        ]),
        SV_.el("div", { class: "row end" }, [SV_.button("목록으로", () => SV_.pages.community(), "ghost")]),
      ]);
    }).catch((error) => SV_.fail(error));
  }

  SV_.pages.community = async function () {
    SV_.render(SV_.el("p", { class: "muted", text: "공개 계정을 불러오는 중입니다…" }));
    try {
      const users = await SV_.api("/api/community/users");
      const head = ["계정", "일차", "암기 / 전체", "과제 완수율", "시험 정답률"];
      const rows = users.map((item) => SV_.el("tr", {}, [
        SV_.el("td", {}, [SV_.button(item.username + (item.is_me ? " (나)" : ""), () => showDetail(item.username), "ghost")]),
        SV_.el("td", { text: item.day ? `${item.day}일차` : "-" }),
        SV_.el("td", { text: `${item.memorized} / ${item.total}` }),
        SV_.el("td", { text: pct(item.completion_rate) }),
        SV_.el("td", { text: pct(item.test_accuracy) }),
      ]));
      const listing = users.length
        ? SV_.el("div", { class: "table-scroll" }, [
          SV_.el("table", { class: "table" }, [
            SV_.el("thead", {}, [SV_.el("tr", {}, head.map((text) => SV_.el("th", { text })))]),
            SV_.el("tbody", {}, rows),
          ]),
        ])
        : SV_.el("p", { class: "muted", text: "공개된 계정이 없습니다. 내 계정 화면에서 공개를 켜면 여기에 나옵니다." });
      SV_.render([
        SV_.el("h2", { text: "다른 계정 보기" }),
        SV_.el("p", { class: "muted", text: "공개를 켠 계정의 진척 통계만 보입니다. 읽기 전용입니다." }),
        SV_.card([listing]),
      ]);
    } catch (error) {
      SV_.fail(error);
    }
  };
})();
