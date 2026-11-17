"""Generate the BF16-to-FP16 chapter's two original SVG diagrams.

Run with Python 3.10+; only the standard library is required.
The shared Figure class keeps the same 440px display width as earlier chapters.
"""

from generate_precision_figures import AMBER, BLUE, INK, LINE, MUTED, TEAL, Figure


def conversion_boundary():
    fig = Figure(
        792,
        "转换边界：三个数不能混用",
        "最近偶数舍入、非饱和转换的正数边界。上方线性数轴从65472到65536。"
        "65504是FP16最大有限值，65520是舍入溢出阈值。65536只是将有效数精度"
        "保持不变、把指数范围继续延伸时的假想下一点，不是有限FP16值。"
        "下方单独列出BF16转换：65280转FP16保持65280，65536转为正无穷。"
        "FP32的65504若先存入BF16，会成为65536，再转FP16则溢出。",
    )
    fig.text(36, 96, "最近偶数舍入 · 非饱和转换 · 正数", 25, MUTED)

    fig.rect(24, 122, 672, 342, "#ffffff", radius=12)
    left, right, axis = 80, 620, 218
    pos = lambda value: left + (value - 65472) / 64 * (right - left)
    fig.line(left, axis, right, axis, LINE, 2)
    for value in [65472, 65504]:
        fig.dot(pos(value), axis, BLUE, 7)
    fig.line(pos(65520), axis - 29, pos(65520), axis + 18, AMBER, 3, "5 5")
    fig.dot(pos(65536), axis, MUTED, 7, hollow=True)

    for value, label, color in [
        (65504, "最大有限值", BLUE),
        (65520, "溢出阈值", AMBER),
        (65536, "假想下一点", MUTED),
    ]:
        fig.text(pos(value), 170, label, 25, color, "middle", 700)
    for value in [65472, 65504, 65520, 65536]:
        color = AMBER if value == 65520 else BLUE if value <= 65504 else MUTED
        fig.text(pos(value), 264, str(value), 27, color, "middle", 700)

    fig.text(44, 319, "65520 = (65504 + 65536) / 2", 27, INK)
    fig.text(44, 361, "65536 在此是假想下一点，非有限 FP16", 25, MUTED)
    fig.text(44, 403, "输入 ≥ 65520 → +Inf", 27, AMBER, weight=700)
    fig.text(44, 441, "Inf 不是数轴上的有限点", 25, MUTED)

    fig.rect(24, 488, 672, 204, "#ffffff", radius=12)
    fig.text(44, 528, "BF16 输入：相邻值直接转换", 28, weight=700)
    fig.text(56, 578, "65280  →  FP16 65280", 28, TEAL, weight=700)
    fig.text(56, 626, "65536  →  FP16 +Inf", 28, AMBER, weight=700)
    fig.text(44, 672, "这两行是转换示例，不是共享比例尺", 25, MUTED)

    fig.text(36, 738, "先存 BF16：65504 → 65536", 27, INK, weight=700)
    fig.text(36, 774, "再转 FP16：65536 → +Inf", 27, AMBER)
    fig.save("conversion-boundary.svg")


def overflow_path():
    fig = Figure(
        850,
        "溢出发生在输出写回时",
        "构造的点积再除以4的计算。输入x和权重W均为[256,256]，FP32点积为131072。"
        "左路先写回FP16得到Inf，再除以4仍为Inf。右路保留FP32输出，执行模型原有的"
        "除以4得到32768，此时写回FP16可精确保留。这里的缩放是模型原有运算，"
        "不能通过随意添加除法来保持模型等价。Inf继续参与运算还可能产生NaN。",
    )
    fig.text(36, 96, "x = [256, 256]，W = [256, 256]", 27, MUTED)
    fig.rect(36, 122, 648, 104, "#ffffff", radius=12)
    fig.text(360, 161, "FP16 输入：每个元素 256，均有限", 27, INK, "middle")
    fig.text(360, 204, "FP32 点积：256² + 256² = 131072", 27, BLUE, "middle", 700)

    fig.line(360, 226, 360, 253, MUTED)
    fig.line(192, 253, 528, 253, MUTED)
    for x in [192, 528]:
        fig.line(x, 253, x, 282, MUTED, arrow=True)

    def box(left, top, title, result, color, fill):
        fig.rect(left, top, 312, 106, fill, radius=12)
        fig.text(left + 156, top + 40, title, 26, color, "middle", 700)
        fig.text(left + 156, top + 82, result, 27, color, "middle")

    for left, color, fill, rows in [
        (36, AMBER, "#fff0d9", [
            ("先写回 FP16", "131072 → +Inf"),
            ("按模型原式 ÷ 4", "+Inf → +Inf"),
            ("继续写回 FP16", "仍然是 +Inf"),
        ]),
        (372, TEAL, "#dff3ef", [
            ("保留 FP32 输出", "131072（有限）"),
            ("按模型原式 ÷ 4", "131072 → 32768"),
            ("此时写回 FP16", "32768（有限）"),
        ]),
    ]:
        for i, (title, result) in enumerate(rows):
            top = 288 + i * 150
            box(left, top, title, result, color, fill)
            if i < len(rows) - 1:
                fig.line(left + 156, top + 106, left + 156, top + 144, color, arrow=True)

    fig.text(36, 748, "÷ 4 是模型原有运算，不能随意添加。", 26, MUTED)
    fig.text(36, 791, "左路的 Inf 再参与运算，可能产生 NaN。", 26, MUTED)
    fig.text(36, 830, "关键：在安全的数值范围内再写回 FP16。", 26, TEAL, weight=700)
    fig.save("overflow-path.svg")


if __name__ == "__main__":
    conversion_boundary()
    overflow_path()
    print("Generated conversion-boundary.svg and overflow-path.svg")
