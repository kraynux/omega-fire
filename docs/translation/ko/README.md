<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->

<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-fire.png" alt="Omega-Fire" width="384">
</div>

# 󰦝 OMEGA-FIRE

**네트워크 보안 통합 관리 스테이션**

> [kraynux](https://github.com/kraynux)가 [Omega-Server](https://kraynux.snake-mackarel.ts.net)를 위해 개발   

공식 페이지: [OMEGA-FIRE](https://kraynux.snake-mackarel.ts.net/omega-fire/) &nbsp; 미리 보기: [스크린샷](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/)  

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)
[![Interface](https://img.shields.io/badge/Interface-Textual%20TUI-cyan.svg)](https://github.com/Textualize/textual)

🌐 문서, 내보내기 및 인터페이스를 **17개 언어**로 제공합니다 — [인터페이스 언어](#인터페이스-언어)를 참조하십시오.  
**언어:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

**Omega-Fire**는 [Textual](https://github.com/Textualize/textual)로 만든 Python TUI(Terminal User Interface) 애플리케이션입니다. 터미널에서 하나의 인터페이스로 Linux 방화벽, Fail2Ban, 차단된 주소, 네트워크 규칙, 로그, 시스템 통계를 관리할 수 있습니다.

Textual 인터페이스가 기본 작동 모드이며 메뉴, 검증된 폼(필수 항목은 모두 다음 단계로 넘어가기 전에 확인됨), 전용 화면으로 이동합니다. 테마, 상황별 도움말, 키보드 단축키는 OMEGA 도구 모음의 나머지(omega-check, omega-deep, omega-stress...)와 공유됩니다. 번호를 입력해 순서대로 조작하는 예전 [Rich](https://github.com/Textualize/rich) 인터페이스도 `--legacy-cli`로 계속 사용할 수 있습니다([실행](#실행) 참조). 
미리 보기: [스크린샷](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/index-2.html)

<p align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/translation/ko/omega-fire/A.png" width="24%" />
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/translation/ko/omega-fire/B.png" width="24%" />
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/translation/ko/omega-fire/C.png" width="24%" />
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/translation/ko/omega-fire/D.png" width="24%" />
</p>

이 프로젝트는 **Clean Architecture** 원칙에 따라 설계되었으며, 비즈니스 도메인, 오케스트레이션, 인프라, 사용자 인터페이스가 명확히 분리되어 있습니다.

## 목차

- [소개](#소개)
- [기능](#기능)
- [아키텍처](#아키텍처)
- [사전 요구 사항](#사전-요구-사항)
- [설치](#설치)
- [사용법](#사용법)
- [설정](#9-설정)
- [백엔드와 호환성](#백엔드와-호환성)
- [영속성, 로그, 내보내기](#영속성-로그-내보내기)
- [보안](#보안)
- [테스트와 품질](#테스트와-품질)
- [프로젝트 상태](#프로젝트-상태)
- [제거](#제거)
- [라이선스](#라이선스)

---

## 소개

Omega-Fire는 네트워크 보안을 위한 **로컬 조종석** 역할을 합니다. 머신에 있는 구성 요소를 자동으로 감지하고 실제로 사용할 수 있는 기능에 맞게 메뉴를 조정합니다.

### 목표

- nftables, iptables, ip6tables, Fail2Ban을 일관된 하나의 인터페이스로 모은다.
- 연결, 차단, 시스템 이벤트를 쉽게 관찰하고 조치할 수 있게 한다.
- 내보내기, 백업, 감사, 작업 기록을 한곳에 모은다.
- 테스트 가능하고 확장 가능한 아키텍처를 유지한다.
- 선택 구성 요소가 없을 때도 제한 모드로 작동한다.

### Omega-Fire가 하는 일

- 사용 가능한 백엔드, 서비스, 커널, 도구를 감지합니다.
- nftables, iptables, ip6tables가 있으면 이를 관리합니다.
- 차단된 IP를 개별 또는 일괄로 관리하며 가져오기, 내보내기, 동기화, flush를 지원합니다.
- 고급 규칙을 만들고, 나열하고, 삭제합니다.
- 사전에 자동 백업을 한 뒤 미리 정의된 정책을 적용합니다.
- Fail2Ban jail과 그 차단을 관리합니다.
- 로그를 실시간으로 또는 통계 형태로 분석합니다.
- 모니터링 형태의 감시를 제공합니다.
- conntrack을 사용할 수 있으면 활성 연결을 표시합니다.
- JSON, TXT, HTML 내보내기를 만듭니다.
- 전체 상태를 `.tar.gz` 아카이브로 백업하고 복원합니다.
- 작업을 애플리케이션 로그와 구조화된 JSON 감사에 기록합니다.
- 감지된 서비스와 애플리케이션을 감시합니다: systemd, runit, OpenRC, Docker, 서버, VNC 등.

### 이 프로젝트가 하지 않는 일

- nftables, iptables, Fail2Ban을 대체하지 않습니다.
- 시스템과 독립된 단독 방화벽이 아닙니다.
- 다중 사용자 인증을 제공하지 않습니다.
- 정상 작동 중에는 네트워크 API를 노출하지 않습니다.
- 웹 대시보드가 아닙니다.
- 다른 머신에서 원격 머신을 직접 보호하지 않습니다.
- 기본적으로 자기 폴더 밖에는 어떤 파일도 설치하지 않습니다.
- 모든 배포판에서 모든 백엔드를 사용할 수 있다고 보장하지 않습니다.

---

## 기능

### 1. 기능 감지와 진단

- 감지된 기능의 레지스트리 표시.
- 식별자로 특정 기능의 상세 정보 조회.
- 구성 요소 설치 후 시스템을 수동으로 다시 스캔.
- 최근 진단 결과 조회.
- 애플리케이션 로그 조회 및 검색.
- 상태와 진단을 JSON, TXT, HTML로 내보내기.
- **omega 제품군** 범주: omega-serv(감지되어 실행 중인 인스턴스), omega-waf(`magnet` 확장 활성화), omega-jail(설치된 jail)이 레지스트리, 대시보드, 보고서에 표시됩니다.

### 2. 통합 IP 관리

통합 블랙리스트로 같은 화면에서 nftables와 iptables를 다룰 수 있습니다.

- IP 하나 또는 IP 목록 차단.
- 개별 또는 일괄 차단 해제.
- 직접 입력 또는 파일에서 가져오기.
- 백엔드별 목록 또는 통합 보기.
- NFTables/IPTables 백엔드 간 동기화.
- 목록 내보내기와 다시 가져오기.
- 하나 이상의 백엔드 전체 정리.
- IPv4와 IPv6 지원.
- 전용 화면에서 차단 목록 파일(`var/blocklist/`)과 그 고정 항목을 바로 관리. 기본으로 제안되는 파일 `blocklist.txt`와 `blocklist-f2b.txt`는 첫 실행 시 빈 파일로 생성됩니다.

### 3. 규칙과 정책 관리

- 고급 규칙을 만드는 단계별 마법사.
- 시스템 규칙과 Omega-Fire가 만든 규칙의 목록.
- 선택으로 규칙 삭제.
- 참조 데이터베이스의 비활성 규칙 자동 정리.
- 실제 방화벽에 맞춰 데이터베이스를 정리하고 다시 동기화합니다. 미리 보기와 사전 백업을 제공하며 방화벽 자체는 절대 수정하지 않습니다.
- 다른 도구(UFW, Tailscale, Docker…)의 규칙을 출처로 식별: 정보용으로 표시만 하며 Omega-Fire에서 절대 삭제하지 않습니다.
- 다른 도구가 iptables에 규칙을 가지고 있을 때 정책 적용이나 iptables 비우기 전에 안전장치: 모두 적용, nftables에만 적용, 또는 취소 — 결과는 도움말에 자세히 설명되어 있습니다.
- 미리 정의된 정책 적용.
- 정책 적용 전 자동 백업.
- 정책 사용자 정의, 저장, 복원.
- 상태 메뉴와 대시보드에서 활성 정책 표시.
- 수정된 프로필을 `프로필 + CUSTOM` 형태로 표시.
- 테이블 관리(메뉴 3.5): 백엔드별 읽기 전용 진단(테이블 존재 여부, input/output/forward 정책, 규칙 수)과 백엔드마다 다른 정책에 대한 설명(실제 효과, 원인, 해결 방법).
- 처음 사용할 때 nftables 테이블을 초기화하며, 이미 설정된 chain은 결코 덮어쓰지 않음.
- 이전 프로필이 남긴 고아 제한 정책을 바로잡기 위해 백엔드의 chain 정책을 ACCEPT로 재설정.
- 특정 백엔드만 비우거나, 감지된 모든 백엔드를 한 번의 동작으로 동기화해 비우기.
- nftables 테이블 전체 삭제(개별 규칙 삭제를 넘어서는 고급 동작).

### 4. Fail2Ban 관리

- jail과 그 매개변수의 상세 상태.
- 차단된 IP 수와 rate-limit 정보.
- jail에서 IP 검색.
- 개별 또는 다중 ban과 unban.
- jail, 백엔드, 파일 간 IP 이동.
- 안내에 따른 사용자 jail 생성.
- 미리 정의된 jail 템플릿, 수정 및 삭제 가능.
- 각 jail의 출처: Omega-Fire, omega-jail, fail2ban 기본 구성 또는 기타 파일.
- 파일 이름과 관계없이 확실한 jail 삭제: omega-jail이 설치한 jail에는 경고, `jail.local` 또는 공유 파일의 jail은 이유를 설명하며 거부, fail2ban 표준 필터는 절대 삭제하지 않습니다.
- jail 비우기 또는 전체 정리.
- JSON, TXT, HTML로 내보내기.
- 설정 확인과 감사.
- 서비스 제어: 상태, 시작, 중지, 재시작, 부팅 시 활성화와 비활성화. 시작이나 중지 후에는 기능 레지스트리와 대시보드가 갱신됩니다.

### 5. 로그와 유지 관리

- **로그 라이브러리**(5.1): 감지된 omega-serv 인스턴스의 로그(omega-waf 로그 포함) 자동 가져오기, 경로 수동 고정, SSH로 원격 로그 가져오기(키 또는 에이전트, 비밀번호는 절대 사용하지 않음).
- **즐겨찾기**(5.2): 라이브러리의 로그를 조합해 이름과 뷰어를 지정하여 저장하고 바로 실행합니다.
- **로그 보기**(5.3): 설정 없이 로그 하나를 원하는 뷰어로 — 단순(실시간 대시보드: 403 및 429 거부를 포함한 HTTP 상태, Top 5 IP, 요청된 경로, 404 경로, omega-log와 동일), 클래식(마지막 줄 표시 후 실시간 추적) 또는 `lnav`.
- **라이브러리는 모든 로그 선택에 쓰입니다**: 5.4, 5.5, 5.6, 그리고 8.5와 8.6에서 라이브러리의 로그가 고정 항목보다 먼저 목록 맨 위에 표시됩니다.
- `lnav` 통합: 여러 로그를 하나의 시간순 보기로 병합하고 Omega-Fire 헤더/푸터로 감쌈([탐색](#탐색) 참조).
- Top N(5.4)으로 가장 빈번한 IP 분석, 내보내서 대상 지정 정리에 다시 불러올 수 있습니다. 파일 전체에서 특정 IP를 검색하고 선택한 IP를 바로 제거할 수 있으며, 그동안 인터페이스가 멈추지 않습니다.
- LOG 또는 TXT 파일에서 하나 이상의 IP를 대상 지정 정리, 직접 입력하거나 내보내기에서 체크하여 선택.
- **체크해서 고르는 프리셋**이 있는 고정 파일: 시스템에 실제로 존재하는 일반적인 경로만 제안됩니다.
- 로테이션과 즉시 또는 예약 백업, **실제로 매일 밤 실행됨**(root로 실행되는 systemd 타이머, 없으면 root의 crontab 한 줄). 보관할 백업 수, 마지막 백업과 다음 백업을 표시합니다.
- 백업 복원.
- 기간, 할당량, 유형, 수동 선택에 따른 정리.
- 폴더나 환경별 고급 정리.
- 24시간, 7일, 30일 통계(5.10, 빠른 보기).
- jail에 있는 이벤트, 변동, 할당량, IP 분석.

### 6. 내보내기와 보고서

사용 가능한 형식:

- **JSON**: 구조화되고 재사용 가능한 데이터.
- **TXT**: 원시 형식 또는 주입에 맞춘 형식.
- **HTML**: 읽기 쉽고 시각적인 보고서.

사용 가능한 보고서:

- 전체 블랙리스트.
- 구조화된 ruleset.
- 출처별로 선택한 규칙: 시스템, Omega-Fire, 또는 활성.
- 전체 감사 보고서.
- Fail2Ban 통계.
- 시스템 상태와 진단.
- 7일 또는 30일 통계 보고서.
- IP Top N 순위.
- **로그 통계**(6.5): omega-serv, omega-log와 같은 보고서(요약, HTTP 상태, 상위 IP, 요청된 경로, 404 경로, 시간대별 분포, 일별 추세), 로그 전용. 차단과 방화벽 상태는 7일 및 30일 보고서에 남아 있습니다.
- 도움말 가이드와 FAQ.

**모든 내보내기 보기**(6.6): 내보낸 모든 파일을 한곳에서 유형, 날짜, 크기와 함께 표시. HTML 보고서는 사용자의 기본 웹 브라우저에서 열리고, JSON이나 TXT는 Omega-Fire 안에서 읽을 수 있어 터미널이나 파일 관리자가 필요 없습니다.

HTML 테마:

- `omega-base` — 미드나이트 블루와 시안, 기본 테마.
- `omega-burn` — 붉은 주황빛 불씨.
- `omega-neon` — 시안과 마젠타의 사이버펑크.
- `light-basic` — 밝고 차분함.
- `light-alt` — 크림색 종이와 숲색 초록.

내보내기 언어: 설정에서 따로 지정할 수 있으며(기본값 « 인터페이스와 같음 »), 인터페이스 언어를 바꾸지 않고 읽는 사람의 언어로 보고서를 전달할 수 있습니다.

### 7. 시스템과 영속성

- 전체 상태 백업: 규칙, nftables 차단, iptables 차단, Fail2Ban.
- 타임스탬프가 붙은 `.tar.gz` 아카이브 생성.
- 스냅샷 목록과 복원: 동일하게 다시 만들 수 있는 Omega-Fire 규칙만 되돌리며, 다른 도구의 규칙은 절대 건드리지 않습니다.
- 작업 기록.
- 기록 필터링과 정리.
- 재시작 없이 설정 다시 불러오기와 다시 스캔.

### 8. 모니터링과 통계

- 주기적으로(2초마다) 새로 고치는 실시간 대시보드, 수집 중에도 인터페이스를 막지 않음.
- 활성 정책 표시.
- conntrack을 통한 활성 연결.
- 트래픽, 이벤트, 통계, 서버 로그.
- 7일과 30일 종합 보고서.
- 스냅숏과 보고서의 HTML 내보내기.

### 9. 설정

- 도구 모음의 나머지와 공유하는 열 가지 `omega-*` 테마 중에서 활성 테마 선택([테마와 터미널](#테마와-터미널) 참조), 실행 사이에도 유지.
- 렌더링 프로필(자동, 완전, 표준, 축소, mono 전용)을 수동으로 지정하며, 다음 실행부터 적용.
- 17개 언어 중 인터페이스 언어 선택([인터페이스 언어](#인터페이스-언어) 참조): 인터페이스만 다시 시작되며 방화벽 규칙, Fail2Ban, 서비스는 건드리지 않습니다.
- HTML 및 TXT 내보내기 언어, 인터페이스 언어와 별개.
- 변경 가능한 내보내기 및 스크린샷 폴더, 확인 후 비우기.
- 메인 메뉴(`9. 설정`) 또는 `s` 키로 바로 열 수 있음.

### 10. 도움말

- **도움말 가이드**: 모든 도움말 시트를 메뉴 순서대로 모았으며, 각 시트에서 관련 시트를 열 수 있습니다.
- **FAQ**: 실제 사용 중에 나온 질문(다른 도구의 규칙, 복원, Fail2Ban, 로그, 내보내기와 브라우저).
- 가이드와 FAQ를 내보내기 언어로 HTML 내보내기.
- `a` 키는 계속 현재 화면의 도움말입니다.

---

## 아키텍처

```text
src/omega_fire/
├── app/              부트스트랩과 의존성 주입 컨테이너
├── core/             기능, 열거형, 예외
├── domain/           순수 비즈니스 로직: 규칙, IP, jail, 로그
├── application/      오케스트레이션: commands와 queries
├── infrastructure/   백엔드, 저장소, 내보내기, 로그, 시스템 프로브
├── ports/            Protocol/ABC 계약
├── interfaces/       interfaces/tui/ (Textual, 기본) + interfaces/cli/ (Rich, --legacy-cli)
├── plugins/          내장 확장: nftables, iptables, Fail2Ban, conntrack
└── shared/           파싱, 네트워크, 서식, 공통 유틸리티
```

### 설계 원칙

- `domain/`에는 I/O도 인프라 의존성도 없습니다.
- `application/`은 도메인과 포트를 통해 사용 사례를 오케스트레이션합니다 — Textual 화면과 Rich 인터페이스의 동작은 같은 commands/queries를 호출하며, 비즈니스 로직은 두 인터페이스 어느 쪽에도 의존하지 않습니다.
- `infrastructure/`는 `nft`, `iptables`, `fail2ban-client`와 그 밖의 외부 도구(subprocess, pty, 파일)를 호출할 수 있는 유일한 계층입니다.
- `interfaces/`는 `subprocess`를 직접 호출하면 안 됩니다.
- `ports/`는 어댑터가 기대하는 계약을 정의합니다.
- `core/`는 여러 계층이 사용하는 기능 레지스트리를 제공합니다.
- 플러그인 덕분에 비즈니스 도메인을 수정하지 않고 백엔드를 추가하거나 발전시킬 수 있습니다.
- Textual 인터페이스(`interfaces/tui/`)는 [`omega-lib`](https://github.com/)(OMEGA 도구 모음 전체가 공유하는 의존성: 9개 토큰 테마, 터미널 감지, 공통 포트 계약)에 기반하며, PyPI에 공개되지 않았고 배포 아카이브에 포함되어 있습니다(`vendor/omega-lib/`, [설치](#설치) 참조).
- Textual 화면에서 시작한, 시간이 걸릴 수 있는 모든 호출(방화벽 백엔드, `fail2ban-client`, 디스크)은 백그라운드(스레드)에서 실행되며 인터페이스의 메인 스레드에서는 결코 실행되지 않습니다 — 작업 중에도 대시보드나 폼이 응답을 유지하며 애플리케이션 전체가 멈추지 않습니다.

### 데이터 구조

Omega-Fire는 외부 ORM 없이 표준 라이브러리 `sqlite3`를 통해 SQLite를 사용합니다. 주요 데이터 집합은 차단, 규칙, 감사 이벤트, 스냅숏에 관한 것입니다.

마이그레이션은 버전이 관리되며 시작할 때 자동으로 적용됩니다.

---

## 사전 요구 사항

### 시스템

- Linux, 특히 Arch Linux와 호환 배포판.
- Python 3.10 이상.
- `sudo`로 사용할 수 있는 root 권한.
- 서비스 관리자: systemd, runit 또는 OpenRC.
- 방화벽 백엔드 하나 이상: nftables 또는 iptables.
- 최소 80x24 터미널(사용 가능한 크기에 따른 렌더링 프로필은 [테마와 터미널](#테마와-터미널) 참조).

### Python 의존성

운영용 의존성은 `requirements.txt`에 정의되어 있습니다:

- `textual` — 기본 TUI 인터페이스.
- `omega-lib` — 테마, 터미널 감지, OMEGA 도구 모음과 공유하는 계약(PyPI에 공개되지 않음, [아키텍처](#아키텍처)와 [설치](#설치) 참조).
- `rich` — `--legacy-cli` 인터페이스와 일부 보고서의 렌더링.
- `psutil` — 대시보드와 진단을 위한 시스템 정보(CPU, 메모리, 네트워크, 프로세스).
- `jinja2` — HTML 내보내기 생성.
- `python-dotenv` — 환경 변수.
- `pyte` — `lnav`를 감싸기 위한 가상 터미널 에뮬레이터(메뉴 8.6 및 5.2 / 5.3의 lnav 뷰어).

품질 도구(`pytest`, `black`, `flake8`, `mypy`)는 `requirements.txt`에 주석으로 적혀 있습니다: 프로젝트에 기여한다면 주석을 해제하거나 따로 설치하십시오([테스트와 품질](#테스트와-품질) 참조).

### 권장 선택 도구

이 도구가 없으면 애플리케이션은 제한 모드로 작동합니다:

- `fail2ban` — 자동 차단.
- `conntrack` 또는 `conntrack-tools` — 활성 연결과 네트워크 통계.
- `lnav` — 여러 파일에 걸친 고급 로그 분석.

Arch Linux와 그 파생 배포판에서:

```bash
sudo pacman -S fail2ban conntrack-tools lnav
```

---

## 설치

공식 아카이브는 `.tar.gz` 형식으로 제공됩니다. 설치 전에 무결성을 확인하십시오:

```bash
sha256sum omega-fire.tar.gz
```

> ⚠️ **아래 세 가지 방법은 첫 설치용입니다.** `~/omega-fire`가 이미 있다면(이전 버전 업데이트) 아래 [업데이트](#업데이트) 절을 사용하십시오 — 기존 `omega-fire` 폴더 안에서 이 명령을 다시 실행하지 마십시오: `tar`가 중첩된 `omega-fire/omega-fire/`를 만들려다 그 폴더가 root 소유라면 권한 오류로 실패합니다(이전 압축 해제를 실수로 `sudo tar`로 했다면 흔히 생깁니다).

### 방법 1 — 설치 스크립트

```bash
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ 이미 omega-fire 폴더 안에 있는 것 같습니다 — README의 업데이트 절을 참조하십시오." >&2; exit 1; }
[ -d omega-fire ] && echo "ℹ️ 이미 여기에 압축이 풀려 있어 이 단계를 건너뜁니다." || tar -xzf omega-fire.tar.gz
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire가 이미 있어 이동을 건너뜁니다." || mv omega-fire ~/
cd ~/omega-fire/
chmod +x install.sh
./install.sh
```

실행:

```bash
./omega-fire.sh
```

별칭을 설치했다면 새 터미널을 열고 다음을 사용하십시오:

```bash
fire
```

### 방법 2 — 견고한 전체 설치

이 명령은 다시 실행할 수 있습니다: 이미 끝난 단계는 건너뜁니다.

```bash
([ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ 이미 omega-fire 폴더 안에 있는 것 같습니다 — README의 업데이트 절을 참조하십시오." >&2; exit 1; }; [ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire가 이미 있어 압축 해제를 건너뜁니다." || (tar -xzf omega-fire.tar.gz && mv omega-fire ~/)) && cd ~/omega-fire/ && ([ -d .venv ] && echo "ℹ️ .venv가 이미 있어 이 단계를 건너뜁니다." || python3 -m venv .venv) && source .venv/bin/activate && ([ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib || true) && pip install -r requirements.txt && chmod +x omega-fire.sh && mkdir -p var && (getent group omega-fire >/dev/null 2>&1 && echo "ℹ️ omega-fire 그룹이 이미 있습니다." || sudo groupadd omega-fire) && (groups "$USER" 2>/dev/null | grep -qw omega-fire && echo "ℹ️ $USER는 이미 omega-fire 그룹의 구성원입니다." || sudo usermod -aG omega-fire "$USER") && sudo chgrp -R omega-fire var && sudo chmod -R 2775 var && echo "✅ Omega-Fire를 설치했습니다. ./omega-fire.sh를 실행하십시오."
```

### 방법 3 — 상세 설치

```bash
# 0. 기존 omega-fire 안에서 다시 실행하는 것이 아닌지 확인
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ 이미 omega-fire 폴더 안에 있는 것 같습니다 — README의 업데이트 절을 참조하십시오." >&2; exit 1; }

# 1. 압축 해제
[ -d omega-fire ] && echo "ℹ️ 이미 여기에 압축이 풀려 있어 이 단계를 건너뜁니다." || tar -xzf omega-fire.tar.gz

# 2. 홈으로 이동
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire가 이미 있어 이동을 건너뜁니다." || mv omega-fire ~/

# 3. 프로젝트로 들어가기
cd ~/omega-fire/

# 4. 가상 환경 만들기
[ -d .venv ] && echo "ℹ️ .venv가 이미 있어 생성을 건너뜁니다." || python3 -m venv .venv

# 5. 의존성 설치(포함된 omega-lib가 있으면 requirements.txt보다 먼저)
source .venv/bin/activate
[ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib
pip install -r requirements.txt

# 6. 실행기에 실행 권한 부여
chmod +x omega-fire.sh

# 7. root와 현재 사용자를 위해 var/ 준비
mkdir -p var
getent group omega-fire >/dev/null 2>&1 || sudo groupadd omega-fire
groups "$USER" 2>/dev/null | grep -qw omega-fire || sudo usermod -aG omega-fire "$USER"
sudo chgrp -R omega-fire var
sudo chmod -R 2775 var

# 8. 실행
./omega-fire.sh
```

`vendor/omega-lib/`는 공식 아카이브에만 들어 있습니다(omega-lib가 PyPI에 공개되지 않았으므로 `build-release.sh`가 자동으로 포함함). 개발용 클론에서는 해당 저장소에서 따로 설치하십시오(`pip install -e path/to/omega-lib`).

전용 그룹과 `setgid` 비트 덕분에 root와 사용자는 시스템 전체에 권한을 열지 않고도 `var/`에 생성된 파일을 공유할 수 있습니다. 그룹 소속을 바로 적용하려면 다시 로그인하거나 `newgrp omega-fire`가 필요할 수 있습니다.

### 업데이트

`~/omega-fire`가 이미 있다면(이전 설치), **이 폴더 안에서 설치 명령을 다시 실행하지 마십시오**: `tar`가 중첩된 `omega-fire/omega-fire/`를 만들려다 실패하며, 폴더가 `root` 소유라면 보통 « 허가 거부 » 오류가 줄줄이 납니다(이전 압축 해제를 실수로 `sudo tar`로 했다면 흔히 생깁니다).

권장 절차이며, **`~/omega-fire`가 아닌** 아무 폴더(보통 `~` 자체)에서 실행합니다:

```bash
# 1. 기존 설치의 상태와 소유자 확인
ls -ld ~/omega-fire

# 2. 덮어쓰지 말고 예전 설치를 옆으로 옮겨 두기
sudo mv ~/omega-fire ~/omega-fire.old-$(date +%Y%m%d)

# 3. 새 아카이브를 홈에 바로 압축 해제
tar -xzf omega-fire.tar.gz -C ~/

# 4. 다시 설치(venv를 다시 만들고, 의존성을 다시 설치하고, var/ 권한을 다시 설정)
cd ~/omega-fire
chmod +x install.sh
./install.sh

# 5. 실행
./omega-fire.sh
```

4단계(`./install.sh`)는 이 상황을 자동으로 감지하고(여기에는 `var/db/` 데이터베이스가 없고, 바로 옆에서 `~/omega-fire.old-YYYYMMDD` 폴더를 찾음) 예전 설치에서 `config/omega-fire.conf`, 데이터베이스, 차단 목록, 백업, 내보내기, 스크린샷을 **스스로 가져옵니다** — 질문도 수동 단계도 없습니다. 이전 설치에 무엇이 있었든 위의 1~5단계 외에 할 일은 없습니다.

예전 설치처럼 보이는 폴더가 옆에 여러 개 있으면(모호함) `install.sh`는 아무것도 추측하지 않습니다: 그 경로를 보여 주고, 올바른 원본을 확인한 뒤 `sudo ./migrate-state.sh <폴더>`를 직접 실행하라고 안내합니다.

새 설치가 확인되면 예전 폴더 `~/omega-fire.old-YYYYMMDD`는 삭제해도 됩니다(`sudo rm -rf ~/omega-fire.old-YYYYMMDD`).

### Bash 또는 Zsh 별칭

```bash
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.bashrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.bashrc
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.zshrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.zshrc
```

그런 다음 셸을 다시 불러옵니다:

```bash
source ~/.bashrc 2>/dev/null || source ~/.zshrc
```

### Nerd Fonts 아이콘과 기호

아이콘이 보이지 않으면 Nerd Fonts 기호를 설치하십시오:

```bash
mkdir -p ~/.local/share/fonts
curl -fLo /tmp/NerdFontsSymbolsOnly.zip \
  https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip
unzip -o /tmp/NerdFontsSymbolsOnly.zip -d ~/.local/share/fonts
fc-cache -fv
```

---

## 사용법

### 실행

```bash
cd ~/omega-fire
./omega-fire.sh

# 또는 별칭을 만들었다면 간단히:
fire
```

실행기는:

1. root 권한을 확인하고 필요하면 `sudo`로 다시 실행합니다.
2. `.venv`, `venv` 또는 시스템 Python을 감지합니다.
3. `PYTHONPATH`를 `src/`로 설정합니다.
4. `python -m omega_fire`를 실행합니다 — 기본적으로 **Textual** 인터페이스입니다.

대신 예전 Rich 인터페이스(번호를 순서대로 입력)를 실행하려면:

```bash
./omega-fire.sh --legacy-cli
```

**기존 Rich 인터페이스는 더 이상 개발되지 않지만 계속 사용할 수 있습니다.** 기존 인터페이스는 버전 3.0 그대로이며 프랑스어입니다: 원래 메뉴 5(라이브러리, 즐겨찾기, 클래식 뷰어 없음), "모든 내보내기 보기" 없음, 도움말 가이드와 FAQ 없음, 프리셋 없음. Textual 인터페이스에 완전한 버전 3.5가 담겨 있습니다.

### 인터페이스 언어

17개 언어: 프랑스어, 영어, 스페인어, 포르투갈어(브라질), 이탈리아어, 독일어, 네덜란드어, 폴란드어, 러시아어, 중국어, 베트남어, 태국어, 인도네시아어, 일본어, 한국어, 힌디어, 아랍어. 설정에서 선택하며(`s` 키, 번역되지 않는 레이블 « Langue / Language »), 인터페이스만 다시 시작하여 적용합니다. 한 번만 쓰려면 `OMEGA_FIRE_LANG=ko ./omega-fire.sh`를 사용합니다(실행 스크립트가 `sudo`를 거쳐도 유지합니다). Linux 텍스트 콘솔(TTY)에서는 콘솔 글꼴에 문자가 없는 언어(베트남어, 중국어, 태국어, 일본어, 한국어, 힌디어, 아랍어)가 해당 세션 동안 영어로 표시됩니다. 아랍어는 오른쪽에서 왼쪽으로 표시됩니다. 힌디어의 경우 Terminator, GNOME Terminal, Xfce Terminal, Alacritty는 텍스트를 정렬해 표시하며, 결합 문자를 직접 조합하는 터미널(Kitty, Ghostty, Konsole)에서는 테두리와 열이 어긋날 수 있습니다. **내보내기 언어**(HTML 및 TXT 보고서)는 따로 설정하며 기본값은 « 인터페이스와 같음 »입니다. 애플리케이션 로그와 감사 기록은 계속 프랑스어로 저장되며, 기록의 제목은 선택한 언어로 표시됩니다. 이전 인터페이스(`--legacy-cli`)는 프랑스어로 유지됩니다.

### 문의 및 지원

도움말(`a` 키)에는 **문의 및 지원** 화면이 있습니다: *커피 한 잔 사기*(개발자의 PayPal 페이지), *지원팀에 문의*(이메일 주소와 사이트의 문의 양식을 그대로 표시), *사용자로 등록(익명)*, *업데이트 확인*. 등록은 자발적이며 기본적으로 꺼져 있고 한 번만 전송됩니다. 사용자 수와, 원하면 사용자의 대륙 또는 국가(닫힌 목록, 자유 입력 없음)를 세는 데에만 쓰입니다. 무작위로 생성한 키, 소프트웨어 이름(`omega-fire`)과 버전만 보내며, 이름, 컴퓨터 이름, 설정, 대상, 결과는 절대 보내지 않습니다. IP 주소는 등록 정보에 저장되지 않지만, 모든 방문과 마찬가지로 수신 서버의 보안 검사와 로그를 거칩니다. 같은 화면에서 언제든지 철회할 수 있습니다(*등록 취소*). 업데이트 확인은 사이트에 게시된 버전 목록만 읽으며, 클릭하지 않으면 절대 실행되지 않습니다.

### 전체 흐름

1. 시작 화면(splash), 터미널이 너무 작으면 이어서 경고.
2. 시스템 기능 감지(전용 화면, 차단하지 않음).
3. 메인 메뉴: 8개의 주제별 섹션(1-8), 설정(9), 도움말(10).
4. 섹션을 고른 다음 동작을 선택 — 각 동작은 폼을 열며, 필수 항목은 모두 다음 단계로 넘어가기 전에 검증됩니다.
5. 민감하거나 파괴적인 작업(flush, 정리, 복원...) 전에는 명시적 확인.
6. 오래 걸리는 작업은 백그라운드에서 실행되며(기다리는 동안 인터페이스를 계속 쓸 수 있음), 끝나면 결과 요약과 함께 메뉴로 돌아갑니다.

### 탐색

- 위/아래 화살표: 목록이나 메뉴에서 커서 이동.
- Tab / Shift+Tab: 폼의 항목 사이 이동.
- Enter: 선택 또는 확인.
- 표의 행 클릭: 그 행을 선택하고 관련 항목(고정할 소스, 대상 jail 등)을 미리 채움.
- `Esc`: 이전 화면으로 돌아가기(홈에서는 종료 확인을 묻음).
- `a`: 상황별 도움말 — 현재 작업을 자세히 설명하거나, 아직 작업 화면이 열려 있지 않으면 현재 섹션의 모든 작업을 설명합니다. 전체 가이드와 FAQ는 메뉴 10에 있습니다.
- `t`: 확인 없이 다음 테마로 전환.
- `r`: 터미널의 크기와 종류를 다시 감지.
- `s`: 설정 열기(테마, 렌더링 프로필, 언어, 폴더).
- `q` / `Ctrl+Q`: 확인 후 종료.

#### lnav 화면의 특징(8.6 및 5.2 / 5.3의 lnav 뷰어)

`lnav`는 의사 터미널 안에 들어가며, 그 화면 둘레에 Omega-Fire 헤더/푸터가 계속 표시됩니다. `lnav` 고유 단축키와 Omega-Fire 단축키가 충돌하지 않게 하기 위해서입니다:

- 화살표 ↑↓: 로그 안에서 이동(`lnav` 고유 단축키, 그대로 전달).
- 화살표 ←→: 긴 줄에서 가로 스크롤(`lnav` 고유 단축키).
- `g` / `G`: 처음 / 끝으로 이동(`lnav` 고유 단축키).
- `Ctrl+C`: 현재 줄을 표시하고 시스템 클립보드로 복사(일부 시스템에서 멈출 수 있는 `lnav` 고유 복사 명령을 대신함).
- 소문자 `t`: 이 화면 전용 다음 테마(대문자 `T`는 줄 사이 경과 시간을 표시하는 `lnav` 고유 단축키로 남음).
- `Ctrl+Q`: Omega-Fire로 돌아가기(애플리케이션을 끝내지 않고 `lnav`를 깔끔하게 닫음).

---

## 테마와 터미널

열 가지 `omega-*` 테마가 OMEGA 도구 모음의 나머지와 공유됩니다:

```text
omega-base       omega-dark       omega-light
omega-neon       omega-burn       omega-pink
omega-hack       omega-contrast   omega-mono
omega-minimal
```

- `t`로 테마를 바꾸거나 설정(`s`)에서 직접 고르십시오.
- 선택한 테마는 저장되어 다음 실행에도 적용됩니다.
- Omega-Fire는 감지된 터미널에 맞춰 **렌더링 프로필**로 시각적 복잡도(테두리, splash, 정보 밀도)를 자동 조정합니다: 완전, 표준, 축소, Mono(ASCII 전용). 프로필은 설정에서 수동으로 지정할 수 있습니다.

| 최소 크기 | 프로필 | 대표 터미널 |
|---|---|---|
| 120×32 이상 | 완전 | Ghostty, Alacritty, WezTerm, Kitty |
| 100×28 이상 | 표준 | Konsole, GNOME Terminal, Terminator, xfce4-terminal |
| 80×24 이상 | 축소 | urxvt, xterm, 최신 SSH |
| 80×24 미만 | Mono(ASCII 전용) | Linux TTY, 오래된 SSH |

80×24 미만에서는 실행이 거부됩니다(최소 크기 필요). 터미널 크기를 바꾼 뒤 다시 실행하거나, 화면이 자동으로 갱신되지 않으면 크기를 바꾼 뒤 `r`을 누르십시오.

---

## 설정

개별 설정은 다음 파일에서 조정할 수 있습니다:

```text
omega-fire/config/omega-fire.conf
```

특히 다음을 정의할 수 있습니다:

- 로그 경로;
- 모니터링 서버와 소스;
- 사용 가능한 백엔드 또는 사용자 경로;
- 분석할 환경;
- 특정 설치에 맞춘 매개변수.

설정은 재시작하거나 수동으로 다시 스캔할 때(메뉴 1.3 또는 7.4) 다시 읽힙니다.

이 파일은 완전히 선택 사항이며(없어도 애플리케이션은 환경 변수로 대체해 정상 작동함) **배포 아카이브에서 제외됩니다** — 업데이트가 조용히 덮어쓰는 일은 결코 없으며, 해당되면 `install.sh`가 예전 설치에서 자동으로 가져옵니다(위의 « 업데이트 » 참조).

### 내부 경로와 시스템 경로

기본적으로 Omega-Fire는 자기 폴더 안에서 작업합니다:

```text
var/exports/       # 프로젝트 내부 폴더
/var/exports/      # 시스템 절대 경로
```

따라서 맨 앞의 `/`는 의미가 있습니다. 시스템으로의 가져오기와 내보내기는 사용자가 명시적으로 요청해야 합니다.

---

## 백엔드와 호환성

Omega-Fire는 구성 요소를 감지하고 사용할 수 있는 기능만 활성화합니다.

| 구성 요소 | 역할 | 상태 |
|---|---|---|
| nftables | 최신 IPv4/IPv6 방화벽 | 권장 |
| iptables | IPv4 방화벽 | 호환 |
| ip6tables | iptables를 사용하는 IPv6 방화벽 | 있으면 호환 |
| Fail2Ban | jail과 자동 차단 | 선택 |
| conntrack | 활성 연결 | 선택 |
| lnav | 고급 로그 분석 | 선택 |
| systemd, runit, OpenRC | 서비스 관리 | 자동 감지 |
| Docker, VNC, 서버 | 감지된 애플리케이션과 서비스 | 설치에 따라 |

### IPv4와 IPv6

두 주소 체계 모두 호환 백엔드에서 지원됩니다:

- nftables: IPv4와 IPv6 듀얼 스택;
- iptables/ip6tables: 사용 가능한 바이너리에 따라;
- Fail2Ban: jail과 시스템 설정에 따라.

긴 형식, 축약 형식, 로컬, 혼합 형식, 0이 포함된 형식, CIDR 표기의 IPv6는 해당 구성 요소가 처리합니다.

---

## 영속성, 로그, 내보내기

### 영속성

- `sqlite3`를 통한 SQLite.
- 차단, 규칙, 감사, 스냅숏 관련 테이블.
- 자동으로 적용되는 버전 관리 마이그레이션.
- `.tar.gz` 형식의 전체 상태 아카이브.
- 고정 항목(즐겨찾는 로그 소스)과 최근 기록은 JSON(`var/runtime/`)으로 저장되어 재시작 후에도 남습니다.

### 로그

- 애플리케이션 텍스트 로그: `var/logs/app.log`.
- `event_type`, `actor`, `action`, `result`, `details` 등을 포함한 구조화된 JSON 감사 로그.

### 내보내기

내보내기는 JSON, TXT, HTML로 제공되며 HTML 보고서용 CSS 테마가 여러 개 있습니다.

---

## 보안

Omega-Fire는 시스템의 핵심 구성 요소에 작용하므로 신중하게 사용해야 합니다.

- 실행하려면 `sudo`를 통한 root 권한이 필요합니다.
- flush, 전체 정리, 정책 적용은 파괴적일 수 있습니다.
- 미리 정의된 정책은 변경 전에 자동 백업을 실행합니다.
- iptables / ip6tables에서는 정책을 적용하거나 백엔드를 비우면 다른 도구(UFW…)의 규칙도 지워집니다: Omega-Fire가 이를 알리고 실행 전에 선택하게 합니다.
- 큰 변경 전에는 매번 수동으로 백업하십시오.
- 각 작업 후 방화벽, jail, 연결의 실제 상태를 확인하십시오.
- 먼저 버려도 되는 머신이나 대상에서 테스트하십시오.
- IPv4 테스트에는 RFC 5737 문서용 네트워크를 사용하십시오: `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`.
- 운영 머신에서 복원하기 전에 내보내기와 스냅숏을 확인하십시오.
- `var/` 폴더에 필요 이상으로 넓은 권한을 주지 마십시오.

---

## 테스트와 품질

테스트 모음은 137개의 단위 테스트(8,000개 이상의 검증 사례)로 구성됩니다: 비즈니스 도메인, 오케스트레이션(`application/`), 인프라, 그리고 3.5에서 추가되거나 수정된 Textual 화면을 실제 스타일시트로 실행합니다(레이아웃, 전체 흐름, 내보내기 언어). 이 아카이브에는 `tests/` 폴더가 없습니다. 실행이 필요하면 개발 저장소에서 가져오세요.

```bash
source .venv/bin/activate
python -m unittest discover -s tests/unit -t .
```

계층형 아키텍처는 비즈니스 도메인과 표현 계층을 엄격히 분리합니다(`domain/`, `application/`, `Protocol`로 된 `ports/`, [아키텍처](#아키텍처) 참조): 대부분의 테스트는 root도 실제 방화벽도 필요하지 않습니다.

프로젝트에 기여한다면 `requirements.txt`에 (주석으로) 적힌 품질 도구를 설치하십시오:

```bash
pip install pytest pytest-cov black flake8 mypy
```

설치 후 사용할 수 있는 도구:

```bash
black .
flake8 .
mypy src/
pytest --cov
```

---

## 프로젝트 상태

### 작동 중인 부분

- 주요 네트워크 보안 메커니즘을 위한 통합 Textual TUI, 검증된 폼, 테마, 상황별 도움말을 OMEGA 도구 모음과 공유.
- 기존 Rich 인터페이스를 대안으로 유지(`--legacy-cli`).
- 기능 자동 감지.
- 사용 가능한 백엔드 관리.
- 존재하는 도구에 따른 IPv4/IPv6 지원.
- 애플리케이션 로그 기록과 감사.
- 백업과 복원.
- JSON, TXT, HTML 내보내기.
- 인터페이스를 막지 않고 백그라운드에서 새로 고치는 대시보드와 통계.
- 문서화된 계층형 아키텍처.

### 알려진 한계

- 테스트 모음은 3.5의 Textual 화면을 다루지만, 이전 화면 전체는 아직 다루지 않습니다([테스트와 품질](#테스트와-품질) 참조).
- `ExecutionPlan`/`PipelineStep` 메커니즘이 프로젝트에 일부 남아 있습니다.
- 기능을 실제로 쓸 수 있는지는 호스트 머신의 바이너리, 서비스, 권한, 설정에 달려 있습니다.
- 기존 Rich 인터페이스(`--legacy-cli`)는 더 이상 활발한 개발의 중심이 아니며, Textual 인터페이스가 실제 환경에서 완전히 안정될 때까지 유지됩니다.

---

## 제거

데이터가 프로젝트 폴더 안에 남아 있다면:

```bash
sudo rm -rf ~/omega-fire
```

다른 곳으로 내보낸 파일, `~/.bashrc`나 `~/.zshrc`에 추가했을 수 있는 `fire` 별칭, 그리고 더 이상 쓰지 않는 전용 그룹은 직접 삭제하십시오:

```bash
sudo groupdel omega-fire
```

이 마지막 명령은 다른 파일이나 서비스가 이 그룹에 의존하지 않을 때만 실행하십시오.

---

## 라이선스

Omega-Fire는 **MIT** 라이선스로 배포됩니다. 전체 내용은 [`LICENSE`](../../../LICENSE) 파일을 참조하십시오.

---

> **Omega-Fire — 관찰하고, 조종하고, 감사하고, 보호한다.**
>
> nftables, iptables, ip6tables, Fail2Ban, 로그, 네트워크 모니터링을 위한 통합 TUI 인터페이스.
