---
title:      "深度学习数据精度（二）：浮点运算中的舍入、溢出与下溢"
subtitle:   "用小实验理解数值误差如何产生，以及存储、累加和输出格式为什么要分别检查"
date:       2026-10-28 23:23:35 +0800
permalink:  /2026/10/28/deep-learning-floating-point-errors/
tags:
    - Deep Learning
---

[上一篇](/2026/10/28/deep-learning-numerical-precision-basics/)介绍了浮点数的位分配与表示范围。这一篇继续回答：当这些数参与运算时，为什么加法可能“没有加上”，为什么改变相加顺序会改变结果，以及正常的输入怎样产生 `Inf` 或 `NaN`？

关键是区分三个环节：**输入在存储时可能已经舍入，运算中间结果可能再次舍入，输出写回另一种格式时还可能溢出。** 只看张量的 dtype，往往无法解释整条计算路径。

## 1. 实验约定：明确在哪一步舍入

本文实验已在 Windows x64、Python 3.12.14、NumPy 2.3.5 的 CPU 环境运行。它们用于观察数值表示与逐步舍入，不用于测量 GPU 性能，也不代表某个深度学习框架的全部算子行为。

将下面各个 Python 代码块按顺序放在同一个脚本或交互会话中运行。先导入 NumPy，并查看本机版本：

```python
import numpy as np

print("NumPy:", np.__version__)
```

实验采用通常的“舍入到最近值，平局取偶数”规则，显式指定每步结果的 dtype。`np.add(..., dtype=np.float16)` 表示这一步返回 FP16 结果，不意味着 CPU 内部一定使用原生 FP16 指令。类似地，Python 直接写 `2048 + 1` 得到的是整数 2049，不能用它代替 FP16 实验。

部分代码用 `np.errstate` 暂时关闭预期中的溢出、下溢或无效运算警告，以便集中观察数值。这不会修复异常，也不是实际训练中隐藏警告的建议。

## 2. 舍入：为什么 2048 加 1，结果还是 2048？

FP16 有 10 位小数。在 `[2048, 4096)`，即 `[2^11, 2^12)` 内，相邻可表示值的间隔是：

```text
Δ = 2^(11 - 10) = 2

可表示值：2048、2050、2052、2054……
```

1 本身可以被 FP16 精确表示，但 2049 不行。它位于 2048 和 2050 的正中间；平局取偶数规则选择保留的二进制有效数最低位为 0 的候选，因此得到 2048。这里的“偶”指二进制有效数的末位，不是直接判断两个十进制整数谁是偶数。

```python
a = np.float16(2048)
one = np.float16(1)

print("spacing:", float(np.spacing(a)))
print("2048 + 1:", float(np.add(a, one, dtype=np.float16)))
print("2048 + 3:", float(np.add(a, np.float16(3), dtype=np.float16)))
```

运行结果：

```text
spacing: 2.0
2048 + 1: 2048.0
2048 + 3: 2052.0
```

第二个加法也遇到平局：2051 位于 2050 和 2052 之间，这次向上舍入到 2052。舍入并不总是向下截断。

这个例子体现的是**小量在加法结果中被舍掉**，不是 1 本身太小而发生下溢。放到深度学习中，如果参数更新或残差相加的结果要保存为低精度，小增量也可能因为相对于当前数值间隔太小而消失。是否真的发生，要看更新与存储的实际格式；不能据此认定所有混合精度训练都会丢掉这些增量。

## 3. 溢出与下溢：数太大、太小时分别发生什么？

### 3.1 输入有限，结果仍然可以溢出

400 可以被 FP16 精确表示，但 `400 × 400 = 160000` 超过了 FP16 的最大有限值 65504。先在 FP32 中计算，再写回 FP16，就能把两个阶段分开观察：

```python
x16 = np.float16(400)
product32 = np.multiply(np.float32(x16), np.float32(x16), dtype=np.float32)

with np.errstate(over="ignore"):
    product16 = np.float16(product32)

print("input:", float(x16))
print("FP32 product:", float(product32))
print("FP16 output:", float(product16))
print("back to FP32:", float(np.float32(product16)))
```

