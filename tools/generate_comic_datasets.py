#!/usr/bin/env python3
"""
Generate multi-comic test datasets for Youdao Dictionary Pen S7 Pro (03_comic_reader).
Follows the zero-config folder convention:
  - Each comic is a folder named after the comic title.
  - Files inside are numbered images (e.g., 001.png..120.png or 1.png..14.png).
  - The first numbered image is the cover.
Includes:
  1. 苍穹铁道纪行 (120 pages, 6 aspect ratios & resolutions: B5 portrait, HD portrait,
     16:9 wide spread, 21:9 ultrawide, 4:3 landscape, 1:1 square, 1:3.2 4-panel strip)
  2. 猫咪日记 (16 pages, daily manga with mixed portrait, square, and wide spreads)
  3. 星际远征队 (18 pages, landscape-heavy sci-fi comic with 16:9, 21:9, and 4:3 spreads)
  4. 四格学园祭 (14 pages, unpadded 1.png..14.png testing natural numeric sort + 4-panel strips)
  5. 深海幻境录 (12 pages, multi-resolution artwork & comic panels)
"""

import os
import json
import shutil
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMICS_ROOT = os.path.join(BASE_DIR, "examples", "03_comic_reader", "assets", "comics")


def get_font(size):
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


FONT_CACHE = {}


def font(size):
    if size not in FONT_CACHE:
        FONT_CACHE[size] = get_font(size)
    return FONT_CACHE[size]


PALETTES = [
    # (bg, panel_bg, accent, secondary, text_light, border_col)
    ((22, 27, 38), (33, 41, 58), (59, 130, 246), (245, 158, 11), (248, 250, 252), (96, 165, 250)),
    ((28, 24, 36), (44, 36, 58), (236, 72, 153), (56, 189, 248), (250, 245, 255), (244, 114, 182)),
    ((20, 32, 30), (30, 49, 46), (16, 185, 129), (250, 204, 21), (240, 253, 244), (52, 211, 153)),
    ((36, 26, 22), (56, 40, 34), (249, 115, 22), (56, 189, 248), (255, 247, 237), (251, 146, 60)),
    ((25, 25, 42), (38, 38, 66), (139, 92, 246), (34, 211, 238), (245, 243, 255), (167, 139, 250)),
    ((32, 22, 28), (52, 34, 45), (244, 63, 94), (163, 230, 53), (255, 241, 242), (251, 113, 133)),
]


