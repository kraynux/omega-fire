<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - MIT License (see LICENSE file) -->

<div align="center">
  <img src="docs/assets/omega-fire.png" alt="Omega-Fire" width="256">
</div>

# 󰦝 OMEGA-FIRE

**Unified network security management console**

> Developed by **kraynux** for **Omega-server** 
[https://kraynux.snake-mackarel.ts.net](https://kraynux.snake-mackarel.ts.net)

Official page: [OMEGA-FIRE](https://kraynux.snake-mackarel.ts.net/omega-fire/) &nbsp; Preview: [Screenshots](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/)  

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)
[![Interface](https://img.shields.io/badge/Interface-Textual%20TUI-cyan.svg)](https://github.com/Textualize/textual)

🇫🇷 [Français](README.md) · 🇬🇧 **English** · 🇪🇸 [Español](README.es.md) · 🇷🇺 [Русский](README.ru.md) · 🇨🇳 [中文](README.zh.md)

---

**Omega-Fire** is a Python TUI (Terminal User Interface) application built with [Textual](https://github.com/Textualize/textual). From a single terminal, it provides one interface to administer Linux firewalls, Fail2Ban, banned addresses, network rules, logs and system statistics.

The Textual interface is the default mode of operation, navigated through menus, validated forms (all required fields are checked before continuing) and dedicated screens, with themes, contextual help and keyboard shortcuts shared with the rest of the OMEGA suite (omega-check, omega-deep, omega-stress...). The former sequential, number-driven [Rich](https://github.com/Textualize/rich) interface remains available via `--legacy-cli` (see [Launch](#launch)).

The project is designed around **Clean Architecture** principles, with a clear separation between business domain, orchestration, infrastructure and user interface.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Backends and compatibility](#backends-and-compatibility)
- [Persistence, logs and exports](#persistence-logs-and-exports)
- [Security](#security)
- [Tests and quality](#tests-and-quality)
- [Project status](#project-status)
- [Uninstallation](#uninstallation)
- [License](#license)

---

## Overview

Omega-Fire acts as a **local control console** for network security. It automatically detects the components present on the machine and adapts its menus to the capabilities actually available.

### Goals

- Bring nftables, iptables, ip6tables and Fail2Ban together into a coherent interface.
- Make it easier to observe and act on connections, bans and system events.
- Centralize exports, backups, audits and the operation history.
- Keep the architecture testable and extensible.
- Operate in degraded mode when an optional component is missing.

### What Omega-Fire does

- Detects available backends, services, kernel and tools.
- Administers nftables, iptables and ip6tables when these components are present.
- Manages banned IPs, individually or in batches, with import, export, synchronization and flush.
- Creates, lists and deletes advanced rules.
- Applies predefined policies with an automatic backup taken beforehand.
- Administers Fail2Ban jails and their bans.
- Analyzes logs live or as statistics.
- Provides monitoring-style surveillance.
- Uses conntrack to display active connections when it is available.
- Produces JSON, TXT and HTML exports.
- Backs up and restores the complete state into `.tar.gz` archives.
- Logs operations to an application log and a structured JSON audit trail.
- Monitors detected services and applications: systemd, runit, OpenRC, Docker, servers, VNC, etc.

### What the project does not do

- It does not replace nftables, iptables or Fail2Ban.
- It is not a standalone firewall independent of the system.
- It does not provide multi-user authentication.
- It does not expose a network API in normal operation.
- It is not a web dashboard.
- It does not directly protect a remote machine from another machine.
- It does not install any file outside its own folder by default.
- It does not guarantee the availability of every backend on every distribution.

---

## Features

### 1. Capabilities and diagnostics

- Display of the detected capabilities registry.
- Detailed lookup of a single capability by identifier.
- Manual system re-scan after installing a component.
- Review of recent diagnostics.
- Browsing and search within the application log.
- Export of system state and diagnostics to JSON, TXT or HTML.

### 2. Unified IP management

The unified blacklist lets you work with nftables and iptables from a single screen.

- Ban a single IP or a list of IPs.
- Unban individually or in batches.
- Direct entry or import from a file.
- Per-backend list or unified view.
- Synchronization between the NFTables/IPTables backends.
- Export and re-import of lists.
- Complete flush of one or more backends.
- IPv4 and IPv6 support.
- Manage blocklist files (`var/blocklist/`) and their pins directly from the dedicated screen.

### 3. Rules and policy management

- Step-by-step wizard to create an advanced rule.
- List of system rules and rules created by Omega-Fire.
- Delete a rule by selection.
- Automatic cleanup of inactive rules in the reference database.
- Apply predefined policies.
- Automatic backup before applying a policy.
- Customize, save and restore a policy.
- Identification of the active policy in the status menu and the dashboard.
- Modified profiles flagged as `Profile + CUSTOM`.

### 4. Fail2Ban management

- Detailed state of jails and their parameters.
- Number of banned IPs and rate-limit information.
- Search for an IP across jails.
- Individual or bulk ban/unban.
- Transfer IPs between jails, backends and files.
- Guided creation of a custom jail.
- Predefined jail templates.
- Delete a jail.
- Flush a single jail or a full purge.
- Export to JSON, TXT or HTML.
- Configuration verification and audit.
- Service control: status, start, stop, restart, enable and disable at boot.

### 5. Logs and maintenance

- Live Tail with an Omega-Fire dashboard.
- Multi-file display with pins (favorite sources, persisted across launches).
- `lnav` integration: select one or more files (line numbers or manual paths, comma-separated), automatically merged into a single chronological view, encapsulated inside an Omega-Fire header/footer (see [Navigation](#navigation)).
- Top N analysis of the most frequent IPs.
- Targeted removal of an IP from LOG or TXT files.
- Immediate or scheduled rotation and backups.
- Restore a backup.
- Purge by age, quota, type or manual selection.
- Advanced cleanup by folder or environment.
- Statistics over 24 hours, 7 days or 30 days.
- Analysis of events, movements, quotas and IPs present in jails.

### 6. Exports and reports

Available formats:

- **JSON**: structured, reusable data.
- **TXT**: raw format or one suited for injection.
- **HTML**: readable, visual report.

Available reports:

- Complete blacklist.
- Structured ruleset.
- Rules selected by origin: system, Omega-Fire or active.
- Complete audit report.
- Fail2Ban statistics.
- System state and diagnostics.
- Statistical reports over 7 or 30 days.

HTML themes:

- `omega-base` — midnight blue and cyan, default theme.
- `omega-burn` — red-orange ember.
- `omega-neon` — cyberpunk cyan and magenta.
- `light-basic` — light and sober.
- `light-alt` — cream paper and forest green.

### 7. System and persistence

- Backup of the complete state: rules, nftables bans, iptables bans and Fail2Ban.
- Creation of timestamped `.tar.gz` archives.
- List and restore snapshots.
- Action history.
- Filter and purge the history.
- Reload configuration and re-scan without restarting.

### 8. Monitoring and statistics

- Real-time dashboard with periodic refresh (every 2 seconds), without blocking the interface during collection.
- Display of the active policy.
- Active connections via conntrack.
- Traffic, events, statistics and server logs.
- Consolidated reports over 7 and 30 days.
- HTML export of snapshots and reports.

### 9. Settings

- Choose the active theme among the ten `omega-*` themes shared with the rest of the suite (see [Themes and terminals](#themes-and-terminals)), persisted across launches.
- Manually override the render profile (automatic, complete, standard, reduced or mono only), applied on the next launch.
- Accessible from the main menu (`9. SETTINGS`) or directly via the `s` key.

---

## Architecture

```text
src/omega_fire/
├── app/              Bootstrap and dependency-injection container
├── core/             Capabilities, enums and exceptions
├── domain/           Pure business logic: rules, IPs, jails, logs
├── application/      Orchestration: commands and queries
├── infrastructure/   Backends, storage, exports, logs and system probes
├── ports/            Protocol/ABC contracts
├── interfaces/       interfaces/tui/ (Textual, default) + interfaces/cli/ (Rich, --legacy-cli)
├── plugins/          Built-in extensions: nftables, iptables, Fail2Ban, conntrack
└── shared/           Parsing, networking, formatting and cross-cutting utilities
```

### Design principles

- `domain/` contains no I/O and no dependency on infrastructure.
- `application/` orchestrates use cases via the domain and the ports — Textual screens and Rich interface actions call the same commands/queries; business logic depends on neither interface.
- `infrastructure/` is the only layer allowed to call `nft`, `iptables`, `fail2ban-client` and other external tools (subprocess, pty, files).
- `interfaces/` must never call `subprocess` directly.
- `ports/` defines the contracts expected from adapters.
- `core/` provides the capability registry used by the different layers.
- Plugins allow backends to be added or evolved without modifying the business domain.
- The Textual interface (`interfaces/tui/`) relies on [`omega-lib`](https://github.com/) (a dependency shared across the whole OMEGA suite: 9-token theme, terminal detection, common port contracts), not published on PyPI — vendored inside the distributable archive (`vendor/omega-lib/`, see [Installation](#installation)).
- Any potentially slow call (firewall backend, `fail2ban-client`, disk) triggered from a Textual screen runs in a background thread, never on the interface's main thread — a dashboard or a form stays responsive during the operation instead of freezing the whole application.

### Data structure

Omega-Fire uses SQLite via the `sqlite3` standard library, with no external ORM. The main datasets concern bans, rules, audit events and snapshots.

Migrations are versioned and applied automatically at startup.

---

## Requirements

### System

- Linux, primarily Arch Linux and compatible distributions.
- Python 3.10 or higher.
- Root privileges available via `sudo`.
- A service manager: systemd, runit or OpenRC.
- At least one firewall backend: nftables or iptables.
- A terminal of at least 80x24 (see [Themes and terminals](#themes-and-terminals) for the render-profile details depending on the available size).

### Python dependencies

Production dependencies are defined in `requirements.txt`:

- `textual` — default TUI interface.
- `omega-lib` — theme, terminal detection and contracts shared with the OMEGA suite (not published on PyPI, see [Architecture](#architecture) and [Installation](#installation)).
- `rich` — rendering for the `--legacy-cli` interface and some reports.
- `psutil` — system information (CPU, memory, network, processes) for the dashboard and diagnostics.
- `jinja2` — HTML export generation.
- `python-dotenv` — environment variables.
- `pyte` — virtual terminal emulator, for the `lnav` encapsulation (menus 5.9/8.6).

Quality tools (`pytest`, `black`, `flake8`, `mypy`) are listed as comments in `requirements.txt`: uncomment them or install them separately if you contribute to the project (see [Tests and quality](#tests-and-quality)).

### Recommended optional tools

The application runs in degraded mode if these tools are absent:

- `fail2ban` — automated banning.
- `conntrack` or `conntrack-tools` — active connections and network statistics.
- `lnav` — advanced, multi-file log analysis.

On Arch Linux and derivatives:

```bash
sudo pacman -S fail2ban conntrack-tools lnav
```

---

## Installation

The official archive is provided as a `.tar.gz`. Verify its integrity before installing:

```bash
sha256sum omega-fire.tar.gz
```

### Method 1 — installation script

```bash
[ -d omega-fire ] && echo "ℹ️ Already extracted here, step skipped." || tar -xzf omega-fire.tar.gz
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire already exists, move skipped." || mv omega-fire ~/
cd ~/omega-fire/
chmod +x install.sh
./install.sh
```

Launch:

```bash
./omega-fire.sh
```

If the alias has been installed, open a new terminal and use:

```bash
fire
```

### Method 2 — resilient full installation

This command can be re-run: it skips steps already completed.

```bash
([ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire already exists, extraction skipped." || (tar -xzf omega-fire.tar.gz && mv omega-fire ~/)) && cd ~/omega-fire/ && ([ -d .venv ] && echo "ℹ️ .venv already exists, step skipped." || python3 -m venv .venv) && source .venv/bin/activate && ([ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib || true) && pip install -r requirements.txt && chmod +x omega-fire.sh && mkdir -p var && (getent group omega-fire >/dev/null 2>&1 && echo "ℹ️ omega-fire group already present." || sudo groupadd omega-fire) && (groups "$USER" 2>/dev/null | grep -qw omega-fire && echo "ℹ️ $USER already a member of the omega-fire group." || sudo usermod -aG omega-fire "$USER") && sudo chgrp -R omega-fire var && sudo chmod -R 2775 var && echo "✅ Omega-Fire installed. Run ./omega-fire.sh."
```

### Method 3 — detailed installation

```bash
# 1. Extract
[ -d omega-fire ] && echo "ℹ️ Already extracted here, step skipped." || tar -xzf omega-fire.tar.gz

# 2. Move into the home directory
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire already exists, move skipped." || mv omega-fire ~/

# 3. Enter the project
cd ~/omega-fire/

# 4. Create the virtual environment
[ -d .venv ] && echo "ℹ️ .venv already exists, creation skipped." || python3 -m venv .venv

# 5. Install dependencies (vendored omega-lib, if present, before requirements.txt)
source .venv/bin/activate
[ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib
pip install -r requirements.txt

# 6. Make the launcher executable
chmod +x omega-fire.sh

# 7. Prepare var/ for root and the current user
mkdir -p var
getent group omega-fire >/dev/null 2>&1 || sudo groupadd omega-fire
groups "$USER" 2>/dev/null | grep -qw omega-fire || sudo usermod -aG omega-fire "$USER"
sudo chgrp -R omega-fire var
sudo chmod -R 2775 var

# 8. Launch
./omega-fire.sh
```

`vendor/omega-lib/` is only present in the official archive (`build-release.sh` bundles it automatically, since omega-lib is not published on PyPI); in a development clone, install it separately from its own repository (`pip install -e path/to/omega-lib`).

The dedicated group and the `setgid` bit let root and the user share the files produced under `var/` without opening permissions to the whole system. A new login session or `newgrp omega-fire` may be needed to immediately benefit from the group membership.

### Bash or Zsh alias

```bash
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.bashrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.bashrc
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.zshrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.zshrc
```

Then reload the shell:

```bash
source ~/.bashrc 2>/dev/null || source ~/.zshrc
```

### Icons and Nerd Fonts symbols

If icons are not available, install the Nerd Fonts symbols:

```bash
mkdir -p ~/.local/share/fonts
curl -fLo /tmp/NerdFontsSymbolsOnly.zip \
  https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip
unzip -o /tmp/NerdFontsSymbolsOnly.zip -d ~/.local/share/fonts
fc-cache -fv
```

---

## Usage

### Launch

```bash
cd ~/omega-fire
./omega-fire.sh

# or simply, if the alias was created:
fire
```

The launcher:

1. Checks for root privileges and re-launches via `sudo` if needed.
2. Detects `.venv`, `venv` or the system Python.
3. Sets `PYTHONPATH` to `src/`.
4. Launches `python -m omega_fire` — the **Textual** interface, by default.

To launch the former Rich interface (sequential number entry) instead:

```bash
./omega-fire.sh --legacy-cli
```

### General flow

1. Startup (splash) screen, then a warning if the terminal is too small.
2. System capability detection (dedicated, non-blocking screen).
3. Main menu: 8 thematic sections (1-8) plus settings (9).
4. Select a section, then an action — each action opens a form whose required fields are all validated before continuing.
5. Explicit confirmation before any sensitive or destructive operation (flush, purge, restore...).
6. Background execution for slow operations (the interface stays usable while waiting), then return to the menu with a result summary.

### Navigation

- Up/down arrows: move the cursor within a list or menu.
- Tab / Shift+Tab: navigate between the fields of a form.
- Enter: select or confirm.
- Click a table row: select it and pre-fill the relevant fields (source to pin, targeted jail, etc.).
- `Esc`: go back to the previous screen (asks for confirmation to quit from the home screen).
- `a`: contextual help — details the current action, or every action of the current section if no action screen is open yet.
- `t`: switch to the next theme, without confirmation.
- `r`: re-detect the terminal's size and family.
- `s`: open the settings (theme, render profile).
- `q` / `Ctrl+Q`: quit, with confirmation.

#### Particularities of the lnav screen (5.9 / 8.6)

`lnav` is encapsulated inside a pseudo-terminal with a persistent Omega-Fire header/footer around its own view, to avoid any collision between its native shortcuts and Omega-Fire's:

- Arrows ↑↓: navigate through the logs (native `lnav` shortcut, passed through as-is).
- Arrows ←→: scroll horizontally over long lines (native `lnav` shortcut).
- `g` / `G`: go to the start / end (native `lnav` shortcut).
- `Ctrl+C`: mark the current line and copy it to the system clipboard (replaces `lnav`'s native copy command, which can hang on some systems).
- lowercase `t`: next theme, specific to this view (uppercase `T` remains `lnav`'s native shortcut to display the elapsed time between lines).
- `Ctrl+Q`: return to Omega-Fire (closes `lnav` cleanly, without quitting the application).

---

## Themes and terminals

Ten `omega-*` themes are shared with the rest of the OMEGA suite:

```text
omega-base       omega-dark       omega-light
omega-neon       omega-burn       omega-pink
omega-hack       omega-contrast   omega-mono
omega-minimal
```

- Switch between themes with `t`, or pick one directly from the settings (`s`).
- The chosen theme is persisted and restored on the next launch.
- Omega-Fire automatically adapts visual complexity (borders, splash, information density) to the detected terminal via a **render profile**: Complete, Standard, Reduced or Mono (ASCII only). The profile can be manually overridden from the settings.

| Minimum size | Profile | Typical terminals |
|---|---|---|
| 120×32 or more | Complete | Ghostty, Alacritty, WezTerm, Kitty |
| 100×28 or more | Standard | Konsole, GNOME Terminal, Terminator, xfce4-terminal |
| 80×24 or more | Reduced | urxvt, xterm, modern SSH |
| below 80×24 | Mono (ASCII only) | Linux TTY, legacy SSH |

Below 80×24, launch is refused (minimum size required); resize the terminal and relaunch, or use `r` after resizing if the display did not update automatically.

---

## Configuration

Project-specific configuration can be adjusted in:

```text
omega-fire/config/omega-fire.conf
```

It can notably define:

- log paths;
- monitoring servers and sources;
- available backends or custom paths;
- environments to analyze;
- parameters tailored to a specific installation.

The configuration is reloaded on restart or during a manual re-scan (menu 1.3 or 7.4).

### Internal paths and system paths

By default, Omega-Fire works within its own folder:

```text
var/exports/       # folder internal to the project
/var/exports/      # absolute system path
```

The leading `/` is therefore significant. Imports and exports to the system must be explicitly requested by the user.

---

## Backends and compatibility

Omega-Fire detects components and only enables usable features.

| Component | Role | Status |
|---|---|---|
| nftables | Modern IPv4/IPv6 firewall | Recommended |
| iptables | IPv4 firewall | Compatible |
| ip6tables | IPv6 firewall via iptables | Compatible if available |
| Fail2Ban | Jails and automated bans | Optional |
| conntrack | Active connections | Optional |
| lnav | Advanced log analysis | Optional |
| systemd, runit, OpenRC | Service management | Automatic detection |
| Docker, VNC, servers | Detected applications and services | Depending on installation |

### IPv4 and IPv6

Both address families are supported by compatible backends:

- nftables: IPv4 and IPv6 in dual stack;
- iptables/ip6tables: depending on available binaries;
- Fail2Ban: depending on jail and system configuration.

Long, compressed, local, mixed, zero-padded and CIDR-notation IPv6 formats are handled by the relevant components.

---

## Persistence, logs and exports

### Persistence

- SQLite via `sqlite3`.
- Tables for bans, rules, audits and snapshots.
- Versioned migrations applied automatically.
- Complete-state archives in `.tar.gz` format.
- Pins (favorite log sources) and recent history persisted as JSON (`var/runtime/`), surviving a restart.

### Logs

- Text application log: `var/logs/app.log`.
- Structured JSON audit log, notably including `event_type`, `actor`, `action`, `result` and `details`.

### Exports

Exports are available in JSON, TXT and HTML, with several CSS themes for HTML reports.

---

## Security

Omega-Fire acts on critical system components and must be used with caution.

- Launching requires root privileges via `sudo`.
- Flush, full purge and applying a policy can be destructive.
- A predefined policy triggers an automatic backup before modification.
- Perform a manual backup before every major change.
- Check the actual state of the firewall, jails and connections after each operation.
- Test first on a machine or a disposable target.
- Use the RFC 5737 documentation networks for IPv4 testing: `192.0.2.0/24`, `198.51.100.0/24` and `203.0.113.0/24`.
- Verify exports and snapshots before restoring them on a production machine.
- Do not grant broader permissions than necessary to the `var/` folder.

---

## Tests and quality

The project has a historical suite of 152 unit tests, written before the Textual migration: it covers the business domain, orchestration (`application/`), infrastructure and the Rich interface (`interfaces/cli/`), but **does not yet cover `interfaces/tui/`** (the default Textual interface). This archive does not include the `tests/` folder: pull it from your development repository if you need to run it.

```bash
source .venv/bin/activate
python -m unittest discover tests/unit -v
```

Since the layered architecture strictly separates business domain from presentation (`domain/`, `application/`, `ports/` as `Protocol`, see [Architecture](#architecture)), this suite remains valid unchanged despite the migration: only the more recent Textual interface does not yet have its own dedicated coverage.

If you contribute to the project, install the quality tools declared as comments in `requirements.txt`:

```bash
pip install pytest pytest-cov black flake8 mypy
```

Tools available once installed:

```bash
black .
flake8 .
mypy src/
pytest --cov
```

---

## Project status

### Operational points

- Unified Textual TUI for the main network security mechanisms, validated forms, themes and contextual help shared with the OMEGA suite.
- Historical Rich interface kept as a fallback (`--legacy-cli`).
- Automatic capability detection.
- Management of available backends.
- IPv4/IPv6 support depending on the tools present.
- Application logging and audit.
- Backup and restore.
- JSON, TXT and HTML exports.
- Dashboard and statistics, refreshed in the background without blocking the interface.
- Documented layered architecture.

### Known limitations

- The test suite (152) does not yet cover the Textual interface (`interfaces/tui/`), written after it (see [Tests and quality](#tests-and-quality)).
- The `ExecutionPlan`/`PipelineStep` mechanism remains partially retained in the project.
- The exact availability of features depends on the binaries, services, permissions and configuration of the host machine.
- The historical Rich interface (`--legacy-cli`) is no longer the active development focus; it is kept while the Textual interface is fully hardened under real-world conditions.

---

## Uninstallation

If data remained inside the project folder:

```bash
sudo rm -rf ~/omega-fire
```

Manually remove any files exported elsewhere, any `fire` alias added to `~/.bashrc` or `~/.zshrc`, and the dedicated group if it is no longer used:

```bash
sudo groupdel omega-fire
```

Only run this last command if no other file or service depends on this group.

---

## License

Omega-Fire is distributed under the **MIT** license. See the [`LICENSE`](LICENSE) file for the full text.

---

> **Omega-Fire — Observe, control, audit, secure.**
>
> A unified TUI interface for nftables, iptables, ip6tables, Fail2Ban, logs and network monitoring.