运行结果：

```text
input: 400.0
FP32 product: 160000.0
FP16 output: inf
back to FP32: inf
```

这里能明确定位：FP32 乘法结果仍然有限，溢出发生在转成 FP16 的时候。已经变成 `Inf` 后，再转回 FP32 无法恢复 160000。

65504 是 FP16 的最大有限值，但不能对任意来源的数简单断言“一超过 65504 就立即变成 `Inf`”，边界附近还受舍入规则影响。本文选择明显越界的 160000；转换边界留到 BF16 转 FP16 专题进一步分析。

### 3.2 小于最小正规数，不一定立即变成零

FP16 的最小正正规数为 `2^-14`，约 `6.10 × 10^-5`；最小正非正规数为 `2^-24`，约 `5.96 × 10^-8`。两者之间仍有可以表示的非零数。

```python
small64 = np.array([2**-24, 1e-7, 1e-8], dtype=np.float64)

with np.errstate(under="ignore"):
    small16 = small64.astype(np.float16)

for original, converted in zip(small64, small16):
    print(f"{original:.9e} -> {float(converted):.9e}")
```

运行结果：

```text
5.960464478e-08 -> 5.960464478e-08
1.000000000e-07 -> 1.192092896e-07
1.000000000e-08 -> 0.000000000e+00
```

三个结果分别说明：

- `2^-24` 是可以精确保存的非正规数，不需要把它舍入成零。
- `1e-7` 转成了相邻非正规数，仍非零，但相对误差已经约为 19.2%。
- `1e-8` 比最小正非正规数的一半还小，按最近值规则舍入后得到零。

严格地说，IEEE 754 的下溢异常与结果“过小且不精确”有关；一个精确可表示的非正规结果，不应仅因它很小就被判定为下溢异常。本文主要观察数值结果，不依赖是否出现运行时警告来判断。

实际硬件或算子还可能把非正规输入、输出刷新为零。这是实现行为，需要与上述格式本身的表示与舍入规则分开看；本次 CPU 实验保留了表中的非正规值。

对训练而言，若很小的梯度在低精度保存或计算时变成零，相应信息就会丢失。损失缩放正是为缓解某些这样的情况而设计的，但它不能扩大 FP16 的表示范围，也不能通用地修复前向溢出。

## 4. 运算顺序与累加：误差如何影响后续结果？

### 4.1 浮点加法不满足一般意义上的结合律

实数运算满足 `(a + b) + c = a + (b + c)`。但如果每一步都需要舍入，两边经历的中间结果不同，最后就可能不同。

```python
p = np.float16(10000)
q = np.float16(-10000)
r = np.float16(1)

left = np.add(np.add(p, q, dtype=np.float16), r, dtype=np.float16)
right = np.add(p, np.add(q, r, dtype=np.float16), dtype=np.float16)

print("(p + q) + r:", float(left))
print("p + (q + r):", float(right))
```

运行结果：

```text
(p + q) + r: 1.0
p + (q + r): 0.0
```

左边先精确抵消为零，再加 1。右边的 `-10000 + 1 = -9999` 无法被 FP16 精确表示，在这一数量级的间隔为 8，因而舍入回 -10000；随后再加 10000 得到零。

差异来自中间结果的舍入。不能把“发生了相减或抵消”本身视为错误：这里左边的抵消恰好是精确的。如果两个相近数此前已经包含误差，做差还可能使这些误差相对于很小的差值变得很大，这才是另一个需要关注的精度损失机制。

### 4.2 FP32 累加为什么有帮助？

从 2048 开始连续加 100 次 1。如果每次都舍入成 FP16，每次加法都可能重复前面的“小量丢失”；如果先用 FP32 累加，最后才写回 FP16，这个例子的结果就不同。

