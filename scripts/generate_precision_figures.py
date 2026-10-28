"""Generate the five original SVG diagrams used by the precision articles.

Run with Python 3.10+; only the standard library is required.
Coordinates on numeric axes are computed from the values being illustrated.
"""

from html import escape
from pathlib import Path


OUT = Path(__file__).resolve().parents[1] / "img/posts/numerical-precision"
# Keep diagram labels close to the article's 16px body text at desktop size.
DISPLAY_WIDTH = 440
INK = "#172b45"
MUTED = "#52657c"
LINE = "#a8b6c7"
BLUE = "#245bcc"
TEAL = "#087f78"
AMBER = "#a45908"
PURPLE = "#7551b5"


class Figure:
    def __init__(self, height, title, description):
        self.parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{DISPLAY_WIDTH}" '
            f'height="{height * DISPLAY_WIDTH / 720:g}" '
            f'viewBox="0 0 720 {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title>',
            f'<desc id="desc">{escape(description)}</desc>',
            '<defs><marker id="arrow" markerWidth="8" markerHeight="8" '
            'refX="7" refY="4" orient="auto-start-reverse" markerUnits="userSpaceOnUse">'
            '<path d="M0,0 L8,4 L0,8 Z" fill="context-stroke"/></marker></defs>',
            '<style>text{font-family:"Microsoft YaHei","Noto Sans CJK SC",'
            '"PingFang SC",sans-serif;font-variant-numeric:tabular-nums}</style>',
            f'<rect width="720" height="{height}" rx="18" fill="#f7f9fc"/>',
        ]
        self.text(36, 52, title, 32, INK, weight=700)

    def text(self, x, y, text, size=27, color=INK, anchor="start", weight=400):
        self.parts.append(
            f'<text x="{x:g}" y="{y:g}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{escape(text)}</text>'
        )

    def rect(self, x, y, width, height, fill, stroke="none", radius=0):
        self.parts.append(
            f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" '
            f'rx="{radius}" fill="{fill}" stroke="{stroke}"/>'
        )

    def line(self, x1, y1, x2, y2, color=LINE, width=2, dash=None, arrow=False):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        extra += ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(
            f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" '
            f'stroke="{color}" stroke-width="{width}"{extra}/>'
        )

    def dot(self, x, y, color=BLUE, radius=6, hollow=False):
        self.parts.append(
            f'<circle cx="{x:g}" cy="{y:g}" r="{radius}" '
            f'fill="{"white" if hollow else color}" stroke="{color}" stroke-width="3"/>'
        )

    def path(self, d, color, width=3, arrow=False):
        extra = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{extra}/>'
        )

    def save(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / name).write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def bit_layout():
    fig = Figure(730, "同一个 6.5，两种 16 位编码", "FP16 与 BF16 都精确表示 6.5。"
                 "FP16 为 0|10001|1010000000，BF16 为 0|10000001|1010000。"
                 "隐含的前导 1 不在存储位格中。")
    fig.text(36, 94, "每格 1 bit；两行都没有舍入误差", 26, MUTED)
    for x, color, label in [(36, AMBER, "符号"), (220, BLUE, "指数"), (404, TEAL, "小数")]:
        fig.rect(x, 119, 22, 22, color, radius=4)
        fig.text(x + 34, 139, label, 26)
    for y, name, fields, counts in [
        (218, "FP16", ["0", "10001", "1010000000"], [1, 5, 10]),
        (443, "BF16", ["0", "10000001", "1010000"], [1, 8, 7]),
    ]:
        fig.text(36, y - 28, name, 29, weight=700)
        fig.text(684, y - 28, " / ".join(map(str, counts)), 26, MUTED, "end")
        x = 40
        for bits, color, fill in zip(fields, [AMBER, BLUE, TEAL], ["#fff0d9", "#e7eeff", "#dff3ef"]):
            for bit in bits:
                fig.rect(x, y, 40, 52, fill, "#ffffff", 3)
                fig.text(x + 20, y + 36, bit, 28, color, "middle", 700)
                x += 40
        exp = "17 − 15 = 2" if name == "FP16" else "129 − 127 = 2"
        fig.text(40, y + 93, f"指数：{exp}", 27, BLUE)
        fig.text(40, y + 133, "小数：.101₂ = 0.625", 27, TEAL)
    fig.rect(36, 609, 648, 85, "#ffffff", radius=10)
    fig.text(56, 642, "隐含的 1 在位格外补上", 27, PURPLE, weight=700)
    fig.text(56, 679, "1.101₂ × 2² = 1.625 × 4 = 6.5", 28)
    fig.save("bit-layout.svg")


