---
layout:     post
title:      Codex Skill 制作流程：从想法到可复用能力
subtitle:   一个 skill 不只是 prompt，而是一套可被触发、可验证、可迭代的工作流
date:       2026-05-31 01:06:00 +0800
permalink:  /2026/05/31/codex-skill-creation-workflow/
author:     ctzmx
header-img: /img/ct/1%20(218).jpg
catalog: true
tags:
    - Codex
    - Skill
    - AI
---

# Codex Skill 制作流程：从想法到可复用能力

## 0. Skill 是什么

在 Codex 里，skill 可以理解成一组本地能力说明。它通常不是单纯的一段 prompt，而是一个目录，里面至少包含一个 `SKILL.md`。这个文件告诉 Codex：这个能力适合什么场景、应该怎么执行、遇到复杂任务时应该读取哪些参考资料或调用哪些脚本。

一个最小的 skill 长这样：

```text
<skill-name>/
  SKILL.md
```

一个更完整的 skill 可能长这样：

```text
<skill-name>/
  SKILL.md
  agents/
    openai.yaml
  scripts/
  references/
  assets/
```

其中：

- `SKILL.md` 是核心说明文件。
- `scripts/` 放可复用脚本，适合稳定、重复、容易写错的操作。
- `references/` 放按需读取的长文档，比如 API 说明、业务规则、数据库结构。
- `assets/` 放模板、图片、字体、示例工程等输出时会用到的资源。
- `agents/openai.yaml` 通常用于 UI 展示，比如显示名称、简短描述和默认提示词。

## 1. 触发机制

Codex 并不是每次都读取所有 skill 的完整内容。通常只有 skill 的元信息会被放进上下文，比如名称、描述和 `SKILL.md` 路径。

真正决定是否使用某个 skill 的关键，是 `SKILL.md` 头部的 `description`。所以 `description` 不应该只写一句很泛的介绍，而应该明确说明：

- 这个 skill 能做什么。
- 什么用户请求应该触发它。
- 它适合处理哪些文件、工具、流程或场景。

例如：

```markdown
---
name: skill-name
description: Use when Codex needs to create or update a specialized skill, including writing SKILL.md, organizing scripts, references, assets, and validating the final skill folder.
---
```

正文只有在 skill 被触发后才会读取，所以“什么时候使用这个 skill”最好写进 `description`，不要只放在正文里。

## 2. 制作前先确认使用场景

做 skill 不建议从写 prompt 开始，而是先明确真实用法。可以先问几个问题：

- 用户会怎么提需求？
- 哪些请求应该触发这个 skill？
- 这个 skill 要指导 Codex 完成哪些固定步骤？
- 有没有容易做错、应该固化成脚本的地方？
- 有没有大量规则、文档或模板，应该放进 `references/` 或 `assets/`？

如果一个 skill 没有清晰场景，它很容易变成一篇泛泛的说明文。好的 skill 应该像一份给另一个 Codex 实例看的上手指南：短、准、能直接指导行动。

## 3. 命名和目录

skill 名称建议使用小写字母、数字和短横线：

```text
pdf-editor
brand-guidelines
gh-address-comments
linear-address-issue
```

目录名应该和 skill 名称一致：

```text
<skills-root>/
  pdf-editor/
    SKILL.md
```

常见安装位置可以写成通用路径：

```text
$CODEX_HOME/skills
~/.codex/skills
```

不要把具体机器上的用户目录、公司目录、内部仓库地址写进公开文章或公开 skill 里。需要表达路径时，用 `<skills-root>`、`<skill-name>`、`<project-root>` 这类占位符更安全。

## 4. 规划可复用资源

一个实用判断标准是：如果 Codex 每次执行这个任务都要重复写同一段代码、查同一份文档、复制同一套模板，那它就可能适合放进 skill。

可以这样拆：

```text
重复代码          -> scripts/
长篇规则或说明    -> references/
模板和素材        -> assets/
核心流程          -> SKILL.md
```

例如：

- PDF 旋转、合并、拆分这类操作，可以放脚本。
- 数据库表结构、内部 API 说明，可以放参考文档。
- PPT 模板、品牌 logo、前端脚手架，可以放资产目录。

`SKILL.md` 只保留最核心的流程和导航。详细内容放到其他文件里，并在 `SKILL.md` 中说明什么时候读取。

## 5. 初始化 skill

规范做法是用初始化脚本生成基础结构：

```bash
scripts/init_skill.py <skill-name> --path <skills-root>
```

如果需要同时创建资源目录，可以传入类似参数：

```bash
scripts/init_skill.py <skill-name> --path <skills-root> --resources scripts,references,assets
```

这里的 `<skills-root>` 是脱敏后的占位符。实际使用时，可以是：

```bash
${CODEX_HOME:-$HOME/.codex}/skills
```

Windows、macOS、Linux 的具体路径可能不同，但文章或公开文档里一般不需要暴露真实本机路径。

## 6. 编写 SKILL.md

`SKILL.md` 包含两部分：

```markdown
---
name: skill-name
description: Clear trigger description here.
---

# Skill Name

Instructions go here.
```

写的时候有几个原则：

- `description` 要明确，因为它决定触发。
- 正文要短，写必要流程，不写无关背景。
- 用命令式写法，比如“Read ...”“Run ...”“Validate ...”。
- 只写 Codex 不一定知道、或者容易做错的信息。
- 长文档不要堆在正文里，放到 `references/`，并在正文中说明何时读取。

一个好的 `SKILL.md` 不是教程文章，而是执行手册。它的读者是另一个正在干活的 Codex。

## 7. 加脚本、参考资料和资产

如果 skill 里有脚本，需要实际运行测试。脚本的价值在于稳定和复用，如果脚本本身没验证过，反而会把问题固化进 skill。

如果 skill 里有参考资料，要注意“渐进式加载”：

```text
SKILL.md 只放入口和选择逻辑
references/ 放详细规则
需要哪个文件再读取哪个文件
```

例如：

```text
cloud-deploy/
  SKILL.md
  references/
    aws.md
    gcp.md
    azure.md
```

当用户要部署到 AWS 时，只需要读取 `references/aws.md`，不用把所有云厂商文档都塞进上下文。

## 8. 验证

完成后要跑验证脚本：

```bash
scripts/quick_validate.py <path-to-skill-folder>
```

它通常会检查：

- YAML frontmatter 是否合法。
- 是否包含必需字段。
- skill 名称是否符合规则。
- 文件夹结构是否基本正确。

如果校验失败，先修复再继续。

## 9. 真实任务中迭代

skill 第一次写完不代表结束。更可靠的方式是拿真实任务试用：

1. 用真实请求触发它。
2. 观察 Codex 有没有走错流程。
3. 看是否有信息缺失、说明太长、脚本不稳定的问题。
4. 修改 `SKILL.md` 或资源文件。
5. 再用相似任务验证一次。

复杂 skill 还可以做 forward-test：让一个新的上下文只拿到 skill 和任务，看它能不能独立完成。这能检验 skill 是否真的把关键流程写清楚了，而不是依赖当前对话里的隐含信息。

## 10. 总结

制作 skill 的核心流程可以压缩成一句话：

```text
先定义真实场景，再设计可复用资源，最后写一个短而准的 SKILL.md，并用验证和真实任务迭代。
```

它不是把一大段 prompt 塞进目录里，而是把某类任务中稳定、重复、容易出错的部分沉淀成可触发、可复用、可验证的本地能力。