```python
sum16 = np.float16(2048)
sum32 = np.float32(2048)

for _ in range(100):
    sum16 = np.add(sum16, np.float16(1), dtype=np.float16)
    sum32 = np.add(sum32, np.float32(1), dtype=np.float32)

print("FP16 each step:", float(sum16))
print("FP32 accumulation:", float(sum32))
print("one final FP16 cast:", float(np.float16(sum32)))
```

运行结果：

```text
FP16 each step: 2048.0
FP32 accumulation: 2148.0
one final FP16 cast: 2148.0
```

2148 恰好可以用 FP16 表示，所以最后一次转换没有丢失这个结果。更宽的累加格式保留了中间的小增量；它并不保证所有问题都得到精确答案，也不能恢复输入在更早阶段已经丢掉的信息。

点积、矩阵乘法、归约求和都包含大量累加，但实际算子不一定按这个 Python 循环的顺序工作。并行归约可能采用树形结构，融合乘加可能减少一次舍入，某些实现还可能在部分步骤降低中间精度。不能直接用逐次 FP16 加法的结果预测 GPU 矩阵乘法的结果。

误差也不总是单向增长：不同步骤的误差可能积累、抵消，或者被后续计算放大。判断最终影响，需要看具体数据与算法。

## 5. 存储、计算、累加与输出：应当分别检查

“模型使用 FP16”没有完整描述每个算子。分析一条计算路径时，至少需要确认：

| 环节 | 要确认的问题 | 可能丢失的信息 |
| --- | --- | --- |
| 输入存储与类型转换 | 输入原先是什么格式，转换后是什么格式？ | 输入舍入误差，或转换时直接溢出 |
| 乘法等中间计算 | 实际采用多少有效位，何时发生舍入？ | 乘积或其他中间值的误差与异常 |
| 累加与归约 | 用什么格式，按什么顺序累加？ | 小增量丢失，中间累加值越界 |
| 输出与缓存写回 | 结果最终保存为什么格式？ | 宽格式结果在写回窄格式时溢出或舍入 |

第 3 节的 `400 × 400` 就说明：即便中间结果能由 FP32 保存，最终写回 FP16 仍会溢出。“使用 FP32 累加”只能说明其中一部分计算方式，不能单独保证整条路径安全。

### 5.1 稳定公式也很重要：以 softmax 为例

扩大位数并非唯一办法。即使用 FP32，直接对 1000、1001 计算指数也会超出范围：

```python
logits = np.array([1000, 1001], dtype=np.float32)

with np.errstate(over="ignore", invalid="ignore"):
    exp_raw = np.exp(logits)
    naive = exp_raw / np.sum(exp_raw, dtype=np.float32)

exp_shifted = np.exp(logits - np.max(logits))
stable = exp_shifted / np.sum(exp_shifted, dtype=np.float32)

print("naive:", naive)
print("stable:", stable)
```

本机运行结果：

```text
naive: [nan nan]
stable: [0.2689414 0.7310586]
```

对有限的输入，softmax 可以在数学上等价地改写为：

```text
softmax(z_i) = exp(z_i - max(z)) / Σ_j exp(z_j - max(z))
```

减去最大值后，指数的输入不大于零，从而避免这里的指数溢出；但有限精度下仍可能有舍入误差，小项也可能下溢。实际框架通常会采用稳定实现，不应据此推断框架的 softmax 都使用朴素公式。

如果 logits 在进入 softmax 前就已包含 `Inf` 或 `NaN`，这个改写无法自动恢复原始有限值。例如 `Inf - Inf` 本身就会产生 `NaN`。这也是需要定位首次异常位置的原因。

## 6. 如何区分正常误差与数值异常？

### 6.1 先检查有限性，再分析误差

有限的舍入误差、`Inf` 与 `NaN` 不是同一种现象。`NaN` 可能由 `Inf - Inf`、`Inf / Inf`、`0 / 0` 等无效运算产生，因此看到最终 loss 为 `NaN` 时，不能只检查最后一步，也不能直接断言根因一定是溢出。

最基本的检查是同时报告非有限值数量与有限值范围：

