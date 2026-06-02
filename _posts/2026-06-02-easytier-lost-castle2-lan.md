---
layout:     post
title:      EasyTier 组虚拟局域网联机《失落城堡2》的可行性评估
subtitle:   如果游戏真的支持 LAN Co-op，EasyTier 值得一试；如果实际只走官方服务器，它不能替代专用服
date:       2026-06-02 23:40:00 +0800
permalink:  /2026/06/02/easytier-lost-castle2-lan/
author:     ctzmx
header-img: /img/ct/1%20(218).jpg
catalog: true
tags:
    - Games
    - Network
    - EasyTier
---

# EasyTier 组虚拟局域网联机《失落城堡2》的可行性评估

时间：2026-06-02

## 结论

EasyTier 值得用来做一次《失落城堡2》虚拟局域网实验，但不能保证成功。

核心判断：

- EasyTier 本身具备组建虚拟局域网、P2P 打洞、NAT 穿透、子网代理、KCP 代理、TCP 转发等能力，官方也明确把“游戏加速”和“虚拟局域网”作为使用场景。
- 《失落城堡2》的英文 Steam 页面列出 `LAN Co-op`，但简中页面主要列出在线合作、本地/分屏合作和 Remote Play Together。页面信息存在不一致。
- 如果游戏内确实有可用的局域网合作入口，并且局域网房间发现能通过 EasyTier 的虚拟网卡或 UDP 广播中继工作，那么可行。
- 如果游戏的多人合作实际只走官方区域服务器或 Steam Lobby，中间没有真正的 LAN 直连路径，那么 EasyTier 不能绕过官方服务器，也不能从根本上解决官方服延迟。

实际可行性评级：中等，偏实验性质。建议投入 30 分钟做最小验证，不建议一开始就花时间搭复杂节点。

## 资料来源