def draw_manga_page(w, h, book_title, page_num, total_pages, ratio_tag, is_cover=False):
    pal = PALETTES[(page_num + len(book_title)) % len(PALETTES)]
    bg, panel_bg, accent, secondary, text_light, border_col = pal

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    # 1. Outer precision boundary frame (for verifying 0px pan clamping and seamless stitching)
    draw.rectangle([0, 0, w - 1, h - 1], outline=border_col, width=4)
    draw.rectangle([6, 6, w - 7, h - 7], outline=(60, 72, 96), width=2)

    # Corner target markers (24x24 L-brackets at all 4 corners)
    m = 22
    for cx, cy, dx, dy in [(0, 0, 1, 1), (w - 1, 0, -1, 1), (0, h - 1, 1, -1), (w - 1, h - 1, -1, -1)]:
        draw.line([(cx, cy), (cx + dx * m, cy)], fill=secondary, width=4)
        draw.line([(cx, cy), (cx, cy + dy * m)], fill=secondary, width=4)

    is_wide = w > h * 1.05
    is_strip = (w / float(h)) <= 0.45

    # 2. Draw manga panels according to aspect ratio
    pad = 16
    inner_w = w - pad * 2
    inner_h = h - pad * 2

    if is_cover:
        # Rich cover layout
        draw.rectangle([pad, pad, w - pad, h - pad], fill=panel_bg, outline=accent, width=3)
        # Decorative diagonal speed lines
        for step in range(0, inner_w + inner_h, 36):
            x0 = pad + min(inner_w, step)
            y0 = pad + max(0, step - inner_w)
            x1 = pad + max(0, step - inner_h)
            y1 = pad + min(inner_h, step)
            draw.line([(x0, y0), (x1, y1)], fill=(45, 55, 78), width=2)

        # Central emblem
        cx, cy = w // 2, int(h * 0.44)
        r = min(w, h) // 4
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent, outline=secondary, width=4)
        draw.ellipse([cx - int(r * 0.65), cy - int(r * 0.65), cx + int(r * 0.65), cy + int(r * 0.65)], fill=bg, outline=text_light, width=2)

        # Cover banner
        banner_h = max(64, int(h * 0.22))
        draw.rectangle([pad + 8, h - pad - banner_h, w - pad - 8, h - pad - 8], fill=(14, 18, 26), outline=secondary, width=2)
        draw.text((pad + 20, pad + 16), book_title, fill=text_light, font=font(max(22, min(40, w // 12))))
        draw.text((pad + 20, h - pad - banner_h + 10), f"COVER · P01/{total_pages}", fill=secondary, font=font(max(18, min(28, w // 18))))
        draw.text((pad + 20, h - pad - banner_h + 40), f"{w}x{h} · {ratio_tag}", fill=text_light, font=font(max(15, min(22, w // 22))))
    elif is_wide:
        # Wide spread: 3 horizontal cinematic panels
        col_w = (inner_w - 20) // 3
        for c in range(3):
            px0 = pad + c * (col_w + 10)
            py0 = pad
            px1 = px0 + col_w if c < 2 else (w - pad)
            py1 = h - pad
            draw.rectangle([px0, py0, px1, py1], fill=panel_bg, outline=accent if c == 1 else (71, 85, 105), width=3)
            # Comic horizon & action geometry inside panel
            mid_y = (py0 + py1) // 2 + (c - 1) * 24
            draw.line([(px0 + 6, mid_y), (px1 - 6, mid_y - 18)], fill=secondary, width=2)
            # Speech bubble
            bx0, by0 = px0 + 14, py0 + 14
            bx1, by1 = min(px1 - 14, bx0 + 120), min(py1 - 14, by0 + 48)
            draw.rectangle([bx0, by0, bx1, by1], fill=(15, 20, 28), outline=text_light, width=2)
            draw.text((bx0 + 10, by0 + 10), f"WIDE #{page_num}" if c == 0 else f"PANEL {c+1}", fill=text_light, font=font(16))

        # Big center badge showing WIDE orientation & exact resolution
        bw, bh = min(inner_w - 20, 420), min(inner_h - 20, 128)
        bx0 = (w - bw) // 2
        by0 = (h - bh) // 2
        draw.rectangle([bx0, by0, bx0 + bw, by0 + bh], fill=(12, 16, 24), outline=secondary, width=3)
        draw.text((bx0 + 18, by0 + 12), f"{book_title} · P{page_num:03d}", fill=text_light, font=font(24))
        draw.text((bx0 + 18, by0 + 50), f"横向宽幅 {w}x{h} ({ratio_tag})", fill=secondary, font=font(20))
        draw.text((bx0 + 18, by0 + 84), "单栏自适应 880px / 单页 1/1 (912px)", fill=border_col, font=font(16))
    elif is_strip:
        # 4-panel vertical strip (4-koma)
        panel_h = (inner_h - 30) // 4
        for r in range(4):
            py0 = pad + r * (panel_h + 10)
            py1 = py0 + panel_h if r < 3 else (h - pad)
            draw.rectangle([pad, py0, w - pad, py1], fill=panel_bg, outline=accent if r % 2 == 0 else secondary, width=3)
            draw.rectangle([pad + 10, py0 + 10, w - pad - 10, py0 + 52], fill=(14, 18, 26), outline=text_light, width=1)
            draw.text((pad + 18, py0 + 18), f"P{page_num:03d} · 第{r+1}格 ({w}x{h})", fill=text_light if r % 2 == 0 else secondary, font=font(16))
            # Character silhouette
            cx = w // 2 + (r % 2 * 2 - 1) * 24
            cy = (py0 + py1) // 2 + 18
            draw.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=accent, outline=text_light, width=2)
    else:
        # Standard portrait or square manga page: 3-tier manga panel layout
        top_h = int(inner_h * 0.34)
        mid_h = int(inner_h * 0.34)
        # Top panel
        draw.rectangle([pad, pad, w - pad, pad + top_h], fill=panel_bg, outline=accent, width=3)
        # Middle split panels
        mid_y0 = pad + top_h + 10
        mid_y1 = mid_y0 + mid_h
        split_x = pad + inner_w // 2
        draw.rectangle([pad, mid_y0, split_x - 5, mid_y1], fill=panel_bg, outline=(100, 116, 139), width=2)
        draw.rectangle([split_x + 5, mid_y0, w - pad, mid_y1], fill=panel_bg, outline=secondary, width=2)
        # Bottom panel
        bot_y0 = mid_y1 + 10
        draw.rectangle([pad, bot_y0, w - pad, h - pad], fill=panel_bg, outline=accent, width=3)

        # Page header & resolution stamp in top panel
        draw.rectangle([pad + 12, pad + 12, w - pad - 12, pad + min(top_h - 12, 118)], fill=(12, 16, 24), outline=secondary, width=2)
        draw.text((pad + 22, pad + 18), f"{book_title} · P{page_num:03d}/{total_pages}", fill=text_light, font=font(max(18, min(26, w // 22))))
        draw.text((pad + 22, pad + 54), f"竖向/方幅 {w}x{h} ({ratio_tag})", fill=secondary, font=font(max(16, min(22, w // 26))))

        # Center visual badge in middle panels
        draw.ellipse([pad + 24, mid_y0 + 20, split_x - 24, mid_y1 - 20], fill=accent, outline=text_light, width=2)
        draw.text((split_x + 18, mid_y0 + 28), f"#{page_num:03d}", fill=text_light, font=font(max(22, min(34, w // 16))))
        draw.text((split_x + 18, mid_y0 + 74), ratio_tag, fill=border_col, font=font(18))

        # Bottom panel speech bubble
        draw.rectangle([pad + 16, bot_y0 + 16, w - pad - 16, h - pad - 16], fill=(16, 21, 30), outline=border_col, width=2)
        draw.text((pad + 28, bot_y0 + 28), f"PAGE {page_num:03d} · {w}x{h}", fill=text_light, font=font(20))

    # Quantize to 16-color palette PNG for ultra-fast embedded decoding & small footprint
    return img.quantize(colors=16, method=Image.Quantize.FASTOCTREE)


def build_120_page_spec():
    """
    Generate 120 pages for '苍穹铁道纪行' with diverse aspect ratios and resolutions:
      - P001, P002: 600x848 (B5 Portrait)
      - P003: 960x540 (16:9 Wide Spread)
      - P004, P005: 720x1080 (2:3 HD Portrait)
      - P006: 1050x450 (21:9 Ultrawide Spread)
      - P007, P008: 600x600 (1:1 Square)
      - P009, P010: 320x1024 (4-Panel Vertical Strip)
      - P011: 800x600 (4:3 Landscape)
      - P012: 600x848 (B5 Portrait)
    Repeats with variations across 120 pages so every section (top, middle, bottom)
    tests all aspect ratios and resolutions!
    """
    pattern = [
        (600, 848, "B5竖漫"),
        (600, 848, "B5竖漫"),
        (960, 540, "16:9横跨页"),
        (720, 1080, "2:3高清竖图"),
        (720, 1080, "2:3高清竖图"),
        (1050, 450, "21:9超宽幅"),
        (600, 600, "1:1方漫"),
        (600, 600, "1:1方漫"),
        (320, 1024, "1:3四格长条"),
        (320, 1024, "1:3四格长条"),
        (800, 600, "4:3横幅"),
        (600, 848, "B5竖漫"),
    ]
    pages = []
    for i in range(120):
        w, h, tag = pattern[i % len(pattern)]
        pages.append((f"{i + 1:03d}.png", w, h, tag))
    return pages


def build_datasets():
    if os.path.exists(COMICS_ROOT):
        shutil.rmtree(COMICS_ROOT)
    os.makedirs(COMICS_ROOT, exist_ok=True)

    books_spec = [
        {
            "folder": "苍穹铁道纪行",
            "subtitle": "长篇 · 120页多比例",
            "pages": build_120_page_spec(),
        },
        {
            "folder": "猫咪日记",
            "subtitle": "日常 · 混排短篇",
            "pages": [
                ("01.png", 600, 848, "B5竖漫"),
                ("02.png", 600, 848, "B5竖漫"),
                ("03.png", 960, 540, "16:9横跨页"),
                ("04.png", 600, 848, "B5竖漫"),
                ("05.png", 600, 848, "B5竖漫"),
                ("06.png", 1050, 450, "21:9超宽幅"),
                ("07.png", 600, 600, "1:1方漫"),
                ("08.png", 600, 600, "1:1方漫"),
                ("09.png", 800, 600, "4:3横幅"),
                ("10.png", 600, 848, "B5竖漫"),
                ("11.png", 600, 848, "B5竖漫"),
                ("12.png", 960, 540, "16:9横跨页"),
                ("13.png", 320, 1024, "1:3四格长条"),
                ("14.png", 320, 1024, "1:3四格长条"),
                ("15.png", 600, 848, "B5竖漫"),
                ("16.png", 960, 540, "16:9终章跨页"),
            ],
        },
        {
            "folder": "星际远征队",
            "subtitle": "科幻 · 宽幅画卷",
            "pages": [
                ("01.png", 960, 540, "16:9横版封面"),
                ("02.png", 1050, 450, "21:9星舰全景"),
                ("03.png", 800, 600, "4:3舰桥分镜"),
                ("04.png", 600, 848, "B5人物特写"),
                ("05.png", 600, 848, "B5人物特写"),
                ("06.png", 960, 540, "16:9跃迁跨页"),
                ("07.png", 1050, 450, "21:9轨道展开"),
                ("08.png", 960, 540, "16:9星云全景"),
                ("09.png", 600, 600, "1:1雷达方图"),
                ("10.png", 600, 600, "1:1舱门方图"),
                ("11.png", 800, 600, "4:3登陆分镜"),
                ("12.png", 960, 540, "16:9基地跨页"),
                ("13.png", 720, 1080, "2:3机甲竖图"),
                ("14.png", 720, 1080, "2:3机甲竖图"),
                ("15.png", 1050, 450, "21:9舰队齐射"),
                ("16.png", 960, 540, "16:9决战跨页"),
                ("17.png", 800, 600, "4:3返航分镜"),
                ("18.png", 960, 540, "16:9尾声全景"),
            ],
        },
        {
            "folder": "四格学园祭",
            "subtitle": "校园 · 四格条漫",
            # Intentionally unpadded filenames (1.png..14.png) to verify natural numeric sort!
            "pages": [
                ("1.png", 320, 1024, "1:3四格封面"),
                ("2.png", 320, 1024, "1:3四格条漫"),
                ("3.png", 960, 540, "16:9舞台跨页"),
                ("4.png", 320, 1024, "1:3四格条漫"),
                ("5.png", 320, 1024, "1:3四格条漫"),
                ("6.png", 600, 600, "1:1社团方漫"),
                ("7.png", 600, 600, "1:1社团方漫"),
                ("8.png", 800, 600, "4:3合影横图"),
                ("9.png", 320, 1024, "1:3四格条漫"),
                ("10.png", 320, 1024, "1:3四格条漫"),
                ("11.png", 960, 540, "16:9篝火跨页"),
                ("12.png", 600, 848, "B5特写竖漫"),
                ("13.png", 600, 848, "B5特写竖漫"),
                ("14.png", 1050, 450, "21:9谢幕横幅"),
            ],
        },
        {
            "folder": "深海幻境录",
            "subtitle": "奇幻 · 多分辨率",
            "pages": [
                ("01.png", 480, 680, "紧凑竖图"),
                ("02.png", 480, 680, "紧凑竖图"),
                ("03.png", 880, 440, "2:1海沟全景"),
                ("04.png", 720, 1080, "2:3高清竖图"),
                ("05.png", 720, 1080, "2:3高清竖图"),
                ("06.png", 960, 540, "16:9遗迹跨页"),
                ("07.png", 500, 500, "1:1深潜方图"),
                ("08.png", 500, 500, "1:1深潜方图"),
                ("09.png", 1050, 450, "21:9巨鲸横幅"),
                ("10.png", 600, 848, "B5竖漫"),
                ("11.png", 600, 848, "B5竖漫"),
                ("12.png", 800, 600, "4:3浮出水面"),
            ],
        },
    ]

    catalog_index = []
    total_files = 0

    for book in books_spec:
        folder_name = book["folder"]
        book_dir = os.path.join(COMICS_ROOT, folder_name)
        os.makedirs(book_dir, exist_ok=True)
        total_p = len(book["pages"])
        page_entries = []

        for idx, (fname, w, h, tag) in enumerate(book["pages"]):
            page_num = idx + 1
            img = draw_manga_page(
                w, h, folder_name, page_num, total_p, tag, is_cover=(idx == 0)
            )
            out_path = os.path.join(book_dir, fname)
            img.save(out_path, format="PNG", optimize=True)
            total_files += 1
            page_entries.append({
                "file": fname,
                "imgW": w,
                "imgH": h,
                "tag": tag,
            })

        catalog_index.append({
            "folder": folder_name,
            "subtitle": book["subtitle"],
            "pages": page_entries,
        })

    catalog_path = os.path.join(COMICS_ROOT, "catalog.json")
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog_index, f, ensure_ascii=False, indent=2)

    print(f"[Done] Generated {len(books_spec)} comic folders ({total_files} total pages) in {COMICS_ROOT}")


if __name__ == "__main__":
    build_datasets()
