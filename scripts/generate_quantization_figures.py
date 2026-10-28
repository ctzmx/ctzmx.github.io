"""Generate the four original diagrams for the INT8 quantization introduction.

Run with Python 3.10+; only the standard library is required.
Numeric axes use coordinates calculated from the stated values. The parameter
sharing diagram is schematic and does not encode weight magnitudes.
"""

from html import escape
from pathlib import Path


OUT = Path(__file__).resolve().parents[1] / "img/posts/quant-int8"
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
            f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="{height}" '
            f'viewBox="0 0 720 {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title>',
            f'<desc id="desc">{escape(description)}</desc>',
            '<defs><marker id="arrow" markerWidth="10" markerHeight="10" '
            'refX="9" refY="5" orient="auto-start-reverse" markerUnits="userSpaceOnUse">'
            '<path d="M0,0 L10,5 L0,10 Z" fill="context-stroke"/></marker></defs>',
            '<style>text{font-family:"Microsoft YaHei","Noto Sans CJK SC",'
            '"PingFang SC",sans-serif;font-variant-numeric:tabular-nums}</style>',
            f'<rect width="720" height="{height}" rx="18" fill="#f7f9fc"/>',
        ]
        self.text(36, 52, title, 32, INK, weight=700)

    def text(self, x, y, value, size=27, color=INK, anchor="start", weight=400):
        self.parts.append(
            f'<text x="{x:g}" y="{y:g}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{escape(str(value))}</text>'
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

    def path(self, path, color, width=3, arrow=False):
        extra = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}"{extra}/>'
        )

    def save(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / name).write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def affine_grid():
    fig = Figure(732, "同样的间距，不同的零点", "两图均为零附近的局部放大，scale=0.02。"
                 "上图 INT8 的 zero_point=0，实数零用编码0表示，完整范围为[-2.56,2.54]；"
                 "下图 UINT8 的 zero_point=50，实数零用编码50表示，完整范围为[-1,4.1]。")
    fig.text(36, 96, "局部放大：相邻实数格点都相差 0.02", 26, MUTED)
    pos = lambda value: 180 + (value + 0.04) / 0.08 * 460
    for top, name, zero, color, full_range in [
        (126, "INT8", 0, BLUE, "[-2.56, 2.54]"),
        (390, "UINT8", 50, TEAL, "[-1.00, 4.10]"),
    ]:
        fig.rect(24, top, 672, 244, "#ffffff", radius=12)
        fig.text(44, top + 40, f"{name}    scale = 0.02    zero_point = {zero}", 27, color, weight=700)
        fig.rect(pos(0) - 20, top + 55, 40, 142, "#edf0ff" if zero == 0 else "#e2f5ee", radius=8)
        fig.text(44, top + 105, "编码 q", 26, MUTED)
        fig.text(44, top + 166, "实数 x̂", 26, MUTED)
        fig.line(160, top + 97, 657, top + 97)
        fig.line(160, top + 159, 657, top + 159)
        for offset in range(-2, 3):
            real = offset * 0.02
            x = pos(real)
            fig.line(x, top + 105, x, top + 150, color if offset == 0 else LINE, 2, "4 4", True)
            fig.dot(x, top + 97, color, 5)
            fig.dot(x, top + 159, color, 5)
            fig.text(x, top + 79, zero + offset, 28, color, "middle", 700)
            fig.text(x, top + 196, "0" if offset == 0 else f"{real:.2f}", 27, color, "middle")
        fig.text(44, top + 230, f"完整解码范围：{full_range}", 26, MUTED)
    fig.text(36, 678, "zero_point = 50：用整数 50 编码实数 0", 27, weight=700)
    fig.text(36, 714, "它移动编码中的零点位置，不改变格点间距。", 26, MUTED)
    fig.save("affine-grid.svg")


