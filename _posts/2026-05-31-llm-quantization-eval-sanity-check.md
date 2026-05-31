---
layout:     post
title:      LLM 低精度部署排查：先确认不是评测问题
subtitle:   比较 NVFP4 和 BF16 前，先把输入、解码、停止规则和打分脚本固定住
date:       2026-05-31 23:30:00 +0800
permalink:  /2026/05/31/llm-quantization-eval-sanity-check/
author:     ctzmx
header-img: /img/ct/1%20(218).jpg
catalog: true
tags:
    - LLM
    - Quantization
    - Deployment
    - Evaluation
---

# LLM 低精度部署排查：先确认不是评测问题

部署 LLM 时，如果发现 NVFP4、INT4、FP8 这类低精度版本相比 BF16 掉分很多，不要一上来就判断是量化算法不行。第一步应该先确认：**这次比较里，唯一变量是不是真的只有精度**。

如果 tokenizer、chat template、system prompt、采样参数、EOS 配置、batch shape、评测数据或答案抽取逻辑有任何一个不一致，那么看到的差异可能来自评测链路，而不是 NVFP4 本身。

这一步的目标很简单：让 BF16 和低精度模型看到完全相同的输入，使用完全相同的解码规则，并被完全相同的脚本打分。

## 0x00 总原则：先固定变量

排查时建议至少准备三组结果：

```text
1. 原始 HF BF16 模型
2. 部署框架内 BF16 模型
3. 部署框架内 NVFP4 模型
```

判断顺序是：

```text
如果 1 和 2 不一致：
    优先查部署框架、模型转换、tokenizer、chat template 和推理参数。
    这时还不能归因到 NVFP4。

如果 1 和 2 基本一致，但 3 明显变差：
    再进入 NVFP4 的量化、校准、scale、kernel、KV cache 等排查。
```

也就是说，部署框架里的 BF16 版本要先和原始 BF16 对齐。否则低精度对比没有可靠基线。

## 0x01 tokenizer 必须一致

tokenizer 决定文本如何被切成 token，以及每个 token 对应什么 id。对模型来说，输入不是原始字符串，而是 token id 序列。

同一句话：

```text
你好，请介绍一下你自己。
```

如果 tokenizer 不一致，可能得到完全不同的 `input_ids`。模型看到的输入已经不是同一个问题，后面再比较 BF16 和 NVFP4 的输出就没有意义。

需要检查：

- `tokenizer.json`、`tokenizer.model`、`vocab.json`、`merges.txt` 是否来自同一个模型目录。
- `special_tokens_map.json`、`tokenizer_config.json` 是否和模型匹配。
- `bos_token_id`、`eos_token_id`、`pad_token_id` 是否一致。
- `add_special_tokens` 的设置是否一致。
- 中文、空格、换行、制表符是否被一致处理。
- 框架是否自动插入 BOS、EOS 或其他特殊 token。

最直接的验证方式是打印同一个 prompt 的 token 结果：

```text
原始 BF16 input_ids
部署框架 BF16 input_ids
部署框架 NVFP4 input_ids
```

这三者应该完全一致。至少在进入模型前，`input_ids`、`attention_mask`、`position_ids` 都应该可解释、可对齐。

## 0x02 chat template 必须一致

对话模型通常不会直接吃用户输入，而是先经过 chat template 拼成模型训练时熟悉的格式。

同一个用户问题：

```text
请解释一下量化。
```

不同模板可能变成：

```text
<|system|>
You are a helpful assistant.
<|user|>
请解释一下量化。
<|assistant|>
```

也可能变成：

```text
[INST] 请解释一下量化。 [/INST]
```

还可能变成：

```text
User: 请解释一下量化。
Assistant:
```

这些 prompt 在模型眼里是完全不同的输入。

需要检查：

- 是否使用同一个 `apply_chat_template`。
- 是否设置了 `add_generation_prompt`。
- system、user、assistant 的 role token 是否一致。
- 多轮对话的拼接顺序是否一致。
- assistant 历史回复是否被正确保留。
- tool call、function call、JSON mode 等特殊格式是否一致。
- 部署框架是否内置了默认模板。

