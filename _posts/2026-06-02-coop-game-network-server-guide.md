---
layout:     post
title:      合作游戏联机卡顿排查：失落城堡2、土豆兄弟与饥荒联机版
subtitle:   不能自建服时先排区域、路由和串流；能自建服时把服务器放到离玩家最近的稳定网络上
date:       2026-06-02 02:20:00 +0800
permalink:  /2026/06/02/coop-game-network-server-guide/
author:     ctzmx
header-img: /img/ct/1%20(218).jpg
catalog: true
tags:
    - Games
    - Network
    - Server
---

# 合作游戏联机卡顿排查：失落城堡2、土豆兄弟与饥荒联机版

这篇记录只讨论 PC / Steam 版本，时间点是 2026-06-02。先给结论：

| 游戏 | 能否部署官方专用服务器 | 联机形态 | 优先处理方向 |
| --- | --- | --- | --- |
| 失落城堡2 | 未发现官方自建专用服务器或独立服务端 | 在线合作、本地/分屏合作、Steam Remote Play Together；部分 Steam 页面也显示 LAN Co-op | 先确认区域服务器和进房方式，再排路由 |
| 土豆兄弟 | 未发现官方自建专用服务器 | 本地/分屏合作、Steam Remote Play Together | 它更像串流联机，优先优化主机上传、编码和 Remote Play 设置 |
| 饥荒联机版 | 可以部署专用服务器 | 客户端连接 Klei / Steam 服务器列表中的独立世界 | 用 Klei token + SteamCMD 部署 DST Dedicated Server |

这里的“不能部署”不是说一定没有任何民间逆向方案，而是没有找到官方支持的 dedicated server、独立服务端包或可维护的部署入口。联机问题优先按官方支持路径排查，不建议下载来路不明的“服务端”。

## 1. 失落城堡2：不能自建服，先排区域服务器

