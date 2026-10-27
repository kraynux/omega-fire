<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->

<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-fire.png" alt="Omega-Fire" width="384">
</div>

# 󰦝 OMEGA-FIRE

**Geïntegreerde beheerpost voor netwerkbeveiliging**

> Ontwikkeld door **kraynux** voor **Omega-server** 
[https://kraynux.snake-mackarel.ts.net](https://kraynux.snake-mackarel.ts.net)

Officiële pagina: [OMEGA-FIRE](https://kraynux.snake-mackarel.ts.net/omega-fire/) &nbsp; Voorbeeld: [Schermafbeeldingen](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/)  

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)
[![Interface](https://img.shields.io/badge/Interface-Textual%20TUI-cyan.svg)](https://github.com/Textualize/textual)

**Talen:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

**Omega-Fire** is een Python-TUI-toepassing (Terminal User Interface) gebouwd met [Textual](https://github.com/Textualize/textual). Ze biedt vanuit een terminal één enkele interface om Linux-firewalls, Fail2Ban, verbannen adressen, netwerkregels, logs en systeemstatistieken te beheren.

De Textual-interface is de standaardwerkwijze en navigeert via menu's, gevalideerde formulieren (alle verplichte velden worden gecontroleerd voordat je verdergaat) en eigen schermen, met thema's, contextuele hulp en sneltoetsen die gedeeld worden met de rest van de OMEGA-suite (omega-check, omega-deep, omega-stress...). De oude [Rich](https://github.com/Textualize/rich)-interface, sequentieel en gestuurd door het invoeren van nummers, blijft beschikbaar via `--legacy-cli` (zie [Starten](#starten)). 
Voorbeeld: [Schermafbeeldingen](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/index-2.html)

Het project volgt de principes van de **Clean Architecture**, met een duidelijke scheiding tussen bedrijfsdomein, orkestratie, infrastructuur en gebruikersinterface.

## Inhoud

- [Presentatie](#presentatie)
- [Functies](#functies)
- [Architectuur](#architectuur)
- [Vereisten](#vereisten)
- [Installatie](#installatie)
- [Gebruik](#gebruik)
- [Configuratie](#configuratie)
- [Backends en compatibiliteit](#backends-en-compatibiliteit)
- [Persistentie, logs en exports](#persistentie-logs-en-exports)
- [Beveiliging](#beveiliging)
- [Tests en kwaliteit](#tests-en-kwaliteit)
- [Projectstatus](#projectstatus)
- [Verwijderen](#verwijderen)
- [Licentie](#licentie)

---

## Presentatie

Omega-Fire fungeert als een **lokale bedieningspost** voor netwerkbeveiliging. Het detecteert automatisch de componenten die op de machine aanwezig zijn en past de menu's aan de werkelijk beschikbare mogelijkheden aan.

### Doelstellingen

- nftables, iptables, ip6tables en Fail2Ban samenbrengen in één samenhangende interface.
- Het observeren van en ingrijpen op verbindingen, verbanningen en systeemgebeurtenissen vergemakkelijken.
- Exports, back-ups, audits en de geschiedenis van bewerkingen centraliseren.
- Een testbare en uitbreidbare architectuur behouden.
- In beperkte modus werken wanneer een optionele component ontbreekt.

### Wat Omega-Fire doet

- Detecteert de beschikbare backends, diensten, kernel en hulpmiddelen.
- Beheert nftables, iptables en ip6tables wanneer deze componenten aanwezig zijn.
- Beheert verbannen IP's, afzonderlijk of in batch, met import, export, synchronisatie en flush.
- Maakt, toont en verwijdert geavanceerde regels.
- Past vooraf gedefinieerde beleidsregels toe met een automatische back-up vooraf.
- Beheert de Fail2Ban-jails en hun verbanningen.
- Analyseert logs live of in de vorm van statistieken.
- Biedt bewaking in de vorm van monitoring.
- Gebruikt conntrack om actieve verbindingen te tonen wanneer het beschikbaar is.
- Maakt JSON-, TXT- en HTML-exports.
- Maakt back-ups van de volledige toestand en herstelt die in `.tar.gz`-archieven.
- Registreert bewerkingen in een applicatielog en een gestructureerde JSON-audit.
- Bewaakt de gedetecteerde diensten en toepassingen: systemd, runit, OpenRC, Docker, servers, VNC enz.

### Wat het project niet doet

- Het vervangt nftables, iptables of Fail2Ban niet.
- Het is geen zelfstandige firewall die onafhankelijk is van het systeem.
- Het biedt geen authenticatie voor meerdere gebruikers.
- Het stelt bij normaal gebruik geen netwerk-API beschikbaar.
- Het is geen webdashboard.
- Het beschermt een externe machine niet rechtstreeks vanaf een andere machine.
- Standaard installeert het geen enkel bestand buiten zijn eigen map.
- Het garandeert niet dat alle backends op alle distributies beschikbaar zijn.

---

## Functies

### 1. Mogelijkheden en diagnose

- Weergave van het register van gedetecteerde mogelijkheden.
- Gedetailleerde weergave van een mogelijkheid op basis van haar identificatie.
- Handmatige herscan van het systeem na installatie van een component.
- Weergave van recente diagnoses.
- Weergave en doorzoeken van het applicatielog.
- Export van toestand en diagnoses als JSON, TXT of HTML.

### 2. Geïntegreerd IP-beheer

De geïntegreerde blacklist maakt het mogelijk met nftables en iptables te werken vanuit hetzelfde scherm.

- Verbannen van een IP of een lijst van IP's.
- Opheffen van een ban, afzonderlijk of in batch.
- Directe invoer of import uit een bestand.
- Lijst per backend of geïntegreerde weergave.
- Synchronisatie tussen de backends NFTables/IPTables.
- Export en herimport van de lijsten.
- Volledige opschoning van één of meer backends.
- Ondersteuning voor IPv4 en IPv6.
- Beheer van de blocklist-bestanden (`var/blocklist/`) en hun vastgezette items rechtstreeks vanuit het eigen scherm.

### 3. Beheer van regels en beleid

- Stapsgewijze assistent om een geavanceerde regel te maken.
- Lijst van systeemregels en van regels die door Omega-Fire zijn gemaakt.
- Verwijderen van een regel via selectie.
- Automatische opschoning van inactieve regels in de referentiedatabase.
- Toepassen van vooraf gedefinieerd beleid.
- Automatische back-up vóór het toepassen van een beleid.
- Aanpassen, opslaan en herstellen van een beleid.
- Aanduiding van het actieve beleid in het statusmenu en het dashboard.
- Aanduiding van gewijzigde profielen in de vorm `Profiel + CUSTOM`.
- Tabelbeheer (menu 3.5): alleen-lezen diagnose per backend (aanwezigheid van de tabel, input/output/forward-beleid, aantal regels) met detectie van verschillen tussen backends.
- Initialisatie van een nftables-tabel bij eerste gebruik, zonder ooit een reeds geconfigureerde chain te overschrijven.
- Terugzetten van het chainbeleid naar ACCEPT op een backend, om een verweesd restrictief beleid van een eerder profiel te corrigeren.
- Gericht leegmaken van een backend of gesynchroniseerd leegmaken van alle gedetecteerde backends in één handeling.
- Volledig verwijderen van een nftables-tabel (geavanceerde actie, naast losse regels).

### 4. Fail2Ban-beheer

- Gedetailleerde status van de jails en hun parameters.
- Aantal verbannen IP's en rate-limit-informatie.
- Zoeken naar een IP in de jails.
- Ban en unban, afzonderlijk of meervoudig.
- Overdracht van IP's tussen jails, backends en bestanden.
- Begeleid aanmaken van een eigen jail.
- Vooraf gedefinieerde jail-sjablonen.
- Verwijderen van een jail.
- Leegmaken van een jail of algemene opschoning.
- Export als JSON, TXT of HTML.
- Controle en audit van de configuratie.
- Dienstbeheer: status, starten, stoppen, herstarten, inschakelen en uitschakelen bij het opstarten.

### 5. Logs en onderhoud

- Live Tail met Omega-Fire-dashboard.
- Weergave van meerdere bestanden met vastgezette items (favoriete bronnen, bewaard tussen twee starts).
- Integratie van `lnav`: selectie van één of meer bestanden (nummers of handmatige paden, gescheiden door komma's), automatische samenvoeging tot één chronologische weergave, ingebed in een Omega-Fire-header/footer (zie [Navigatie](#navigatie)).
- Analyse van de meest voorkomende IP's met Top N.
- Gericht verwijderen van een IP uit LOG- of TXT-bestanden.
- Rotatie en onmiddellijke of geautomatiseerde back-ups.
- Herstellen van een back-up.
- Opschonen op basis van ouderdom, quotum, type of handmatige selectie.
- Geavanceerde opschoning per map of omgeving.
- Statistieken over 24 uur, 7 dagen of 30 dagen.
- Analyse van gebeurtenissen, bewegingen, quota en IP's in de jails.

### 6. Exports en rapporten

Beschikbare formaten:

- **JSON**: gestructureerde en herbruikbare gegevens.
- **TXT**: ruw formaat of aangepast voor injectie.
- **HTML**: leesbaar en visueel rapport.

Beschikbare rapporten:

- Volledige blacklist.
- Gestructureerde ruleset.
- Regels geselecteerd op herkomst: systeem, Omega-Fire of actief.
- Volledig auditrapport.
- Fail2Ban-statistieken.
- Systeemtoestand en -diagnose.
- Statistische rapporten over 7 of 30 dagen.

HTML-thema's:

- `omega-base` — nachtblauw en cyaan, standaardthema.
- `omega-burn` — roodoranje gloed.
- `omega-neon` — cyberpunk in cyaan en magenta.
- `light-basic` — licht en sober.
- `light-alt` — crèmekleurig papier en bosgroen.

### 7. Systeem en persistentie

- Back-up van de volledige toestand: regels, nftables-bans, iptables-bans en Fail2Ban.
- Aanmaken van `.tar.gz`-archieven met tijdstempel.
- Lijst en herstel van snapshots.
- Geschiedenis van de acties.
- Filteren en opschonen van de geschiedenis.
- Herladen van de configuratie en herscan zonder herstart.

### 8. Monitoring en statistieken

- Realtime dashboard met periodieke vernieuwing (elke 2 seconden), zonder de interface tijdens het verzamelen te blokkeren.
- Weergave van het actieve beleid.
- Actieve verbindingen via conntrack.
- Verkeer, gebeurtenissen, statistieken en serverlogs.
- Geconsolideerde rapporten over 7 en 30 dagen.
- HTML-export van snapshots en rapporten.

### 9. Instellingen

- Keuze van het actieve thema uit de tien `omega-*`-thema's die met de rest van de suite worden gedeeld (zie [Thema's en terminals](#themas-en-terminals)), bewaard tussen twee starts.
- Handmatig overschrijven van het weergaveprofiel (automatisch, volledig, standaard, beperkt of alleen mono), toegepast bij de volgende start.
- Bereikbaar via het hoofdmenu (`9. RÉGLAGES`) of rechtstreeks met de toets `s`.

---

## Architectuur

```text
src/omega_fire/
├── app/              Bootstrap en container voor dependency injection
├── core/             Mogelijkheden, enumeraties en uitzonderingen
├── domain/           Pure bedrijfslogica: regels, IP's, jails, logs
├── application/      Orkestratie: commands en queries
├── infrastructure/   Backends, opslag, exports, logs en systeemsondes
├── ports/            Protocol/ABC-contracten
├── interfaces/       interfaces/tui/ (Textual, standaard) + interfaces/cli/ (Rich, --legacy-cli)
├── plugins/          Ingebouwde uitbreidingen: nftables, iptables, Fail2Ban, conntrack
└── shared/           Parsing, netwerk, opmaak en transversale hulpmiddelen
```

### Ontwerpprincipes

- `domain/` bevat geen I/O en geen afhankelijkheid van de infrastructuur.
- `application/` orkestreert de use cases via het domein en de ports — de Textual-schermen en de acties van de Rich-interface roepen dezelfde commands/queries aan, en de bedrijfslogica hangt van geen van beide interfaces af.
- `infrastructure/` is de enige laag die `nft`, `iptables`, `fail2ban-client` en de andere externe hulpmiddelen mag aanroepen (subprocess, pty, bestanden).
- `interfaces/` mag `subprocess` niet rechtstreeks aanroepen.
- `ports/` definieert de contracten die de adapters verwachten.
- `core/` levert het register van mogelijkheden dat de verschillende lagen gebruiken.
- Met de plugins kunnen backends worden toegevoegd of verder ontwikkeld zonder het bedrijfsdomein te wijzigen.
- De Textual-interface (`interfaces/tui/`) steunt op [`omega-lib`](https://github.com/) (door de hele OMEGA-suite gedeelde afhankelijkheid: thema met 9 tokens, terminaldetectie, gemeenschappelijke port-contracten), niet gepubliceerd op PyPI — opgenomen in het verspreidbare archief (`vendor/omega-lib/`, zie [Installatie](#installatie)).
- Elke mogelijk trage aanroep (firewall-backend, `fail2ban-client`, schijf) die vanuit een Textual-scherm wordt gestart, draait op de achtergrond (thread), nooit op de hoofdthread van de interface — een dashboard of formulier blijft tijdens de bewerking reageren in plaats van de hele toepassing te laten bevriezen.

### Gegevensstructuur

Omega-Fire gebruikt SQLite via de standaardbibliotheek `sqlite3`, zonder externe ORM. De belangrijkste gegevenssets betreffen bans, regels, auditgebeurtenissen en snapshots.

De migraties zijn geversioneerd en worden bij het opstarten automatisch toegepast.

---

## Vereisten

### Systeem

- Linux, bij voorkeur Arch Linux en compatibele distributies.
- Python 3.10 of hoger.
- Rootrechten beschikbaar via `sudo`.
- Een dienstbeheerder: systemd, runit of OpenRC.
- Ten minste één firewall-backend: nftables of iptables.
- Een terminal van minstens 80x24 (zie [Thema's en terminals](#themas-en-terminals) voor de details van de weergaveprofielen afhankelijk van de beschikbare grootte).

### Python-afhankelijkheden

De productieafhankelijkheden zijn gedefinieerd in `requirements.txt`:

- `textual` — standaard-TUI-interface.
- `omega-lib` — thema, terminaldetectie en met de OMEGA-suite gedeelde contracten (niet gepubliceerd op PyPI, zie [Architectuur](#architectuur) en [Installatie](#installatie)).
- `rich` — weergave van de `--legacy-cli`-interface en van sommige rapporten.
- `psutil` — systeeminformatie (CPU, geheugen, netwerk, processen) voor het dashboard en de diagnose.
- `jinja2` — aanmaak van de HTML-exports.
- `python-dotenv` — omgevingsvariabelen.
- `pyte` — virtuele terminalemulator, voor het inbedden van `lnav` (menu's 5.9/8.6).

De kwaliteitshulpmiddelen (`pytest`, `black`, `flake8`, `mypy`) staan als commentaar in `requirements.txt`: haal het commentaar weg of installeer ze apart als je bijdraagt aan het project (zie [Tests en kwaliteit](#tests-en-kwaliteit)).

### Aanbevolen optionele hulpmiddelen

De toepassing werkt in beperkte modus als deze hulpmiddelen ontbreken:

- `fail2ban` — geautomatiseerd verbannen.
- `conntrack` of `conntrack-tools` — actieve verbindingen en netwerkstatistieken.
- `lnav` — geavanceerde loganalyse over meerdere bestanden.

Op Arch Linux en afgeleiden:

```bash
sudo pacman -S fail2ban conntrack-tools lnav
```

---

## Installatie

Het officiële archief wordt geleverd in `.tar.gz`-formaat. Controleer de integriteit vóór de installatie:

```bash
sha256sum omega-fire.tar.gz
```

> ⚠️ **Deze drie methoden zijn bedoeld voor een eerste installatie.** Als `~/omega-fire` al bestaat (bijwerken van een eerdere versie), gebruik dan de sectie [Bijwerken](#bijwerken) hieronder — voer deze commando's nooit opnieuw uit vanuit een bestaande `omega-fire`-map: `tar` zou proberen een genest `omega-fire/omega-fire/` aan te maken en mislukken met toegangsfouten als die map van root is (vaak het geval als een eerdere extractie per ongeluk met `sudo tar` is gedaan).

### Methode 1 — installatiescript

```bash
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Je lijkt je al in een omega-fire-map te bevinden — zie de sectie Bijwerken in de README." >&2; exit 1; }
[ -d omega-fire ] && echo "ℹ️ Hier al uitgepakt, stap overgeslagen." || tar -xzf omega-fire.tar.gz
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire bestaat al, verplaatsen overgeslagen." || mv omega-fire ~/
cd ~/omega-fire/
chmod +x install.sh
./install.sh
```

Starten:

```bash
./omega-fire.sh
```

Als de alias is geïnstalleerd, open dan een nieuwe terminal en gebruik:

```bash
fire
```

### Methode 2 — robuuste volledige installatie

Dit commando kan opnieuw worden uitgevoerd: het slaat stappen die al zijn uitgevoerd over.

```bash
([ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Je lijkt je al in een omega-fire-map te bevinden — zie de sectie Bijwerken in de README." >&2; exit 1; }; [ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire bestaat al, uitpakken overgeslagen." || (tar -xzf omega-fire.tar.gz && mv omega-fire ~/)) && cd ~/omega-fire/ && ([ -d .venv ] && echo "ℹ️ .venv bestaat al, stap overgeslagen." || python3 -m venv .venv) && source .venv/bin/activate && ([ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib || true) && pip install -r requirements.txt && chmod +x omega-fire.sh && mkdir -p var && (getent group omega-fire >/dev/null 2>&1 && echo "ℹ️ Groep omega-fire bestaat al." || sudo groupadd omega-fire) && (groups "$USER" 2>/dev/null | grep -qw omega-fire && echo "ℹ️ $USER is al lid van de groep omega-fire." || sudo usermod -aG omega-fire "$USER") && sudo chgrp -R omega-fire var && sudo chmod -R 2775 var && echo "✅ Omega-Fire geïnstalleerd. Start ./omega-fire.sh."
```

### Methode 3 — gedetailleerde installatie

```bash
# 0. Controleren dat er niet vanuit een bestaande omega-fire wordt gestart
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Je lijkt je al in een omega-fire-map te bevinden — zie de sectie Bijwerken in de README." >&2; exit 1; }

# 1. Uitpakken
[ -d omega-fire ] && echo "ℹ️ Hier al uitgepakt, stap overgeslagen." || tar -xzf omega-fire.tar.gz

# 2. Naar de homemap verplaatsen
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire bestaat al, verplaatsen overgeslagen." || mv omega-fire ~/

# 3. Het project openen
cd ~/omega-fire/

# 4. De virtuele omgeving aanmaken
[ -d .venv ] && echo "ℹ️ .venv bestaat al, aanmaken overgeslagen." || python3 -m venv .venv

# 5. De afhankelijkheden installeren (meegeleverde omega-lib, indien aanwezig, vóór requirements.txt)
source .venv/bin/activate
[ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib
pip install -r requirements.txt

# 6. De starter uitvoerbaar maken
chmod +x omega-fire.sh

# 7. var/ voorbereiden voor root en de huidige gebruiker
mkdir -p var
getent group omega-fire >/dev/null 2>&1 || sudo groupadd omega-fire
groups "$USER" 2>/dev/null | grep -qw omega-fire || sudo usermod -aG omega-fire "$USER"
sudo chgrp -R omega-fire var
sudo chmod -R 2775 var

# 8. Starten
./omega-fire.sh
```

`vendor/omega-lib/` is alleen aanwezig in het officiële archief (`build-release.sh` voegt het automatisch toe, omdat omega-lib niet op PyPI is gepubliceerd); installeer het in een ontwikkelkloon apart vanuit de eigen repository (`pip install -e pad/naar/omega-lib`).

Met de eigen groep en de `setgid`-bit kunnen root en de gebruiker de in `var/` aangemaakte bestanden delen zonder de rechten voor het hele systeem open te zetten. Opnieuw aanmelden of `newgrp omega-fire` kan nodig zijn om het groepslidmaatschap meteen te benutten.

### Bijwerken

Als `~/omega-fire` al bestaat (eerdere installatie), **voer de installatiecommando's dan nooit opnieuw uit vanuit deze map**: `tar` zou proberen een genest `omega-fire/omega-fire/` aan te maken en mislukken, meestal met een reeks fouten « Toegang geweigerd » als de map van `root` is (vaak het geval als een eerdere extractie per ongeluk met `sudo tar` is gedaan).

Aanbevolen procedure, vanuit elke map **behalve `~/omega-fire`** (meestal `~` zelf):

```bash
# 1. De toestand en de eigenaar van de bestaande installatie controleren
ls -ld ~/omega-fire

# 2. De oude installatie opzijzetten in plaats van haar te overschrijven
sudo mv ~/omega-fire ~/omega-fire.old-$(date +%Y%m%d)

# 3. Het nieuwe archief rechtstreeks in de homemap uitpakken
tar -xzf omega-fire.tar.gz -C ~/

# 4. Opnieuw installeren (maakt de venv opnieuw aan, installeert de afhankelijkheden opnieuw, zet de rechten van var/ opnieuw)
cd ~/omega-fire
chmod +x install.sh
./install.sh

# 5. Starten
./omega-fire.sh
```

Stap 4 (`./install.sh`) detecteert deze situatie automatisch (database `var/db/` hier afwezig, map `~/omega-fire.old-JJJJMMDD` er vlak naast gevonden) en **haalt zelf** `config/omega-fire.conf`, de database, de blocklist, de back-ups, de exports en de schermafbeeldingen uit de oude installatie op — zonder vragen, zonder handmatige stap. Verder hoef je niets te doen dan de punten 1 tot en met 5 hierboven, wat je vorige installatie ook bevatte.

Als er meerdere mappen naast liggen die op een oude installatie lijken (dubbelzinnig), raadt `install.sh` niets: het toont hun paden en vraagt je `sudo ./migrate-state.sh <map>` zelf uit te voeren zodra de juiste bron is vastgesteld.

Zodra de nieuwe installatie is goedgekeurd, kan de oude map `~/omega-fire.old-JJJJMMDD` worden verwijderd (`sudo rm -rf ~/omega-fire.old-JJJJMMDD`).

### Bash- of Zsh-alias

```bash
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.bashrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.bashrc
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.zshrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.zshrc
```

Herlaad daarna de shell:

```bash
source ~/.bashrc 2>/dev/null || source ~/.zshrc
```

### Nerd Fonts-pictogrammen en -symbolen

Als de pictogrammen niet beschikbaar zijn, installeer dan de Nerd Fonts-symbolen:

```bash
mkdir -p ~/.local/share/fonts
curl -fLo /tmp/NerdFontsSymbolsOnly.zip \
  https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip
unzip -o /tmp/NerdFontsSymbolsOnly.zip -d ~/.local/share/fonts
fc-cache -fv
```

---

## Gebruik

### Starten

```bash
cd ~/omega-fire
./omega-fire.sh

# of eenvoudig, als de alias is aangemaakt:
fire
```

De starter:

1. Controleert de rootrechten en start indien nodig opnieuw via `sudo`.
2. Detecteert `.venv`, `venv` of de systeem-Python.
3. Stelt `PYTHONPATH` in op `src/`.
4. Start `python -m omega_fire` — standaard de **Textual**-interface.

Om in plaats daarvan de oude Rich-interface (sequentiële invoer van nummers) te starten:

```bash
./omega-fire.sh --legacy-cli
```

### Algemeen verloop

1. Startscherm (splash), daarna een waarschuwing als de terminal te klein is.
2. Detectie van de systeemmogelijkheden (eigen, niet-blokkerend scherm).
3. Hoofdmenu: 8 thematische secties (1-8) plus de instellingen (9).
4. Selectie van een sectie en daarna van een actie — elke actie opent een formulier waarvan alle verplichte velden worden gevalideerd voordat je verdergaat.
5. Uitdrukkelijke bevestiging vóór elke gevoelige of destructieve bewerking (flush, opschoning, herstel...).
6. Uitvoering op de achtergrond voor trage bewerkingen (de interface blijft tijdens het wachten bruikbaar), daarna terug naar het menu met een samenvatting van het resultaat.

### Navigatie

- Pijltoetsen omhoog/omlaag: de cursor in een lijst of menu verplaatsen.
- Tab / Shift+Tab: tussen de velden van een formulier navigeren.
- Enter: selecteren of bevestigen.
- Op een rij van een tabel klikken: die selecteren en de betreffende velden vooraf invullen (vast te zetten bron, doeljail enz.).
- `Esc`: terug naar het vorige scherm (vraagt op het startscherm om bevestiging om af te sluiten).
- `a`: contextuele hulp — beschrijft de lopende actie, of alle acties van de huidige sectie als er nog geen actiescherm open is.
- `t`: naar het volgende thema gaan, zonder bevestiging.
- `r`: de grootte en familie van de terminal opnieuw detecteren.
- `s`: de instellingen openen (thema, weergaveprofiel).
- `q` / `Ctrl+Q`: afsluiten, met bevestiging.

#### Bijzonderheden van het lnav-scherm (5.9 / 8.6)

`lnav` is ingebed in een pseudoterminal met een blijvende Omega-Fire-header/footer rond zijn eigen weergave, om elke botsing tussen zijn eigen sneltoetsen en die van Omega-Fire te voorkomen:

- Pijltoetsen ↑↓: in de logs navigeren (eigen `lnav`-sneltoets, ongewijzigd doorgegeven).
- Pijltoetsen ←→: horizontaal scrollen over lange regels (eigen `lnav`-sneltoets).
- `g` / `G`: naar het begin / het einde gaan (eigen `lnav`-sneltoets).
- `Ctrl+C`: de huidige regel markeren en naar het systeemklembord kopiëren (vervangt het eigen kopieercommando van `lnav`, dat op sommige systemen kan vastlopen).
- kleine `t`: volgend thema, alleen voor deze weergave (de hoofdletter `T` blijft de eigen `lnav`-sneltoets om de verstreken tijd tussen regels te tonen).
- `Ctrl+Q`: terug naar Omega-Fire (sluit `lnav` netjes af, zonder de toepassing te verlaten).

---

## Thema's en terminals

Tien `omega-*`-thema's worden gedeeld met de rest van de OMEGA-suite:

```text
omega-base       omega-dark       omega-light
omega-neon       omega-burn       omega-pink
omega-hack       omega-contrast   omega-mono
omega-minimal
```

- Wissel met `t` tussen de thema's, of kies er rechtstreeks een in de instellingen (`s`).
- Het gekozen thema wordt bewaard en bij de volgende start teruggevonden.
- Omega-Fire past de visuele complexiteit (randen, splash, informatiedichtheid) via een **weergaveprofiel** automatisch aan de gedetecteerde terminal aan: Volledig, Standaard, Beperkt of Mono (alleen ASCII). Het profiel kan in de instellingen handmatig worden overschreven.

| Minimale grootte | Profiel | Typische terminals |
|---|---|---|
| 120×32 of meer | Volledig | Ghostty, Alacritty, WezTerm, Kitty |
| 100×28 of meer | Standaard | Konsole, GNOME Terminal, Terminator, xfce4-terminal |
| 80×24 of meer | Beperkt | urxvt, xterm, moderne SSH |
| kleiner dan 80×24 | Mono (alleen ASCII) | Linux-TTY, oude SSH |

Onder 80×24 wordt het starten geweigerd (minimale grootte vereist); vergroot de terminal en start opnieuw, of gebruik `r` na het vergroten als de weergave niet automatisch is bijgewerkt.

---

## Configuratie

De specifieke configuratie kan worden aangepast in:

```text
omega-fire/config/omega-fire.conf
```

Ze kan onder meer het volgende vastleggen:

- paden van de logs;
- servers en bronnen voor monitoring;
- beschikbare backends of eigen paden;
- te analyseren omgevingen;
- parameters die zijn afgestemd op een bepaalde installatie.

De configuratie wordt opnieuw ingelezen bij een herstart of bij een handmatige herscan (menu 1.3 of 7.4).

Dit bestand is volledig optioneel (de toepassing werkt zonder normaal, met terugval op omgevingsvariabelen) en **uitgesloten van het verspreidbare archief** — een update overschrijft het nooit stilzwijgend, en `install.sh` haalt het indien nodig zelf automatisch uit een oude installatie op (zie « Bijwerken » hierboven).

### Interne paden en systeempaden

Standaard werkt Omega-Fire in zijn eigen map:

```text
var/exports/       # map binnen het project
/var/exports/      # absoluut systeempad
```

De eerste `/` is dus van belang. Imports en exports naar het systeem moeten uitdrukkelijk door de gebruiker worden gevraagd.

---

## Backends en compatibiliteit

Omega-Fire detecteert de componenten en activeert alleen de bruikbare functies.

| Component | Rol | Status |
|---|---|---|
| nftables | Moderne IPv4/IPv6-firewall | Aanbevolen |
| iptables | IPv4-firewall | Compatibel |
| ip6tables | IPv6-firewall met iptables | Compatibel indien beschikbaar |
| Fail2Ban | Jails en geautomatiseerde verbanningen | Optioneel |
| conntrack | Actieve verbindingen | Optioneel |
| lnav | Geavanceerde loganalyse | Optioneel |
| systemd, runit, OpenRC | Dienstbeheer | Automatische detectie |
| Docker, VNC, servers | Gedetecteerde toepassingen en diensten | Afhankelijk van de installatie |

### IPv4 en IPv6

Beide adresfamilies worden ondersteund door de compatibele backends:

- nftables: IPv4 en IPv6 in dual stack;
- iptables/ip6tables: afhankelijk van de beschikbare binaries;
- Fail2Ban: afhankelijk van de configuratie van de jail en het systeem.

Lange, gecomprimeerde, lokale, gemengde IPv6-formaten, met nullen en in CIDR-notatie, worden door de betreffende componenten verwerkt.

---

## Persistentie, logs en exports

### Persistentie

- SQLite via `sqlite3`.
- Tabellen voor bans, regels, audits en snapshots.
- Geversioneerde migraties die automatisch worden toegepast.
- Archieven van de volledige toestand in `.tar.gz`-formaat.
- Vastgezette items (favoriete logbronnen) en recente geschiedenis bewaard in JSON (`var/runtime/`), blijven behouden na een herstart.

### Logs

- Tekstueel applicatielog: `var/logs/app.log`.
- Gestructureerd JSON-auditlog met onder meer `event_type`, `actor`, `action`, `result` en `details`.

### Exports

De exports zijn beschikbaar als JSON, TXT en HTML, met meerdere CSS-thema's voor de HTML-rapporten.

---

## Beveiliging

Omega-Fire werkt op kritieke systeemcomponenten en moet met voorzichtigheid worden gebruikt.

- Het starten vereist rootrechten via `sudo`.
- Flush, algemene opschoning en het toepassen van een beleid kunnen destructief zijn.
- Een vooraf gedefinieerd beleid start vóór de wijziging een automatische back-up.
- Maak vóór elke grote wijziging een handmatige back-up.
- Controleer na elke bewerking de werkelijke toestand van de firewall, de jails en de verbindingen.
- Test eerst op een wegwerpmachine of -doel.
- Gebruik voor IPv4-tests de documentatienetwerken uit RFC 5737: `192.0.2.0/24`, `198.51.100.0/24` en `203.0.113.0/24`.
- Controleer exports en snapshots voordat je ze op een productiemachine herstelt.
- Geef de map `var/` geen ruimere rechten dan nodig.

---

## Tests en kwaliteit

Het project telt een historische suite van 152 unittests, geschreven vóór de migratie naar Textual: ze dekt het bedrijfsdomein, de orkestratie (`application/`), de infrastructuur en de Rich-interface (`interfaces/cli/`), maar **dekt `interfaces/tui/` nog niet** (de standaard-Textual-interface). Dit archief bevat de map `tests/` niet: haal die zo nodig uit je ontwikkelrepository om ze uit te voeren.

```bash
source .venv/bin/activate
python -m unittest discover tests/unit -v
```

Omdat de gelaagde architectuur het bedrijfsdomein strikt scheidt van de presentatie (`domain/`, `application/`, `ports/` als `Protocol`, zie [Architectuur](#architectuur)), blijft deze suite ondanks de migratie ongewijzigd geldig: alleen de recentere Textual-interface heeft nog geen eigen dekking.

Als je bijdraagt aan het project, installeer dan de kwaliteitshulpmiddelen die (als commentaar) in `requirements.txt` staan:

```bash
pip install pytest pytest-cov black flake8 mypy
```

Beschikbare hulpmiddelen na installatie:

```bash
black .
flake8 .
mypy src/
pytest --cov
```

---

## Projectstatus

### Operationele punten

- Geïntegreerde Textual-TUI voor de belangrijkste netwerkbeveiligingsmechanismen, gevalideerde formulieren, thema's en contextuele hulp gedeeld met de OMEGA-suite.
- Historische Rich-interface behouden als terugvaloptie (`--legacy-cli`).
- Automatische detectie van mogelijkheden.
- Beheer van de beschikbare backends.
- IPv4/IPv6-ondersteuning afhankelijk van de aanwezige hulpmiddelen.
- Applicatielogging en audit.
- Back-up en herstel.
- JSON-, TXT- en HTML-exports.
- Dashboard en statistieken, op de achtergrond vernieuwd zonder de interface te blokkeren.
- Gedocumenteerde gelaagde architectuur.

### Bekende beperkingen

- De testsuite (152) dekt de na haar geschreven Textual-interface (`interfaces/tui/`) nog niet (zie [Tests en kwaliteit](#tests-en-kwaliteit)).
- Het mechanisme `ExecutionPlan`/`PipelineStep` is gedeeltelijk nog aanwezig in het project.
- De precieze beschikbaarheid van de functies hangt af van de binaries, diensten, rechten en configuraties van de hostmachine.
- De historische Rich-interface (`--legacy-cli`) is niet langer de focus van de actieve ontwikkeling; ze blijft behouden tot de Textual-interface onder reële omstandigheden volledig betrouwbaar is.

---

## Verwijderen

Als de gegevens in de projectmap zijn gebleven:

```bash
sudo rm -rf ~/omega-fire
```

Verwijder handmatig de elders geëxporteerde bestanden, eventuele `fire`-aliassen die aan `~/.bashrc` of `~/.zshrc` zijn toegevoegd, en de eigen groep als die niet meer wordt gebruikt:

```bash
sudo groupdel omega-fire
```

Voer dit laatste commando alleen uit als geen enkel ander bestand of geen enkele andere dienst van deze groep afhangt.

---

## Licentie

Omega-Fire wordt verspreid onder de **MIT**-licentie. Zie het bestand [`LICENSE`](../../../LICENSE) voor de volledige tekst.

---

> **Omega-Fire — Observeren, besturen, auditen, beveiligen.**
>
> Een geïntegreerde TUI-interface voor nftables, iptables, ip6tables, Fail2Ban, de logs en netwerkmonitoring.
