---
layout:     post
title:      Bazel 从零入门：看懂 BUILD、load 和项目里的构建关系
subtitle:   从 Bazel 和 gcc 的区别讲起，用一个 C++ 小例子串起目标、依赖、测试、label、.bzl 和常用命令
date:       2026-06-08 01:20:00 +0800
permalink:  /2026/06/08/bazel-zero-to-one/
author:     ctzmx
header-img: /img/ct/1%20(218).jpg
catalog: true
tags:
    - Bazel
    - Build
    - Cpp
---

# Bazel 从零入门：看懂 BUILD、load 和项目里的构建关系

这篇写给完全没有 Bazel 基础、但已经接手了一个 Bazel 项目的人。

目标不是把 Bazel 所有功能讲完，而是先解决几个最实际的问题：

- Bazel 到底是什么，和 gcc、clang、make、cmake 有什么区别。
- Bazel 构建时从哪个文件开始看。
- 项目里哪些文件通常是 Bazel 相关文件。
- `BUILD` 文件里的 `name`、`srcs`、`hdrs`、`deps` 怎么读。
- `:add`、`//math:add`、`@repo//pkg:target` 这种写法是什么意思。
- `load(...)` 是什么，为什么项目里到处有自定义函数。
- 接手一个现有项目时，应该按什么顺序读。

先给一句话版本：

```text
Bazel 是构建系统，负责描述和调度整个项目怎么编译、测试、打包；
gcc / clang 是编译器，负责把 C / C++ 源码真正编译成机器码。
```

## 1. Bazel 不是编译器

如果你写一个非常小的 C 程序：

```c
#include <stdio.h>

int main() {
    printf("hello\n");
    return 0;
}
```

可以直接用 gcc：

```bash
gcc main.c -o main
```

这里 gcc 做的是编译和链接。

但是实际项目通常不止一个文件：

```text
app/
  main.cc
base/
  logging.h
  logging.cc
math/
  add.h
  add.cc
  add_test.cc
third_party/
  ...
```

这时你要解决的不只是“怎么编译一个文件”，而是：

- 哪些源码属于同一个库。
- 哪些库依赖哪些库。
- 哪些目标是可执行程序。
- 哪些目标是测试。
- 改了一个文件后，哪些东西需要重新构建。
- 测试怎么跑，测试日志放哪里。
- 外部依赖从哪里来。
- CI 和本地是否用同一套构建逻辑。

这些就是 Bazel 负责的事情。

可以把关系理解成：

```text
Bazel 负责组织工程和调度构建
gcc / clang 负责执行具体 C/C++ 编译
```

Bazel 可以在内部调用 gcc 或 clang，但 Bazel 本身不是 gcc 的替代品。

## 2. Bazel 构建从哪里开始

很多人刚看 Bazel 项目时会问：Bazel 是从哪个文件开始构建的？

更准确的答案是：

```text
Bazel 从你命令里指定的目标开始，而不是从某个固定 BUILD 文件开始。
```

例如：

```bash
bazel build //app:server
```

这条命令的意思是：

```text
构建 app 这个包里的 server 目标。
```

Bazel 会去找：

```text
app/BUILD
app/BUILD.bazel
```

然后在里面找到：

```python
cc_binary(
    name = "server",
    ...
)
```

如果 `server` 依赖别的目标：

```python
deps = [
    "//base:logging",
    "//math:add",
]
```

Bazel 又会继续读取：

```text
base/BUILD 或 base/BUILD.bazel
math/BUILD 或 math/BUILD.bazel
```

也就是说，Bazel 不是一上来把整个仓库的所有 `BUILD` 文件都扫一遍。它会根据你指定的 target pattern 和依赖关系，加载需要的包。

当然，如果你运行的是：

```bash
bazel build //...
```

那就是让 Bazel 构建当前工作区下所有可构建目标。这个时候它会展开大量包，读到的 `BUILD` 文件自然会多很多。

## 3. 常见 Bazel 文件

一个 Bazel 项目里常见这些文件。

### MODULE.bazel

现代 Bazel 项目常见的模块文件，主要用来声明当前项目模块和外部依赖。它属于 Bzlmod 这套依赖管理方式。