def spacing():
    fig = Figure(680, "同一数轴上，FP16 的刻度更密", "两个局部线性窗口。"
                 "1 到 1.015625 内 FP16 有 17 个点、BF16 有 3 个点；"
                 "1024 到 1040 内也分别有 17 个点和 3 个点。不同窗口的单位跨度不同。")
    fig.text(36, 94, "实心点 = 可表示值；空隙内并非都能表示", 25, MUTED)
    for top, title, ticks in [
        (122, "窗口 A：1 附近", ["1", "1.0078125", "1.015625"]),
        (382, "窗口 B：1024 附近", ["1024", "1032", "1040"]),
    ]:
        fig.rect(24, top, 672, 240, "#ffffff", radius=12)
        fig.text(44, top + 38, title, 28, weight=700)
        left, right = 152, 644
        for row, label, color, step in [(0, "FP16", BLUE, 1), (1, "BF16", TEAL, 8)]:
            y = top + 92 + row * 66
            fig.text(44, y + 9, label, 27, color, weight=700)
            fig.line(left, y, right, y)
            for i in range(0, 17, step):
                fig.dot(left + (right - left) * i / 16, y, color, 5 if row == 0 else 7)
        for i, label in enumerate(ticks):
            fig.text(left + (right - left) * i / 2, top + 205, label, 24, MUTED, "middle")
        fig.text(680, top + 38, f"间隔比 1 : 8", 25, MUTED, "end")
    fig.text(36, 661, "A 间隔：1/1024、1/128；B 间隔：1、8", 25, MUTED)
    fig.save("floating-point-spacing.svg")


def round_even():
    fig = Figure(486, "平局取偶数：有时向下，有时向上", "FP16 的 2048、2050、2052 可精确表示，"
                 "有效数末位依次为 0、1、0。2049 向 2048 舍入，2051 向 2052 舍入。")
    fig.text(36, 96, "此处间隔为 2；2049 与 2051 都在正中间", 25, MUTED)
    left, right, axis = 90, 630, 240
    pos = lambda value: left + (value - 2048) / 4 * (right - left)
    fig.line(left - 25, axis, right + 25, axis, MUTED, 2)
    for value in range(2048, 2053):
        is_mid = value % 2 == 1
        color = AMBER if is_mid else BLUE
        fig.dot(pos(value), axis, color, 8, hollow=is_mid)
        fig.text(pos(value), axis + 45, str(value), 28, color, "middle", 700)
        if not is_mid:
            last_bit = 1 if value == 2050 else 0
            fig.text(pos(value), axis + 91, f"末位 {last_bit}", 26, MUTED, "middle")
    for source, target, y in [(2049, 2048, 151), (2051, 2052, 151)]:
        fig.path(f"M{pos(source)},225 L{pos(source)},{y} L{pos(target)},{y} L{pos(target)},222", AMBER, arrow=True)
    fig.rect(36, 365, 648, 86, "#ffffff", radius=10)
    fig.text(56, 400, "“偶”看保留的二进制有效数末位", 27, weight=700)
    fig.text(56, 435, "末位为 0 的候选胜出；不是一律向下取整", 25, MUTED)
    fig.save("round-to-even.svg")