很多“量化后效果差”的问题，最后其实是因为 BF16 测试脚本和部署服务使用了不同 chat template。

## 0x03 system prompt 必须一致

system prompt 会显著影响模型行为。比如：

```text
You are a helpful assistant.
```

和：

```text
你是一个严谨的中文技术助手，回答要简洁。
```

这两种设置下，即使模型和精度完全一样，输出也可能不同。

需要确认：

- system prompt 内容是否一致。
- 是否一个链路显式传入，另一个链路由框架默认注入。
- 换行、空格、标点、语言是否一致。
- system prompt 是否被 chat template 放在正确位置。
- 多轮对话时 system prompt 是否只出现一次。

如果 BF16 没有 system prompt，而 NVFP4 部署服务默认加了 system prompt，输出差异不能算量化误差。

## 0x04 生成长度必须一致

常见参数有两个：

```text
max_new_tokens
max_length
```

它们不是一回事。

`max_new_tokens` 限制新生成 token 的数量。`max_length` 通常限制输入和输出加起来的总长度。

例如输入已经有 800 tokens：

```text
max_length = 1024
```

这时最多只能继续生成约 224 tokens。

而：

```text
max_new_tokens = 1024
```

则表示可以额外生成 1024 tokens。

如果 BF16 用 `max_new_tokens=1024`，NVFP4 用 `max_length=1024`，NVFP4 可能只是被提前截断，并不是模型能力下降。

需要检查：

- 使用的是 `max_new_tokens` 还是 `max_length`。
- 输入较长时是否触发截断。
- 部署框架是否有默认最大输出长度。
- 评测脚本是否因为输出太短而判错。
- 是否不同任务使用了不同输出长度限制。

## 0x05 采样参数必须一致

做量化误差对比时，优先使用确定性解码：

```text
temperature = 0
do_sample = false
```

或者等价的 greedy decode。

原因是：采样会放大很小的 logits 差异。BF16 和 NVFP4 的 logits 只要在某一步略有不同，就可能采到不同 token。生成式模型一旦某一步分叉，后续文本会越走越远。

需要固定的参数包括：

- `temperature`
- `top_p`
- `top_k`
- `do_sample`
- `seed`
- `repetition_penalty`
- `frequency_penalty`
- `presence_penalty`
- `no_repeat_ngram_size`

几个典型参数的影响：

```text
temperature 越高，随机性越强。
top_p 控制候选 token 的累计概率范围。
top_k 控制只从概率最高的 k 个 token 中采样。
repetition_penalty 会改变模型重复已有 token 的倾向。
```

如果 BF16 是 greedy，NVFP4 是 `temperature=0.7, top_p=0.9`，结果不能直接比较。

建议第一轮排查使用：

```text
do_sample = false
temperature = 0
top_p = 1
top_k = 1 或不启用
repetition_penalty = 1.0
```

等确定性链路对齐以后，再测试真实线上采样参数。

## 0x06 stop words 和 EOS 必须一致

stop words 和 EOS 配置决定模型什么时候停止生成。

常见问题包括：

- BF16 正常停止，NVFP4 一直生成到最大长度。
- NVFP4 提前停止，只输出半句话。
- 输出里残留 `<|eot_id|>`、`</s>` 等特殊 token。
- 模型回答完后继续模拟下一轮用户输入。

需要检查：

- `eos_token_id` 是否一致。
- 是否存在多个 EOS token。
- tokenizer 里的 EOS 是否和 model config 一致。
- 部署服务是否额外配置了 stop strings。
- stop strings 是否包含换行、空格等不可见差异。
- chat template 的结束标记是否被正确加入。
- 流式输出时 stop 逻辑是否和非流式一致。

不同模型家族的停止规则不完全一样。Llama、Qwen、Mistral、ChatGLM、DeepSeek 等模型，都应该按各自 tokenizer 和官方模板确认，而不是复用一套通用 EOS。

## 0x07 batch size 要先从 1 开始

理论上，batch size 不应该改变模型输出。但在真实部署框架里，batch size 可能影响：

- padding 方式
- attention mask
- position ids
- KV cache 排布
- paged attention 行为
- kernel 选择
- 动态 shape engine 路径
- activation scale 的统计和使用方式