例如：

```python
module(name = "my_project", version = "1.0")

bazel_dep(name = "rules_cc", version = "0.1.1")
```

你可以粗略类比成：

```text
Node.js 的 package.json
Go 的 go.mod
Rust 的 Cargo.toml
```

这个类比不是说语法一样，而是说它们都承担“项目和依赖入口”的角色。

### WORKSPACE / WORKSPACE.bazel

老一些的 Bazel 项目会用 `WORKSPACE` 或 `WORKSPACE.bazel` 声明工作区和外部依赖。

现在很多新项目会转向 `MODULE.bazel`，但大量已有项目仍然保留 `WORKSPACE`。所以看到它不要惊讶。

如果一个项目同时有 `MODULE.bazel` 和 `WORKSPACE`，不要急着删任何一个。先看项目当前 Bazel 版本、`.bazelrc` 和 CI 怎么跑。

### BUILD / BUILD.bazel

这是最常看的文件。

`BUILD` 或 `BUILD.bazel` 定义当前目录这个 Bazel package 里的构建目标，比如库、二进制、测试、文件组等。

常见内容：

```python
cc_library(
    name = "add",
    srcs = ["add.cc"],
    hdrs = ["add.h"],
)

cc_test(
    name = "add_test",
    srcs = ["add_test.cc"],
    deps = [":add"],
)
```

如果同一个目录里同时存在 `BUILD` 和 `BUILD.bazel`，Bazel 使用 `BUILD.bazel`。实际项目里不要这样混用，容易让人误读。

### .bzl

`.bzl` 文件是 Bazel 的扩展脚本文件。里面通常放：

- 宏。
- 自定义规则。
- 公共常量。
- 公共构建封装。
- 第三方规则导出的入口。

例如：

```python
load("//build:cc_defs.bzl", "project_cc_library")

project_cc_library(
    name = "net",
    srcs = ["net.cc"],
)
```

这里 `project_cc_library` 不是 Bazel 内置规则，而是从 `build/cc_defs.bzl` 加载出来的项目自定义封装。

### .bazelrc

`.bazelrc` 是 Bazel 命令配置文件。它可以给 `build`、`test`、`run` 等命令配置默认参数。

例如：

```text
build --cxxopt=-std=c++17
test --test_output=errors
build:debug --compilation_mode=dbg
```

于是：

```bash
bazel build --config=debug //app:server
```

会额外带上 `debug` 配置里的参数。

接手项目时一定要看 `.bazelrc`，因为很多“为什么本地命令和 CI 不一样”的答案都在这里。

### .bazelignore

告诉 Bazel 忽略某些目录。常用于排除不应该被 Bazel 当成包扫描的子目录。

### .bazelversion

通常给 Bazelisk 使用，用来指定项目期望使用的 Bazel 版本。

### MODULE.bazel.lock

模块依赖锁文件，作用类似其他生态里的 lock file。一般不要手改。

### bazel-bin / bazel-out / bazel-testlogs

这些通常是 Bazel 构建后生成的输出目录或符号链接。

常见含义：

```text
bazel-bin       构建产物入口
bazel-out       内部输出树
bazel-testlogs  测试日志入口
```

这些不是你写业务代码的地方。

## 4. 用一个 C++ 例子看 BUILD 文件

假设目录如下：

```text
math/
  BUILD
  add.h
  add.cc
  add_test.cc
```

代码：

```cpp
// add.h
int add(int a, int b);
```

```cpp
// add.cc
#include "add.h"

int add(int a, int b) {
    return a + b;
}
```

```cpp
// add_test.cc
#include "add.h"
#include <cassert>

int main() {
    assert(add(1, 2) == 3);
    assert(add(-1, 1) == 0);
    return 0;
}
```

对应 `math/BUILD`：

```python
cc_library(
    name = "add",
    srcs = ["add.cc"],
    hdrs = ["add.h"],
)

cc_test(
    name = "add_test",
    srcs = ["add_test.cc"],
    deps = [":add"],
)
```

这个文件定义了两个目标：

