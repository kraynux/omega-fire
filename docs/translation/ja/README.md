<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->

<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-fire.png" alt="Omega-Fire" width="384">
</div>

# 󰦝 OMEGA-FIRE

**ネットワークセキュリティの統合管理ステーション**

> **kraynux** が **Omega-server** のために開発 
[https://kraynux.snake-mackarel.ts.net](https://kraynux.snake-mackarel.ts.net)

公式ページ：[OMEGA-FIRE](https://kraynux.snake-mackarel.ts.net/omega-fire/) &nbsp; プレビュー：[スクリーンショット](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/)  

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)
[![Interface](https://img.shields.io/badge/Interface-Textual%20TUI-cyan.svg)](https://github.com/Textualize/textual)

🌐 ドキュメント・エクスポート・インターフェースは **17 言語** に対応しています — [インターフェースの言語](#インターフェースの言語) を参照してください。  
**言語：**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

**Omega-Fire** は [Textual](https://github.com/Textualize/textual) で構築された Python の TUI（Terminal User Interface）アプリケーションです。ターミナルから単一のインターフェースで、Linux のファイアウォール、Fail2Ban、BAN されたアドレス、ネットワークルール、ログ、システム統計を管理できます。

Textual インターフェースが既定の動作モードで、メニュー、検証付きフォーム（必須項目はすべて先に進む前に確認されます）、専用画面で操作します。テーマ、コンテキストヘルプ、キーボードショートカットは OMEGA スイートの他のツール（omega-check、omega-deep、omega-stress...）と共通です。番号入力で順に操作する従来の [Rich](https://github.com/Textualize/rich) インターフェースも `--legacy-cli` で引き続き利用できます（[起動](#起動) を参照）。 
プレビュー：[スクリーンショット](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/index-2.html)

本プロジェクトは **Clean Architecture** の原則に従って設計されており、ビジネスドメイン、オーケストレーション、インフラストラクチャ、ユーザーインターフェースが明確に分離されています。

## 目次

- [概要](#概要)
- [機能](#機能)
- [アーキテクチャ](#アーキテクチャ)
- [前提条件](#前提条件)
- [インストール](#インストール)
- [使い方](#使い方)
- [設定](#9-設定)
- [バックエンドと互換性](#バックエンドと互換性)
- [永続化、ログ、エクスポート](#永続化ログエクスポート)
- [セキュリティ](#セキュリティ)
- [テストと品質](#テストと品質)
- [プロジェクトの状況](#プロジェクトの状況)
- [アンインストール](#アンインストール)
- [ライセンス](#ライセンス)

---

## 概要

Omega-Fire はネットワークセキュリティのための **ローカルな操縦席** として機能します。マシン上にあるコンポーネントを自動的に検出し、実際に利用できる機能に合わせてメニューを調整します。

### 目的

- nftables、iptables、ip6tables、Fail2Ban を一貫したインターフェースにまとめる。
- 接続、BAN、システムイベントの観察と操作を容易にする。
- エクスポート、バックアップ、監査、操作履歴を一元化する。
- テスト可能で拡張可能なアーキテクチャを維持する。
- オプションのコンポーネントがなくても縮退モードで動作する。

### Omega-Fire ができること

- 利用可能なバックエンド、サービス、カーネル、ツールを検出する。
- nftables、iptables、ip6tables が存在する場合にそれらを管理する。
- BAN された IP を個別または一括で管理し、インポート、エクスポート、同期、flush を行う。
- 高度なルールを作成、一覧表示、削除する。
- 事前に自動バックアップを取ったうえで定義済みポリシーを適用する。
- Fail2Ban の jail とその BAN を管理する。
- ログをリアルタイムまたは統計の形で分析する。
- モニタリングの形で監視を提供する。
- conntrack が利用可能な場合、アクティブな接続を表示する。
- JSON、TXT、HTML のエクスポートを作成する。
- 完全な状態を `.tar.gz` アーカイブにバックアップし、復元する。
- 操作をアプリケーションログと構造化された JSON 監査に記録する。
- 検出されたサービスやアプリケーションを監視する：systemd、runit、OpenRC、Docker、サーバー、VNC など。

### 本プロジェクトが行わないこと

- nftables、iptables、Fail2Ban を置き換えるものではありません。
- システムから独立した単体のファイアウォールではありません。
- 複数ユーザーの認証は提供しません。
- 通常の動作ではネットワーク API を公開しません。
- Web ダッシュボードではありません。
- 別のマシンからリモートマシンを直接保護するものではありません。
- 既定では自身のフォルダー以外にファイルをインストールしません。
- すべてのディストリビューションですべてのバックエンドが利用できることは保証しません。

---

## 機能

### 1. 機能検出と診断

- 検出された機能のレジストリを表示。
- 識別子で特定の機能の詳細を表示。
- コンポーネントのインストール後にシステムを手動で再スキャン。
- 最近の診断結果を表示。
- アプリケーションログの閲覧と検索。
- 状態と診断を JSON、TXT、HTML でエクスポート。
- **omega スイート** カテゴリ：omega-serv（検出済みで稼働中のインスタンス）、omega-waf（`magnet` エクストラが有効）、omega-jail（インストール済みの jail）。レジストリ、ダッシュボード、レポートに表示されます。

### 2. IP の統合管理

統合ブラックリストにより、同じ画面から nftables と iptables を扱えます。

- 1 つの IP または IP のリストを BAN。
- BAN の解除を個別または一括で。
- 直接入力またはファイルからのインポート。
- バックエンドごとの一覧または統合ビュー。
- NFTables/IPTables バックエンド間の同期。
- リストのエクスポートと再インポート。
- 1 つまたは複数のバックエンドの完全なクリーンアップ。
- IPv4 と IPv6 に対応。
- 専用画面からブロックリストファイル（`var/blocklist/`）とそのピン留めを直接管理。

### 3. ルールとポリシーの管理

- 高度なルールを作成するためのステップバイステップのウィザード。
- システムのルールと Omega-Fire が作成したルールの一覧。
- 選択によるルールの削除。
- 参照データベース内の無効なルールを自動的に整理。
- データベースを実際のファイアウォールに合わせてクリーンアップ・再同期します。プレビューと事前バックアップ付きで、ファイアウォール自体は一切変更しません。
- 他のツール（UFW、Tailscale、Docker…）のルールを由来で識別：情報として表示し、Omega-Fire から削除することはありません。
- 他のツールが iptables にルールを持つ場合、ポリシーの適用や iptables のフラッシュの前に安全確認：すべてに適用、nftables のみ、またはキャンセル — 影響はヘルプに詳しく記載されています。
- 定義済みポリシーの適用。
- ポリシー適用前の自動バックアップ。
- ポリシーのカスタマイズ、保存、復元。
- ステータスメニューとダッシュボードでアクティブなポリシーを表示。
- 変更されたプロファイルを `プロファイル + CUSTOM` の形で表示。
- テーブル管理（メニュー 3.5）：バックエンドごとの読み取り専用診断（テーブルの有無、input/output/forward ポリシー、ルール数）と、バックエンド間で異なるポリシーの説明（実際の効果、原因、対処法）。
- 初回利用時に nftables テーブルを初期化し、設定済みの chain を上書きすることはありません。
- 以前のプロファイルが残した孤立した制限的ポリシーを修正するため、バックエンドの chain ポリシーを ACCEPT にリセット。
- 1 つのバックエンドを対象に空にする、または検出されたすべてのバックエンドを 1 回の操作で同期して空にする。
- nftables テーブルの完全な削除（個別ルールの削除を超える高度な操作）。

### 4. Fail2Ban の管理

- jail とそのパラメーターの詳細な状態。
- BAN された IP の数とレート制限の情報。
- jail 内での IP の検索。
- 個別または複数の ban と unban。
- jail、バックエンド、ファイル間での IP の移動。
- カスタム jail のガイド付き作成。
- 定義済みの jail テンプレート（編集・削除可能）。
- 各 jail の由来：Omega-Fire、omega-jail、fail2ban のメイン設定、またはその他のファイル。
- ファイル名に関係なく確実に jail を削除：omega-jail がインストールした jail には警告、`jail.local` や共有ファイルの jail は理由を示して拒否、fail2ban の標準フィルターは決して削除しません。
- jail を空にする、または全体のパージ。
- JSON、TXT、HTML でのエクスポート。
- 設定の確認と監査。
- サービスの制御：状態、起動、停止、再起動、起動時の有効化と無効化。起動または停止の後、機能レジストリとダッシュボードが更新されます。

### 5. ログとメンテナンス

- **ログライブラリ**（5.1）：検出された omega-serv インスタンスのログ（omega-waf のログを含む）の自動インポート、パスの手動ピン留め、SSH によるリモートログの取得（鍵またはエージェント、パスワードは使いません）。
- **お気に入り**（5.2）：ライブラリのログを組み合わせ、名前とビューアーを付けて保存し、直接起動します。
- **ログを見る**（5.3）：設定なしで 1 つのログを、好みのビューアーで — シンプル（リアルタイムダッシュボード）、クラシック（最後の数行の後ライブ追跡）、または `lnav`。
- `lnav` の統合：複数のログを 1 つの時系列ビューに統合し、Omega-Fire のヘッダー/フッターで包みます（[ナビゲーション](#ナビゲーション) を参照）。
- Top N による最頻出 IP の分析。エクスポートして対象指定のクリーンアップに再読み込みできます。
- LOG または TXT ファイルから 1 つ以上の IP を対象指定で削除。手入力、またはエクスポートからチェックして選択します。
- **チェックで選べるプリセット**付きのピン留めファイル：マシン上に実際に存在する一般的なパスだけが提示されます。
- ローテーションと、即時または自動のバックアップ。
- バックアップの復元。
- 経過期間、クォータ、種類、手動選択によるパージ。
- フォルダーまたは環境ごとの高度なクリーンアップ。
- 24 時間、7 日、30 日の統計。
- jail 内のイベント、変動、クォータ、IP の分析。

### 6. エクスポートとレポート

利用できる形式：

- **JSON**：構造化された再利用可能なデータ。
- **TXT**：生の形式、または取り込み用に調整した形式。
- **HTML**：読みやすく視覚的なレポート。

利用できるレポート：

- 完全なブラックリスト。
- 構造化された ruleset。
- 由来で選択したルール：システム、Omega-Fire、またはアクティブ。
- 完全な監査レポート。
- Fail2Ban の統計。
- システムの状態と診断。
- 7 日または 30 日の統計レポート。
- IP の Top N ランキング。
- ヘルプガイドと FAQ。

**すべてのエクスポートを見る**（6.5）：エクスポートしたすべてのファイルを 1 か所に、種類・日付・サイズ付きで表示。HTML レポートはユーザーの既定の Web ブラウザーで開き、JSON や TXT は Omega-Fire 内で読めます。ターミナルもファイルマネージャーも不要です。

HTML テーマ：

- `omega-base` — ミッドナイトブルーとシアン、既定のテーマ。
- `omega-burn` — 赤橙色の熾火。
- `omega-neon` — シアンとマゼンタのサイバーパンク。
- `light-basic` — 明るく落ち着いた配色。
- `light-alt` — クリーム色の紙とフォレストグリーン。

エクスポートの言語：設定で別に指定でき（既定は「インターフェースと同じ」）、インターフェースの言語を変えずに、読み手の言語でレポートを渡せます。

### 7. システムと永続化

- 完全な状態のバックアップ：ルール、nftables の BAN、iptables の BAN、Fail2Ban。
- タイムスタンプ付き `.tar.gz` アーカイブの作成。
- スナップショットの一覧と復元：同一に再作成できる Omega-Fire のルールだけを戻し、他のツールのルールには一切触れません。
- 操作の履歴。
- 履歴のフィルタリングとパージ。
- 再起動なしでの設定の再読み込みと再スキャン。

### 8. モニタリングと統計

- 定期更新（2 秒ごと）のリアルタイムダッシュボード。収集中もインターフェースはブロックされません。
- アクティブなポリシーの表示。
- conntrack によるアクティブな接続。
- トラフィック、イベント、統計、サーバーログ。
- 7 日と 30 日の統合レポート。
- スナップショットとレポートの HTML エクスポート。

### 9. 設定

- スイートの他のツールと共通の 10 種類の `omega-*` テーマからアクティブなテーマを選択（[テーマとターミナル](#テーマとターミナル) を参照）。起動をまたいで保持されます。
- 描画プロファイル（自動、完全、標準、縮小、mono のみ）を手動で上書きでき、次回の起動時に適用されます。
- 17 言語から選ぶインターフェースの言語（[インターフェースの言語](#インターフェースの言語) を参照）：再起動するのはインターフェースだけで、ファイアウォールのルール、Fail2Ban、各サービスには影響しません。
- HTML と TXT のエクスポートの言語（インターフェースの言語とは独立）。
- 変更できるエクスポートとスクリーンショットのフォルダー（確認後に空にできます）。
- メインメニュー（`9. 設定`）から、または `s` キーで直接開けます。

### 10. ヘルプ

- **ヘルプガイド**：すべてのヘルプシートをメニュー順にまとめ、各シートから関連シートを開けます。
- **FAQ**：実際の利用で出会った質問（他のツールのルール、復元、Fail2Ban、ログ、エクスポートとブラウザー）。
- ガイドと FAQ の HTML エクスポート（エクスポート言語で）。
- `a` キーは引き続き現在の画面のヘルプです。

---

## アーキテクチャ

```text
src/omega_fire/
├── app/              ブートストラップと依存性注入コンテナー
├── core/             機能、列挙型、例外
├── domain/           純粋なビジネスロジック：ルール、IP、jail、ログ
├── application/      オーケストレーション：commands と queries
├── infrastructure/   バックエンド、ストレージ、エクスポート、ログ、システムプローブ
├── ports/            Protocol/ABC の契約
├── interfaces/       interfaces/tui/（Textual、既定）+ interfaces/cli/（Rich、--legacy-cli）
├── plugins/          組み込み拡張：nftables、iptables、Fail2Ban、conntrack
└── shared/           パース、ネットワーク、整形、横断的ユーティリティ
```

### 設計原則

- `domain/` は I/O もインフラストラクチャへの依存も含みません。
- `application/` はドメインとポートを通じてユースケースをオーケストレーションします — Textual の画面と Rich インターフェースのアクションは同じ commands/queries を呼び出し、ビジネスロジックはどちらのインターフェースにも依存しません。
- `infrastructure/` は `nft`、`iptables`、`fail2ban-client` などの外部ツール（subprocess、pty、ファイル）を呼び出すことが許された唯一のレイヤーです。
- `interfaces/` は `subprocess` を直接呼び出してはいけません。
- `ports/` はアダプターが期待する契約を定義します。
- `core/` は各レイヤーが使う機能レジストリを提供します。
- プラグインにより、ビジネスドメインを変更せずにバックエンドを追加・発展させられます。
- Textual インターフェース（`interfaces/tui/`）は [`omega-lib`](https://github.com/)（OMEGA スイート全体で共有される依存関係：9 トークンのテーマ、ターミナル検出、共通のポート契約）に依存しています。PyPI では公開されておらず、配布アーカイブに同梱されています（`vendor/omega-lib/`、[インストール](#インストール) を参照）。
- Textual の画面から起動される時間のかかる可能性がある呼び出し（ファイアウォールのバックエンド、`fail2ban-client`、ディスク）はすべてバックグラウンド（スレッド）で実行され、インターフェースのメインスレッドでは決して実行されません — 操作中もダッシュボードやフォームは応答し続け、アプリケーション全体が固まることはありません。

### データ構造

Omega-Fire は外部 ORM を使わず、標準ライブラリの `sqlite3` を介して SQLite を使用します。主なデータセットは BAN、ルール、監査イベント、スナップショットに関するものです。

マイグレーションはバージョン管理されており、起動時に自動的に適用されます。

---

## 前提条件

### システム

- Linux。Arch Linux と互換ディストリビューションを優先。
- Python 3.10 以上。
- `sudo` で利用できる root 権限。
- サービスマネージャー：systemd、runit、OpenRC のいずれか。
- 少なくとも 1 つのファイアウォールバックエンド：nftables または iptables。
- 80x24 以上のターミナル（利用可能なサイズに応じた描画プロファイルの詳細は [テーマとターミナル](#テーマとターミナル) を参照）。

### Python の依存関係

本番用の依存関係は `requirements.txt` に定義されています：

- `textual` — 既定の TUI インターフェース。
- `omega-lib` — テーマ、ターミナル検出、OMEGA スイートと共有する契約（PyPI では非公開。[アーキテクチャ](#アーキテクチャ) と [インストール](#インストール) を参照）。
- `rich` — `--legacy-cli` インターフェースと一部のレポートの描画。
- `psutil` — ダッシュボードと診断用のシステム情報（CPU、メモリ、ネットワーク、プロセス）。
- `jinja2` — HTML エクスポートの生成。
- `python-dotenv` — 環境変数。
- `pyte` — `lnav` を埋め込むための仮想ターミナルエミュレーター（メニュー 8.6 と 5.2 / 5.3 の lnav ビューアー）。

品質ツール（`pytest`、`black`、`flake8`、`mypy`）は `requirements.txt` にコメントとして記載されています。プロジェクトに貢献する場合は、コメントを外すか個別にインストールしてください（[テストと品質](#テストと品質) を参照）。

### 推奨されるオプションのツール

これらのツールがない場合、アプリケーションは縮退モードで動作します：

- `fail2ban` — 自動 BAN。
- `conntrack` または `conntrack-tools` — アクティブな接続とネットワーク統計。
- `lnav` — 複数ファイルにまたがる高度なログ分析。

Arch Linux とその派生ディストリビューションでは：

```bash
sudo pacman -S fail2ban conntrack-tools lnav
```

---

## インストール

公式アーカイブは `.tar.gz` 形式で提供されます。インストール前に整合性を確認してください：

```bash
sha256sum omega-fire.tar.gz
```

> ⚠️ **以下の 3 つの方法は初回インストール用です。** `~/omega-fire` がすでに存在する場合（以前のバージョンからの更新）は、下の [更新](#更新) セクションを使ってください — 既存の `omega-fire` フォルダーの中からこれらのコマンドを再実行しないでください：`tar` は入れ子の `omega-fire/omega-fire/` を作成しようとし、そのフォルダーが root の所有であれば権限エラーで失敗します（以前の展開を誤って `sudo tar` で行った場合によく起こります）。

### 方法 1 — インストールスクリプト

```bash
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ すでに omega-fire フォルダーの中にいるようです — README の更新セクションを参照してください。" >&2; exit 1; }
[ -d omega-fire ] && echo "ℹ️ ここにはすでに展開済みのため、この手順を省略します。" || tar -xzf omega-fire.tar.gz
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire はすでに存在するため、移動を省略します。" || mv omega-fire ~/
cd ~/omega-fire/
chmod +x install.sh
./install.sh
```

起動：

```bash
./omega-fire.sh
```

エイリアスをインストールした場合は、新しいターミナルを開いて次を使います：

```bash
fire
```

### 方法 2 — 堅牢な完全インストール

このコマンドは再実行できます：すでに完了した手順は省略されます。

```bash
([ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ すでに omega-fire フォルダーの中にいるようです — README の更新セクションを参照してください。" >&2; exit 1; }; [ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire はすでに存在するため、展開を省略します。" || (tar -xzf omega-fire.tar.gz && mv omega-fire ~/)) && cd ~/omega-fire/ && ([ -d .venv ] && echo "ℹ️ .venv はすでに存在するため、この手順を省略します。" || python3 -m venv .venv) && source .venv/bin/activate && ([ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib || true) && pip install -r requirements.txt && chmod +x omega-fire.sh && mkdir -p var && (getent group omega-fire >/dev/null 2>&1 && echo "ℹ️ omega-fire グループはすでに存在します。" || sudo groupadd omega-fire) && (groups "$USER" 2>/dev/null | grep -qw omega-fire && echo "ℹ️ $USER はすでに omega-fire グループのメンバーです。" || sudo usermod -aG omega-fire "$USER") && sudo chgrp -R omega-fire var && sudo chmod -R 2775 var && echo "✅ Omega-Fire をインストールしました。./omega-fire.sh を実行してください。"
```

### 方法 3 — 詳細なインストール

```bash
# 0. 既存の omega-fire の中から再実行していないことを確認する
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ すでに omega-fire フォルダーの中にいるようです — README の更新セクションを参照してください。" >&2; exit 1; }

# 1. 展開する
[ -d omega-fire ] && echo "ℹ️ ここにはすでに展開済みのため、この手順を省略します。" || tar -xzf omega-fire.tar.gz

# 2. ホームに移動する
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire はすでに存在するため、移動を省略します。" || mv omega-fire ~/

# 3. プロジェクトに入る
cd ~/omega-fire/

# 4. 仮想環境を作成する
[ -d .venv ] && echo "ℹ️ .venv はすでに存在するため、作成を省略します。" || python3 -m venv .venv

# 5. 依存関係をインストールする（同梱の omega-lib があれば requirements.txt より先に）
source .venv/bin/activate
[ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib
pip install -r requirements.txt

# 6. ランチャーを実行可能にする
chmod +x omega-fire.sh

# 7. root と現在のユーザーのために var/ を準備する
mkdir -p var
getent group omega-fire >/dev/null 2>&1 || sudo groupadd omega-fire
groups "$USER" 2>/dev/null | grep -qw omega-fire || sudo usermod -aG omega-fire "$USER"
sudo chgrp -R omega-fire var
sudo chmod -R 2775 var

# 8. 起動する
./omega-fire.sh
```

`vendor/omega-lib/` は公式アーカイブにのみ含まれます（omega-lib は PyPI で公開されていないため、`build-release.sh` が自動的に同梱します）。開発用クローンでは、専用のリポジトリから個別にインストールしてください（`pip install -e path/to/omega-lib`）。

専用グループと `setgid` ビットにより、root とユーザーはシステム全体に権限を開くことなく `var/` に生成されたファイルを共有できます。グループへの所属をすぐに反映させるには、再ログインまたは `newgrp omega-fire` が必要になる場合があります。

### 更新

`~/omega-fire` がすでに存在する場合（以前のインストール）、**このフォルダーの中からインストールコマンドを再実行しないでください**：`tar` は入れ子の `omega-fire/omega-fire/` を作成しようとして失敗し、フォルダーが `root` の所有であれば通常「許可がありません」のエラーが続出します（以前の展開を誤って `sudo tar` で行った場合によく起こります）。

推奨手順。**`~/omega-fire` 以外** の任意のフォルダー（通常は `~` そのもの）から実行します：

```bash
# 1. 既存のインストールの状態と所有者を確認する
ls -ld ~/omega-fire

# 2. 上書きせずに古いインストールを退避する
sudo mv ~/omega-fire ~/omega-fire.old-$(date +%Y%m%d)

# 3. 新しいアーカイブをホームに直接展開する
tar -xzf omega-fire.tar.gz -C ~/

# 4. 再インストールする（venv を作り直し、依存関係を再インストールし、var/ の権限を設定し直す）
cd ~/omega-fire
chmod +x install.sh
./install.sh

# 5. 起動する
./omega-fire.sh
```

手順 4（`./install.sh`）はこの状況を自動的に検出し（ここに `var/db/` データベースがなく、すぐ隣に `~/omega-fire.old-YYYYMMDD` フォルダーが見つかる）、古いインストールから `config/omega-fire.conf`、データベース、ブロックリスト、バックアップ、エクスポート、スクリーンショットを **自ら回収します** — 質問も手動の手順もありません。以前のインストールの内容にかかわらず、上記の手順 1〜5 以外に行うことはありません。

古いインストールに見えるフォルダーが隣に複数ある場合（あいまい）、`install.sh` は何も推測しません：それらのパスを表示し、正しいソースを特定したうえで `sudo ./migrate-state.sh <フォルダー>` を自分で実行するよう促します。

新しいインストールを確認できたら、古いフォルダー `~/omega-fire.old-YYYYMMDD` は削除できます（`sudo rm -rf ~/omega-fire.old-YYYYMMDD`）。

### Bash または Zsh のエイリアス

```bash
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.bashrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.bashrc
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.zshrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.zshrc
```

続いてシェルを再読み込みします：

```bash
source ~/.bashrc 2>/dev/null || source ~/.zshrc
```

### Nerd Fonts のアイコンと記号

アイコンが表示されない場合は、Nerd Fonts の記号をインストールしてください：

```bash
mkdir -p ~/.local/share/fonts
curl -fLo /tmp/NerdFontsSymbolsOnly.zip \
  https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip
unzip -o /tmp/NerdFontsSymbolsOnly.zip -d ~/.local/share/fonts
fc-cache -fv
```

---

## 使い方

### 起動

```bash
cd ~/omega-fire
./omega-fire.sh

# またはエイリアスを作成済みなら単に：
fire
```

ランチャーは：

1. root 権限を確認し、必要なら `sudo` で再起動します。
2. `.venv`、`venv`、またはシステムの Python を検出します。
3. `PYTHONPATH` を `src/` に設定します。
4. `python -m omega_fire` を起動します — 既定では **Textual** インターフェースです。

代わりに従来の Rich インターフェース（番号を順に入力）を起動するには：

```bash
./omega-fire.sh --legacy-cli
```

旧インターフェースはバージョン 3.0 のまま、フランス語です：元のメニュー 5（ライブラリ、お気に入り、クラシックビューアーなし）、「すべてのエクスポートを見る」なし、ヘルプガイドと FAQ なし、プリセットなし。Textual インターフェースには完全なバージョン 3.5 が含まれます。

### インターフェースの言語

17 言語：フランス語、英語、スペイン語、ポルトガル語（ブラジル）、イタリア語、ドイツ語、オランダ語、ポーランド語、ロシア語、中国語、ベトナム語、タイ語、インドネシア語、日本語、韓国語、ヒンディー語、アラビア語。設定（`s` キー、翻訳されないラベル「Langue / Language」）で選択し、インターフェースだけを再起動して適用します。一時的に `OMEGA_FIRE_LANG=ja ./omega-fire.sh` で指定することもできます（起動スクリプトが `sudo` 越しに保持します）。Linux のテキストコンソール（TTY）では、コンソールフォントに文字がない言語（ベトナム語、中国語、タイ語、日本語、韓国語、ヒンディー語、アラビア語）はそのセッションの間、英語で表示されます。アラビア語は右から左に表示されます。ヒンディー語では、Terminator、GNOME Terminal、Xfce Terminal、Alacritty はテキストを揃えて表示します。結合文字を自前で組み立てるターミナル（Kitty、Ghostty、Konsole）では枠や列がずれることがあります。**エクスポートの言語**（HTML と TXT のレポート）は別に設定でき、既定は「インターフェースと同じ」です。アプリケーションログと監査履歴はフランス語で記録されたままで、履歴のタイトルは選んだ言語で表示されます。旧インターフェース（`--legacy-cli`）はフランス語のままです。

### 全体の流れ

1. 起動画面（splash）。ターミナルが小さすぎる場合は続いて警告。
2. システム機能の検出（専用画面、ブロックしない）。
3. メインメニュー：8 つのテーマ別セクション（1-8）、設定（9）、ヘルプ（10）。
4. セクションを選び、次にアクションを選択 — 各アクションはフォームを開き、必須項目はすべて先に進む前に検証されます。
5. 重要または破壊的な操作（flush、パージ、復元...）の前には明示的な確認。
6. 時間のかかる操作はバックグラウンドで実行され（待機中もインターフェースは使用可能）、結果の要約とともにメニューに戻ります。

### ナビゲーション

- 上下の矢印キー：リストやメニューでカーソルを移動。
- Tab / Shift+Tab：フォームの項目間を移動。
- Enter：選択または確定。
- 表の行をクリック：その行を選択し、関連する項目（ピン留めするソース、対象の jail など）を自動入力。
- `Esc`：前の画面に戻る（ホーム画面では終了の確認を求めます）。
- `a`：コンテキストヘルプ — 現在のアクションを詳しく説明します。アクション画面がまだ開いていない場合は、現在のセクションのすべてのアクションを説明します。完全なガイドと FAQ はメニュー 10 にあります。
- `t`：確認なしで次のテーマに切り替え。
- `r`：ターミナルのサイズと種類を再検出。
- `s`：設定（テーマ、描画プロファイル、言語、フォルダー）を開く。
- `q` / `Ctrl+Q`：確認のうえ終了。

#### lnav 画面の特徴（8.6、および 5.2 / 5.3 の lnav ビューアー）

`lnav` は疑似ターミナルに埋め込まれ、そのビューの周囲に Omega-Fire のヘッダー/フッターが常に表示されます。これにより、`lnav` 固有のショートカットと Omega-Fire のショートカットが衝突しないようにしています：

- 矢印 ↑↓：ログ内を移動（`lnav` 固有のショートカット、そのまま転送）。
- 矢印 ←→：長い行を横スクロール（`lnav` 固有のショートカット）。
- `g` / `G`：先頭 / 末尾へ移動（`lnav` 固有のショートカット）。
- `Ctrl+C`：現在の行にマークを付けてシステムのクリップボードにコピー（一部のシステムで固まることがある `lnav` 固有のコピーコマンドの代わり）。
- 小文字の `t`：このビュー専用の次のテーマ（大文字の `T` は行間の経過時間を表示する `lnav` 固有のショートカットのままです）。
- `Ctrl+Q`：Omega-Fire に戻る（アプリケーションを終了せずに `lnav` を正しく閉じます）。

---

## テーマとターミナル

10 種類の `omega-*` テーマが OMEGA スイートの他のツールと共通です：

```text
omega-base       omega-dark       omega-light
omega-neon       omega-burn       omega-pink
omega-hack       omega-contrast   omega-mono
omega-minimal
```

- `t` でテーマを切り替えるか、設定（`s`）から直接選択します。
- 選択したテーマは保存され、次回の起動時にも使われます。
- Omega-Fire は検出したターミナルに合わせて、**描画プロファイル** により視覚的な複雑さ（枠線、splash、情報密度）を自動調整します：完全、標準、縮小、Mono（ASCII のみ）。プロファイルは設定から手動で上書きできます。

| 最小サイズ | プロファイル | 代表的なターミナル |
|---|---|---|
| 120×32 以上 | 完全 | Ghostty, Alacritty, WezTerm, Kitty |
| 100×28 以上 | 標準 | Konsole, GNOME Terminal, Terminator, xfce4-terminal |
| 80×24 以上 | 縮小 | urxvt, xterm, 最新の SSH |
| 80×24 未満 | Mono（ASCII のみ） | Linux TTY, 古い SSH |

80×24 未満では起動が拒否されます（最小サイズが必要）。ターミナルのサイズを変えて再起動するか、表示が自動更新されない場合はサイズ変更後に `r` を使ってください。

---

## 設定

個別の設定は次のファイルで調整できます：

```text
omega-fire/config/omega-fire.conf
```

主に次の内容を定義できます：

- ログのパス；
- モニタリングのサーバーとソース；
- 利用可能なバックエンドまたはカスタムパス；
- 分析対象の環境；
- 特定のインストールに合わせたパラメーター。

設定は再起動時、または手動の再スキャン時（メニュー 1.3 または 7.4）に再読み込みされます。

このファイルは完全にオプションであり（なくてもアプリケーションは環境変数にフォールバックして正常に動作します）、**配布アーカイブからは除外されています** — 更新によって黙って上書きされることはなく、該当する場合は `install.sh` が古いインストールから自動的に回収します（上の「更新」を参照）。

### 内部パスとシステムパス

既定では、Omega-Fire は自身のフォルダー内で動作します：

```text
var/exports/       # プロジェクト内部のフォルダー
/var/exports/      # システムの絶対パス
```

したがって先頭の `/` には意味があります。システムへのインポートとエクスポートはユーザーが明示的に要求する必要があります。

---

## バックエンドと互換性

Omega-Fire はコンポーネントを検出し、利用可能な機能だけを有効にします。

| コンポーネント | 役割 | 状態 |
|---|---|---|
| nftables | 最新の IPv4/IPv6 ファイアウォール | 推奨 |
| iptables | IPv4 ファイアウォール | 対応 |
| ip6tables | iptables による IPv6 ファイアウォール | 利用可能なら対応 |
| Fail2Ban | jail と自動 BAN | オプション |
| conntrack | アクティブな接続 | オプション |
| lnav | 高度なログ分析 | オプション |
| systemd, runit, OpenRC | サービス管理 | 自動検出 |
| Docker, VNC, サーバー | 検出されたアプリケーションとサービス | インストールによる |

### IPv4 と IPv6

両方のアドレスファミリーが対応するバックエンドでサポートされます：

- nftables：IPv4 と IPv6 のデュアルスタック；
- iptables/ip6tables：利用可能なバイナリによる；
- Fail2Ban：jail とシステムの設定による。

長い形式、圧縮形式、ローカル、混在形式、ゼロを含む形式、CIDR 表記の IPv6 は、対応するコンポーネントによって処理されます。

---

## 永続化、ログ、エクスポート

### 永続化

- `sqlite3` による SQLite。
- BAN、ルール、監査、スナップショットに関するテーブル。
- 自動的に適用されるバージョン管理されたマイグレーション。
- `.tar.gz` 形式の完全な状態のアーカイブ。
- ピン留め（お気に入りのログソース）と最近の履歴は JSON（`var/runtime/`）に保存され、再起動後も残ります。

### ログ

- アプリケーションのテキストログ：`var/logs/app.log`。
- `event_type`、`actor`、`action`、`result`、`details` などを含む構造化された JSON 監査ログ。

### エクスポート

エクスポートは JSON、TXT、HTML で利用でき、HTML レポート用に複数の CSS テーマがあります。

---

## セキュリティ

Omega-Fire はシステムの重要なコンポーネントに作用するため、慎重に使用する必要があります。

- 起動には `sudo` による root 権限が必要です。
- flush、全体のパージ、ポリシーの適用は破壊的になり得ます。
- 定義済みポリシーは変更前に自動バックアップを実行します。
- iptables / ip6tables では、ポリシーの適用やバックエンドのフラッシュによって他のツール（UFW…）のルールも消えます：Omega-Fire はそれを知らせ、実行前に選択させます。
- 大きな変更の前には毎回手動でバックアップを取ってください。
- 各操作の後に、ファイアウォール、jail、接続の実際の状態を確認してください。
- まず使い捨てのマシンや対象でテストしてください。
- IPv4 のテストには RFC 5737 のドキュメント用ネットワークを使ってください：`192.0.2.0/24`、`198.51.100.0/24`、`203.0.113.0/24`。
- 本番マシンで復元する前に、エクスポートとスナップショットを確認してください。
- `var/` フォルダーに必要以上の権限を与えないでください。

---

## テストと品質

テストスイートには 137 のユニットテスト（8,000 件以上の検証ケース）があります：ビジネスドメイン、オーケストレーション（`application/`）、インフラストラクチャ、そして 3.5 で追加・修正された Textual 画面を、実際のスタイルシートで実行します（レイアウト、完全な操作フロー、エクスポート言語）。このアーカイブには `tests/` フォルダーは含まれていません。実行する必要がある場合は、開発リポジトリから取得してください。

```bash
source .venv/bin/activate
python -m unittest discover -s tests/unit -t .
```

レイヤードアーキテクチャにより、ビジネスドメインとプレゼンテーションは厳密に分離されています（`domain/`、`application/`、`Protocol` としての `ports/`、[アーキテクチャ](#アーキテクチャ) を参照）。ほとんどのテストは root も実際のファイアウォールも必要としません。

プロジェクトに貢献する場合は、`requirements.txt` に（コメントとして）記載されている品質ツールをインストールしてください：

```bash
pip install pytest pytest-cov black flake8 mypy
```

インストール後に使えるツール：

```bash
black .
flake8 .
mypy src/
pytest --cov
```

---

## プロジェクトの状況

### 稼働しているポイント

- 主要なネットワークセキュリティ機構のための統合 Textual TUI。検証付きフォーム、テーマ、コンテキストヘルプは OMEGA スイートと共通。
- 従来の Rich インターフェースを代替として維持（`--legacy-cli`）。
- 機能の自動検出。
- 利用可能なバックエンドの管理。
- 存在するツールに応じた IPv4/IPv6 対応。
- アプリケーションのログ記録と監査。
- バックアップと復元。
- JSON、TXT、HTML のエクスポート。
- インターフェースをブロックせずバックグラウンドで更新されるダッシュボードと統計。
- 文書化されたレイヤードアーキテクチャ。

### 既知の制限

- テストスイートは 3.5 の Textual 画面をカバーしていますが、古い画面のすべてはまだカバーしていません（[テストと品質](#テストと品質) を参照）。
- `ExecutionPlan`/`PipelineStep` の仕組みはプロジェクト内に一部残っています。
- 機能が実際に使えるかどうかは、ホストマシンのバイナリ、サービス、権限、設定によって決まります。
- 従来の Rich インターフェース（`--legacy-cli`）は、もはや開発の中心ではありません。Textual インターフェースが実環境で完全に信頼できるようになるまでの間、維持されています。

---

## アンインストール

データがプロジェクトフォルダー内に残っている場合：

```bash
sudo rm -rf ~/omega-fire
```

他の場所にエクスポートしたファイル、`~/.bashrc` や `~/.zshrc` に追加した `fire` エイリアス、そして使われなくなった専用グループは手動で削除してください：

```bash
sudo groupdel omega-fire
```

この最後のコマンドは、他のファイルやサービスがこのグループに依存していない場合にのみ実行してください。

---

## ライセンス

Omega-Fire は **MIT** ライセンスで配布されています。全文はファイル [`LICENSE`](../../../LICENSE) を参照してください。

---

> **Omega-Fire — 観察し、操縦し、監査し、守る。**
>
> nftables、iptables、ip6tables、Fail2Ban、ログ、ネットワーク監視のための統合 TUI インターフェース。