所以排查时建议：

```text
先用 batch_size = 1 对齐
再测试 batch_size = 2 / 4 / 8 / 16
```

如果 `batch_size=1` 正常，batch 变大后掉分，重点查：

- padding side 是 left 还是 right。
- attention mask 是否屏蔽了 padding。
- position ids 是否从正确位置开始。
- 不同样本的 KV cache 是否串扰。
- 框架是否在不同 batch size 下选择了不同 kernel。

这类问题容易被误判为量化问题，因为它只在部署服务里出现，而离线单样本测试正常。

## 0x08 context length 必须覆盖真实场景

context length 是输入上下文长度。短 prompt 正常，不代表长上下文正常。

比如：

```text
512 tokens 正常
4096 tokens 开始变差
32768 tokens 明显崩
```

这时不一定是 NVFP4 本身的问题，也可能是长上下文配置不一致。

需要检查：

- `max_position_embeddings` 是否一致。
- RoPE base、theta、scaling、NTK、YaRN 等配置是否一致。
- `position_ids` 是否正确。
- engine 构建时的 max sequence length 是否足够。
- prompt 是否被部署框架静默截断。
- KV cache 是否被量化。
- sliding window attention 是否配置一致。
- calibration 数据是否覆盖长上下文。

如果短文本结果接近 BF16，长文本明显掉分，优先查：

```text
RoPE / position_ids / KV cache / max_seq_len / prompt truncation
```

## 0x09 eval 数据和预处理必须一致

评测数据不只是原始问题，还包括预处理、few-shot 示例、输出抽取和打分逻辑。

需要确认：

- 是否使用同一份测试集。
- 样本顺序是否一致。
- 是否过滤了部分样本。
- 输入是否被截断。
- 是否清理 HTML、空格、换行、特殊字符。
- 是否做了大小写转换。
- 是否做了中文繁简转换。
- few-shot 示例是否一致。
- 选择题选项顺序是否一致。
- 答案抽取规则是否一致。
- 打分脚本是否一致。

选择题里尤其容易出问题。比如模型输出：

```text
答案是 A。
```

一个评测脚本能抽取出 `A`，另一个脚本只接受纯字符：

```text
A
```

那同一个模型也可能被判成一个对、一个错。

数学评测也类似：

- `1/2` 和 `0.5` 是否都算对。
- 是否允许先解释再给最终答案。
- `\boxed{}` 里的答案是否会被提取。
- 单位、百分号、小数精度是否处理一致。

代码评测需要额外检查：

- 是否抽取 markdown code block。
- 是否保留 import。
- 是否运行相同单元测试。
- timeout 是否一致。
- 依赖版本是否一致。

## 0x0A 推荐的第一轮对齐配置

第一轮不要直接用线上采样配置，也不要直接看开放问答主观感受。建议先用尽量确定的配置：

```text
同一个 tokenizer
同一个 chat template
同一个 system prompt
同一个 eval 数据
同一个预处理脚本
同一个答案抽取脚本
batch_size = 1
固定 context length
do_sample = false
temperature = 0
top_p = 1
repetition_penalty = 1.0
max_new_tokens 固定
EOS / stop words 固定
```

然后比较：

```text
原始 HF BF16
部署框架 BF16
部署框架 NVFP4
```

可以先看这些指标：

- `input_ids` 是否完全一致。
- 首 token logits 是否接近。
- greedy 输出是否一致或高度接近。
- 输出长度是否异常。
- 是否提前停止或无法停止。
- 同一个答案抽取脚本下分数是否一致。

如果要更严谨，可以比较：

```text
logits cosine similarity
top-k token overlap
cross entropy / perplexity
每一步生成 token 是否分叉
```

## 0x0B 一句话总结

排查低精度模型掉分时，第一步不是看量化参数，而是先确认评测链路本身可靠：

```text
同一个输入，
同一个模板，
同一个解码，
同一个停止规则，
同一个评测脚本。
```

只有当部署框架里的 BF16 已经能对齐原始 BF16，NVFP4 的差异才适合继续归因到量化、校准、scale、kernel 或 KV cache。
