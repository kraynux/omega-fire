<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->

<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-fire.png" alt="Omega-Fire" width="384">
</div>

# 󰦝 OMEGA-FIRE

**Einheitliche Leitstelle für die Netzwerksicherheit**

> Entwickelt von **kraynux** für **Omega-server** 
[https://kraynux.snake-mackarel.ts.net](https://kraynux.snake-mackarel.ts.net)

Offizielle Seite: [OMEGA-FIRE](https://kraynux.snake-mackarel.ts.net/omega-fire/) &nbsp; Vorschau: [Screenshots](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/)  

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)
[![Interface](https://img.shields.io/badge/Interface-Textual%20TUI-cyan.svg)](https://github.com/Textualize/textual)

**Sprachen:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

**Omega-Fire** ist eine Python-TUI-Anwendung (Terminal User Interface), gebaut mit [Textual](https://github.com/Textualize/textual). Sie bietet im Terminal eine einheitliche Oberfläche zur Verwaltung von Linux-Firewalls, Fail2Ban, gesperrten Adressen, Netzwerkregeln, Logs und Systemstatistiken.

Die Textual-Oberfläche ist der Standardbetriebsmodus und navigiert über Menüs, validierte Formulare (alle Pflichtfelder werden vor dem Fortfahren geprüft) und eigene Bildschirme, mit Themes, kontextbezogener Hilfe und Tastenkürzeln, die mit dem Rest der OMEGA-Suite geteilt werden (omega-check, omega-deep, omega-stress...). Die alte, sequenzielle und über Zifferneingabe gesteuerte [Rich](https://github.com/Textualize/rich)-Oberfläche bleibt über `--legacy-cli` verfügbar (siehe [Start](#start)). 
Vorschau: [Screenshots](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/index-2.html)

Das Projekt folgt den Prinzipien der **Clean Architecture**, mit einer klaren Trennung zwischen Fachdomäne, Orchestrierung, Infrastruktur und Benutzeroberfläche.

## Inhalt

- [Vorstellung](#vorstellung)
- [Funktionen](#funktionen)
- [Architektur](#architektur)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Verwendung](#verwendung)
- [Konfiguration](#konfiguration)
- [Backends und Kompatibilität](#backends-und-kompatibilität)
- [Persistenz, Logs und Exporte](#persistenz-logs-und-exporte)
- [Sicherheit](#sicherheit)
- [Tests und Qualität](#tests-und-qualität)
- [Projektstatus](#projektstatus)
- [Deinstallation](#deinstallation)
- [Lizenz](#lizenz)

---

## Vorstellung

Omega-Fire dient als **lokale Leitstelle** für die Netzwerksicherheit. Es erkennt automatisch die auf dem Rechner vorhandenen Komponenten und passt die Menüs an die tatsächlich verfügbaren Fähigkeiten an.

### Ziele

- nftables, iptables, ip6tables und Fail2Ban in einer stimmigen Oberfläche zusammenführen.
- Beobachtung von und Eingriffe in Verbindungen, Sperren und Systemereignisse erleichtern.
- Exporte, Sicherungen, Audits und den Verlauf der Vorgänge zentralisieren.
- Eine testbare und erweiterbare Architektur bewahren.
- Im eingeschränkten Modus arbeiten, wenn eine optionale Komponente fehlt.

### Was Omega-Fire leistet

- Erkennt die verfügbaren Backends, Dienste, den Kernel und die Werkzeuge.
- Verwaltet nftables, iptables und ip6tables, wenn diese Komponenten vorhanden sind.
- Verwaltet gesperrte IPs, einzeln oder stapelweise, mit Import, Export, Synchronisation und Flush.
- Erstellt, listet und löscht erweiterte Regeln.
- Wendet vordefinierte Richtlinien mit vorheriger automatischer Sicherung an.
- Verwaltet die Fail2Ban-Jails und ihre Sperren.
- Analysiert Logs live oder in Form von Statistiken.
- Bietet Überwachung in Form von Monitoring.
- Nutzt conntrack zur Anzeige aktiver Verbindungen, wenn verfügbar.
- Erzeugt JSON-, TXT- und HTML-Exporte.
- Sichert und stellt den vollständigen Zustand in `.tar.gz`-Archiven wieder her.
- Protokolliert die Vorgänge in einem Anwendungslog und einem strukturierten JSON-Audit.
- Überwacht die erkannten Dienste und Anwendungen: systemd, runit, OpenRC, Docker, Server, VNC usw.

### Was das Projekt nicht leistet

- Es ersetzt weder nftables, iptables noch Fail2Ban.
- Es ist keine vom System unabhängige, eigenständige Firewall.
- Es bietet keine Mehrbenutzer-Authentifizierung.
- Es stellt im Normalbetrieb keine Netzwerk-API bereit.
- Es ist kein Web-Dashboard.
- Es schützt keinen entfernten Rechner direkt von einem anderen Rechner aus.
- Standardmäßig installiert es keine Datei außerhalb seines eigenen Ordners.
- Es garantiert nicht die Verfügbarkeit aller Backends auf allen Distributionen.

---

## Funktionen

### 1. Fähigkeiten und Diagnose

- Anzeige des Registers der erkannten Fähigkeiten.
- Detaillierte Ansicht einer Fähigkeit anhand ihrer Kennung.
- Manueller Neuscan des Systems nach der Installation einer Komponente.
- Ansicht der jüngsten Diagnosen.
- Ansicht und Suche im Anwendungslog.
- Export von Zustand und Diagnosen als JSON, TXT oder HTML.

### 2. Einheitliche IP-Verwaltung

Die einheitliche Blacklist erlaubt die Arbeit mit nftables und iptables vom selben Bildschirm aus.

- Sperren einer IP oder einer Liste von IPs.
- Entsperren einzeln oder stapelweise.
- Direkte Eingabe oder Import aus einer Datei.
- Liste pro Backend oder einheitliche Ansicht.
- Synchronisation zwischen den Backends NFTables/IPTables.
- Export und erneuter Import der Listen.
- Vollständige Bereinigung eines oder mehrerer Backends.
- Unterstützung für IPv4 und IPv6.
- Verwaltung der Blocklist-Dateien (`var/blocklist/`) und ihrer angehefteten Einträge direkt im zugehörigen Bildschirm.

### 3. Verwaltung von Regeln und Richtlinien

- Schritt-für-Schritt-Assistent zum Erstellen einer erweiterten Regel.
- Liste der Systemregeln und der von Omega-Fire erstellten Regeln.
- Löschen einer Regel per Auswahl.
- Automatische Bereinigung inaktiver Regeln in der Referenzdatenbank.
- Anwendung vordefinierter Richtlinien.
- Automatische Sicherung vor der Anwendung einer Richtlinie.
- Anpassung, Sicherung und Wiederherstellung einer Richtlinie.
- Kennzeichnung der aktiven Richtlinie im Statusmenü und im Dashboard.
- Kennzeichnung geänderter Profile in der Form `Profil + CUSTOM`.
- Tabellenverwaltung (Menü 3.5): schreibgeschützte Diagnose pro Backend (Vorhandensein der Tabelle, input/output/forward-Richtlinien, Anzahl der Regeln) mit Erkennung von Abweichungen zwischen den Backends.
- Initialisierung einer nftables-Tabelle bei der ersten Verwendung, ohne je eine bereits konfigurierte Chain zu überschreiben.
- Zurücksetzen der Chain-Richtlinien auf ACCEPT in einem Backend, um eine verwaiste restriktive Richtlinie eines früheren Profils zu korrigieren.
- Gezieltes Leeren eines Backends oder synchronisiertes Leeren aller erkannten Backends in einem einzigen Schritt.
- Vollständiges Löschen einer nftables-Tabelle (erweiterte Aktion, über einzelne Regeln hinaus).

### 4. Fail2Ban-Verwaltung

- Detaillierter Status der Jails und ihrer Parameter.
- Anzahl gesperrter IPs und Rate-Limit-Informationen.
- Suche nach einer IP in den Jails.
- Ban und Unban einzeln oder mehrfach.
- Übertragung von IPs zwischen Jails, Backends und Dateien.
- Geführte Erstellung eines eigenen Jails.
- Vordefinierte Jail-Vorlagen.
- Löschen eines Jails.
- Leeren eines Jails oder allgemeine Bereinigung.
- Export als JSON, TXT oder HTML.
- Prüfung und Audit der Konfiguration.
- Dienststeuerung: Status, Start, Stopp, Neustart, Aktivierung und Deaktivierung beim Systemstart.

### 5. Logs und Wartung

- Live Tail mit Omega-Fire-Dashboard.
- Anzeige mehrerer Dateien mit angehefteten Einträgen (bevorzugte Quellen, über Neustarts hinweg gespeichert).
- Integration von `lnav`: Auswahl einer oder mehrerer Dateien (Nummern oder manuelle Pfade, durch Kommas getrennt), automatische Zusammenführung in einer einzigen chronologischen Ansicht, eingebettet in einen Omega-Fire-Header/-Footer (siehe [Navigation](#navigation)).
- Analyse der häufigsten IPs mit Top N.
- Gezieltes Entfernen einer IP aus LOG- oder TXT-Dateien.
- Rotation und sofortige oder automatisierte Sicherungen.
- Wiederherstellung einer Sicherung.
- Bereinigung nach Alter, Kontingent, Typ oder manueller Auswahl.
- Erweiterte Bereinigung nach Ordner oder Umgebung.
- Statistiken über 24 Stunden, 7 Tage oder 30 Tage.
- Analyse von Ereignissen, Bewegungen, Kontingenten und in den Jails vorhandenen IPs.

### 6. Exporte und Berichte

Verfügbare Formate:

- **JSON**: strukturierte und wiederverwendbare Daten.
- **TXT**: Rohformat oder für die Einspeisung angepasst.
- **HTML**: lesbarer und visueller Bericht.

Verfügbare Berichte:

- Vollständige Blacklist.
- Strukturiertes Ruleset.
- Regeln nach Herkunft ausgewählt: System, Omega-Fire oder aktiv.
- Vollständiger Auditbericht.
- Fail2Ban-Statistiken.
- Systemzustand und -diagnose.
- Statistikberichte über 7 oder 30 Tage.

HTML-Themes:

- `omega-base` — Nachtblau und Cyan, Standard-Theme.
- `omega-burn` — rot-orange Glut.
- `omega-neon` — Cyberpunk in Cyan und Magenta.
- `light-basic` — hell und schlicht.
- `light-alt` — cremefarbenes Papier und Waldgrün.

### 7. System und Persistenz

- Sicherung des vollständigen Zustands: Regeln, nftables-Sperren, iptables-Sperren und Fail2Ban.
- Erstellung von `.tar.gz`-Archiven mit Zeitstempel.
- Liste und Wiederherstellung der Snapshots.
- Verlauf der Aktionen.
- Filtern und Bereinigen des Verlaufs.
- Neuladen der Konfiguration und Neuscan ohne Neustart.

### 8. Monitoring und Statistiken

- Echtzeit-Dashboard mit periodischer Aktualisierung (alle 2 Sekunden), ohne die Oberfläche während der Erfassung zu blockieren.
- Anzeige der aktiven Richtlinie.
- Aktive Verbindungen über conntrack.
- Datenverkehr, Ereignisse, Statistiken und Serverlogs.
- Konsolidierte Berichte über 7 und 30 Tage.
- HTML-Export von Snapshots und Berichten.

### 9. Einstellungen

- Auswahl des aktiven Themes unter den zehn `omega-*`-Themes, die mit dem Rest der Suite geteilt werden (siehe [Themes und Terminals](#themes-und-terminals)), über Neustarts hinweg gespeichert.
- Manuelles Überschreiben des Darstellungsprofils (automatisch, vollständig, Standard, reduziert oder nur Mono), angewendet beim nächsten Start.
- Erreichbar über das Hauptmenü (`9. RÉGLAGES`) oder direkt über die Taste `s`.

---

## Architektur

```text
src/omega_fire/
├── app/              Bootstrap und Container für Dependency Injection
├── core/             Fähigkeiten, Aufzählungen und Ausnahmen
├── domain/           Reine Fachlogik: Regeln, IPs, Jails, Logs
├── application/      Orchestrierung: Commands und Queries
├── infrastructure/   Backends, Speicherung, Exporte, Logs und Systemsonden
├── ports/            Protocol/ABC-Verträge
├── interfaces/       interfaces/tui/ (Textual, Standard) + interfaces/cli/ (Rich, --legacy-cli)
├── plugins/          Integrierte Erweiterungen: nftables, iptables, Fail2Ban, conntrack
└── shared/           Parsing, Netzwerk, Formatierung und übergreifende Hilfsfunktionen
```

### Gestaltungsprinzipien

- `domain/` enthält weder I/O noch Abhängigkeiten zur Infrastruktur.
- `application/` orchestriert die Anwendungsfälle über Domäne und Ports — die Textual-Bildschirme und die Aktionen der Rich-Oberfläche rufen dieselben Commands/Queries auf, die Fachlogik hängt von keiner der beiden Oberflächen ab.
- `infrastructure/` ist die einzige Schicht, die `nft`, `iptables`, `fail2ban-client` und die anderen externen Werkzeuge aufrufen darf (subprocess, pty, Dateien).
- `interfaces/` darf `subprocess` nicht direkt aufrufen.
- `ports/` definiert die von den Adaptern erwarteten Verträge.
- `core/` stellt das von den verschiedenen Schichten genutzte Fähigkeitsregister bereit.
- Die Plugins ermöglichen das Hinzufügen oder Weiterentwickeln von Backends, ohne die Fachdomäne zu ändern.
- Die Textual-Oberfläche (`interfaces/tui/`) stützt sich auf [`omega-lib`](https://github.com/) (von der gesamten OMEGA-Suite geteilte Abhängigkeit: Theme mit 9 Tokens, Terminalerkennung, gemeinsame Port-Verträge), nicht auf PyPI veröffentlicht — im verteilbaren Archiv enthalten (`vendor/omega-lib/`, siehe [Installation](#installation)).
- Jeder potenziell langsame Aufruf (Firewall-Backend, `fail2ban-client`, Festplatte), der von einem Textual-Bildschirm ausgelöst wird, läuft im Hintergrund (Thread), nie im Hauptthread der Oberfläche — ein Dashboard oder Formular bleibt während des Vorgangs reaktionsfähig, statt die ganze Anwendung einzufrieren.

### Datenstruktur

Omega-Fire verwendet SQLite über die Standardbibliothek `sqlite3`, ohne externes ORM. Die wichtigsten Datensätze betreffen Sperren, Regeln, Audit-Ereignisse und Snapshots.

Die Migrationen sind versioniert und werden beim Start automatisch angewendet.

---

## Voraussetzungen

### System

- Linux, vorrangig Arch Linux und kompatible Distributionen.
- Python 3.10 oder höher.
- Root-Rechte über `sudo` verfügbar.
- Ein Dienstmanager: systemd, runit oder OpenRC.
- Mindestens ein Firewall-Backend: nftables oder iptables.
- Ein Terminal mit mindestens 80x24 (siehe [Themes und Terminals](#themes-und-terminals) für die Details der Darstellungsprofile je nach verfügbarer Größe).

### Python-Abhängigkeiten

Die Produktionsabhängigkeiten sind in `requirements.txt` definiert:

- `textual` — Standard-TUI-Oberfläche.
- `omega-lib` — Theme, Terminalerkennung und mit der OMEGA-Suite geteilte Verträge (nicht auf PyPI veröffentlicht, siehe [Architektur](#architektur) und [Installation](#installation)).
- `rich` — Darstellung der `--legacy-cli`-Oberfläche und einiger Berichte.
- `psutil` — Systeminformationen (CPU, Speicher, Netzwerk, Prozesse) für Dashboard und Diagnose.
- `jinja2` — Erzeugung der HTML-Exporte.
- `python-dotenv` — Umgebungsvariablen.
- `pyte` — virtueller Terminalemulator für die Einbettung von `lnav` (Menüs 5.9/8.6).

Die Qualitätswerkzeuge (`pytest`, `black`, `flake8`, `mypy`) sind als Kommentar in `requirements.txt` aufgeführt: Entkommentieren Sie sie oder installieren Sie sie separat, wenn Sie zum Projekt beitragen (siehe [Tests und Qualität](#tests-und-qualität)).

### Empfohlene optionale Werkzeuge

Die Anwendung arbeitet im eingeschränkten Modus, wenn diese Werkzeuge fehlen:

- `fail2ban` — automatisierte Sperren.
- `conntrack` oder `conntrack-tools` — aktive Verbindungen und Netzwerkstatistiken.
- `lnav` — erweiterte Log-Analyse über mehrere Dateien.

Unter Arch Linux und Derivaten:

```bash
sudo pacman -S fail2ban conntrack-tools lnav
```

---

## Installation

Das offizielle Archiv wird im Format `.tar.gz` bereitgestellt. Prüfen Sie seine Integrität vor der Installation:

```bash
sha256sum omega-fire.tar.gz
```

> ⚠️ **Diese drei Methoden dienen einer Erstinstallation.** Wenn `~/omega-fire` bereits existiert (Aktualisierung einer früheren Version), verwenden Sie den Abschnitt [Aktualisierung](#aktualisierung) unten — führen Sie diese Befehle nie aus einem bestehenden `omega-fire`-Ordner heraus erneut aus: `tar` würde versuchen, ein verschachteltes `omega-fire/omega-fire/` anzulegen, und mit Berechtigungsfehlern scheitern, wenn dieser Ordner root gehört (häufig, wenn eine frühere Extraktion versehentlich mit `sudo tar` erfolgt ist).

### Methode 1 — Installationsskript

```bash
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Sie scheinen sich bereits in einem omega-fire-Ordner zu befinden — siehe den Abschnitt Aktualisierung im README." >&2; exit 1; }
[ -d omega-fire ] && echo "ℹ️ Hier bereits entpackt, Schritt übersprungen." || tar -xzf omega-fire.tar.gz
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire existiert bereits, Verschieben übersprungen." || mv omega-fire ~/
cd ~/omega-fire/
chmod +x install.sh
./install.sh
```

Start:

```bash
./omega-fire.sh
```

Wenn der Alias installiert wurde, öffnen Sie ein neues Terminal und verwenden Sie:

```bash
fire
```

### Methode 2 — robuste Komplettinstallation

Dieser Befehl kann erneut ausgeführt werden: Bereits erledigte Schritte werden übersprungen.

```bash
([ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Sie scheinen sich bereits in einem omega-fire-Ordner zu befinden — siehe den Abschnitt Aktualisierung im README." >&2; exit 1; }; [ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire existiert bereits, Entpacken übersprungen." || (tar -xzf omega-fire.tar.gz && mv omega-fire ~/)) && cd ~/omega-fire/ && ([ -d .venv ] && echo "ℹ️ .venv existiert bereits, Schritt übersprungen." || python3 -m venv .venv) && source .venv/bin/activate && ([ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib || true) && pip install -r requirements.txt && chmod +x omega-fire.sh && mkdir -p var && (getent group omega-fire >/dev/null 2>&1 && echo "ℹ️ Gruppe omega-fire bereits vorhanden." || sudo groupadd omega-fire) && (groups "$USER" 2>/dev/null | grep -qw omega-fire && echo "ℹ️ $USER ist bereits Mitglied der Gruppe omega-fire." || sudo usermod -aG omega-fire "$USER") && sudo chgrp -R omega-fire var && sudo chmod -R 2775 var && echo "✅ Omega-Fire installiert. Starten Sie ./omega-fire.sh."
```

### Methode 3 — ausführliche Installation

```bash
# 0. Prüfen, dass nicht aus einem bestehenden omega-fire heraus gestartet wird
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Sie scheinen sich bereits in einem omega-fire-Ordner zu befinden — siehe den Abschnitt Aktualisierung im README." >&2; exit 1; }

# 1. Entpacken
[ -d omega-fire ] && echo "ℹ️ Hier bereits entpackt, Schritt übersprungen." || tar -xzf omega-fire.tar.gz

# 2. In das Home-Verzeichnis verschieben
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire existiert bereits, Verschieben übersprungen." || mv omega-fire ~/

# 3. In das Projekt wechseln
cd ~/omega-fire/

# 4. Die virtuelle Umgebung erstellen
[ -d .venv ] && echo "ℹ️ .venv existiert bereits, Erstellung übersprungen." || python3 -m venv .venv

# 5. Die Abhängigkeiten installieren (enthaltene omega-lib, falls vorhanden, vor requirements.txt)
source .venv/bin/activate
[ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib
pip install -r requirements.txt

# 6. Den Starter ausführbar machen
chmod +x omega-fire.sh

# 7. var/ für root und den aktuellen Benutzer vorbereiten
mkdir -p var
getent group omega-fire >/dev/null 2>&1 || sudo groupadd omega-fire
groups "$USER" 2>/dev/null | grep -qw omega-fire || sudo usermod -aG omega-fire "$USER"
sudo chgrp -R omega-fire var
sudo chmod -R 2775 var

# 8. Starten
./omega-fire.sh
```

`vendor/omega-lib/` ist nur im offiziellen Archiv enthalten (`build-release.sh` fügt sie automatisch hinzu, da omega-lib nicht auf PyPI veröffentlicht ist); installieren Sie sie in einem Entwicklungsklon separat aus ihrem eigenen Repository (`pip install -e pfad/zu/omega-lib`).

Die eigene Gruppe und das `setgid`-Bit erlauben es root und dem Benutzer, die in `var/` erzeugten Dateien zu teilen, ohne die Berechtigungen für das gesamte System zu öffnen. Eine neue Anmeldung oder `newgrp omega-fire` kann nötig sein, um die Gruppenzugehörigkeit sofort zu nutzen.

### Aktualisierung

Wenn `~/omega-fire` bereits existiert (frühere Installation), **führen Sie die Installationsbefehle nie aus diesem Ordner heraus erneut aus**: `tar` würde versuchen, ein verschachteltes `omega-fire/omega-fire/` anzulegen, und scheitern, meist mit einer Kaskade von Fehlern « Keine Berechtigung », wenn der Ordner `root` gehört (häufig, wenn eine frühere Extraktion versehentlich mit `sudo tar` erfolgt ist).

Empfohlenes Vorgehen, aus einem beliebigen Ordner **außer `~/omega-fire`** (typischerweise `~` selbst):

```bash
# 1. Zustand und Eigentümer der bestehenden Installation prüfen
ls -ld ~/omega-fire

# 2. Die alte Installation beiseitelegen, statt sie zu überschreiben
sudo mv ~/omega-fire ~/omega-fire.old-$(date +%Y%m%d)

# 3. Das neue Archiv direkt ins Home-Verzeichnis entpacken
tar -xzf omega-fire.tar.gz -C ~/

# 4. Neu installieren (erstellt das venv neu, installiert die Abhängigkeiten neu, setzt die Berechtigungen von var/ neu)
cd ~/omega-fire
chmod +x install.sh
./install.sh

# 5. Starten
./omega-fire.sh
```

Schritt 4 (`./install.sh`) erkennt diesen Fall automatisch (Datenbank `var/db/` hier nicht vorhanden, Ordner `~/omega-fire.old-JJJJMMTT` direkt daneben gefunden) und **übernimmt selbst** `config/omega-fire.conf`, die Datenbank, die Blocklist, die Sicherungen, die Exporte und die Screenshots aus der alten Installation — ohne Rückfrage, ohne manuellen Schritt. Über die Punkte 1 bis 5 oben hinaus ist nichts weiter zu tun, ganz gleich, was Ihre frühere Installation enthielt.

Liegen mehrere Ordner daneben, die wie eine alte Installation aussehen (mehrdeutig), rät `install.sh` nichts: Es zeigt deren Pfade an und fordert Sie auf, `sudo ./migrate-state.sh <ordner>` selbst auszuführen, sobald die richtige Quelle feststeht.

Sobald die neue Installation bestätigt ist, kann der alte Ordner `~/omega-fire.old-JJJJMMTT` gelöscht werden (`sudo rm -rf ~/omega-fire.old-JJJJMMTT`).

### Bash- oder Zsh-Alias

```bash
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.bashrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.bashrc
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.zshrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.zshrc
```

Laden Sie danach die Shell neu:

```bash
source ~/.bashrc 2>/dev/null || source ~/.zshrc
```

### Nerd-Fonts-Icons und -Symbole

Wenn die Icons nicht verfügbar sind, installieren Sie die Nerd-Fonts-Symbole:

```bash
mkdir -p ~/.local/share/fonts
curl -fLo /tmp/NerdFontsSymbolsOnly.zip \
  https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip
unzip -o /tmp/NerdFontsSymbolsOnly.zip -d ~/.local/share/fonts
fc-cache -fv
```

---

## Verwendung

### Start

```bash
cd ~/omega-fire
./omega-fire.sh

# oder einfach, wenn der Alias erstellt wurde:
fire
```

Der Starter:

1. Prüft die Root-Rechte und startet bei Bedarf über `sudo` neu.
2. Erkennt `.venv`, `venv` oder das System-Python.
3. Setzt `PYTHONPATH` auf `src/`.
4. Startet `python -m omega_fire` — standardmäßig die **Textual**-Oberfläche.

Um stattdessen die alte Rich-Oberfläche (sequenzielle Zifferneingabe) zu starten:

```bash
./omega-fire.sh --legacy-cli
```

### Allgemeiner Ablauf

1. Startbildschirm (Splash), danach eine Warnung, falls das Terminal zu klein ist.
2. Erkennung der Systemfähigkeiten (eigener, nicht blockierender Bildschirm).
3. Hauptmenü: 8 thematische Bereiche (1-8) plus die Einstellungen (9).
4. Auswahl eines Bereichs, dann einer Aktion — jede Aktion öffnet ein Formular, dessen Pflichtfelder alle vor dem Fortfahren validiert werden.
5. Ausdrückliche Bestätigung vor jedem sensiblen oder zerstörerischen Vorgang (Flush, Bereinigung, Wiederherstellung...).
6. Ausführung langsamer Vorgänge im Hintergrund (die Oberfläche bleibt während des Wartens nutzbar), danach Rückkehr ins Menü mit einer Zusammenfassung des Ergebnisses.

### Navigation

- Pfeiltasten auf/ab: den Cursor in einer Liste oder einem Menü bewegen.
- Tab / Umschalt+Tab: zwischen den Feldern eines Formulars wechseln.
- Eingabe: auswählen oder bestätigen.
- Auf eine Tabellenzeile klicken: sie auswählen und die betreffenden Felder vorausfüllen (anzuheftende Quelle, Ziel-Jail usw.).
- `Esc`: zum vorherigen Bildschirm zurückkehren (fragt auf dem Startbildschirm nach einer Bestätigung zum Beenden).
- `a`: kontextbezogene Hilfe — beschreibt die laufende Aktion oder alle Aktionen des aktuellen Bereichs, wenn noch kein Aktionsbildschirm geöffnet ist.
- `t`: zum nächsten Theme wechseln, ohne Bestätigung.
- `r`: Größe und Familie des Terminals neu erkennen.
- `s`: die Einstellungen öffnen (Theme, Darstellungsprofil).
- `q` / `Ctrl+Q`: beenden, mit Bestätigung.

#### Besonderheiten des lnav-Bildschirms (5.9 / 8.6)

`lnav` ist in ein Pseudo-Terminal eingebettet, mit dauerhaftem Omega-Fire-Header/-Footer um seine eigene Ansicht, um jede Kollision zwischen seinen nativen Kürzeln und denen von Omega-Fire zu vermeiden:

- Pfeiltasten ↑↓: in den Logs navigieren (natives `lnav`-Kürzel, unverändert weitergereicht).
- Pfeiltasten ←→: auf langen Zeilen horizontal scrollen (natives `lnav`-Kürzel).
- `g` / `G`: zum Anfang / zum Ende springen (natives `lnav`-Kürzel).
- `Ctrl+C`: die aktuelle Zeile markieren und in die Systemzwischenablage kopieren (ersetzt den nativen Kopierbefehl von `lnav`, der auf manchen Systemen hängen bleiben kann).
- `t` klein: nächstes Theme, nur für diese Ansicht (das große `T` bleibt das native `lnav`-Kürzel zur Anzeige der Zeit zwischen den Zeilen).
- `Ctrl+Q`: zu Omega-Fire zurückkehren (schließt `lnav` sauber, ohne die Anwendung zu beenden).

---

## Themes und Terminals

Zehn `omega-*`-Themes werden mit dem Rest der OMEGA-Suite geteilt:

```text
omega-base       omega-dark       omega-light
omega-neon       omega-burn       omega-pink
omega-hack       omega-contrast   omega-mono
omega-minimal
```

- Wechseln Sie mit `t` zwischen den Themes oder wählen Sie eines direkt in den Einstellungen (`s`).
- Das gewählte Theme wird gespeichert und beim nächsten Start wiederhergestellt.
- Omega-Fire passt die visuelle Komplexität (Rahmen, Splash, Informationsdichte) über ein **Darstellungsprofil** automatisch an das erkannte Terminal an: Vollständig, Standard, Reduziert oder Mono (nur ASCII). Das Profil kann in den Einstellungen manuell überschrieben werden.

| Mindestgröße | Profil | Typische Terminals |
|---|---|---|
| 120×32 oder mehr | Vollständig | Ghostty, Alacritty, WezTerm, Kitty |
| 100×28 oder mehr | Standard | Konsole, GNOME Terminal, Terminator, xfce4-terminal |
| 80×24 oder mehr | Reduziert | urxvt, xterm, modernes SSH |
| unter 80×24 | Mono (nur ASCII) | Linux-TTY, altes SSH |

Unter 80×24 wird der Start verweigert (Mindestgröße erforderlich); vergrößern Sie das Terminal und starten Sie neu, oder drücken Sie nach dem Vergrößern `r`, falls sich die Anzeige nicht automatisch aktualisiert hat.

---

## Konfiguration

Die spezifische Konfiguration kann angepasst werden in:

```text
omega-fire/config/omega-fire.conf
```

Sie kann insbesondere festlegen:

- Pfade der Logs;
- Server und Quellen für das Monitoring;
- verfügbare Backends oder eigene Pfade;
- zu analysierende Umgebungen;
- an eine bestimmte Installation angepasste Parameter.

Die Konfiguration wird beim Neustart oder bei einem manuellen Neuscan (Menü 1.3 oder 7.4) neu eingelesen.

Diese Datei ist vollständig optional (die Anwendung funktioniert ohne sie normal und greift auf Umgebungsvariablen zurück) und **vom verteilbaren Archiv ausgeschlossen** — eine Aktualisierung überschreibt sie nie stillschweigend, und `install.sh` übernimmt sie gegebenenfalls selbst automatisch aus einer alten Installation (siehe « Aktualisierung » weiter oben).

### Interne Pfade und Systempfade

Standardmäßig arbeitet Omega-Fire in seinem eigenen Ordner:

```text
var/exports/       # projektinterner Ordner
/var/exports/      # absoluter Systempfad
```

Der führende `/` ist also bedeutsam. Importe und Exporte in das System müssen vom Benutzer ausdrücklich angefordert werden.

---

## Backends und Kompatibilität

Omega-Fire erkennt die Komponenten und aktiviert nur die nutzbaren Funktionen.

| Komponente | Rolle | Status |
|---|---|---|
| nftables | Moderne IPv4/IPv6-Firewall | Empfohlen |
| iptables | IPv4-Firewall | Kompatibel |
| ip6tables | IPv6-Firewall mit iptables | Kompatibel, falls verfügbar |
| Fail2Ban | Jails und automatisierte Sperren | Optional |
| conntrack | Aktive Verbindungen | Optional |
| lnav | Erweiterte Log-Analyse | Optional |
| systemd, runit, OpenRC | Dienstverwaltung | Automatische Erkennung |
| Docker, VNC, Server | Erkannte Anwendungen und Dienste | Je nach Installation |

### IPv4 und IPv6

Beide Adressfamilien werden von den kompatiblen Backends unterstützt:

- nftables: IPv4 und IPv6 im Dual Stack;
- iptables/ip6tables: je nach verfügbaren Binärdateien;
- Fail2Ban: je nach Konfiguration des Jails und des Systems.

Lange, komprimierte, lokale, gemischte IPv6-Formate, solche mit Nullen und in CIDR-Notation werden von den betreffenden Komponenten verarbeitet.

---

## Persistenz, Logs und Exporte

### Persistenz

- SQLite über `sqlite3`.
- Tabellen für Sperren, Regeln, Audits und Snapshots.
- Versionierte, automatisch angewendete Migrationen.
- Archive des vollständigen Zustands im Format `.tar.gz`.
- Angeheftete Einträge (bevorzugte Log-Quellen) und jüngster Verlauf in JSON gespeichert (`var/runtime/`), überstehen einen Neustart.

### Logs

- Textuelles Anwendungslog: `var/logs/app.log`.
- Strukturiertes JSON-Auditlog, unter anderem mit `event_type`, `actor`, `action`, `result` und `details`.

### Exporte

Die Exporte sind als JSON, TXT und HTML verfügbar, mit mehreren CSS-Themes für die HTML-Berichte.

---

## Sicherheit

Omega-Fire greift auf kritische Systemkomponenten zu und muss mit Vorsicht verwendet werden.

- Der Start erfordert Root-Rechte über `sudo`.
- Flush, allgemeine Bereinigung und die Anwendung einer Richtlinie können zerstörerisch sein.
- Eine vordefinierte Richtlinie löst vor der Änderung eine automatische Sicherung aus.
- Erstellen Sie vor jeder größeren Änderung eine manuelle Sicherung.
- Prüfen Sie nach jedem Vorgang den tatsächlichen Zustand von Firewall, Jails und Verbindungen.
- Testen Sie zuerst auf einem Wegwerf-Rechner oder -Ziel.
- Verwenden Sie für IPv4-Tests die Dokumentationsnetze aus RFC 5737: `192.0.2.0/24`, `198.51.100.0/24` und `203.0.113.0/24`.
- Prüfen Sie Exporte und Snapshots, bevor Sie sie auf einem Produktionsrechner wiederherstellen.
- Gewähren Sie dem Ordner `var/` keine weitergehenden Berechtigungen als nötig.

---

## Tests und Qualität

Das Projekt umfasst eine historische Suite von 152 Unit-Tests, geschrieben vor der Migration zu Textual: Sie deckt die Fachdomäne, die Orchestrierung (`application/`), die Infrastruktur und die Rich-Oberfläche (`interfaces/cli/`) ab, **deckt aber `interfaces/tui/` noch nicht ab** (die Standard-Textual-Oberfläche). Dieses Archiv enthält den Ordner `tests/` nicht: Holen Sie ihn bei Bedarf aus Ihrem Entwicklungs-Repository.

```bash
source .venv/bin/activate
python -m unittest discover tests/unit -v
```

Da die Schichtenarchitektur die Fachdomäne strikt von der Darstellung trennt (`domain/`, `application/`, `ports/` als `Protocol`, siehe [Architektur](#architektur)), bleibt diese Suite trotz der Migration unverändert gültig: Nur die neuere Textual-Oberfläche hat noch keine eigene Testabdeckung.

Wenn Sie zum Projekt beitragen, installieren Sie die in `requirements.txt` (als Kommentar) angegebenen Qualitätswerkzeuge:

```bash
pip install pytest pytest-cov black flake8 mypy
```

Nach der Installation verfügbare Werkzeuge:

```bash
black .
flake8 .
mypy src/
pytest --cov
```

---

## Projektstatus

### Einsatzbereite Punkte

- Einheitliche Textual-TUI für die wichtigsten Netzwerksicherheitsmechanismen, validierte Formulare, Themes und kontextbezogene Hilfe, geteilt mit der OMEGA-Suite.
- Historische Rich-Oberfläche als Ausweichlösung beibehalten (`--legacy-cli`).
- Automatische Erkennung der Fähigkeiten.
- Verwaltung der verfügbaren Backends.
- IPv4/IPv6-Unterstützung je nach vorhandenen Werkzeugen.
- Anwendungsprotokollierung und Audit.
- Sicherung und Wiederherstellung.
- JSON-, TXT- und HTML-Exporte.
- Dashboard und Statistiken, im Hintergrund aktualisiert, ohne die Oberfläche zu blockieren.
- Dokumentierte Schichtenarchitektur.

### Bekannte Einschränkungen

- Die Testsuite (152) deckt die nach ihr geschriebene Textual-Oberfläche (`interfaces/tui/`) noch nicht ab (siehe [Tests und Qualität](#tests-und-qualität)).
- Der Mechanismus `ExecutionPlan`/`PipelineStep` ist im Projekt teilweise noch vorhanden.
- Die genaue Verfügbarkeit der Funktionen hängt von den Binärdateien, Diensten, Berechtigungen und Konfigurationen des Host-Rechners ab.
- Die historische Rich-Oberfläche (`--legacy-cli`) ist nicht mehr der Schwerpunkt der aktiven Entwicklung; sie bleibt erhalten, bis die Textual-Oberfläche unter realen Bedingungen vollständig zuverlässig ist.

---

## Deinstallation

Wenn die Daten im Projektordner geblieben sind:

```bash
sudo rm -rf ~/omega-fire
```

Löschen Sie manuell die anderswo exportierten Dateien, etwaige in `~/.bashrc` oder `~/.zshrc` hinzugefügte `fire`-Aliase sowie die eigene Gruppe, wenn sie nicht mehr verwendet wird:

```bash
sudo groupdel omega-fire
```

Führen Sie diesen letzten Befehl nur aus, wenn keine andere Datei und kein anderer Dienst von dieser Gruppe abhängt.

---

## Lizenz

Omega-Fire wird unter der **MIT**-Lizenz verteilt. Den vollständigen Text finden Sie in der Datei [`LICENSE`](../../../LICENSE).

---

> **Omega-Fire — Beobachten, steuern, prüfen, absichern.**
>
> Eine einheitliche TUI-Oberfläche für nftables, iptables, ip6tables, Fail2Ban, die Logs und das Netzwerk-Monitoring.
