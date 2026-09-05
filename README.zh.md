<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - MIT 许可证（见 LICENSE 文件） -->

<div align="center">
  <img src="docs/assets/omega-fire.png" alt="Omega-Fire" width="256">
</div>

# 󰦝 OMEGA-FIRE

**统一的网络安全管理平台**

> 由 **kraynux** 为 **Omega-server** 打造 
[https://kraynux.snake-mackarel.ts.net](https://kraynux.snake-mackarel.ts.net)

官方页面：[OMEGA-FIRE](https://kraynux.snake-mackarel.ts.net/omega-fire/) &nbsp; 预览：[Screenshots](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/)  

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)
[![Interface](https://img.shields.io/badge/Interface-Textual%20TUI-cyan.svg)](https://github.com/Textualize/textual)

🇫🇷 [Français](README.md) · 🇬🇧 [English](README.en.md) · 🇪🇸 [Español](README.es.md) · 🇷🇺 [Русский](README.ru.md) · 🇨🇳 **中文**

---

**Omega-Fire** 是一个基于 [Textual](https://github.com/Textualize/textual) 构建的 Python TUI（终端用户界面）应用程序。它在终端中提供一个统一的界面，用于管理 Linux 防火墙、Fail2Ban、被封禁的地址、网络规则、日志以及系统统计信息。

Textual 界面是默认的运行模式，通过菜单、经过校验的表单（所有必填字段在继续之前都会被检查）以及专用界面进行导航，并与 OMEGA 套件其余工具（omega-check、omega-deep、omega-stress……）共享主题、上下文帮助和键盘快捷键。旧版 [Rich](https://github.com/Textualize/rich) 界面（顺序式、通过输入编号操作）仍可通过 `--legacy-cli` 使用（参见[启动](#使用方法)）。

本项目依据 **Clean Architecture（整洁架构）** 原则设计，业务领域、编排逻辑、基础设施与用户界面之间有清晰的分层。

## 目录

- [简介](#简介)
- [功能](#功能)
- [架构](#架构)
- [前置条件](#前置条件)
- [安装](#安装)
- [使用方法](#使用方法)
- [配置](#配置)
- [后端与兼容性](#后端与兼容性)
- [持久化日志与导出](#持久化日志与导出)
- [安全性](#安全性)
- [测试与质量](#测试与质量)
- [项目现状](#项目现状)
- [卸载](#卸载)
- [许可证](#许可证)

---

## 简介

Omega-Fire 是网络安全的**本地操作平台**。它会自动检测机器上存在的组件，并根据实际可用的能力调整菜单。

### 目标

- 将 nftables、iptables、ip6tables 和 Fail2Ban 整合到一个统一的界面中。
- 便于观察和操作连接、封禁以及系统事件。
- 集中管理导出、备份、审计以及操作历史。
- 保持架构的可测试性与可扩展性。
- 在某个可选组件缺失时以降级模式运行。

### Omega-Fire 能做什么

- 检测可用的后端、服务、内核和工具。
- 在这些组件存在时管理 nftables、iptables 和 ip6tables。
- 管理被封禁的 IP（单个或批量），支持导入、导出、同步和清空。
- 创建、列出并删除高级规则。
- 应用预定义策略，并在此之前自动备份。
- 管理 Fail2Ban 的 jail 及其封禁记录。
- 实时分析日志，或以统计形式展示。
- 以监控形式提供系统监视功能。
- 在 conntrack 可用时用它显示活动连接。
- 生成 JSON、TXT 和 HTML 格式的导出。
- 将完整状态备份和恢复到 `.tar.gz` 归档文件中。
- 将操作记录到应用日志和结构化的 JSON 审计日志中。
- 监控检测到的服务与应用程序：systemd、runit、OpenRC、Docker、服务器、VNC 等。

### 本项目不做什么

- 它不会替代 nftables、iptables 或 Fail2Ban。
- 它不是一个独立于系统之外的防火墙。
- 它不提供多用户身份验证。
- 在正常运行时不会暴露任何网络 API。
- 它不是一个网页仪表盘。
- 它不能从另一台机器直接保护一台远程机器。
- 默认情况下它不会在自身目录之外安装任何文件。
- 它不保证所有后端在所有发行版上都可用。

---

## 功能

### 1. 能力与诊断

- 显示已检测到的能力注册表。
- 按标识符查看某项能力的详细信息。
- 在安装新组件后手动重新扫描系统。
- 查看最近的诊断信息。
- 查看并搜索应用日志。
- 将状态和诊断信息导出为 JSON、TXT 或 HTML。

### 2. 统一的 IP 管理

统一黑名单允许在同一个界面中同时操作 nftables 和 iptables。

- 封禁单个 IP 或一组 IP。
- 单个或批量解封。
- 直接输入或从文件导入。
- 按后端查看或统一视图查看。
- 在 NFTables/IPTables 后端之间同步。
- 导出并重新导入列表。
- 完全清空一个或多个后端。
- 支持 IPv4 和 IPv6。
- 直接从专用界面管理黑名单文件（`var/blocklist/`）及其收藏项。

### 3. 规则与策略管理

- 分步向导用于创建高级规则。
- 列出系统规则以及 Omega-Fire 创建的规则。
- 通过选择删除某条规则。
- 自动清理参照库中的无效规则。
- 应用预定义策略。
- 在应用策略前自动备份。
- 自定义、保存并恢复某个策略。
- 在状态菜单和仪表盘中标识当前激活的策略。
- 以 `Profil + CUSTOM`（配置文件 + 自定义）的形式标记被修改过的配置文件。

### 4. Fail2Ban 管理

- 查看各 jail 及其参数的详细状态。
- 已封禁 IP 数量以及速率限制信息。
- 在各 jail 中搜索某个 IP。
- 单个或批量的封禁/解封操作。
- 在 jail、后端和文件之间转移 IP。
- 引导式创建自定义 jail。
- 预定义的 jail 模板。
- 删除某个 jail。
- 清空某个 jail 或执行全面清空。
- 导出为 JSON、TXT 或 HTML。
- 校验并审计配置。
- 控制服务：状态查看、启动、停止、重启、开机自启的启用与禁用。

### 5. 日志与维护

- 带有 Omega-Fire 仪表盘的实时日志追踪（Live Tail）。
- 支持多文件显示，并可收藏常用来源（在两次启动之间保持持久化）。
- 集成 `lnav`：可选择一个或多个文件（用编号或手动输入路径，以逗号分隔），自动合并为一个按时间排序的单一视图，并封装在 Omega-Fire 的页眉/页脚中（参见[导航](#使用方法)）。
- 使用 Top N 分析出现频率最高的 IP。
- 在 LOG 或 TXT 文件中针对性清理某个 IP。
- 立即或自动化的日志轮转与备份。
- 恢复某个备份。
- 按存留时间、配额、类型或手动选择进行清理。
- 按目录或环境进行高级清理。
- 24 小时、7 天或 30 天的统计信息。
- 分析 jail 中的事件、变动、配额和现有 IP。

### 6. 导出与报告

可用格式：

- **JSON**：结构化且可重复使用的数据。
- **TXT**：原始格式或适合注入使用的格式。
- **HTML**：可读性强的可视化报告。

可用报告：

- 完整黑名单。
- 结构化规则集。
- 按来源筛选的规则：系统、Omega-Fire 或当前生效的规则。
- 完整审计报告。
- Fail2Ban 统计信息。
- 系统状态与诊断信息。
- 7 天或 30 天的统计报告。

HTML 主题：

- `omega-base` — 深蓝与青色，默认主题。
- `omega-burn` — 红橙余烬色调。
- `omega-neon` — 青色与洋红的赛博朋克风格。
- `light-basic` — 明亮简洁。
- `light-alt` — 米色纸张与森林绿。

### 7. 系统与持久化

- 备份完整状态：规则、nftables 封禁记录、iptables 封禁记录和 Fail2Ban 记录。
- 创建带时间戳的 `.tar.gz` 归档文件。
- 列出并恢复快照。
- 操作历史记录。
- 筛选并清理历史记录。
- 无需重启即可重新加载配置并重新扫描。

### 8. 监控与统计

- 实时仪表盘，周期性刷新（每 2 秒一次），收集数据期间不会阻塞界面。
- 查看当前生效的策略。
- 通过 conntrack 查看活动连接。
- 流量、事件、统计信息及服务器日志。
- 7 天和 30 天的综合报告。
- 导出快照和报告为 HTML 格式。

### 9. 设置

- 从与套件其余工具共享的十种 `omega-*` 主题中选择当前主题（参见[主题与终端](#主题与终端)），并在两次启动之间保持持久化。
- 手动覆盖渲染模式（自动、完整、标准、精简或纯 ASCII 单色），在下次启动时生效。
- 可从主菜单（`9. RÉGLAGES`）或直接通过按键 `s` 访问。

---

## 架构

```text
src/omega_fire/
├── app/              启动引导与依赖注入容器
├── core/             能力、枚举与异常
├── domain/           纯业务逻辑：规则、IP、jail、日志
├── application/      编排层：commands 与 queries
├── infrastructure/   后端、存储、导出、日志与系统探测
├── ports/            Protocol/ABC 契约
├── interfaces/       interfaces/tui/（Textual，默认）+ interfaces/cli/（Rich，--legacy-cli）
├── plugins/          内置扩展：nftables、iptables、Fail2Ban、conntrack
└── shared/           解析、网络、格式化及跨层工具函数
```

### 设计原则

- `domain/` 既不包含任何 I/O 操作，也不依赖 infrastructure。
- `application/` 通过 domain 和 ports 编排各类用例——Textual 界面与 Rich 界面的操作调用的是同一批 commands/queries，业务逻辑不依赖任何一种界面。
- `infrastructure/` 是唯一被允许调用 `nft`、`iptables`、`fail2ban-client` 及其他外部工具（subprocess、pty、文件操作）的层。
- `interfaces/` 不得直接调用 `subprocess`。
- `ports/` 定义适配器所需遵循的契约。
- `core/` 提供各层共用的能力注册表。
- 插件机制使得可以在不修改业务领域的情况下新增或演进后端。
- Textual 界面（`interfaces/tui/`）依赖 [`omega-lib`](https://github.com/)（整个 OMEGA 套件共享的依赖：9 项令牌构成的主题、终端检测、通用端口契约），该库未发布到 PyPI —— 已在可分发的归档包中随附（`vendor/omega-lib/`，参见[安装](#安装)）。
- 从 Textual 界面触发的任何可能耗时的调用（防火墙后端、`fail2ban-client`、磁盘操作）都会在后台线程中执行，绝不会占用界面主线程——仪表盘或表单在操作期间保持响应，而不会让整个应用卡死。

### 数据结构

Omega-Fire 通过标准库 `sqlite3` 使用 SQLite，不依赖任何外部 ORM。主要的数据集合涉及封禁记录、规则、审计事件和快照。

数据库迁移带有版本号，并在启动时自动应用。

---

## 前置条件

### 系统

- Linux，优先支持 Arch Linux 及兼容发行版。
- Python 3.10 或更高版本。
- 可通过 `sudo` 获取 root 权限。
- 一个服务管理器：systemd、runit 或 OpenRC。
- 至少一个防火墙后端：nftables 或 iptables。
- 至少 80x24 大小的终端（关于根据可用大小划分的渲染模式详情，参见[主题与终端](#主题与终端)）。

### Python 依赖

生产环境依赖定义在 `requirements.txt` 中：

- `textual` — 默认的 TUI 界面。
- `omega-lib` — 与 OMEGA 套件共享的主题、终端检测和契约（未发布到 PyPI，参见[架构](#架构)和[安装](#安装)）。
- `rich` — 用于渲染 `--legacy-cli` 界面以及部分报告。
- `psutil` — 供仪表盘和诊断使用的系统信息（CPU、内存、网络、进程）。
- `jinja2` — 生成 HTML 导出文件。
- `python-dotenv` — 环境变量管理。
- `pyte` — 虚拟终端模拟器，用于封装 `lnav`（菜单 5.9/8.6）。

质量工具（`pytest`、`black`、`flake8`、`mypy`）在 `requirements.txt` 中以注释形式列出：如果您要为项目贡献代码，请取消注释或单独安装它们（参见[测试与质量](#测试与质量)）。

### 推荐的可选工具

如果以下工具缺失，应用程序将以降级模式运行：

- `fail2ban` — 自动化封禁。
- `conntrack` 或 `conntrack-tools` — 活动连接与网络统计信息。
- `lnav` — 高级的多文件日志分析。

在 Arch Linux 及其衍生发行版上：

```bash
sudo pacman -S fail2ban conntrack-tools lnav
```

---

## 安装

官方归档以 `.tar.gz` 格式提供。安装前请先校验其完整性：

```bash
sha256sum omega-fire.tar.gz
```

> ⚠️ **以下三种方法仅适用于首次安装。** 如果 `~/omega-fire` 已经存在（升级自之前的版本），请改用下方的[更新](#更新)章节 —— 切勿在已存在的 `omega-fire` 目录内部重新执行这些命令：`tar` 会尝试创建一个嵌套的 `omega-fire/omega-fire/`，如果该目录属于 root（常见于此前误用 `sudo tar` 解压的情况），则会因权限错误而失败。

### 方法一 — 安装脚本

```bash
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ 您似乎已经位于 omega-fire 目录内 —— 请参阅 README 的更新章节。" >&2; exit 1; }
[ -d omega-fire ] && echo "ℹ️ 已在此解压，跳过此步骤。" || tar -xzf omega-fire.tar.gz
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire 已存在，跳过移动。" || mv omega-fire ~/
cd ~/omega-fire/
chmod +x install.sh
./install.sh
```

启动：

```bash
./omega-fire.sh
```

如果已安装别名，请打开一个新终端后使用：

```bash
fire
```

### 方法二 — 完整的可重复安装

此命令可以重复执行：它会跳过已经完成的步骤。

```bash
([ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ 您似乎已经位于 omega-fire 目录内 —— 请参阅 README 的更新章节。" >&2; exit 1; }; [ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire 已存在，跳过解压。" || (tar -xzf omega-fire.tar.gz && mv omega-fire ~/)) && cd ~/omega-fire/ && ([ -d .venv ] && echo "ℹ️ .venv 已存在，跳过此步骤。" || python3 -m venv .venv) && source .venv/bin/activate && ([ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib || true) && pip install -r requirements.txt && chmod +x omega-fire.sh && mkdir -p var && (getent group omega-fire >/dev/null 2>&1 && echo "ℹ️ omega-fire 组已存在。" || sudo groupadd omega-fire) && (groups "$USER" 2>/dev/null | grep -qw omega-fire && echo "ℹ️ $USER 已是 omega-fire 组成员。" || sudo usermod -aG omega-fire "$USER") && sudo chgrp -R omega-fire var && sudo chmod -R 2775 var && echo "✅ Omega-Fire 已安装。运行 ./omega-fire.sh。"
```

### 方法三 — 详细安装

```bash
# 0. 确认没有在已存在的 omega-fire 目录内重新执行本流程
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ 您似乎已经位于 omega-fire 目录内 —— 请参阅 README 的更新章节。" >&2; exit 1; }

# 1. 解压
[ -d omega-fire ] && echo "ℹ️ 已在此解压，跳过此步骤。" || tar -xzf omega-fire.tar.gz

# 2. 移动到主目录
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire 已存在，跳过移动。" || mv omega-fire ~/

# 3. 进入项目目录
cd ~/omega-fire/

# 4. 创建虚拟环境
[ -d .venv ] && echo "ℹ️ .venv 已存在，跳过创建。" || python3 -m venv .venv

# 5. 安装依赖（如果存在随附的 omega-lib，会先于 requirements.txt 安装）
source .venv/bin/activate
[ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib
pip install -r requirements.txt

# 6. 使启动脚本可执行
chmod +x omega-fire.sh

# 7. 为 root 用户和当前用户准备 var/ 目录
mkdir -p var
getent group omega-fire >/dev/null 2>&1 || sudo groupadd omega-fire
groups "$USER" 2>/dev/null | grep -qw omega-fire || sudo usermod -aG omega-fire "$USER"
sudo chgrp -R omega-fire var
sudo chmod -R 2775 var

# 8. 启动
./omega-fire.sh
```

`vendor/omega-lib/` 仅存在于官方归档中（`build-release.sh` 会自动将其纳入，因为 omega-lib 未发布到 PyPI）；在开发环境的克隆版本中，请从其自己的仓库单独安装（`pip install -e 指向omega-lib的路径`）。

专用用户组和 `setgid` 位使得 root 和当前用户可以共享 `var/` 中产生的文件，而无需向整个系统开放权限。要立即获得该用户组的成员身份，可能需要重新登录，或执行 `newgrp omega-fire`。

### 更新

如果 `~/omega-fire` 已经存在（此前已安装过），**切勿在该目录内部重新执行安装命令**：`tar` 会尝试创建一个嵌套的 `omega-fire/omega-fire/` 并失败，如果该目录属于 `root`（常见于此前误用 `sudo tar` 解压的情况），通常会出现一连串"Permission denied"（权限被拒绝）错误。

推荐流程，从 **`~/omega-fire` 以外**的任意目录执行（通常就是 `~` 本身）：

```bash
# 1. 检查现有安装的状态和所有者
ls -ld ~/omega-fire

# 2. 将旧安装移到一边，而不是直接覆盖
sudo mv ~/omega-fire ~/omega-fire.old-$(date +%Y%m%d)

# 3. 将新归档直接解压到主目录
tar -xzf omega-fire.tar.gz -C ~/

# 4. 重新安装（重建虚拟环境、重新安装依赖、重新设置 var/ 权限）
cd ~/omega-fire
chmod +x install.sh
./install.sh

# 5. 启动
./omega-fire.sh
```

确认新安装工作正常后，可以删除旧的 `~/omega-fire.old-YYYYMMDD` 目录（`sudo rm -rf ~/omega-fire.old-YYYYMMDD`）。

### Bash 或 Zsh 别名

```bash
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.bashrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.bashrc
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.zshrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.zshrc
```

然后重新加载 shell：

```bash
source ~/.bashrc 2>/dev/null || source ~/.zshrc
```

### Nerd Fonts 图标与符号

如果图标不可用，请安装 Nerd Fonts 符号：

```bash
mkdir -p ~/.local/share/fonts
curl -fLo /tmp/NerdFontsSymbolsOnly.zip \
  https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip
unzip -o /tmp/NerdFontsSymbolsOnly.zip -d ~/.local/share/fonts
fc-cache -fv
```

---

## 使用方法

### 启动

```bash
cd ~/omega-fire
./omega-fire.sh

# 或者，如果已创建别名，直接输入：
fire
```

启动脚本会：

1. 检查 root 权限，如有必要则通过 `sudo` 重新启动。
2. 检测 `.venv`、`venv` 或系统自带的 Python。
3. 将 `PYTHONPATH` 配置指向 `src/`。
4. 启动 `python -m omega_fire` —— 默认使用 **Textual** 界面。

若要改为启动旧版 Rich 界面（顺序式输入编号操作）：

```bash
./omega-fire.sh --legacy-cli
```

### 总体流程

1. 启动画面（splash），随后如果终端过小会显示警告。
2. 系统能力检测（专用界面，不会阻塞）。
3. 主菜单：8 个主题分区（1-8）加上设置（9）。
4. 选择一个分区，再选择一个操作——每个操作会打开一个表单，所有必填字段在继续之前都会被校验。
5. 在任何敏感或具有破坏性的操作（清空、清除、恢复……）之前都会要求明确确认。
6. 耗时操作会在后台执行（等待期间界面仍可使用），完成后返回菜单并显示结果摘要。

### 导航

- 上/下方向键：在列表或菜单中移动光标。
- Tab / Shift+Tab：在表单的各字段之间切换。
- 回车键：选择或确认。
- 点击表格中的某一行：选中该行并预填相关字段（要收藏的来源、目标 jail 等）。
- `Esc`：返回上一个界面（从主界面按下时会要求确认退出）。
- `a`：上下文帮助——详细说明当前操作，如果尚未打开任何操作界面，则显示当前分区的全部操作说明。
- `t`：切换到下一个主题，无需确认。
- `r`：重新检测终端的大小和类型。
- `s`：打开设置（主题、渲染模式）。
- `q` / `Ctrl+Q`：退出，需要确认。

#### lnav 界面的特殊之处（5.9 / 8.6）

`lnav` 被封装在一个伪终端中，其自身视图外围始终保留 Omega-Fire 的页眉/页脚，以避免其原生快捷键与 Omega-Fire 的快捷键发生冲突：

- ↑↓ 方向键：在日志中导航（`lnav` 的原生快捷键，原样传递）。
- ←→ 方向键：在过长的行中水平滚动（`lnav` 的原生快捷键）。
- `g` / `G`：跳转到开头/结尾（`lnav` 的原生快捷键）。
- `Ctrl+C`：标记当前行并将其复制到系统剪贴板（替代 `lnav` 原生的复制命令，该命令在某些系统上可能会卡住）。
- 小写 `t`：切换到下一个主题，仅在此视图中生效（大写 `T` 仍是 `lnav` 用于显示行间时间间隔的原生快捷键）。
- `Ctrl+Q`：返回 Omega-Fire（正常关闭 `lnav`，而不退出整个应用程序）。

---

## 主题与终端

十种 `omega-*` 主题与 OMEGA 套件的其余工具共享：

```text
omega-base       omega-dark       omega-light
omega-neon       omega-burn       omega-pink
omega-hack       omega-contrast   omega-mono
omega-minimal
```

- 使用 `t` 在各主题之间切换，或直接从设置（`s`）中选择某个主题。
- 所选主题会被持久化保存，并在下次启动时恢复。
- Omega-Fire 会通过一个**渲染模式**自动调整视觉复杂度（边框、启动画面、信息密度）以适配检测到的终端：完整、标准、精简或纯单色（仅 ASCII）。该模式也可以从设置中手动覆盖。

| 最小尺寸 | 模式 | 典型终端 |
|---|---|---|
| 120×32 及以上 | 完整 | Ghostty、Alacritty、WezTerm、Kitty |
| 100×28 及以上 | 标准 | Konsole、GNOME Terminal、Terminator、xfce4-terminal |
| 80×24 及以上 | 精简 | urxvt、xterm、现代 SSH |
| 低于 80×24 | 单色（仅 ASCII） | Linux TTY、旧版 SSH |

低于 80×24 时，程序将拒绝启动（不满足最小尺寸要求）；请调整终端大小后重新启动，若调整后界面未自动更新，可使用 `r` 键刷新。

---

## 配置

具体配置可以在以下位置调整：

```text
omega-fire/config/omega-fire.conf
```

其中可以定义：

- 日志路径；
- 服务器与监控数据来源；
- 可用的后端或自定义路径；
- 需要分析的运行环境；
- 适配特定安装场景的参数。

配置会在重启时或手动重新扫描时（菜单 1.3 或 7.4）被重新读取。

### 内部路径与系统路径

默认情况下，Omega-Fire 在自己的目录中工作：

```text
var/exports/       # 项目内部目录
/var/exports/      # 系统绝对路径
```

因此开头的 `/` 具有重要意义。向系统进行的导入和导出操作必须由用户明确请求。

---

## 后端与兼容性

Omega-Fire 会检测各组件，并只启用可实际使用的功能。

| 组件 | 作用 | 状态 |
|---|---|---|
| nftables | 现代 IPv4/IPv6 防火墙 | 推荐 |
| iptables | IPv4 防火墙 | 兼容 |
| ip6tables | 配合 iptables 使用的 IPv6 防火墙 | 若可用则兼容 |
| Fail2Ban | Jail 与自动化封禁 | 可选 |
| conntrack | 活动连接 | 可选 |
| lnav | 高级日志分析 | 可选 |
| systemd、runit、OpenRC | 服务管理 | 自动检测 |
| Docker、VNC、服务器 | 检测到的应用与服务 | 视安装情况而定 |

### IPv4 与 IPv6

兼容的后端支持这两种地址类型：

- nftables：双栈支持 IPv4 与 IPv6；
- iptables/ip6tables：取决于可用的二进制程序；
- Fail2Ban：取决于 jail 及系统的配置。

相关组件会处理长格式、压缩格式、本地地址、混合格式、含零填充以及 CIDR 表示法的各种 IPv6 格式。

---

## 持久化日志与导出

### 持久化

- 通过 `sqlite3` 使用 SQLite。
- 与封禁记录、规则、审计和快照相关的数据表。
- 自动应用带版本号的数据库迁移。
- 完整状态的 `.tar.gz` 格式归档文件。
- 收藏项（常用日志来源）以及最近历史记录以 JSON 格式持久化保存（`var/runtime/`），可在重启后保留。

### 日志

- 应用文本日志：`var/logs/app.log`。
- 结构化的 JSON 审计日志，包含 `event_type`、`actor`、`action`、`result` 和 `details` 等字段。

### 导出

导出功能支持 JSON、TXT 和 HTML 格式，HTML 报告还提供多种 CSS 主题。

---

## 安全性

Omega-Fire 操作的是系统中的关键组件，使用时务必谨慎。

- 启动需要通过 `sudo` 获取 root 权限。
- 清空操作、全面清除以及应用策略都可能具有破坏性。
- 应用预定义策略前会自动触发一次备份。
- 在每次重大变更之前请手动进行一次备份。
- 每次操作之后请核实防火墙、jail 和连接的真实状态。
- 请先在一台可丢弃的机器或目标上进行测试。
- 进行 IPv4 测试时请使用 RFC 5737 规定的文档专用网段：`192.0.2.0/24`、`198.51.100.0/24` 和 `203.0.113.0/24`。
- 在生产机器上恢复导出文件或快照之前请先核实其内容。
- 不要为 `var/` 目录授予超出必要范围的权限。

---

## 测试与质量

项目拥有一套历史悠久的 152 个单元测试套件，编写于 Textual 迁移之前：它覆盖了业务领域、编排层（`application/`）、基础设施以及 Rich 界面（`interfaces/cli/`），但**尚未覆盖 `interfaces/tui/`**（默认的 Textual 界面）。此归档包中不包含 `tests/` 目录：如需运行测试，请从您的开发仓库中获取该目录。

```bash
source .venv/bin/activate
python -m unittest discover tests/unit -v
```

由于分层架构严格将业务领域与展示层分离（`domain/`、`application/`、以 `Protocol` 定义的 `ports/`，参见[架构](#架构)），这套测试即使经历了迁移也无需改动、依然有效：只有较新的 Textual 界面尚未拥有自己专属的测试覆盖。

如果您要为项目贡献代码，请安装 `requirements.txt` 中以注释形式声明的质量工具：

```bash
pip install pytest pytest-cov black flake8 mypy
```

安装后可用的工具：

```bash
black .
flake8 .
mypy src/
pytest --cov
```

---

## 项目现状

### 已就绪的功能点

- 统一的 Textual TUI，涵盖主要的网络安全机制，具备经过校验的表单、与 OMEGA 套件共享的主题及上下文帮助。
- 保留旧版 Rich 界面作为后备方案（`--legacy-cli`）。
- 自动检测系统能力。
- 管理可用的后端。
- 根据现有工具支持 IPv4/IPv6。
- 应用日志记录与审计。
- 备份与恢复。
- JSON、TXT 和 HTML 格式导出。
- 仪表盘与统计信息，在后台刷新且不阻塞界面。
- 已文档化的分层架构。

### 已知局限

- 152 个测试组成的套件尚未覆盖 Textual 界面（`interfaces/tui/`），该界面是在测试套件编写之后才出现的（参见[测试与质量](#测试与质量)）。
- `ExecutionPlan`/`PipelineStep` 机制在项目中仍部分保留。
- 各项功能的实际可用性取决于宿主机器上的二进制程序、服务、权限和配置情况。
- 旧版 Rich 界面（`--legacy-cli`）已不再是当前活跃开发的重点；保留它是为了在 Textual 界面于真实环境中被充分验证可靠之前提供过渡。

---

## 卸载

如果数据仍保留在项目目录中：

```bash
sudo rm -rf ~/omega-fire
```

请手动删除导出到其他位置的文件、添加到 `~/.bashrc` 或 `~/.zshrc` 中的 `fire` 别名，以及如果不再需要则删除专用用户组：

```bash
sudo groupdel omega-fire
```

只有在没有其他文件或服务依赖该用户组时，才应执行最后这条命令。

---

## 许可证

Omega-Fire 依据 **MIT** 许可证发布。完整文本请参见 [`LICENSE`](LICENSE) 文件。

---

> **Omega-Fire —— 观察、操控、审计、守护。**
>
> 面向 nftables、iptables、ip6tables、Fail2Ban、日志与网络监控的统一 TUI 界面。
