# -*- coding: utf-8 -*-
"""Икона на Price_Data_Tool — генерира се с код, за да е възпроизводима.

Дизайн: тъмен заоблен квадрат (фонът на интерфейса) + три свещи
(зелена/червена/зелена) с фитили. Казва „ценови данни" от пръв поглед
и се чете дори на 16×16 в лентата на задачите.

    python make_icon.py   →  icon.ico (16..256px) + icon_preview.png
"""
import sys
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")

S = 256                                   # майстор-размер
BG = (16, 20, 29, 255)                    # фонът на интерфейса (#10141D)
BORDER = (38, 200, 138, 255)              # зелен акцент
GREEN = (38, 166, 154, 255)               # #26A69A — свещите на TradingView
RED = (239, 83, 80, 255)                  # #EF5350
WICK_G = (100, 220, 200, 255)
WICK_R = (255, 140, 138, 255)

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# заоблен фон с тънка зелена рамка
d.rounded_rectangle([4, 4, S - 4, S - 4], radius=48, fill=BG,
                    outline=BORDER, width=6)

# три свещи: (x-център, връх на фитила, връх на тялото, дъно на тялото,
#             дъно на фитила, цвят, цвят на фитила)
W = 40                                    # ширина на тялото
candles = [
    (68,  150, 170, 215, 228, GREEN, WICK_G),   # ниска зелена
    (128,  55,  75, 150, 165, RED,   WICK_R),   # висока червена
    (188,  35,  60, 130, 145, GREEN, WICK_G),   # най-висока зелена
]
for cx, wt, bt, bb, wb, col, wcol in candles:
    d.line([(cx, wt), (cx, wb)], fill=wcol, width=8)          # фитил
    d.rounded_rectangle([cx - W // 2, bt, cx + W // 2, bb],   # тяло
                        radius=8, fill=col)

# запис: .ico с всички размери + голям преглед
img.save("icon.ico", sizes=[(16, 16), (24, 24), (32, 32),
                            (48, 48), (64, 64), (128, 128), (256, 256)])
img.save("icon_preview.png")
print("icon.ico + icon_preview.png записани")
