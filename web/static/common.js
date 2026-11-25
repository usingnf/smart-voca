// 2026-11-18 - 클로드 스마트 보카 - 웹 화면 공통 도구 (API 호출, 요소 만들기, 알림, 테마)
// 파일 위치: web/static/common.js

"use strict";

window.SV = { state: { username: null, meta: null, settings: null }, pages: {} };

// 서버 API를 호출한다. 실패하면 서버가 준 한글 메시지로 Error를 던진다.
SV.api = async function (path, options = {}) {
  const init = { method: options.method || "GET", headers: {} };
  if (options.body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.body);
  }
  // 앞의 /를 떼어 현재 화면 주소 기준의 상대 주소로 보낸다.
  // 학교 서버는 앱을 /2026/voca-<학번>/ 아래로 옮기므로 /api/...로 보내면 서버 루트로 가 버린다.
  const relativePath = path.replace(/^\//, "");
  const response = await fetch(relativePath, init);
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (parseError) {
      data = text;
    }
  }
  if (!response.ok) {
    const detail = data && data.detail;
    let message = "요청을 처리하지 못했습니다.";
    if (typeof detail === "string") {
      message = detail;
    } else if (Array.isArray(detail)) {
      message = detail.map((item) => item.msg).join(" ");
    }
    throw new Error(message);
  }
  return data;
};

// 현재 계정을 포함한 쿼리 문자열을 만든다. extra는 {이름: 값} 객체다.
SV.query = function (extra = {}) {
  const params = new URLSearchParams({ username: SV.state.username || "" });
  for (const [key, value] of Object.entries(extra)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, value);
    }
  }
  return params.toString();
};

// 화면 요소를 만든다. text는 글자로만 넣으므로 사용자 입력이 HTML로 해석되지 않는다.
SV.el = function (tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined || value === false) {
      continue;
    }
    if (key === "text") {
      node.textContent = value;
    } else if (key === "class") {
      node.className = value;
    } else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2), value);
    } else {
      node.setAttribute(key, value === true ? "" : String(value));
    }
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined || child === false) {
      continue;
    }
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
};

SV.button = function (label, onClick, variant = "") {
  return SV.el("button", { type: "button", class: `btn ${variant}`.trim(), text: label, onclick: onClick });
};

SV.card = function (children, extraClass = "") {
  return SV.el("section", { class: `card ${extraClass}`.trim() }, children);
};

SV.toast = function (message, kind = "info") {
  const box = document.getElementById("toast");
  box.textContent = message;
  box.className = `toast show ${kind}`;
  clearTimeout(SV.toastTimer);
  SV.toastTimer = setTimeout(() => {
    box.className = "toast";
  }, 2800);
};

SV.fail = function (error) {
  SV.toast(error.message || "오류가 발생했습니다.", "error");
};

// 화면 본문을 비우고 새 내용을 넣는다.
SV.render = function (nodes) {
  const view = document.getElementById("view");
  view.replaceChildren(...[].concat(nodes));
  view.scrollTop = 0;
};

SV.isHangul = function (text) {
  return /[ㄱ-힝]/.test(text);
};

SV.posLabel = function (pos) {
  return (SV.state.meta && SV.state.meta.pos_labels[pos]) || pos;
};

// 설정의 테마와 글꼴 크기를 화면에 반영한다.
SV.applySettings = function (settings) {
  SV.state.settings = settings;
  document.documentElement.dataset.theme = settings.theme === "어둡게" ? "dark" : "light";
  document.documentElement.style.setProperty("--base-font", `${settings.font_size}px`);
};

// 입력 칸의 값을 목록으로 바꾼다 (쉼표 또는 줄바꿈으로 구분).
SV.splitList = function (text) {
  return text.split(/[,\n]/).map((item) => item.trim()).filter((item) => item.length > 0);
};

// 정답 설명에 쓰는 짧은 뜻 문자열
SV.meaningText = function (entry) {
  return entry.meanings.join(", ");
};