```text
//math:add
//math:add_test
```

### cc_library

```python
cc_library(
    name = "add",
    srcs = ["add.cc"],
    hdrs = ["add.h"],
)
```

这表示定义一个 C++ 库。

几个属性的意思：

```text
name  目标名
srcs  这个目标要编译的源文件
hdrs  这个库对外暴露的头文件
deps  这个目标依赖的其他 Bazel 目标
```

`name = "add"` 表示这个目标叫 `add`。

因为它定义在 `math/BUILD` 中，所以完整 label 是：

```text
//math:add
```

`srcs = ["add.cc"]` 表示 `add.cc` 会参与编译。

`hdrs = ["add.h"]` 表示 `add.h` 是这个库公开给依赖方使用的头文件。

### cc_test

```python
cc_test(
    name = "add_test",
    srcs = ["add_test.cc"],
    deps = [":add"],
)
```

这表示定义一个 C++ 测试目标。

运行：

```bash
bazel test //math:add_test
```

Bazel 会做这些事：

```text
1. 找到 math/BUILD 里的 add_test。
2. 发现 add_test 的源码是 add_test.cc。
3. 发现 add_test 依赖 :add。
4. 先分析并构建 add。
5. 再编译并链接 add_test。
6. 运行测试程序。
7. 汇报 PASSED 或 FAILED。
```

如果用 gcc 手写命令，你大概需要自己处理：

```bash
g++ -c math/add.cc -o add.o
g++ -c math/add_test.cc -o add_test.o
g++ add.o add_test.o -o add_test
./add_test
```

Bazel 把这套关系写进 `BUILD` 文件，再自动调度。

## 5. label：Bazel 里的目标地址

Bazel 经常出现这种写法：

```text
//math:add_test
```

这叫 label，可以理解成 Bazel 目标的地址。

拆开看：

```text
//math      package 路径，也就是 math/BUILD 所在目录
:add_test  target 名，也就是 name = "add_test"
```

所以：

```text
//math:add_test
```

表示：

```text
math/BUILD 文件里 name = "add_test" 的目标
```

常见写法：

```text
//math:add       本仓库 math 包里的 add 目标
//math:all       math 包里所有目标
//math/...       math 目录及子目录下所有包
//...            当前工作区下所有包
:add            当前 BUILD 文件所在包里的 add 目标
@repo//pkg:lib   外部仓库 repo 里的 pkg/lib 目标
```

`deps = [":add"]` 里的 `:add` 是简写。

如果这行写在 `math/BUILD` 里：

```python
deps = [":add"]
```

它等价于：

```python
deps = ["//math:add"]
```

为什么项目里经常用 `:add`？因为同一个 `BUILD` 文件里互相引用时，简写更短。

## 6. deps：Bazel 的依赖关系

`deps` 是 dependencies 的缩写。

例如：

```python
cc_binary(
    name = "server",
    srcs = ["server.cc"],
    deps = [
        "//base:logging",
        "//math:add",
        "@com_google_absl//absl/strings",
    ],
)
```

这表示：

```text
server 这个二进制目标依赖三个目标：
1. 本项目 base 包里的 logging。
2. 本项目 math 包里的 add。
3. 外部仓库 com_google_absl 里的 absl/strings。
```

依赖关系是 Bazel 的核心。Bazel 通过它知道：

- 构建顺序。
- 哪些头文件或库可以被使用。
- 改了一个文件后哪些目标受影响。
- 哪些构建结果可以复用缓存。

不要把 `deps` 理解成“随便 include 了就能用”。在 Bazel 项目里，源码中用了某个库，通常就应该在 `deps` 里声明对应 Bazel 目标。

## 7. srcs、hdrs、data 的区别

C++ 规则里常见：

```python
srcs = ["foo.cc"]
hdrs = ["foo.h"]
data = ["config.json"]
```

可以先这样理解：

```text
srcs  编译输入，通常是 .cc / .cpp / .c
hdrs  公开头文件，依赖这个库的目标可以 include
data  运行时数据文件，不是编译成代码的一部分
```

例如测试需要读一个 JSON：