def rounding_clipping():
    fig = Figure(772, "舍入与裁剪，是两种不同的误差", "scale=0.125，zero_point=0，编码范围[-127,127]。"
                 "上图局部实数轴[0,0.375]：0.0625舍入为0，0.3125舍入为0.25，平局取偶数编码。"
                 "下图实数轴[-20,20]：±20被裁剪到±15.875，绝对误差4.125，输出仍有限。")
    fig.text(36, 96, "scale = 0.125，zero_point = 0", 27, MUTED)
    fig.rect(24, 123, 672, 318, "#ffffff", radius=12)
    fig.text(44, 163, "范围内：舍入到最近格点", 28, BLUE, weight=700)
    fig.text(44, 201, "中点平局 → 选偶数编码 q", 26, MUTED)
    pos = lambda value: 90 + value / 0.375 * 540
    axis = 298
    fig.line(70, axis, 650, axis)
    for q in range(4):
        value = q * 0.125
        x = pos(value)
        fig.dot(x, axis, BLUE, 7)
        fig.text(x, axis + 42, f"{value:g}", 28, BLUE, "middle", 700)
        fig.text(x, axis + 81, f"q = {q}", 26, MUTED, "middle")
    for source, target in [(0.0625, 0), (0.3125, 0.25)]:
        start, end = pos(source), pos(target)
        fig.text(start, 245, f"{source:g}", 26, AMBER, "middle", 700)
        fig.path(f"M{start},286 L{start},260 L{end},260 L{end},283", AMBER, arrow=True)
        fig.dot(start, axis, AMBER, 7, hollow=True)
    fig.text(44, 420, "两次误差均为 0.0625 = scale / 2", 27, MUTED)
    fig.rect(24, 463, 672, 285, "#ffffff", radius=12)
    fig.text(44, 503, "范围外：裁剪到端点，仍然有限", 28, TEAL, weight=700)
    fig.text(44, 541, "对称编码 q ∈ [-127, 127]", 26, MUTED)
    pos = lambda value: 55 + (value + 20) / 40 * 610
    axis = 623
    fig.rect(pos(-15.875), axis - 20, pos(15.875) - pos(-15.875), 40, "#e2f5ee", radius=7)
    fig.line(pos(-20), axis, pos(20), axis)
    for source, target in [(-20, -15.875), (20, 15.875)]:
        start, end = pos(source), pos(target)
        fig.line(start, axis, end, axis, AMBER, 3, arrow=True)
        fig.dot(start, axis, AMBER, 7, hollow=True)
        fig.dot(end, axis, TEAL, 7)
        fig.text(start, 669, f"{source:g}", 27, AMBER, "middle", 700)
        fig.text(end, 589, f"{target:g}", 27, TEAL, "middle", 700)
    fig.text(360, 632, "解码范围", 26, TEAL, "middle")
    fig.text(44, 718, "裁剪误差 4.125，已大于 scale / 2", 27, AMBER, weight=700)
    fig.save("rounding-clipping.svg")


def range_resolution():
    fig = Figure(760, "同一局部范围，网格间距相差 32 倍", "两图都使用完全相同的实数横轴[-1,1]，"
                 "对称INT8编码均为[-127,127]。A=32时scale=32/127，局部窗口内有7个解码值；"
                 "A=1时scale=1/127，局部窗口内有255个解码值。间距缩小32倍，窗口内点数比不必正好32。"
                 "完整解码范围分别为[-32,32]与[-1,1]，输入32在第二种方案中会裁剪为1。")
    fig.text(36, 96, "同为 INT8；彩色竖线 = 一个可表示值", 26, MUTED)
    pos = lambda value: 80 + (value + 1) / 2 * 560
    for top, bound, color in [(123, 32, BLUE), (384, 1, TEAL)]:
        scale = bound / 127
        fig.rect(24, top, 672, 241, "#ffffff", radius=12)
        approximate = "0.2520" if bound == 32 else "0.007874"
        fig.text(44, top + 40, f"A = {bound}    scale ≈ {approximate}", 28, color, weight=700)
        outcome = "32 可保留" if bound == 32 else "32 被裁剪到 1"
        fig.text(44, top + 79, f"完整范围 [-{bound}, {bound}]；{outcome}", 26, MUTED)
        y = top + 135
        fig.line(80, y, 640, y, LINE)
        for value in [-1, 0, 1]:
            fig.line(pos(value), y - 22, pos(value), y + 24, LINE, 2)
            fig.text(pos(value), y + 66, value, 28, MUTED, "middle")
        for q in range(-127, 128):
            value = q * scale
            if -1 <= value <= 1:
                fig.line(pos(value), y - 12, pos(value), y + 12, color, 3 if bound == 32 else 1.5)
        fig.text(360, top + 230, "相同观察窗口：[-1, 1]", 26, MUTED, "middle")
    fig.rect(24, 646, 672, 91, "#ffffff", radius=12)
    fig.text(44, 682, "更细的网格，伴随更窄的覆盖范围", 28, weight=700)
    fig.text(44, 719, "离群值是否重要，仍要用模型任务评测判断。", 26, MUTED)
    fig.save("range-resolution.svg")