《失落城堡2》的 [Steam 商店页](https://store.steampowered.com/app/2445690/Lost_Castle_2/?l=schinese) 列出的多人功能以在线合作、本地/分屏合作和 Remote Play Together 为主；部分 Steam 页面也显示 LAN Co-op。但无论是否使用局域网合作，都没有看到“专用服务器”一类的玩家可部署服务端入口。

官方在 Steam 置顶帖 [Multiplayer Connection Issues? Here's the Fix!](https://steamcommunity.com/app/2445690/discussions/0/830448456536501638/) 里把多人连接问题重点指向服务器区域选择：开在线房间前，要在营火处选择离你最近的服务器。帖子里还提到游戏曾默认选择 China 区，错误区域会造成明显的连接问题。

可执行排查顺序：

1. 房主先在营火处切到正确服务器区域，再创建房间。不要只看“能进房”，要看进房后延迟和掉线情况。
2. 所有人都退出当前房间，重新进游戏或回到营火界面后再确认一次服务器区域。有玩家反馈界面显示的区域和底部实际区域可能不一致，切到别的区域再切回来能排除一次 UI 状态问题。
3. 优先用游戏内私人房间码进房，少用 Steam 邀请直接跳转。Steam 邀请如果把人带到错误区域或错误房间状态，会让排查变复杂。
4. 如果游戏内当前版本提供局域网合作，且所有玩家在同一物理局域网，优先试局域网合作。远程玩家用虚拟局域网工具只能当实验项，不能当作官方自建服务器方案。
5. 逐个测试裸连、关闭代理、关闭 VPN、打开加速器的不同线路。一次只改一个变量，避免同时改线路和房主导致结论混乱。
6. 让网络最稳定的人开房。房主最好使用有线网络，关闭下载、网盘同步、系统更新和直播推流。
7. 如果只在特定 Boss、特定地图或特定版本后卡顿，记录游戏版本、区域、房主位置、参与人数和掉线时间点，再去 Steam 讨论区反馈。

不建议做的事：

- 不要为了“自建服务器”随便转发端口。没有独立服务端时，端口转发通常解决不了官方中继、区域服务器或房间系统的问题。
- 不要下载不明来源的服务端压缩包。多人游戏服务端会接触 Steam 账号、联机 token 和网络权限，风险很高。

## 2. 土豆兄弟：不能部署服务器，本质上先优化串流

《土豆兄弟》的 [Steam 商店页](https://store.steampowered.com/app/1942280/Brotato/?l=schinese) 重点是单人、本地合作、同屏/分屏合作和 Steam Remote Play Together。没有看到官方在线专用服务器或自建服务端。

这意味着它的远程联机更接近“主机运行游戏，把画面串流给朋友，朋友把输入传回来”。Steam 的 [Remote Play Together 页面](https://store.steampowered.com/remoteplay) 也说明了这种模式：游戏在一台电脑上运行，远端玩家通过串流加入。

所以《土豆兄弟》的卡顿通常不是“服务器延迟”，而是这几类问题：

- 主机上传带宽不足，远端看到画面糊、掉帧或延迟高。
- 主机编码性能不足，画面还没发出去就已经排队。
- 远端下载或解码性能不足，串流画面到达后仍然卡。
- Wi-Fi 抖动、丢包或路由绕路，让输入和画面来回变慢。

可执行排查顺序：

1. 让电脑性能和上传带宽最好的人当主机。Remote Play 模式下，主机的上传和编码能力比“谁离官方服务器近”更重要。
2. 主机优先接有线网络；不能接有线时，用 5GHz 或 6GHz Wi-Fi，并靠近路由器。
3. 主机和远端都关闭下载、网盘同步、视频会议、直播推流和浏览器大文件播放。
4. 在 Steam Remote Play 设置里打开硬件编码；远端机器打开硬件解码。老显卡或核显异常时，反过来关闭一次做 A/B 测试。
5. 先把串流分辨率限制到 1080p；如果仍然卡，降到 720p。帧率也可以从 60 降到 30，先换稳定输入延迟。
6. 带宽限制不要盲目拉满。画面经常糊或卡住时，手动设一个稳定值，比如 10 到 30 Mbps，再观察输入延迟。
7. 尽量让远端玩家使用手柄，并在 Steam 输入里确认手柄顺序。键鼠共享、输入焦点和覆盖层有时会制造额外问题。
8. 关闭不必要的覆盖层，比如录屏、性能监控、显卡滤镜、聊天悬浮窗。先让 Steam Overlay 和手柄输入保持最小变量。
9. 如果 Steam Remote Play 在某条线路上持续不稳定，可以试 Parsec、Moonlight / Sunshine 或 Steam Link 等串流替代方案。这些不是自建游戏服务器，只是替换串流通道。

不建议做的事：

- 不要给《土豆兄弟》找所谓服务器端口。它没有官方独立服务端时，端口转发不会把 Remote Play 变成专用服务器。
- 不要把所有画质选项拉满再排查网络。串流模式下，画面越大、帧率越高，越吃编码、上传和解码。

## 3. 饥荒联机版：可以部署专用服务器

这里说的是《Don't Starve Together》，也就是“饥荒联机版”。单机版《Don't Starve》不是这个部署逻辑。

DST 可以部署官方专用服务器。Klei 论坛有 Windows 版 [Dedicated Server Quick Setup Guide](https://forums.kleientertainment.com/forums/topic/64212-dedicated-server-quick-setup-guide-windows/) 和 Linux 版 [2022 Updated Dedicated Server Quick Setup Guide](https://forums.kleientertainment.com/forums/topic/140715-2022-updated-dedicated-server-quick-setup-guide-linux/)。核心流程是：在 Klei 账号生成服务器配置和 token，用 SteamCMD 安装 Don't Starve Together Dedicated Server，然后启动 Master / Caves 分片。

### 3.1 什么时候值得自建

适合自建专服的情况：

- 朋友分布在固定地区，希望服务器常驻在线。
- 房主电脑经常关机，或者边玩边开房导致卡顿。
- 想固定模组、白名单、管理员、世界设置和自动重启。
- 想把服务器放在香港、日本、新加坡、国内云厂商或其他对大家平均延迟更低的位置。

不适合自建的情况：

- 只是两三个人偶尔玩一次，且房主网络稳定。直接游戏内建房更省事。
- 没有人愿意维护云主机、更新、备份和模组冲突。

### 3.2 准备 Klei token 和世界配置

1. 打开 [Klei Accounts 的游戏服务器页面](https://accounts.klei.com/account/game/servers?game=DontStarveTogether)。
2. 登录拥有《饥荒联机版》的 Klei 账号。
3. 新建一个 Don't Starve Together server。
4. 生成或下载服务器配置。Klei 的工具通常会给出一个集群目录，里面包含 `cluster.ini`、`cluster_token.txt`、`Master` 和可选的 `Caves`。
5. 不要把 `cluster_token.txt` 发到公开仓库，也不要截图公开。这个 token 相当于服务器身份凭据。

常见目录位置：

```text
Linux:
~/.klei/DoNotStarveTogether/MyDediServer

Windows:
Documents\Klei\DoNotStarveTogether\MyDediServer
```

`MyDediServer` 是集群名，可以换成你自己的名字。后面启动命令里的 `-cluster` 要和这个目录名一致。

### 3.3 Linux 部署方式

下面以 Ubuntu / Debian 风格服务器为例。实际路径可以按自己的习惯调整，但建议用单独的 `steam` 用户运行，不要用 root 长期跑游戏服务器。

安装 SteamCMD 和服务端：

```bash
sudo adduser steam
sudo -iu steam

mkdir -p ~/steamcmd ~/steamapps/DST ~/.klei/DoNotStarveTogether
cd ~/steamcmd

# 如果发行版软件源已经提供 steamcmd，也可以直接 apt install steamcmd。
# 关键是最终能执行 steamcmd。
steamcmd +force_install_dir "$HOME/steamapps/DST" \
  +login anonymous \
  +app_update 343050 validate \
  +quit
```

把 Klei 下载的集群目录上传到：

```text
/home/steam/.klei/DoNotStarveTogether/MyDediServer
```

确认至少有这些文件：

```text
MyDediServer/
  cluster.ini
  cluster_token.txt
  Master/
    server.ini
    worldgenoverride.lua
  Caves/
    server.ini
    worldgenoverride.lua
```

如果不开洞穴，可以不启动 `Caves` 分片，也不需要保留 `Caves` 目录。

创建启动脚本：

```bash
cat > ~/run_dst.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

install_dir="$HOME/steamapps/DST"
cluster_name="MyDediServer"

steamcmd +force_install_dir "$install_dir" \
  +login anonymous \
  +app_update 343050 validate \
  +quit

cd "$install_dir/bin64"

./dontstarve_dedicated_server_nullrenderer_x64 \
  -console \
  -cluster "$cluster_name" \
  -shard Caves &

./dontstarve_dedicated_server_nullrenderer_x64 \
  -console \
  -cluster "$cluster_name" \
  -shard Master
EOF

chmod +x ~/run_dst.sh
./run_dst.sh
```

不开洞穴时，把 `-shard Caves` 那段删掉，只启动 `Master`。

### 3.4 Windows 部署方式

Windows 更适合本机测试或朋友小规模固定开服。长期运行仍建议用 Linux VPS。

先安装 SteamCMD，然后执行：

```bat
steamcmd.exe +login anonymous +app_update 343050 validate +quit
```

把 Klei 生成的集群目录放到：

```text
%USERPROFILE%\Documents\Klei\DoNotStarveTogether\MyDediServer
```

启动 Master 和 Caves：

```bat
cd /D "C:\steamcmd\steamapps\common\Don't Starve Together Dedicated Server\bin64"

start dontstarve_dedicated_server_nullrenderer_x64.exe -console -cluster MyDediServer -shard Master
start dontstarve_dedicated_server_nullrenderer_x64.exe -console -cluster MyDediServer -shard Caves
```

如果安装目录不同，把 `cd` 路径换成自己的 Dedicated Server 安装路径。

### 3.5 端口和防火墙

DST 的每个 shard 都要有独立端口。常见配置在 `Master/server.ini` 和 `Caves/server.ini` 里：

```ini
[NETWORK]
server_port = 10999

[STEAM]
authentication_port = 8766
master_server_port = 27016
```

洞穴分片要换成另一组端口，例如：

```ini
[NETWORK]
server_port = 11000

[STEAM]
authentication_port = 8767
master_server_port = 27017
```

公网服务器至少要放行每个 shard 的 UDP `server_port`。如果服务器列表、Steam 认证或 NAT 环境有问题，也把 `authentication_port` 和 `master_server_port` 对应的 UDP 端口放行并转发。

`cluster.ini` 里还有 shard 之间通信的 `master_port`，常见值是 `10888`。Master 和 Caves 在同一台机器上时，让它只绑定 `127.0.0.1` 即可，不要暴露到公网。只有多机器分片部署时，才需要让分片机器之间互通这个端口，并用防火墙限制来源 IP。

### 3.6 专服卡顿的优化顺序

1. 服务器位置比配置更重要。先选所有玩家平均延迟最低、丢包最低的地区。
2. 用有固定公网 IP 或稳定端口映射的机器。家庭宽带做专服时，运营商 NAT 会增加排查成本。
3. Master 和 Caves 不要端口冲突。每个 shard 的 `server_port`、`authentication_port`、`master_server_port` 都要唯一。
4. 模组越多，CPU、内存和同步压力越大。先无模组跑通，再逐个加模组。
5. 不要把云主机 CPU 长期打满。DST 对单核性能和瞬时抖动比较敏感。
6. 定期备份整个集群目录，尤其是 `Master/save`、`Caves/save`、`cluster.ini` 和 `cluster_token.txt`。
7. 服务器更新后如果进不去，先跑一次 `app_update 343050 validate`，再看 `server_log.txt`。
8. 如果服务器列表看不到，先用直连或收藏检查，再查端口、防火墙、密码、token 和 Klei 账号配置。

### 3.7 基础安全设置

至少建议做这些：

- 给服务器设置密码，或者维护白名单。
- 把管理员写进 `adminlist.txt`，不要共享 Klei token。
- 用普通用户运行服务端，不要用 root / Administrator 长期运行。
- 只开放必要 UDP 端口。
- 定期备份，更新前先备份。

## 4. 一句话决策树

如果是《失落城堡2》，先处理服务器区域、房间码、房主网络和加速线路。它没有官方自建服入口。

如果是《土豆兄弟》，按串流游戏处理。主机上传、编码、Remote Play 设置和手柄输入顺序，比端口转发更关键。

如果是《饥荒联机版》，可以认真自建专服。先用 Klei 账号生成 token 和集群配置，再用 SteamCMD 安装 app `343050`，最后按 shard 放行 UDP 端口并长期维护。

## 参考入口

- [Lost Castle 2 - Steam 商店页](https://store.steampowered.com/app/2445690/Lost_Castle_2/?l=schinese)
- [Lost Castle 2 - Multiplayer Connection Issues? Here's the Fix!](https://steamcommunity.com/app/2445690/discussions/0/830448456536501638/)
- [Brotato - Steam 商店页](https://store.steampowered.com/app/1942280/Brotato/?l=schinese)
- [Steam Remote Play](https://store.steampowered.com/remoteplay)
- [Klei - Dedicated Server Quick Setup Guide, Windows](https://forums.kleientertainment.com/forums/topic/64212-dedicated-server-quick-setup-guide-windows/)
- [Klei - 2022 Updated Dedicated Server Quick Setup Guide, Linux](https://forums.kleientertainment.com/forums/topic/140715-2022-updated-dedicated-server-quick-setup-guide-linux/)
- [Klei Accounts - Don't Starve Together Game Servers](https://accounts.klei.com/account/game/servers?game=DontStarveTogether)