```python
cc_test(
    name = "parser_test",
    srcs = ["parser_test.cc"],
    data = ["testdata/sample.json"],
    deps = [":parser"],
)
```

`sample.json` 不是 C++ 源码，不应该放进 `srcs`。

不同语言规则的属性会有差异。例如 Python 有 `imports`、Java 有 `runtime_deps`，Go、Rust、TypeScript 也各有规则。先掌握 `name`、`srcs`、`hdrs`、`deps` 这几个核心概念，再去看具体语言规则会容易很多。

## 8. load 是什么

你在项目里可能会看到：

```python
load("//build:cc_defs.bzl", "project_cc_library")
```

`load` 的作用是从 `.bzl` 文件里导入名字。

可以粗略类比 Python：

```python
from build.cc_defs import project_cc_library
```

但注意：`BUILD` 和 `.bzl` 使用的是 Starlark 语言，不是普通 Python。语法很像 Python，但运行环境和能力被 Bazel 限制过。

`load` 的一般格式是：

```python
load("某个 .bzl 文件的 label", "要导入的名字1", "要导入的名字2")
```

例子：

```python
load("//build:cc_defs.bzl", "project_cc_library")
```

表示：

```text
从本仓库 build/cc_defs.bzl 里导入 project_cc_library。
```

再比如：

```python
load("@rules_python//python:defs.bzl", "py_binary", "py_test")
```

表示：

```text
从外部仓库 rules_python 的 python/defs.bzl 里导入 py_binary 和 py_test。
```

### 为什么需要 load

Bazel 内置一些规则，比如：

```python
cc_library
cc_binary
cc_test
```

但真实项目通常会封装自己的规则或宏：

```python
project_cc_library(
    name = "net",
    srcs = ["net.cc"],
    hdrs = ["net.h"],
    deps = ["//base:logging"],
)
```

这时你要先看文件顶部：

```python
load("//build:cc_defs.bzl", "project_cc_library")
```

然后打开：

```text
build/cc_defs.bzl
```

找：

```python
def project_cc_library(...):
    ...
```

很多项目看起来难，不是因为 Bazel 本身多复杂，而是因为项目封装了很多宏。读懂 `load`，就知道去哪里追定义。

## 9. rule 和 macro

在 `BUILD` 文件中你看到的这些通常是 rule：

```python
cc_library(...)
cc_binary(...)
cc_test(...)
py_library(...)
py_binary(...)
java_library(...)
```

rule 会真正定义一个 Bazel target，也就是构建图里的节点。

项目里自定义的这些通常可能是 macro：

```python
project_cc_library(...)
my_py_test(...)
company_java_library(...)
```

macro 本质上是 `.bzl` 里定义的函数。它可能内部调用一个或多个 rule，帮项目统一默认参数。

例如：

```python
def project_cc_library(name, srcs, hdrs = [], deps = []):
    cc_library(
        name = name,
        srcs = srcs,
        hdrs = hdrs,
        deps = deps + [
            "//base:common",
        ],
        copts = [
            "-Wall",
        ],
    )
```

于是 `BUILD` 里写：

```python
project_cc_library(
    name = "net",
    srcs = ["net.cc"],
    hdrs = ["net.h"],
)
```

实际效果可能等价于：

```python
cc_library(
    name = "net",
    srcs = ["net.cc"],
    hdrs = ["net.h"],
    deps = ["//base:common"],
    copts = ["-Wall"],
)
```

所以看到陌生函数时，不要先猜它是什么。先找 `load`，再打开 `.bzl`。

## 10. Bazel 怎么测试代码

测试目标通常用 `*_test` 规则。

C++：

```python
cc_test(
    name = "add_test",
    srcs = ["add_test.cc"],
    deps = [":add"],
)
```

Python：

```python
py_test(
    name = "parser_test",
    srcs = ["parser_test.py"],
    deps = [":parser"],
)
```

Java：

```python
java_test(
    name = "ParserTest",
    srcs = ["ParserTest.java"],
    deps = [":parser"],
)
```

运行单个测试：

```bash
bazel test //math:add_test
```

运行某个目录下所有测试：

```bash
bazel test //math/...
```