def parameter_granularity():
    fig = Figure(1178, "量化粒度：哪些权重共用参数？", "三图均为同一个4行8列权重矩阵，"
                 "每行代表一个输出通道，每格代表一个权重，未表示权重数值或大小。"
                 "per-tensor全张量共用一套参数；per-channel按行使用4套参数；"
                 "per-group沿每行每4个权重分组，使用8套参数。颜色和s,z编号同时标记参数共享。")
    fig.text(36, 96, "示例：4 行 × 8 列；每行是一个输出通道", 26, MUTED)
    fig.text(36, 134, "每格一个权重；同色共用一套 (s, z)", 26, MUTED)
    colors = [BLUE, TEAL, AMBER, PURPLE, "#a33f6c", "#536b2d", "#397089", "#8a553e"]
    fills = ["#e7eeff", "#dff3ef", "#fff0d9", "#eee7fa", "#fbe7ef", "#edf3dc", "#e1f0f7", "#f4e8df"]
    for top, kind, count, description in [
        (160, "per-tensor", 1, "整个张量共用一套参数"),
        (474, "per-channel", 4, "按行划分：每个输出通道一套参数"),
        (788, "per-group", 8, "沿行分组：每 4 个元素一套参数"),
    ]:
        fig.rect(24, top, 672, 293, "#ffffff", radius=12)
        fig.text(44, top + 39, kind, 29, weight=700)
        fig.text(676, top + 39, f"{count} 套参数", 27, MUTED, "end")
        x0, y0, cell_w, cell_h = 146, top + 65, 64, 40
        for row in range(4):
            fig.text(44, y0 + row * cell_h + 29, f"行 {row + 1}", 26, MUTED)
            for col in range(8):
                group = 0 if count == 1 else row if count == 4 else 2 * row + col // 4
                fig.rect(x0 + col * cell_w, y0 + row * cell_h, cell_w, cell_h,
                         fills[group], "#ffffff", 3)
        groups = [(0, 0, 8, 4)] if count == 1 else [
            (row, 0, 8, 1) for row in range(4)
        ] if count == 4 else [
            (row, col, 4, 1) for row in range(4) for col in [0, 4]
        ]
        for group, (row, col, width, height) in enumerate(groups):
            x, y = x0 + col * cell_w, y0 + row * cell_h
            fig.rect(x + 1, y + 1, width * cell_w - 2, height * cell_h - 2,
                     "none", colors[group], 4)
            cx, cy = x + width * cell_w / 2, y + height * cell_h / 2
            # The small label covers only internal cell boundaries, not the
            # perimeter; the underlying 4-by-8 matrix still has 32 cells.
            fig.rect(cx - 48, cy - 16, 96, 32, fills[group], radius=4)
            fig.text(cx, cy + 9, f"s{group + 1}, z{group + 1}", 26, colors[group], "middle", 700)
        fig.text(44, top + 265, description, 27, MUTED)
    fig.text(36, 1123, "结构示意，不按数值比例；颜色不表示大小", 26, MUTED)
    fig.text(36, 1160, "s = scale，z = zero_point", 26, MUTED)
    fig.save("parameter-granularity.svg")


if __name__ == "__main__":
    for draw in [affine_grid, rounding_clipping, range_resolution, parameter_granularity]:
        draw()
    print(f"Generated 4 SVG diagrams in {OUT}")