```python
def describe(name, value):
    value = np.asarray(value)
    finite = np.isfinite(value)
    finite_values = value[finite].astype(np.float64)
    max_abs = float(np.max(np.abs(finite_values))) if finite_values.size else None
    print(
        f"{name}: dtype={value.dtype}, "
        f"finite={np.count_nonzero(finite)}/{value.size}, "
        f"inf={np.count_nonzero(np.isinf(value))}, "
        f"nan={np.count_nonzero(np.isnan(value))}, "
        f"max_abs_finite={max_abs}"
    )

describe("product32", product32)
describe("product16", product16)
describe("naive_softmax", naive)
```

运行结果：

```text
product32: dtype=float32, finite=1/1, inf=0, nan=0, max_abs_finite=160000.0
product16: dtype=float16, finite=0/1, inf=1, nan=0, max_abs_finite=None
naive_softmax: dtype=float32, finite=0/2, inf=0, nan=2, max_abs_finite=None
```

排查模型时，可以在模块边界或类型转换前后记录这些信息，先定位第一个从有限值变为非有限值的位置，再缩小到具体算子。PyTorch 中有对应的 `torch.isfinite`、`torch.isinf` 和 `torch.isnan`；融合算子内部可能还需要更细的实现级检查。

### 6.2 有限不代表准确：误差应怎样衡量？

如果计算结果和参考值都有限，可以进一步比较：

```text
绝对误差 = abs(actual - reference)
相对误差 = abs(actual - reference) / abs(reference)    # reference != 0
```

以 `2048 + 1` 为例，FP16 结果为 2048，精确数学结果为 2049，绝对误差是 1，相对误差约为 0.0488%。这个误差是否可以接受，要由具体任务判断。

参考值接近零时，相对误差容易很大；参考值为零时，相对误差没有上述定义。常用的混合判据为：

```text
abs(actual - reference) <= atol + rtol × abs(reference)
```

`atol` 控制靠近零时允许的绝对误差，`rtol` 控制随参考值尺度变化的相对误差。容差要根据数值尺度和任务需求设定，不能不断放宽阈值直到检查通过。

参考结果也需要说明来源：本文的小整数例子可以直接与精确数学结果比较；复杂计算中的 FP64 结果通常只是更高精度的参考，不等于精确真值。如果目的是隔离计算误差，应让两条路径使用相同的已量化输入；如果比较原始高精度输入与低精度输入的整条路径，测到的差异还包含输入量化误差。把已经舍入的输入转成 FP64，并不能找回丢失的信息。

这些检查能帮助定位数值问题，却不能替代模型效果评测。一个结果可能全部有限却不够准确，也可能存在小幅数值差异但对任务表现影响很小。

## 小结

浮点运算的误差来自具体的表示与舍入过程：小量可能在加法中消失，改变运算顺序可能改变结果，大数可能在输出写回时溢出，小数可能进入非正规区域或舍入成零。

实际分析时，先明确每一步的格式与舍入位置，再区分有限误差和非有限值，最后结合参考计算及模型评测判断影响。FP32 累加、稳定公式和损失缩放各自解决不同的问题，需要对准异常发生的位置。

下一篇将把这些原理用于 BF16 转 FP16：区分直接转换溢出、前向中间值溢出与反向梯度异常，并讨论各自适用的应对方法。

## 参考资料

- [NumPy：numpy.finfo](https://numpy.org/doc/stable/reference/generated/numpy.finfo.html)：格式边界、最小正规数与非正规数的区别。
- [PyTorch：Numerical accuracy](https://docs.pytorch.org/docs/2.14/notes/numerical_accuracy.html)：运算顺序、平台差异及矩阵乘法中间累加精度的影响。
- [David Goldberg：What Every Computer Scientist Should Know About Floating-Point Arithmetic](https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html)：舍入误差、相对误差、抵消与渐进下溢的基础解释。
- [PyTorch：Automatic Mixed Precision — Gradient Scaling](https://docs.pytorch.org/docs/2.14/amp.html#gradient-scaling)：损失缩放的作用，以及 FP16 数值范围带来的限制。