运行整个仓库所有测试：

```bash
bazel test //...
```

常用测试输出参数：

```bash
bazel test //math:add_test --test_output=errors
```

它会在测试失败时显示错误输出。

测试日志通常可以从这里找：

```text
bazel-testlogs/
```

## 11. 常用命令

构建一个目标：

```bash
bazel build //app:server
```

运行一个程序：

```bash
bazel run //app:server
```

测试一个目标：

```bash
bazel test //math:add_test
```

测试所有目标：

```bash
bazel test //...
```

列出某个包里的所有目标：

```bash
bazel query //math:all
```

看某个目标依赖了什么：

```bash
bazel query "deps(//math:add_test)"
```

看谁依赖了某个目标：

```bash
bazel query "rdeps(//..., //math:add)"
```

看目标实际展开后的属性：

```bash
bazel query --output=build //math:add_test
```

这个命令对看 macro 展开后的结果很有用。

清理构建输出：

```bash
bazel clean
```

注意：`bazel clean` 会让后续构建失去一部分本地缓存收益，不要把它当成日常第一步。只有怀疑输出状态异常、工具链切换或本地缓存污染时再用。

## 12. 接手现有 Bazel 项目时怎么读

建议按这个顺序。

### 第一步：看根目录

先找：

```text
MODULE.bazel
WORKSPACE
WORKSPACE.bazel
.bazelrc
.bazelversion
```

重点判断：

- 项目主要用 Bzlmod 还是传统 WORKSPACE。
- 默认 Bazel 参数是什么。
- 是否指定了 Bazel 版本。
- 有没有特定 config，例如 `--config=linux`、`--config=debug`、`--config=ci`。

### 第二步：找到你关心代码所在目录的 BUILD

例如你在改：

```text
src/net/http_client.cc
```

就找附近的：

```text
src/net/BUILD
src/net/BUILD.bazel
```

如果当前目录没有，就往上或往相关模块目录找。一个 Bazel package 的边界由 `BUILD` / `BUILD.bazel` 决定。

### 第三步：看这个 BUILD 里有哪些 name

例如：

```python
cc_library(
    name = "http_client",
    ...
)

cc_test(
    name = "http_client_test",
    ...
)
```

这说明至少有：

```text
//src/net:http_client
//src/net:http_client_test
```

### 第四步：看 srcs 和 hdrs

看这个目标到底覆盖哪些源码。

```python
srcs = [
    "http_client.cc",
]

hdrs = [
    "http_client.h",
]
```

如果你改的文件不在任何目标的 `srcs`、`hdrs`、`data` 或相关属性里，Bazel 可能根本不会构建到它。

### 第五步：看 deps

依赖关系决定这个目标能使用哪些库。

```python
deps = [
    "//base:logging",
    "//net:url",
    "@com_google_absl//absl/strings",
]
```

看到 `//base:logging`，去读：

```text
base/BUILD
```

看到 `@com_google_absl//absl/strings`，知道这是外部依赖。

### 第六步：看 load

如果 BUILD 里用的是陌生函数：

```python
load("//build:defs.bzl", "project_cc_library")

project_cc_library(
    name = "http_client",
    ...
)
```

就打开：

```text
build/defs.bzl
```

找：

```python
def project_cc_library(...):
    ...
```

确认它内部到底生成了什么规则、默认加了什么依赖、默认带了什么编译参数。

### 第七步：用 bazel query 辅助

如果你不确定目标名：

```bash
bazel query //src/net:all
```

如果你想看依赖树：

```bash
bazel query "deps(//src/net:http_client_test)"
```

如果你想知道某个库影响哪些地方：

```bash
bazel query "rdeps(//..., //base:logging)"
```

如果宏太复杂，想看展开后的 BUILD：

```bash
bazel query --output=build //src/net:http_client
```

## 13. 一个 BUILD 文件的翻译例子

看到这样的文件：

```python
load("//build:cc_defs.bzl", "project_cc_library")

project_cc_library(
    name = "net",
    srcs = ["net.cc"],
    hdrs = ["net.h"],
    deps = [
        "//base:logging",
        "@com_google_absl//absl/strings",
    ],
)

cc_test(
    name = "net_test",
    srcs = ["net_test.cc"],
    deps = [
        ":net",
        "//test:assertions",
    ],
)
```