- EasyTier 官网：[https://easytier.cn/](https://easytier.cn/)
- EasyTier GitHub：[https://github.com/EasyTier/EasyTier](https://github.com/EasyTier/EasyTier)
- EasyTier 下载页：[https://easytier.cn/en/guide/download.html](https://easytier.cn/en/guide/download.html)
- EasyTier 快速组网文档：[https://easytier.cn/en/guide/network/quick-networking.html](https://easytier.cn/en/guide/network/quick-networking.html)
- EasyTier 游戏启动器文档：[https://easytier.cn/guide/gui/easytier-game.html](https://easytier.cn/guide/gui/easytier-game.html)
- EasyTier v2.6.4 发布说明：[https://github.com/EasyTier/EasyTier/releases](https://github.com/EasyTier/EasyTier/releases)
- 《失落城堡2》Steam 页面：[https://store.steampowered.com/app/2445690/Lost_Castle_2/](https://store.steampowered.com/app/2445690/Lost_Castle_2/)
- 《失落城堡2》Steam 多人连接置顶帖：[https://steamcommunity.com/app/2445690/discussions/0/830448456536501638/](https://steamcommunity.com/app/2445690/discussions/0/830448456536501638/)

## EasyTier 是什么

EasyTier 是一个开源的 P2P 虚拟网络工具，官方描述是用 Rust 实现的简单、安全、去中心化 VPN 组网方案。它的目标不是传统公网代理，而是让多台设备进入同一个虚拟网络。

它比较适合这些场景：

- 多台电脑跨公网组成一个虚拟局域网。
- 两台 NAT 后面的机器通过公共节点辅助打洞，成功后尽量走 P2P 直连。
- 远程访问内网服务。
- 用虚拟网卡解决部分游戏局域网联机、远程桌面、NAS 访问等问题。
- 通过子网代理让某个局域网网段被 EasyTier 网络中的其他节点访问。

对游戏联机有价值的能力：

- 虚拟 IPv4 网络：玩家之间可以互相 ping EasyTier 分配的虚拟 IP。
- P2P 优先：打洞成功后，流量可以不经过中继节点。
- TCP / UDP 支持：游戏流量通常依赖 UDP。
- UDP 广播中继：v2.6.4 之后加入了 Windows 相关的 UDP 广播中继能力，但默认不启用，且需要管理员权限。
- EasyTierGame：官方游戏启动器方案，文档里提到默认启用 WinIPBroadcast，用来改善局域网游戏“找不到房间”的问题。

## 《失落城堡2》的联机形态

从 Steam 页面和社区信息看，《失落城堡2》至少支持：

- 在线合作。
- 本地/同屏/分屏合作。
- Steam Remote Play Together。
- 英文 Steam 页面显示过 `LAN Co-op`，但简中页面没有同样明确展示，存在信息不一致。

官方多人连接置顶帖重点建议：

- 开在线房间前，在营火处选择正确的服务器区域。
- 错误区域会造成明显连接问题。
- 有玩家反馈 Steam invite 进房可能导致区域或连接状态异常，使用游戏内房间码更容易排查。

这说明它的在线合作大概率依赖官方区域服务器或官方房间系统。EasyTier 对这条路径帮助有限。

## EasyTier 对《失落城堡2》可能有用的前提

EasyTier 只有在下面条件满足时才可能有效：

1. 游戏内有真实可用的“局域网合作”入口。
2. 局域网房间可以通过虚拟网卡发现，或者可以输入虚拟 IP 直连。
3. 游戏没有强制所有多人连接都走官方区域服务器。
4. Windows 防火墙允许《失落城堡2》和 EasyTier 通过虚拟网卡收发 UDP。
5. EasyTier 网络内所有玩家能互 ping，且延迟稳定。

如果游戏只是 Steam 页面写了 LAN Co-op，但客户端内没有入口，或者 LAN 入口仍然调用官方匹配服务，那么 EasyTier 组网不会解决问题。

## 最小实验方案

目标：验证 EasyTier 能否让两台远程 Windows 电脑像同一局域网一样被《失落城堡2》识别。

建议先用两个人测试，不要一开始拉四个人。

### 1. 准备

两边都做：

1. 下载 EasyTier 最新稳定版本。
2. 优先使用 EasyTierGame 或 EasyTier GUI；如果使用命令行，使用 `easytier-core.exe`。
3. Windows 上用管理员权限运行。
4. 防火墙允许 EasyTier 和《失落城堡2》通过专用网络。
5. 暂时关闭其他 VPN、代理软件的 TUN 模式、虚拟网卡优先级干扰项。

### 2. EasyTierGame 方式

这是更适合游戏的方式。

建议配置：

```text
网络名：lc2-test-随机字符串
网络密钥：一串足够长的随机密码
节点名：player-a / player-b
模式：优先 P2P
WinIPBroadcast：开启
```

验证：

1. 两边进入同一个 EasyTier 网络。
2. 查看对方虚拟 IP。
3. 互相 ping 对方虚拟 IP。
4. 如果 EasyTierGame 有节点延迟或路由信息，确认不是明显绕远。
5. 房主启动《失落城堡2》，寻找是否有 LAN / 局域网建房入口。
6. 客户端打开局域网合作，看能否发现房间。
7. 如果发现不了，尝试让房主关闭再开启房间、双方重启游戏、切换一次 WinIPBroadcast。

### 3. 命令行方式

下面命令只是实验模板，实际公共节点地址以 EasyTier 官方文档和当前版本为准。

房主：

```powershell
.\easytier-core.exe `
  --network-name lc2-test-xxxx `
  --network-secret "replace-with-a-long-random-secret" `
  --hostname player-a `
  --ipv4 10.44.2.1 `
  --peers tcp://public.easytier.cn:11010 `
  --latency-first
```

加入者：

```powershell
.\easytier-core.exe `
  --network-name lc2-test-xxxx `
  --network-secret "replace-with-a-long-random-secret" `
  --hostname player-b `
  --ipv4 10.44.2.2 `
  --peers tcp://public.easytier.cn:11010 `
  --latency-first
```

互 ping：

```powershell
ping 10.44.2.1
ping 10.44.2.2
```

如果命令行参数和当前版本不一致，以 `.\easytier-core.exe --help` 为准。

注意：如果局域网房间依赖 UDP 广播，命令行方案可能需要额外开启广播中继相关参数。Windows 上这类能力通常需要管理员权限。为了少踩坑，优先用 EasyTierGame。

## 测试判定表

| 测试结果 | 判断 |
| --- | --- |
| EasyTier 互 ping 不通 | EasyTier 组网未成功，先不要测游戏 |
| EasyTier 能 ping，但游戏没有 LAN 入口 | 《失落城堡2》当前客户端可能不支持可用 LAN 联机 |
| 有 LAN 入口，但搜不到房间 | 可能是 UDP 广播/虚拟网卡/防火墙问题，重点查 WinIPBroadcast、防火墙和网卡优先级 |
| 搜到房间但进不去 | 可能是游戏仍依赖 Steam Lobby、版本校验、端口或 NAT 状态 |
| 能进房但卡顿 | EasyTier 可用，但当前 P2P 路由或中继质量不够，需要优化节点和线路 |
| 能进房且延迟稳定 | EasyTier 方案可行，可以扩大到 3 到 4 人测试 |

## 如果搜不到房间，按这个顺序排查

1. 确认两边游戏版本一致。
2. 确认两边 EasyTier 网络名和密钥完全一致。
3. 确认能互 ping EasyTier 虚拟 IP。
4. Windows 防火墙允许 EasyTier 和 `LostCastle2.exe`。
5. EasyTierGame 中开启 WinIPBroadcast。
6. 关闭其他虚拟网卡或临时调整网卡优先级。
7. 房主先开 LAN 房，客户端再进 LAN 搜索。
8. 双方都重启游戏，不要只返回主菜单。
9. 如果游戏支持输入 IP，直接输入房主 EasyTier 虚拟 IP。
10. 如果仍失败，基本可以判断该游戏的 LAN 发现或连接不兼容当前 EasyTier 方案。

## 如果能进但很卡，按这个顺序优化

1. 观察 EasyTier 是否 P2P 直连。如果一直中继，延迟可能比官方服务器还差。
2. 两边都改用有线网络。
3. 换 EasyTier 公共节点或自建共享节点，只用它辅助打洞。
4. 选离双方都近的云主机作为 EasyTier 共享节点，例如香港、日本、新加坡或国内云厂商。
5. 打开延迟优先策略。
6. 如果运营商 UDP 打洞质量差，测试 KCP 代理或 TCP 转发，但这可能增加延迟。
7. 关闭下载、网盘同步、直播推流和加速器的 TUN 全局模式。

## 是否值得自建 EasyTier 公共节点

只有在下面情况才值得：

- 公共节点不稳定。
- 两边互 ping 可以通，但路径经常绕路。
- 官方服务器区域延迟高，而两边到某台云主机都很低。
- 多个朋友会长期使用同一套虚拟局域网。

不建议第一步就自建。先用官方公共节点或 EasyTierGame 跑通游戏，再考虑自建节点。

## 最终建议

对《失落城堡2》来说，EasyTier 不是确定解，但值得做一次低成本实验。

推荐实验路径：

1. 两人安装 EasyTierGame。
2. 开同一个网络名和密钥。
3. 确认互 ping。
4. 在游戏内找 LAN / 局域网合作入口。
5. 房主建 LAN 房，另一人搜索。
6. 如果失败，再回到官方在线合作路径，继续按服务器区域、房间码、房主网络和加速线路排查。

一句话结论：

```text
如果《失落城堡2》的 LAN Co-op 在客户端内真实可用，EasyTier 有机会把远程玩家伪装成同一局域网；
如果游戏实际只走官方在线服务器，EasyTier 不能替代服务器，也不能保证改善卡顿。
```