def subnormal():
    fig = Figure(652, "零附近，还有非正规数刻度", "令 h=2^-24。线性数轴上 1e-8 位于约 0.168h，"
                 "舍入至 0；1e-7 位于约 1.678h，舍入至 2h。h 本身精确保留。"
                 "最小正规数为 1024h，不在图中。")
    fig.text(36, 94, "h = 2⁻²⁴ ≈ 5.96046448 × 10⁻⁸", 27, MUTED)
    left, right, axis = 80, 640, 338
    pos = lambda value_h: left + value_h / 3 * (right - left)
    fig.rect(36, 122, 648, 116, "#ffffff", radius=10)
    fig.text(56, 163, "1e−8 ≈ 0.168h  →  0", 28, AMBER, weight=700)
    fig.text(56, 211, "1e−7 ≈ 1.678h  →  2h", 28, PURPLE, weight=700)
    fig.line(left - 20, axis, right + 20, axis, MUTED, 2)
    fig.line(pos(.5), axis - 55, pos(.5), axis + 27, LINE, 2, "5 5")
    fig.text(pos(.5), axis + 71, "h/2", 25, MUTED, "middle")
    for value, label in [(0, "0"), (1, "h"), (2, "2h"), (3, "3h")]:
        fig.dot(pos(value), axis, TEAL, 7)
        fig.text(pos(value), axis + 41, label, 28, TEAL, "middle", 700)
    h = 2 ** -24
    for value, target, color, arc_y in [(1e-8 / h, 0, AMBER, 273), (1e-7 / h, 2, PURPLE, 273)]:
        fig.dot(pos(value), axis, color, 7, hollow=True)
        fig.path(f"M{pos(value):g},323 L{pos(value):g},{arc_y} L{pos(target):g},{arc_y} L{pos(target):g},321", color, arrow=True)
    fig.text(36, 468, "h = 2⁻²⁴ 本身精确保留", 28, TEAL, weight=700)
    fig.text(36, 513, "最小正规数 = 1024h（当前窗口外）", 26, MUTED)
    fig.text(36, 572, "横轴为线性刻度，实心点可精确表示", 26, MUTED)
    fig.text(36, 614, "空心点为待转换输入，箭头为舍入方向", 26, MUTED)
    fig.save("subnormal-grid.svg")


def accumulation():
    fig = Figure(686, "连续加 100 次 1：在哪一步舍入？", "从 2048 开始，逐次舍入到 FP16 的结果一直为 2048；"
                 "FP32 累加与精确参考一致，为 2048+n，最终 2148 转成 FP16 仍为 2148。"
                 "这是逐次累加实验，不是 GPU 并行归约轨迹。")
    fig.text(36, 99, "起点 2048；横轴 n 表示已经相加的次数", 25, MUTED)
    left, right, top, bottom = 114, 632, 200, 460
    x = lambda n: left + n / 100 * (right - left)
    y = lambda value: bottom - (value - 2048) / 100 * (bottom - top)
    for n in range(0, 101, 20):
        fig.line(x(n), top, x(n), bottom, "#e0e6ee", 1)
        fig.text(x(n), bottom + 38, str(n), 25, MUTED, "middle")
    for value in [2048, 2098, 2148]:
        fig.line(left, y(value), right, y(value), "#dce3ed", 1)
        fig.text(left - 15, y(value) + 9, str(value), 25, MUTED, "end")
    fig.line(left, top - 10, left, bottom, MUTED)
    fig.line(left, bottom, right + 12, bottom, MUTED)
    fig.text(36, 165, "FP32 累加 = 精确参考", 27, TEAL, weight=700)
    fig.path("M" + " L".join(f"{x(n):g},{y(2048+n):g}" for n in range(101)), TEAL, 4)
    fig.line(left, bottom, right, bottom, BLUE, 4, "11 7")
    fig.text(380, 432, "每步 FP16：2048", 26, BLUE, weight=700)
    fig.dot(right, top, TEAL, 7)
    fig.text(right - 10, top + 40, "2148", 28, TEAL, "end", 700)
    fig.text(373, 537, "相加次数 n", 26, MUTED, "middle")
    fig.rect(36, 570, 648, 80, "#ffffff", radius=10)
    fig.text(56, 604, "只在最后转 FP16：2148 → 2148", 27, weight=700)
    fig.text(56, 638, "FP32 保留中间增量；本例终点可精确写回", 25, MUTED)
    fig.save("accumulation.svg")


if __name__ == "__main__":
    for draw in [bit_layout, spacing, round_even, subnormal, accumulation]:
        draw()
    print(f"Generated 5 SVG diagrams in {OUT}")
