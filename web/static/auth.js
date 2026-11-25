// 2026-11-26 - 클로드 스마트 보카 - 웹 화면: 로그인과 새 계정 만들기 (비밀번호는 서버에서 해시로 저장)
// 파일 위치: web/static/auth.js

"use strict";

(function () {
  const SV_ = window.SV;

  function field(labelText, input) {
    return SV_.el("div", { class: "form-row" }, [SV_.el("label", { text: labelText }), input]);
  }

  SV_.pages.login = function () {
    const nameInput = SV_.el("input", {
      type: "text", id: "login-name", autocomplete: "username",
      placeholder: "사용자명 (영문·숫자·한글 1~20자)",
    });
    const passwordInput = SV_.el("input", {
      type: "password", id: "login-password", autocomplete: "current-password",
      placeholder: "비밀번호 (새 계정은 8자 이상)",
    });
    const message = SV_.el("p", { class: "notice", "aria-live": "polite" });

    async function submit(path) {
      try {
        const data = await SV_.api(path, {
          method: "POST",
          body: { username: nameInput.value.trim(), password: passwordInput.value },
        });
        passwordInput.value = "";
        SV_.afterLogin(data);
      } catch (error) {
        message.className = "notice error";
        message.textContent = error.message;
      }
    }

    passwordInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        submit("/api/auth/login");
      }
    });

    SV_.render([
      SV_.el("h2", { text: "로그인" }),
      SV_.card([
        SV_.el("p", {
          class: "muted",
          text: "처음이면 '새 계정 만들기'로 가입합니다. 비밀번호가 없던 기존 계정은 같은 이름으로 '새 계정 만들기'를 누르면 비밀번호를 정할 수 있습니다.",
        }),
        field("사용자명", nameInput),
        field("비밀번호", passwordInput),
        message,
        SV_.el("div", { class: "row end" }, [
          SV_.button("새 계정 만들기", () => submit("/api/auth/register"), "ghost"),
          SV_.button("로그인", () => submit("/api/auth/login"), "primary"),
        ]),
      ]),
    ]);
    nameInput.focus();
  };
})();