可以翻译成：

```text
1. 从 build/cc_defs.bzl 导入 project_cc_library。
2. 定义一个叫 net 的库，对应完整 label：//当前包:net。
3. net 的实现文件是 net.cc。
4. net 对外暴露的头文件是 net.h。
5. net 依赖本项目里的 //base:logging。
6. net 依赖外部仓库 com_google_absl 里的 absl/strings。
7. 定义一个叫 net_test 的 C++ 测试。
8. net_test 的源码是 net_test.cc。
9. net_test 依赖当前包里的 :net。
10. net_test 还依赖本项目里的 //test:assertions。
```

这个翻译过程就是读 Bazel 项目的基本功。

## 14. 新手最常见误区

### 误区一：把 BUILD 当成普通 Python

`BUILD` 文件语法像 Python，但它是 Starlark。不要期待它能随便读文件、访问网络、执行系统命令。

### 误区二：只看 include，不看 deps

C++ 里写了：

```cpp
#include "base/logging.h"
```

不代表 Bazel 自动知道你依赖 `//base:logging`。

通常你还要在 `BUILD` 里写：

```python
deps = ["//base:logging"]
```

### 误区三：不知道 :target 是当前包简写

```python
deps = [":add"]
```

不是奇怪语法，它就是当前 `BUILD` 文件所在包里的 `add` 目标。

### 误区四：遇到自定义函数就放弃

看到：

```python
company_cc_library(...)
```

先看顶部 `load`，找到 `.bzl` 文件。大多数项目封装都能顺着这个路径追下去。

### 误区五：一上来就 bazel clean

构建失败不一定是缓存问题。先看报错、看缺失依赖、看目标名、看 config。`bazel clean` 会增加后续构建时间，不应该成为默认动作。

## 15. 最小学习路线

如果只想尽快能看懂项目，建议按这个路线：

```text
1. 知道 Bazel 是构建系统，不是编译器。
2. 会读 //pkg:target、:target、@repo//pkg:target。
3. 会在 BUILD 里找 name、srcs、hdrs、deps。
4. 会顺着 deps 找到别的 BUILD。
5. 会顺着 load 找到 .bzl。
6. 会运行 bazel build、bazel test、bazel query。
7. 会用 bazel query --output=build 看宏展开后的结果。
```

掌握这些后，读大多数 Bazel 项目就不会完全迷路。

## 16. 小结

Bazel 项目的核心不是某一个神秘入口文件，而是一张由 target 组成的依赖图。

`BUILD` 文件负责定义图里的节点：

```text
cc_library
cc_binary
cc_test
```

`deps` 负责连接节点：

```text
add_test -> add -> base/logging
```

`label` 负责给节点命名：

```text
//math:add
:add
@repo//pkg:target
```

`load` 负责从 `.bzl` 文件导入项目自己的封装：

```python
load("//build:defs.bzl", "project_cc_library")
```

所以接手一个 Bazel 项目时，最稳的做法是：

```text
先看根目录配置，再看目标所在 BUILD；
先找 name、srcs、hdrs、deps，再顺着 load 追 .bzl；
最后用 bazel query 验证自己的理解。
```

把这套路径走熟，Bazel 就会从“一堆奇怪文件”变成“可追踪的构建图”。

## 参考资料

- Bazel 官方文档：BUILD files：[https://bazel.build/concepts/build-files](https://bazel.build/concepts/build-files)
- Bazel 官方文档：Labels：[https://bazel.build/concepts/labels](https://bazel.build/concepts/labels)
- Bazel 官方文档：Bzlmod / MODULE.bazel：[https://bazel.build/external/module](https://bazel.build/external/module)
- Bazel 官方文档：load 函数：[https://bazel.build/rules/lib/globals/build#load](https://bazel.build/rules/lib/globals/build#load)
- Bazel 官方文档：Query language：[https://bazel.build/query/language](https://bazel.build/query/language)
