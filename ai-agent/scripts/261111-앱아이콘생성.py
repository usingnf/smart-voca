#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 클로드 스마트 보카 - 앱 아이콘(.ico) 생성 1회성 스크립트 (파란 둥근 사각형 + 펼친 책 + "A")
# 파일 위치: ai-agent/scripts/261111-앱아이콘생성.py

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_PATH = PROJECT_DIR / "src" / "assets" / "SmartVoca.ico"
PREVIEW_PATH = PROJECT_DIR / "src" / "assets" / "SmartVoca_preview.png"
FONT_PATH = Path("C:/Windows/Fonts/arialbd.ttf")
KOREAN_FONT_PATH = Path("C:/Windows/Fonts/malgunbd.ttf")

CANVAS = 1024
ICON_SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]

BG_TOP = (30, 111, 217)
BG_BOTTOM = (13, 60, 150)
PAGE_COLOR = (255, 255, 255)
PAGE_SHADE = (214, 230, 250)
ACCENT_COLOR = (255, 183, 77)
LETTER_COLOR = (13, 60, 150)


def draw_background(image):
    """위에서 아래로 짙어지는 그라데이션을 둥근 사각형 안에 채운다."""
    gradient = Image.new("RGBA", (CANVAS, CANVAS))
    gradient_draw = ImageDraw.Draw(gradient)
    for y in range(CANVAS):
        ratio = y / (CANVAS - 1)
        color = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * ratio) for i in range(3))
        gradient_draw.line([(0, y), (CANVAS, y)], fill=color + (255,))

    mask = Image.new("L", (CANVAS, CANVAS), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, CANVAS - 1, CANVAS - 1], radius=210, fill=255)
    image.paste(gradient, (0, 0), mask)


def draw_book(draw):
    """펼친 책: 왼쪽·오른쪽 페이지를 살짝 휘어진 사다리꼴로 그린다."""
    left_page = [(170, 330), (500, 390), (500, 760), (170, 700)]
    right_page = [(524, 390), (854, 330), (854, 700), (524, 760)]
    draw.polygon(left_page, fill=PAGE_COLOR)
    draw.polygon(right_page, fill=PAGE_SHADE)
    # 가운데 책등
    draw.rectangle([500, 390, 524, 760], fill=(200, 220, 245))
    # 페이지 줄
    for offset in (0, 46):
        draw.line([(574, 500 + offset), (794, 470 + offset)], fill=(150, 180, 220), width=14)


def draw_letter(draw):
    """왼쪽 페이지 위에 큰 영문자 A를 올린다. 단어 학습 앱임을 드러내는 요소."""
    font = ImageFont.truetype(str(FONT_PATH), 300)
    draw.text((345, 430), "A", font=font, fill=LETTER_COLOR, anchor="mm")


def draw_accent(draw):
    """오른쪽 위 주황색 점. 한글 뜻과 영단어를 잇는 '짝' 표시."""
    draw.ellipse([720, 150, 860, 290], fill=ACCENT_COLOR)
    font = ImageFont.truetype(str(KOREAN_FONT_PATH), 90)
    draw.text((790, 222), "가", font=font, fill=(255, 255, 255), anchor="mm")


def build_icon_image():
    image = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw_background(image)
    draw = ImageDraw.Draw(image)
    draw_book(draw)
    draw_letter(draw)
    draw_accent(draw)
    return image


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    master = build_icon_image()
    master.resize((512, 512), Image.LANCZOS).save(PREVIEW_PATH)
    master.save(OUTPUT_PATH, format="ICO", sizes=ICON_SIZES)
    print(f"저장: {OUTPUT_PATH}")
    print(f"미리보기: {PREVIEW_PATH}")


if __name__ == "__main__":
    main()
