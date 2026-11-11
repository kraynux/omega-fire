<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->

<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-fire.png" alt="Omega-Fire" width="512">
</div>

# 󰦝 OMEGA-FIRE

**Postazione unificata di gestione della sicurezza di rete**

> Sviluppato da [kraynux](https://github.com/kraynux) per [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

Pagina ufficiale: [OMEGA-FIRE](https://kraynux.snake-mackarel.ts.net/omega-fire/) &nbsp; Anteprima: [Screenshot](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/)  

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)
[![Interface](https://img.shields.io/badge/Interface-Textual%20TUI-cyan.svg)](https://github.com/Textualize/textual)

🌐 Documentazione, esportazioni e interfaccia disponibili in **17 lingue** — vedi [Lingue dell'interfaccia](#lingue-dellinterfaccia).  
**Lingue:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

**Omega-Fire** è un'applicazione TUI (Terminal User Interface) in Python costruita con [Textual](https://github.com/Textualize/textual). Fornisce da un terminale un'interfaccia unica per amministrare i firewall Linux, Fail2Ban, gli indirizzi bannati, le regole di rete, i log e le statistiche di sistema.

L'interfaccia Textual è la modalità di funzionamento predefinita e naviga tramite menu, moduli convalidati (tutti i campi obbligatori vengono verificati prima di proseguire) e schermate dedicate, con temi, aiuto contestuale e scorciatoie da tastiera condivise con il resto della suite OMEGA (omega-check, omega-deep, omega-stress...). La vecchia interfaccia [Rich](https://github.com/Textualize/rich), sequenziale e guidata dalla digitazione di numeri, resta disponibile tramite `--legacy-cli` (vedi [Avvio](#avvio)). 
Anteprima: [Screenshot](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/index-2.html)

<p align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/translation/it/omega-fire/A.png" width="24%" />
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/translation/it/omega-fire/B.png" width="24%" />
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/translation/it/omega-fire/C.png" width="24%" />
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/translation/it/omega-fire/D.png" width="24%" />
</p>

Il progetto è concepito secondo i principi della **Clean Architecture**, con una separazione chiara tra dominio di business, orchestrazione, infrastruttura e interfaccia utente.

## Sommario

- [Presentazione](#presentazione)
- [Funzionalità](#funzionalità)
- [Architettura](#architettura)
- [Prerequisiti](#prerequisiti)
- [Installazione](#installazione)
- [Utilizzo](#utilizzo)
- [Configurazione](#configurazione)
- [Backend e compatibilità](#backend-e-compatibilità)
- [Persistenza, log ed esportazioni](#persistenza-log-ed-esportazioni)
- [Sicurezza](#sicurezza)
- [Test e qualità](#test-e-qualità)
- [Stato del progetto](#stato-del-progetto)
- [Disinstallazione](#disinstallazione)
- [Licenza](#licenza)

---

## Presentazione

Omega-Fire agisce come una **postazione di comando locale** per la sicurezza di rete. Rileva automaticamente i componenti presenti sulla macchina e adatta i menu alle capacità realmente disponibili.

### Obiettivi

- Riunire nftables, iptables, ip6tables e Fail2Ban in un'interfaccia coerente.
- Facilitare l'osservazione e l'azione su connessioni, ban ed eventi di sistema.
- Centralizzare esportazioni, backup, audit e cronologia delle operazioni.
- Mantenere un'architettura testabile ed estensibile.
- Funzionare in modalità degradata quando un componente opzionale è assente.

### Cosa fa Omega-Fire

- Rileva i backend, i servizi, il kernel e gli strumenti disponibili.
- Amministra nftables, iptables e ip6tables quando questi componenti sono presenti.
- Gestisce gli IP bannati, singolarmente o in blocco, con importazione, esportazione, sincronizzazione e flush.
- Crea, elenca ed elimina regole avanzate.
- Applica politiche predefinite con backup automatico preventivo.
- Amministra i jail di Fail2Ban e i relativi ban.
- Analizza i log in tempo reale o sotto forma di statistiche.
- Offre sorveglianza sotto forma di monitoraggio.
- Usa conntrack per mostrare le connessioni attive quando è disponibile.
- Produce esportazioni JSON, TXT e HTML.
- Salva e ripristina lo stato completo in archivi `.tar.gz`.
- Registra le operazioni in un log applicativo e in un audit JSON strutturato.
- Sorveglia i servizi e le applicazioni rilevati: systemd, runit, OpenRC, Docker, server, VNC ecc.

### Cosa non fa il progetto

- Non sostituisce nftables, iptables o Fail2Ban.
- Non costituisce un firewall autonomo indipendente dal sistema.
- Non fornisce autenticazione multiutente.
- Non espone API di rete durante il normale funzionamento.
- Non è una dashboard web.
- Non protegge direttamente una macchina remota da un'altra macchina.
- Per impostazione predefinita non installa alcun file al di fuori della propria cartella.
- Non garantisce la disponibilità di tutti i backend su tutte le distribuzioni.

---

## Funzionalità

### 1. Capacità e diagnostica

- Visualizzazione del registro delle capacità rilevate.
- Consultazione dettagliata di una capacità per identificatore.
- Nuova scansione manuale del sistema dopo l'installazione di un componente.
- Consultazione delle diagnostiche recenti.
- Consultazione e ricerca nel log applicativo.
- Esportazione dello stato e delle diagnostiche in JSON, TXT o HTML.
- Categoria **Suite omega**: omega-serv (istanze rilevate e in esecuzione), omega-waf (extra `magnet` attivato) e omega-jail (jail installati), visibili nel registro, nella dashboard e nei report.

### 2. Gestione unificata degli IP

La blacklist unificata permette di lavorare con nftables e iptables dalla stessa schermata.

- Ban di un IP o di un elenco di IP.
- Rimozione del ban singola o in blocco.
- Inserimento diretto o importazione da un file.
- Elenco per backend o vista unificata.
- Sincronizzazione tra i backend NFTables/IPTables.
- Esportazione e reimportazione degli elenchi.
- Pulizia completa di uno o più backend.
- Supporto IPv4 e IPv6.
- Gestione dei file di blocklist (`var/blocklist/`) e dei relativi elementi fissati direttamente dalla schermata dedicata; i file proposti di default, `blocklist.txt` e `blocklist-f2b.txt`, vengono creati vuoti al primo avvio.

### 3. Gestione delle regole e delle politiche

- Procedura guidata passo passo per creare una regola avanzata.
- Elenco delle regole di sistema e delle regole create da Omega-Fire.
- Eliminazione di una regola per selezione.
- Pulizia automatica delle regole inattive nella base di riferimento.
- Pulizia e risincronizzazione del database con il firewall reale, con anteprima e backup preventivo, senza mai modificare il firewall stesso.
- Regole di altri strumenti (UFW, Tailscale, Docker…) identificate dalla loro origine: mostrate a titolo informativo, mai eliminate da Omega-Fire.
- Protezione prima di applicare una politica o svuotare iptables quando altri strumenti vi hanno delle regole: applicare ovunque, solo su nftables, oppure annullare — conseguenze dettagliate nell'aiuto.
- Applicazione di politiche predefinite.
- Backup automatico prima dell'applicazione di una politica.
- Personalizzazione, salvataggio e ripristino di una politica.
- Identificazione della politica attiva nel menu di stato e nella dashboard.
- Segnalazione dei profili modificati nella forma `Profilo + CUSTOM`.
- Gestione delle tabelle (menu 3.5): diagnostica in sola lettura per backend (presenza della tabella, politiche input/output/forward, numero di regole) con spiegazione delle politiche diverse tra i backend (effetto reale, causa e rimedio).
- Inizializzazione di una tabella nftables al primo utilizzo, senza mai sovrascrivere una chain già configurata.
- Reimpostazione delle politiche di chain ad ACCEPT su un backend, per correggere una politica restrittiva orfana lasciata da un profilo precedente.
- Svuotamento mirato di un backend o svuotamento sincronizzato di tutti i backend rilevati in un'unica azione.
- Eliminazione completa di una tabella nftables (azione avanzata, oltre alle sole regole).

### 4. Gestione di Fail2Ban

- Stato dettagliato dei jail e dei relativi parametri.
- Numero di IP bannati e informazioni di rate-limit.
- Ricerca di un IP nei jail.
- Ban e unban singoli o multipli.
- Trasferimento di IP tra jail, backend e file.
- Creazione guidata di un jail personalizzato.
- Modelli di jail predefiniti, modificabili ed eliminabili.
- Origine di ogni jail: Omega-Fire, omega-jail, configurazione principale di fail2ban o altro file.
- Eliminazione affidabile di un jail, qualunque sia il nome del suo file: avviso per un jail installato da omega-jail, rifiuto spiegato per un jail di `jail.local` o di un file condiviso, i filtri standard di fail2ban non vengono mai eliminati.
- Svuotamento di un jail o purga generale.
- Esportazione in JSON, TXT o HTML.
- Verifica e audit della configurazione.
- Controllo del servizio: stato, avvio, arresto, riavvio, attivazione e disattivazione all'avvio del sistema; dopo un avvio o un arresto, il registro delle capacità e la dashboard vengono aggiornati.

### 5. Log e manutenzione

- **Libreria di log** (5.1): importazione automatica dei log delle istanze omega-serv rilevate, compresi quelli di omega-waf, fissaggio manuale di un percorso e recupero di un log remoto via SSH (chiave o agente, mai una password).
- **Preferiti** (5.2): combinare log della Libreria, salvarli con un nome e un visualizzatore e avviarli direttamente.
- **Vedi i log** (5.3): un log senza configurazione, con il visualizzatore preferito — Semplice (dashboard in tempo reale: stati HTTP inclusi i rifiuti 403 e 429, Top 5 IP, percorsi richiesti e percorsi in 404, come omega-log), Classico (ultime righe poi aggiornamento in diretta) o `lnav`.
- **La Libreria alimenta tutte le selezioni di log**: 5.4, 5.5, 5.6, oltre a 8.5 e 8.6, la propongono in cima all'elenco, prima degli elementi fissati.
- Integrazione di `lnav`: più log uniti in un'unica vista cronologica, incapsulata in un header/footer Omega-Fire (vedi [Navigazione](#navigazione)).
- Analisi degli IP più frequenti con Top N (5.4), esportabile per essere ricaricata nella pulizia mirata; ricerca di un IP preciso nell'intero file e rimozione diretta dell'IP scelto, senza bloccare l'interfaccia.
- Pulizia mirata di uno o più IP in file LOG o TXT, inseriti a mano o spuntati da un'esportazione.
- File fissati con **preset da spuntare**: vengono proposti solo i percorsi abituali realmente presenti sulla macchina.
- Rotazione e backup immediati o pianificati, **eseguiti davvero ogni notte** (timer systemd avviato come root, altrimenti una riga nella crontab di root), con il numero di backup conservati, l'ultimo e il prossimo backup.
- Ripristino di un backup.
- Purga per anzianità, quota, tipo o selezione manuale.
- Pulizia avanzata per cartella o ambiente.
- Statistiche su 24 ore, 7 giorni o 30 giorni (5.10, vista rapida).
- Analisi di eventi, movimenti, quote e IP presenti nei jail.

### 6. Esportazioni e report

Formati disponibili:

- **JSON**: dati strutturati e riutilizzabili.
- **TXT**: formato grezzo o adatto all'iniezione.
- **HTML**: report leggibile e visivo.

Report disponibili:

- Blacklist completa.
- Ruleset strutturato.
- Regole selezionate per provenienza: sistema, Omega-Fire o attive.
- Report di audit completo.
- Statistiche di Fail2Ban.
- Stato e diagnostica del sistema.
- Report statistici su 7 o 30 giorni.
- Classifica Top N degli IP.
- **Statistiche dei log** (6.5): stesso rapporto di omega-serv e omega-log (sintesi, stati HTTP, top IP, percorsi richiesti, percorsi in 404, distribuzione oraria, tendenza giornaliera), solo log; i ban e lo stato del firewall restano nei report su 7 e 30 giorni.
- Guida di aiuto e FAQ.

**Vedi tutte le esportazioni** (6.6): tutti i file esportati in un unico posto, con tipo, data e dimensione; un report HTML si apre nel browser web predefinito dell'utente, un JSON o un TXT si legge in Omega-Fire, senza terminale né file manager.

Temi HTML:

- `omega-base` — blu notte e ciano, tema predefinito.
- `omega-burn` — brace rosso-arancio.
- `omega-neon` — cyberpunk ciano e magenta.
- `light-basic` — chiaro e sobrio.
- `light-alt` — carta crema e verde bosco.

Lingua delle esportazioni: impostabile a parte nelle impostazioni (« Come l'interfaccia » di default), per consegnare un report nella lingua del suo lettore senza cambiare quella dell'interfaccia.

### 7. Sistema e persistenza

- Backup dello stato completo: regole, ban nftables, ban iptables e Fail2Ban.
- Creazione di archivi `.tar.gz` con data e ora.
- Elenco e ripristino degli snapshot: vengono ripristinate solo le regole di Omega-Fire ricreabili in modo identico; quelle degli altri strumenti non vengono mai toccate.
- Cronologia delle azioni.
- Filtraggio e purga della cronologia.
- Ricaricamento della configurazione e nuova scansione senza riavvio.

### 8. Monitoraggio e statistiche

- Dashboard in tempo reale con aggiornamento periodico (ogni 2 secondi), senza bloccare l'interfaccia durante la raccolta.
- Visualizzazione della politica attiva.
- Connessioni attive tramite conntrack.
- Traffico, eventi, statistiche e log del server.
- Report consolidati su 7 e 30 giorni.
- Esportazione HTML degli snapshot e dei report.

### 9. Impostazioni

- Scelta del tema attivo tra i dieci temi `omega-*` condivisi con il resto della suite (vedi [Temi e terminali](#temi-e-terminali)), mantenuto tra un avvio e l'altro.
- Forzatura manuale del profilo di rendering (automatico, completo, standard, ridotto o solo mono), applicata all'avvio successivo.
- Lingua dell'interfaccia tra 17 lingue (vedi [Lingue dell'interfaccia](#lingue-dellinterfaccia)): si riavvia solo l'interfaccia; regole del firewall, Fail2Ban e servizi non vengono toccati.
- Lingua delle esportazioni HTML e TXT, indipendente da quella dell'interfaccia.
- Cartelle delle esportazioni e degli screenshot modificabili, con svuotamento dopo conferma.
- Accessibile dal menu principale (`9. IMPOSTAZIONI`) o direttamente con il tasto `s`.

### 10. Aiuto

- **Guida di aiuto**: tutte le schede di aiuto riunite nell'ordine dei menu, ogni scheda apre le schede collegate.
- **FAQ**: le domande reali incontrate nell'uso (regole di altri strumenti, ripristino, Fail2Ban, log, esportazioni e browser).
- Esportazione HTML della guida e della FAQ, nella lingua delle esportazioni.
- Il tasto `a` resta l'aiuto della schermata corrente.

---

## Architettura

```text
src/omega_fire/
├── app/              Bootstrap e container di iniezione delle dipendenze
├── core/             Capacità, enumerazioni ed eccezioni
├── domain/           Logica di business pura: regole, IP, jail, log
├── application/      Orchestrazione: commands e queries
├── infrastructure/   Backend, archiviazione, esportazioni, log e sonde di sistema
├── ports/            Contratti Protocol/ABC
├── interfaces/       interfaces/tui/ (Textual, predefinita) + interfaces/cli/ (Rich, --legacy-cli)
├── plugins/          Estensioni integrate: nftables, iptables, Fail2Ban, conntrack
└── shared/           Parsing, rete, formattazione e utilità trasversali
```

### Principi di progettazione

- `domain/` non contiene né I/O né dipendenze verso l'infrastruttura.
- `application/` orchestra i casi d'uso tramite il dominio e le porte — le schermate Textual e le azioni dell'interfaccia Rich chiamano gli stessi commands/queries, e la logica di business non dipende da nessuna delle due interfacce.
- `infrastructure/` è l'unico livello autorizzato a chiamare `nft`, `iptables`, `fail2ban-client` e gli altri strumenti esterni (subprocess, pty, file).
- `interfaces/` non deve chiamare direttamente `subprocess`.
- `ports/` definisce i contratti attesi dagli adattatori.
- `core/` fornisce il registro delle capacità usato dai vari livelli.
- I plugin permettono di aggiungere o far evolvere i backend senza modificare il dominio di business.
- L'interfaccia Textual (`interfaces/tui/`) si appoggia su [`omega-lib`](https://github.com/) (dipendenza condivisa da tutta la suite OMEGA: tema a 9 token, rilevamento del terminale, contratti di porta comuni), non pubblicata su PyPI — inclusa nell'archivio distribuibile (`vendor/omega-lib/`, vedi [Installazione](#installazione)).
- Ogni chiamata potenzialmente lenta (backend firewall, `fail2ban-client`, disco) avviata da una schermata Textual viene eseguita in background (thread), mai sul thread principale dell'interfaccia — una dashboard o un modulo restano reattivi durante l'operazione invece di bloccare l'intera applicazione.

### Struttura dei dati

Omega-Fire usa SQLite tramite la libreria standard `sqlite3`, senza ORM esterno. I principali insiemi di dati riguardano ban, regole, eventi di audit e snapshot.

Le migrazioni sono versionate e applicate automaticamente all'avvio.

---

## Prerequisiti

### Sistema

- Linux, prioritariamente Arch Linux e distribuzioni compatibili.
- Python 3.10 o superiore.
- Privilegi di root disponibili tramite `sudo`.
- Un gestore di servizi: systemd, runit o OpenRC.
- Almeno un backend firewall: nftables o iptables.
- Un terminale di almeno 80x24 (vedi [Temi e terminali](#temi-e-terminali) per il dettaglio dei profili di rendering in base alla dimensione disponibile).

### Dipendenze Python

Le dipendenze di produzione sono definite in `requirements.txt`:

- `textual` — interfaccia TUI predefinita.
- `omega-lib` — tema, rilevamento del terminale e contratti condivisi con la suite OMEGA (non pubblicata su PyPI, vedi [Architettura](#architettura) e [Installazione](#installazione)).
- `rich` — rendering dell'interfaccia `--legacy-cli` e di alcuni report.
- `psutil` — informazioni di sistema (CPU, memoria, rete, processi) per la dashboard e la diagnostica.
- `jinja2` — generazione delle esportazioni HTML.
- `python-dotenv` — variabili d'ambiente.
- `pyte` — emulatore di terminale virtuale, per l'incapsulamento di `lnav` (menu 8.6 e visualizzatore lnav di 5.2 / 5.3).

Gli strumenti di qualità (`pytest`, `black`, `flake8`, `mypy`) sono elencati come commento in `requirements.txt`: decommentali o installali separatamente se contribuisci al progetto (vedi [Test e qualità](#test-e-qualità)).

### Strumenti opzionali consigliati

L'applicazione funziona in modalità degradata se questi strumenti sono assenti:

- `fail2ban` — ban automatizzato.
- `conntrack` o `conntrack-tools` — connessioni attive e statistiche di rete.
- `lnav` — analisi avanzata e multi-file dei log.

Su Arch Linux e derivate:

```bash
sudo pacman -S fail2ban conntrack-tools lnav
```

---

## Installazione

L'archivio ufficiale è fornito in formato `.tar.gz`. Verificane l'integrità prima dell'installazione:

```bash
sha256sum omega-fire.tar.gz
```

> ⚠️ **Questi tre metodi servono per una prima installazione.** Se `~/omega-fire` esiste già (aggiornamento da una versione precedente), usa la sezione [Aggiornamento](#aggiornamento) qui sotto — non rilanciare mai questi comandi dall'interno di una cartella `omega-fire` esistente: `tar` tenterebbe di creare un `omega-fire/omega-fire/` annidato e fallirebbe con errori di permesso se quella cartella appartiene a root (frequente se un'estrazione precedente è stata fatta per errore con `sudo tar`).

### Metodo 1 — script di installazione

```bash
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Sembri già trovarti in una cartella omega-fire — vedi la sezione Aggiornamento del README." >&2; exit 1; }
[ -d omega-fire ] && echo "ℹ️ Già estratto qui, passaggio ignorato." || tar -xzf omega-fire.tar.gz
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire esiste già, spostamento ignorato." || mv omega-fire ~/
cd ~/omega-fire/
chmod +x install.sh
./install.sh
```

Avvio:

```bash
./omega-fire.sh
```

Se l'alias è stato installato, apri un nuovo terminale e usa:

```bash
fire
```

### Metodo 2 — installazione completa resiliente

Questo comando può essere rilanciato: ignora i passaggi già eseguiti.

```bash
([ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Sembri già trovarti in una cartella omega-fire — vedi la sezione Aggiornamento del README." >&2; exit 1; }; [ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire esiste già, estrazione ignorata." || (tar -xzf omega-fire.tar.gz && mv omega-fire ~/)) && cd ~/omega-fire/ && ([ -d .venv ] && echo "ℹ️ .venv esiste già, passaggio ignorato." || python3 -m venv .venv) && source .venv/bin/activate && ([ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib || true) && pip install -r requirements.txt && chmod +x omega-fire.sh && mkdir -p var && (getent group omega-fire >/dev/null 2>&1 && echo "ℹ️ Gruppo omega-fire già presente." || sudo groupadd omega-fire) && (groups "$USER" 2>/dev/null | grep -qw omega-fire && echo "ℹ️ $USER è già membro del gruppo omega-fire." || sudo usermod -aG omega-fire "$USER") && sudo chgrp -R omega-fire var && sudo chmod -R 2775 var && echo "✅ Omega-Fire installato. Avvia ./omega-fire.sh."
```

### Metodo 3 — installazione dettagliata

```bash
# 0. Verificare di non rilanciare dall'interno di un omega-fire esistente
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Sembri già trovarti in una cartella omega-fire — vedi la sezione Aggiornamento del README." >&2; exit 1; }

# 1. Estrarre
[ -d omega-fire ] && echo "ℹ️ Già estratto qui, passaggio ignorato." || tar -xzf omega-fire.tar.gz

# 2. Spostare nella home
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire esiste già, spostamento ignorato." || mv omega-fire ~/

# 3. Entrare nel progetto
cd ~/omega-fire/

# 4. Creare l'ambiente virtuale
[ -d .venv ] && echo "ℹ️ .venv esiste già, creazione ignorata." || python3 -m venv .venv

# 5. Installare le dipendenze (omega-lib inclusa, se presente, prima di requirements.txt)
source .venv/bin/activate
[ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib
pip install -r requirements.txt

# 6. Rendere eseguibile il launcher
chmod +x omega-fire.sh

# 7. Preparare var/ per root e l'utente corrente
mkdir -p var
getent group omega-fire >/dev/null 2>&1 || sudo groupadd omega-fire
groups "$USER" 2>/dev/null | grep -qw omega-fire || sudo usermod -aG omega-fire "$USER"
sudo chgrp -R omega-fire var
sudo chmod -R 2775 var

# 8. Avviare
./omega-fire.sh
```

`vendor/omega-lib/` è presente solo nell'archivio ufficiale (`build-release.sh` la integra automaticamente, perché omega-lib non è pubblicata su PyPI); in un clone di sviluppo, installala separatamente dal suo repository (`pip install -e percorso/di/omega-lib`).

Il gruppo dedicato e il bit `setgid` permettono a root e all'utente di condividere i file prodotti in `var/` senza aprire i permessi a tutto il sistema. Potrebbe essere necessario un nuovo login o `newgrp omega-fire` per beneficiare immediatamente dell'appartenenza al gruppo.

### Aggiornamento

Se `~/omega-fire` esiste già (installazione precedente), **non rilanciare mai i comandi di installazione dall'interno di questa cartella**: `tar` tenterebbe di creare un `omega-fire/omega-fire/` annidato e fallirebbe, di solito con una cascata di errori « Permesso negato » se la cartella appartiene a `root` (caso frequente se un'estrazione precedente è stata fatta per errore con `sudo tar`).

Procedura consigliata, da qualsiasi cartella **diversa da `~/omega-fire`** (tipicamente `~` stessa):

```bash
# 1. Verificare lo stato e il proprietario dell'installazione esistente
ls -ld ~/omega-fire

# 2. Mettere da parte la vecchia installazione invece di sovrascriverla
sudo mv ~/omega-fire ~/omega-fire.old-$(date +%Y%m%d)

# 3. Estrarre il nuovo archivio direttamente nella home
tar -xzf omega-fire.tar.gz -C ~/

# 4. Reinstallare (ricrea il venv, reinstalla le dipendenze, rifà i permessi di var/)
cd ~/omega-fire
chmod +x install.sh
./install.sh

# 5. Avviare
./omega-fire.sh
```

Il passaggio 4 (`./install.sh`) rileva automaticamente questa situazione (database `var/db/` assente qui, cartella `~/omega-fire.old-AAAAMMGG` trovata subito accanto) e **recupera da solo** `config/omega-fire.conf`, il database, la blocklist, i backup, le esportazioni e gli screenshot dalla vecchia installazione — senza domande, senza passaggi manuali. Non c'è nient'altro da fare oltre ai punti da 1 a 5 qui sopra, qualunque cosa contenesse la tua installazione precedente.

Se accanto si trovano più cartelle che sembrano una vecchia installazione (ambiguo), `install.sh` non indovina nulla: mostra i loro percorsi e ti invita a lanciare tu stesso `sudo ./migrate-state.sh <cartella>` una volta identificata la fonte corretta.

Una volta convalidata la nuova installazione, la vecchia cartella `~/omega-fire.old-AAAAMMGG` può essere eliminata (`sudo rm -rf ~/omega-fire.old-AAAAMMGG`).

### Alias Bash o Zsh

```bash
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.bashrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.bashrc
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.zshrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.zshrc
```

Ricarica poi la shell:

```bash
source ~/.bashrc 2>/dev/null || source ~/.zshrc
```

### Icone e simboli Nerd Fonts

Se le icone non sono disponibili, installa i simboli Nerd Fonts:

```bash
mkdir -p ~/.local/share/fonts
curl -fLo /tmp/NerdFontsSymbolsOnly.zip \
  https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip
unzip -o /tmp/NerdFontsSymbolsOnly.zip -d ~/.local/share/fonts
fc-cache -fv
```

---

## Utilizzo

### Avvio

```bash
cd ~/omega-fire
./omega-fire.sh

# o semplicemente, se l'alias è stato creato:
fire
```

Il launcher:

1. Verifica i privilegi di root e rilancia tramite `sudo` se necessario.
2. Rileva `.venv`, `venv` o il Python di sistema.
3. Configura `PYTHONPATH` verso `src/`.
4. Avvia `python -m omega_fire` — l'interfaccia **Textual**, per impostazione predefinita.

Per avviare invece la vecchia interfaccia Rich (digitazione sequenziale di numeri):

```bash
./omega-fire.sh --legacy-cli
```

**La vecchia interfaccia Rich non è più sviluppata, ma resta disponibile.** La vecchia interfaccia resta quella della versione 3.0, in francese: menu 5 originale (senza Libreria, Preferiti né visualizzatore Classico), senza «Vedi tutte le esportazioni», senza guida di aiuto né FAQ, senza preset. L'interfaccia Textual porta la versione 3.5 completa.

### Lingue dell'interfaccia

17 lingue: francese, inglese, spagnolo, portoghese (Brasile), italiano, tedesco, olandese, polacco, russo, cinese, vietnamita, thailandese, indonesiano, giapponese, coreano, hindi, arabo. Scelta nelle impostazioni (tasto `s`, « Langue / Language », etichetta mai tradotta), applicata riavviando solo l'interfaccia, o puntualmente con `OMEGA_FIRE_LANG=it ./omega-fire.sh` (mantenuto attraverso `sudo` dal lanciatore). Nella console testuale di Linux (TTY), le lingue la cui scrittura non esiste nei font della console (vietnamita, cinese, thailandese, giapponese, coreano, hindi, arabo) vengono mostrate in inglese per la sessione. L'arabo viene mostrato da destra a sinistra. In hindi, Terminator, GNOME Terminal, Xfce Terminal e Alacritty mostrano il testo allineato; i terminali che compongono da sé le lettere legate (Kitty, Ghostty, Konsole) possono spostare riquadri e colonne. La **lingua delle esportazioni** (report HTML e TXT) si imposta a parte, « Come l'interfaccia » di default. Il log dell'applicazione e la cronologia di audit restano registrati in francese; i titoli della cronologia sono mostrati nella lingua scelta. La vecchia interfaccia (`--legacy-cli`) resta in francese.

### Contatti e supporto

L'aiuto (tasto `a`) propone una schermata **Contatti e supporto**: *Offrire un caffè* (pagina PayPal dello sviluppatore), *Contattare il supporto* (indirizzo e-mail e modulo di contatto del sito, mostrati in chiaro), *Dichiararmi utente (anonimo)* e *Verifica aggiornamenti*. La dichiarazione è volontaria, disattivata per impostazione predefinita e inviata una sola volta: serve solo a contare gli utenti e, se lo si desidera, il loro continente o paese (elenchi chiusi, mai testo libero). Invia una chiave estratta a caso, il nome del software (`omega-fire`) e la sua versione; mai un nome, un nome di macchina, un'impostazione, un obiettivo o un risultato. L'indirizzo IP non viene registrato nelle dichiarazioni, ma, come per ogni visita, passa per i controlli di sicurezza e il registro del server di ricezione. Ritiro in qualsiasi momento dalla stessa schermata (*Non dichiararmi più*). La verifica degli aggiornamenti legge solo l'elenco delle versioni pubblicate sul sito, e mai senza un clic.

### Percorso generale

1. Schermata di avvio (splash), poi un avviso se il terminale è troppo piccolo.
2. Rilevamento delle capacità di sistema (schermata dedicata, non bloccante).
3. Menu principale: 8 sezioni tematiche (1-8), le impostazioni (9) e l'aiuto (10).
4. Selezione di una sezione, poi di un'azione — ogni azione apre un modulo i cui campi obbligatori vengono tutti convalidati prima di proseguire.
5. Conferma esplicita prima di qualsiasi operazione sensibile o distruttiva (flush, purga, ripristino...).
6. Esecuzione in background per le operazioni lente (l'interfaccia resta utilizzabile durante l'attesa), poi ritorno al menu con un riepilogo del risultato.

### Navigazione

- Frecce su/giù: spostare il cursore in un elenco o in un menu.
- Tab / Maiusc+Tab: navigare tra i campi di un modulo.
- Invio: selezionare o convalidare.
- Fare clic su una riga di una tabella: selezionarla e precompilare i campi interessati (fonte da fissare, jail di destinazione ecc.).
- `Esc`: tornare alla schermata precedente (chiede conferma di uscita dalla schermata iniziale).
- `a`: aiuto contestuale — descrive l'azione in corso, oppure tutte le azioni della sezione corrente se nessuna schermata di azione è ancora aperta; la guida completa e la FAQ sono nel menu 10.
- `t`: passare al tema successivo, senza conferma.
- `r`: rilevare di nuovo la dimensione e la famiglia del terminale.
- `s`: aprire le impostazioni (tema, profilo di rendering, lingue, cartelle).
- `q` / `Ctrl+Q`: uscire, con conferma.

#### Particolarità della schermata lnav (8.6, e visualizzatore lnav di 5.2 / 5.3)

`lnav` è incapsulato in uno pseudo-terminale con un header/footer persistenti di Omega-Fire attorno alla sua vista, per evitare qualsiasi collisione tra le sue scorciatoie native e quelle di Omega-Fire:

- Frecce ↑↓: navigare nei log (scorciatoia nativa di `lnav`, trasmessa così com'è).
- Frecce ←→: scorrere orizzontalmente sulle righe lunghe (scorciatoia nativa di `lnav`).
- `g` / `G`: andare all'inizio / alla fine (scorciatoia nativa di `lnav`).
- `Ctrl+C`: contrassegnare la riga corrente e copiarla negli appunti di sistema (sostituisce il comando nativo di copia di `lnav`, che può bloccarsi su alcuni sistemi).
- `t` minuscola: tema successivo, specifico di questa vista (la `T` maiuscola resta la scorciatoia nativa di `lnav` per mostrare il tempo trascorso tra le righe).
- `Ctrl+Q`: tornare a Omega-Fire (chiude `lnav` in modo pulito, senza uscire dall'applicazione).

---

## Temi e terminali

Dieci temi `omega-*` sono condivisi con il resto della suite OMEGA:

```text
omega-base       omega-dark       omega-light
omega-neon       omega-burn       omega-pink
omega-hack       omega-contrast   omega-mono
omega-minimal
```

- Passa da un tema all'altro con `t`, o scegline uno direttamente dalle impostazioni (`s`).
- Il tema scelto viene mantenuto e ritrovato all'avvio successivo.
- Omega-Fire adatta automaticamente la complessità visiva (bordi, splash, densità di informazioni) al terminale rilevato tramite un **profilo di rendering**: Completo, Standard, Ridotto o Mono (solo ASCII). Il profilo può essere forzato manualmente dalle impostazioni.

| Dimensione minima | Profilo | Terminali tipici |
|---|---|---|
| 120×32 o più | Completo | Ghostty, Alacritty, WezTerm, Kitty |
| 100×28 o più | Standard | Konsole, GNOME Terminal, Terminator, xfce4-terminal |
| 80×24 o più | Ridotto | urxvt, xterm, SSH moderno |
| sotto 80×24 | Mono (solo ASCII) | Linux TTY, SSH datato |

Sotto 80×24, l'avvio viene rifiutato (dimensione minima richiesta); ridimensiona il terminale e riavvia, oppure usa `r` dopo il ridimensionamento se la visualizzazione non si è aggiornata automaticamente.

---

## Configurazione

La configurazione specifica può essere regolata in:

```text
omega-fire/config/omega-fire.conf
```

Può definire in particolare:

- percorsi dei log;
- server e fonti di monitoraggio;
- backend disponibili o percorsi personalizzati;
- ambienti da analizzare;
- parametri adatti a un'installazione particolare.

La configurazione viene riletta al riavvio o durante una nuova scansione manuale (menu 1.3 o 7.4).

Questo file è del tutto opzionale (l'applicazione funziona normalmente senza, ricorrendo alle variabili d'ambiente) ed **escluso dall'archivio distribuibile** — un aggiornamento non lo sovrascrive mai silenziosamente, e `install.sh` lo recupera da solo automaticamente da una vecchia installazione, se presente (vedi « Aggiornamento » più sopra).

### Percorsi interni e percorsi di sistema

Per impostazione predefinita, Omega-Fire lavora nella propria cartella:

```text
var/exports/       # cartella interna al progetto
/var/exports/      # percorso assoluto del sistema
```

La `/` iniziale è quindi significativa. Le importazioni e le esportazioni verso il sistema devono essere richieste esplicitamente dall'utente.

---

## Backend e compatibilità

Omega-Fire rileva i componenti e attiva solo le funzionalità utilizzabili.

| Componente | Ruolo | Stato |
|---|---|---|
| nftables | Firewall IPv4/IPv6 moderno | Consigliato |
| iptables | Firewall IPv4 | Compatibile |
| ip6tables | Firewall IPv6 con iptables | Compatibile se disponibile |
| Fail2Ban | Jail e ban automatizzati | Opzionale |
| conntrack | Connessioni attive | Opzionale |
| lnav | Analisi avanzata dei log | Opzionale |
| systemd, runit, OpenRC | Gestione dei servizi | Rilevamento automatico |
| Docker, VNC, server | Applicazioni e servizi rilevati | Secondo l'installazione |

### IPv4 e IPv6

Le due famiglie di indirizzi sono supportate dai backend compatibili:

- nftables: IPv4 e IPv6 in dual stack;
- iptables/ip6tables: secondo i binari disponibili;
- Fail2Ban: secondo la configurazione del jail e del sistema.

I formati IPv6 lunghi, compressi, locali, misti, con zeri e in notazione CIDR sono gestiti dai componenti interessati.

---

## Persistenza, log ed esportazioni

### Persistenza

- SQLite tramite `sqlite3`.
- Tabelle relative a ban, regole, audit e snapshot.
- Migrazioni versionate applicate automaticamente.
- Archivi di stato completo in formato `.tar.gz`.
- Elementi fissati (fonti di log preferite) e cronologia recente mantenuti in JSON (`var/runtime/`), sopravvivono a un riavvio.

### Log

- Log testuale dell'applicazione: `var/logs/app.log`.
- Log di audit JSON strutturato con, tra l'altro, `event_type`, `actor`, `action`, `result` e `details`.

### Esportazioni

Le esportazioni sono disponibili in JSON, TXT e HTML, con diversi temi CSS per i report HTML.

---

## Sicurezza

Omega-Fire agisce su componenti critici del sistema e deve essere usato con prudenza.

- L'avvio richiede privilegi di root tramite `sudo`.
- Il flush, la purga generale e l'applicazione di una politica possono essere distruttivi.
- Una politica predefinita attiva un backup automatico prima della modifica.
- Su iptables / ip6tables, applicare una politica o svuotare un backend cancella anche le regole di altri strumenti (UFW…): Omega-Fire lo segnala e lascia scegliere prima di agire.
- Esegui un backup manuale prima di ogni cambiamento importante.
- Verifica lo stato reale del firewall, dei jail e delle connessioni dopo ogni operazione.
- Prova prima su una macchina o un bersaglio usa e getta.
- Usa le reti di documentazione RFC 5737 per le prove IPv4: `192.0.2.0/24`, `198.51.100.0/24` e `203.0.113.0/24`.
- Verifica le esportazioni e gli snapshot prima di ripristinarli su una macchina di produzione.
- Non concedere alla cartella `var/` permessi più ampi del necessario.

---

## Test e qualità

La suite conta 137 test unitari (oltre 8.000 casi verificati): dominio applicativo, orchestrazione (`application/`), infrastruttura, e le schermate Textual aggiunte o corrette nella 3.5, eseguite con i fogli di stile reali (impaginazione, percorsi completi, lingue delle esportazioni). Questo archivio non contiene la cartella `tests/`: recuperala dal tuo repository di sviluppo se devi eseguirla.

```bash
source .venv/bin/activate
python -m unittest discover -s tests/unit -t .
```

L'architettura a livelli separa rigorosamente il dominio applicativo dalla presentazione (`domain/`, `application/`, `ports/` come `Protocol`, vedi [Architettura](#architettura)): la maggior parte dei test non richiede né root né un firewall reale.

Se contribuisci al progetto, installa gli strumenti di qualità dichiarati (come commento) in `requirements.txt`:

```bash
pip install pytest pytest-cov black flake8 mypy
```

Strumenti disponibili una volta installati:

```bash
black .
flake8 .
mypy src/
pytest --cov
```

---

## Stato del progetto

### Punti operativi

- TUI Textual unificata per i principali meccanismi di sicurezza di rete, moduli convalidati, temi e aiuto contestuale condivisi con la suite OMEGA.
- Interfaccia Rich storica mantenuta come alternativa (`--legacy-cli`).
- Rilevamento automatico delle capacità.
- Gestione dei backend disponibili.
- Supporto IPv4/IPv6 secondo gli strumenti presenti.
- Log applicativo e audit.
- Backup e ripristino.
- Esportazioni JSON, TXT e HTML.
- Dashboard e statistiche, aggiornate in background senza bloccare l'interfaccia.
- Architettura a livelli documentata.

### Limiti noti

- La suite di test copre le schermate Textual della 3.5, non ancora tutte le schermate più vecchie (vedi [Test e qualità](#test-e-qualità)).
- Il meccanismo `ExecutionPlan`/`PipelineStep` resta parzialmente presente nel progetto.
- La disponibilità esatta delle funzionalità dipende dai binari, servizi, permessi e configurazioni della macchina ospite.
- L'interfaccia Rich storica (`--legacy-cli`) non è più l'asse di sviluppo attivo; viene mantenuta il tempo necessario a rendere del tutto affidabile l'interfaccia Textual in condizioni reali.

---

## Disinstallazione

Se i dati sono rimasti nella cartella del progetto:

```bash
sudo rm -rf ~/omega-fire
```

Elimina manualmente i file esportati altrove, gli eventuali alias `fire` aggiunti in `~/.bashrc` o `~/.zshrc`, nonché il gruppo dedicato se non è più utilizzato:

```bash
sudo groupdel omega-fire
```

Esegui quest'ultimo comando solo se nessun altro file o servizio dipende da questo gruppo.

---

## Licenza

Omega-Fire è distribuito con licenza **MIT**. Consulta il file [`LICENSE`](../../../LICENSE) per il testo completo.

---

> **Omega-Fire — Osservare, pilotare, verificare, proteggere.**
>
> Un'interfaccia TUI unificata per nftables, iptables, ip6tables, Fail2Ban, i log e il monitoraggio di rete.
