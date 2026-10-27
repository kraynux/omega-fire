<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->

<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-fire.png" alt="Omega-Fire" width="384">
</div>

# 󰦝 OMEGA-FIRE

**Zunifikowane stanowisko zarządzania bezpieczeństwem sieci**

> Opracowane przez **kraynux** dla **Omega-server** 
[https://kraynux.snake-mackarel.ts.net](https://kraynux.snake-mackarel.ts.net)

Oficjalna strona: [OMEGA-FIRE](https://kraynux.snake-mackarel.ts.net/omega-fire/) &nbsp; Podgląd: [Zrzuty ekranu](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/)  

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)
[![Interface](https://img.shields.io/badge/Interface-Textual%20TUI-cyan.svg)](https://github.com/Textualize/textual)

**Języki:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

**Omega-Fire** to aplikacja TUI (Terminal User Interface) w Pythonie zbudowana z użyciem [Textual](https://github.com/Textualize/textual). Zapewnia w terminalu jeden interfejs do administrowania zaporami Linux, Fail2Ban, zbanowanymi adresami, regułami sieciowymi, logami i statystykami systemu.

Interfejs Textual jest domyślnym trybem działania i prowadzi przez menu, walidowane formularze (wszystkie wymagane pola są sprawdzane przed przejściem dalej) i dedykowane ekrany, z motywami, pomocą kontekstową i skrótami klawiaturowymi wspólnymi z resztą pakietu OMEGA (omega-check, omega-deep, omega-stress...). Stary interfejs [Rich](https://github.com/Textualize/rich), sekwencyjny i sterowany wpisywaniem numerów, pozostaje dostępny przez `--legacy-cli` (zobacz [Uruchamianie](#uruchamianie)). 
Podgląd: [Zrzuty ekranu](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/index-2.html)

Projekt jest zaprojektowany zgodnie z zasadami **Clean Architecture**, z wyraźnym podziałem na domenę biznesową, orkiestrację, infrastrukturę i interfejs użytkownika.

## Spis treści

- [Prezentacja](#prezentacja)
- [Funkcje](#funkcje)
- [Architektura](#architektura)
- [Wymagania](#wymagania)
- [Instalacja](#instalacja)
- [Użytkowanie](#użytkowanie)
- [Konfiguracja](#konfiguracja)
- [Backendy i zgodność](#backendy-i-zgodność)
- [Trwałość, logi i eksporty](#trwałość-logi-i-eksporty)
- [Bezpieczeństwo](#bezpieczeństwo)
- [Testy i jakość](#testy-i-jakość)
- [Stan projektu](#stan-projektu)
- [Odinstalowanie](#odinstalowanie)
- [Licencja](#licencja)

---

## Prezentacja

Omega-Fire działa jako **lokalne stanowisko dowodzenia** bezpieczeństwem sieci. Automatycznie wykrywa komponenty obecne na maszynie i dostosowuje menu do rzeczywiście dostępnych możliwości.

### Cele

- Połączyć nftables, iptables, ip6tables i Fail2Ban w spójnym interfejsie.
- Ułatwić obserwację połączeń, banów i zdarzeń systemowych oraz działanie na nich.
- Scentralizować eksporty, kopie zapasowe, audyty i historię operacji.
- Zachować testowalną i rozszerzalną architekturę.
- Działać w trybie ograniczonym, gdy brakuje opcjonalnego komponentu.

### Co robi Omega-Fire

- Wykrywa dostępne backendy, usługi, jądro i narzędzia.
- Administruje nftables, iptables i ip6tables, gdy te komponenty są obecne.
- Zarządza zbanowanymi adresami IP, pojedynczo lub partiami, z importem, eksportem, synchronizacją i flushem.
- Tworzy, wyświetla i usuwa zaawansowane reguły.
- Stosuje predefiniowane polityki z wcześniejszą automatyczną kopią zapasową.
- Administruje jailami Fail2Ban i ich banami.
- Analizuje logi na żywo lub w formie statystyk.
- Zapewnia nadzór w formie monitoringu.
- Używa conntrack do wyświetlania aktywnych połączeń, gdy jest dostępny.
- Tworzy eksporty JSON, TXT i HTML.
- Wykonuje kopię zapasową i przywraca pełny stan w archiwach `.tar.gz`.
- Rejestruje operacje w logu aplikacji i w strukturalnym audycie JSON.
- Monitoruje wykryte usługi i aplikacje: systemd, runit, OpenRC, Docker, serwery, VNC itd.

### Czego projekt nie robi

- Nie zastępuje nftables, iptables ani Fail2Ban.
- Nie jest samodzielną zaporą niezależną od systemu.
- Nie zapewnia uwierzytelniania wielu użytkowników.
- W normalnym działaniu nie udostępnia sieciowego API.
- Nie jest dashboardem webowym.
- Nie chroni bezpośrednio zdalnej maszyny z innej maszyny.
- Domyślnie nie instaluje żadnego pliku poza własnym katalogiem.
- Nie gwarantuje dostępności wszystkich backendów we wszystkich dystrybucjach.

---

## Funkcje

### 1. Możliwości i diagnostyka

- Wyświetlanie rejestru wykrytych możliwości.
- Szczegółowy podgląd możliwości według identyfikatora.
- Ręczne ponowne skanowanie systemu po instalacji komponentu.
- Przegląd ostatnich diagnostyk.
- Przegląd i wyszukiwanie w logu aplikacji.
- Eksport stanu i diagnostyki do JSON, TXT lub HTML.

### 2. Zunifikowane zarządzanie adresami IP

Zunifikowana czarna lista pozwala pracować z nftables i iptables z jednego ekranu.

- Banowanie adresu IP lub listy adresów IP.
- Odbanowanie pojedyncze lub partiami.
- Bezpośrednie wpisanie lub import z pliku.
- Lista według backendu lub widok zunifikowany.
- Synchronizacja między backendami NFTables/IPTables.
- Eksport i ponowny import list.
- Pełne czyszczenie jednego lub kilku backendów.
- Obsługa IPv4 i IPv6.
- Zarządzanie plikami blocklisty (`var/blocklist/`) i ich przypięciami bezpośrednio z dedykowanego ekranu.

### 3. Zarządzanie regułami i politykami

- Kreator krok po kroku do tworzenia zaawansowanej reguły.
- Lista reguł systemowych i reguł utworzonych przez Omega-Fire.
- Usuwanie reguły przez zaznaczenie.
- Automatyczne czyszczenie nieaktywnych reguł w bazie referencyjnej.
- Stosowanie predefiniowanych polityk.
- Automatyczna kopia zapasowa przed zastosowaniem polityki.
- Dostosowanie, zapis i przywracanie polityki.
- Oznaczenie aktywnej polityki w menu statusu i na dashboardzie.
- Oznaczanie zmodyfikowanych profili w postaci `Profil + CUSTOM`.
- Zarządzanie tabelami (menu 3.5): diagnostyka tylko do odczytu dla każdego backendu (obecność tabeli, polityki input/output/forward, liczba reguł) z wykrywaniem rozbieżności między backendami.
- Inicjalizacja tabeli nftables przy pierwszym użyciu, bez nadpisywania już skonfigurowanego łańcucha.
- Przywrócenie polityk łańcuchów do ACCEPT w backendzie, aby poprawić osieroconą restrykcyjną politykę pozostawioną przez wcześniejszy profil.
- Celowane opróżnienie jednego backendu lub zsynchronizowane opróżnienie wszystkich wykrytych backendów jedną akcją.
- Pełne usunięcie tabeli nftables (akcja zaawansowana, wykraczająca poza same reguły).

### 4. Zarządzanie Fail2Ban

- Szczegółowy stan jaili i ich parametrów.
- Liczba zbanowanych adresów IP i informacje o rate-limit.
- Wyszukiwanie adresu IP w jailach.
- Ban i unban pojedynczy lub wielokrotny.
- Przenoszenie adresów IP między jailami, backendami i plikami.
- Prowadzone tworzenie własnego jaila.
- Predefiniowane szablony jaili.
- Usunięcie jaila.
- Opróżnienie jaila lub ogólne czyszczenie.
- Eksport do JSON, TXT lub HTML.
- Weryfikacja i audyt konfiguracji.
- Sterowanie usługą: status, start, stop, restart, włączenie i wyłączenie przy starcie systemu.

### 5. Logi i konserwacja

- Live Tail z dashboardem Omega-Fire.
- Wyświetlanie wielu plików z przypięciami (ulubione źródła, zapamiętywane między uruchomieniami).
- Integracja `lnav`: wybór jednego lub kilku plików (numery lub ręczne ścieżki oddzielone przecinkami), automatyczne scalenie w jeden widok chronologiczny, osadzony w nagłówku/stopce Omega-Fire (zobacz [Nawigacja](#nawigacja)).
- Analiza najczęstszych adresów IP z Top N.
- Celowane usunięcie adresu IP z plików LOG lub TXT.
- Rotacja oraz natychmiastowe lub zautomatyzowane kopie zapasowe.
- Przywracanie kopii zapasowej.
- Czyszczenie według wieku, limitu, typu lub ręcznego wyboru.
- Zaawansowane czyszczenie według katalogu lub środowiska.
- Statystyki z 24 godzin, 7 dni lub 30 dni.
- Analiza zdarzeń, ruchów, limitów i adresów IP obecnych w jailach.

### 6. Eksporty i raporty

Dostępne formaty:

- **JSON**: dane strukturalne i wielokrotnego użytku.
- **TXT**: format surowy lub dostosowany do wstrzykiwania.
- **HTML**: czytelny i wizualny raport.

Dostępne raporty:

- Pełna czarna lista.
- Strukturalny ruleset.
- Reguły wybrane według pochodzenia: systemowe, Omega-Fire lub aktywne.
- Pełny raport z audytu.
- Statystyki Fail2Ban.
- Stan i diagnostyka systemu.
- Raporty statystyczne z 7 lub 30 dni.

Motywy HTML:

- `omega-base` — granat i cyjan, motyw domyślny.
- `omega-burn` — czerwono-pomarańczowy żar.
- `omega-neon` — cyberpunk w cyjanie i magencie.
- `light-basic` — jasny i stonowany.
- `light-alt` — kremowy papier i leśna zieleń.

### 7. System i trwałość

- Kopia zapasowa pełnego stanu: reguły, bany nftables, bany iptables i Fail2Ban.
- Tworzenie archiwów `.tar.gz` ze znacznikiem czasu.
- Lista i przywracanie snapshotów.
- Historia działań.
- Filtrowanie i czyszczenie historii.
- Przeładowanie konfiguracji i ponowne skanowanie bez restartu.

### 8. Monitoring i statystyki

- Dashboard w czasie rzeczywistym z okresowym odświeżaniem (co 2 sekundy), bez blokowania interfejsu podczas zbierania danych.
- Wizualizacja aktywnej polityki.
- Aktywne połączenia przez conntrack.
- Ruch, zdarzenia, statystyki i logi serwera.
- Skonsolidowane raporty z 7 i 30 dni.
- Eksport HTML snapshotów i raportów.

### 9. Ustawienia

- Wybór aktywnego motywu spośród dziesięciu motywów `omega-*` wspólnych z resztą pakietu (zobacz [Motywy i terminale](#motywy-i-terminale)), zapamiętywany między uruchomieniami.
- Ręczne nadpisanie profilu renderowania (automatyczny, pełny, standardowy, ograniczony lub tylko mono), stosowane przy następnym uruchomieniu.
- Dostępne z menu głównego (`9. RÉGLAGES`) lub bezpośrednio klawiszem `s`.

---

## Architektura

```text
src/omega_fire/
├── app/              Bootstrap i kontener wstrzykiwania zależności
├── core/             Możliwości, wyliczenia i wyjątki
├── domain/           Czysta logika biznesowa: reguły, IP, jaile, logi
├── application/      Orkiestracja: commands i queries
├── infrastructure/   Backendy, przechowywanie, eksporty, logi i sondy systemowe
├── ports/            Kontrakty Protocol/ABC
├── interfaces/       interfaces/tui/ (Textual, domyślny) + interfaces/cli/ (Rich, --legacy-cli)
├── plugins/          Wbudowane rozszerzenia: nftables, iptables, Fail2Ban, conntrack
└── shared/           Parsowanie, sieć, formatowanie i narzędzia przekrojowe
```

### Zasady projektowe

- `domain/` nie zawiera ani I/O, ani zależności od infrastruktury.
- `application/` orkiestruje przypadki użycia przez domenę i porty — ekrany Textual i akcje interfejsu Rich wywołują te same commands/queries, a logika biznesowa nie zależy od żadnego z dwóch interfejsów.
- `infrastructure/` jest jedyną warstwą uprawnioną do wywoływania `nft`, `iptables`, `fail2ban-client` i innych narzędzi zewnętrznych (subprocess, pty, pliki).
- `interfaces/` nie może bezpośrednio wywoływać `subprocess`.
- `ports/` definiuje kontrakty oczekiwane przez adaptery.
- `core/` dostarcza rejestr możliwości używany przez różne warstwy.
- Pluginy pozwalają dodawać lub rozwijać backendy bez zmieniania domeny biznesowej.
- Interfejs Textual (`interfaces/tui/`) opiera się na [`omega-lib`](https://github.com/) (zależność współdzielona przez cały pakiet OMEGA: motyw z 9 tokenami, wykrywanie terminala, wspólne kontrakty portów), nieopublikowanej w PyPI — dołączonej do archiwum dystrybucyjnego (`vendor/omega-lib/`, zobacz [Instalacja](#instalacja)).
- Każde potencjalnie wolne wywołanie (backend zapory, `fail2ban-client`, dysk) uruchomione z ekranu Textual działa w tle (wątek), nigdy w głównym wątku interfejsu — dashboard lub formularz pozostaje responsywny podczas operacji, zamiast zamrażać całą aplikację.

### Struktura danych

Omega-Fire używa SQLite przez standardową bibliotekę `sqlite3`, bez zewnętrznego ORM. Główne zbiory danych dotyczą banów, reguł, zdarzeń audytu i snapshotów.

Migracje są wersjonowane i stosowane automatycznie przy starcie.

---

## Wymagania

### System

- Linux, przede wszystkim Arch Linux i zgodne dystrybucje.
- Python 3.10 lub nowszy.
- Uprawnienia roota dostępne przez `sudo`.
- Menedżer usług: systemd, runit lub OpenRC.
- Co najmniej jeden backend zapory: nftables lub iptables.
- Terminal o rozmiarze co najmniej 80x24 (zobacz [Motywy i terminale](#motywy-i-terminale), aby poznać szczegóły profili renderowania zależnie od dostępnego rozmiaru).

### Zależności Pythona

Zależności produkcyjne są zdefiniowane w `requirements.txt`:

- `textual` — domyślny interfejs TUI.
- `omega-lib` — motyw, wykrywanie terminala i kontrakty współdzielone z pakietem OMEGA (nieopublikowana w PyPI, zobacz [Architektura](#architektura) i [Instalacja](#instalacja)).
- `rich` — renderowanie interfejsu `--legacy-cli` i niektórych raportów.
- `psutil` — informacje o systemie (CPU, pamięć, sieć, procesy) dla dashboardu i diagnostyki.
- `jinja2` — generowanie eksportów HTML.
- `python-dotenv` — zmienne środowiskowe.
- `pyte` — wirtualny emulator terminala do osadzania `lnav` (menu 5.9/8.6).

Narzędzia jakości (`pytest`, `black`, `flake8`, `mypy`) są wymienione w komentarzu w `requirements.txt`: odkomentuj je lub zainstaluj osobno, jeśli współtworzysz projekt (zobacz [Testy i jakość](#testy-i-jakość)).

### Zalecane narzędzia opcjonalne

Aplikacja działa w trybie ograniczonym, jeśli tych narzędzi brakuje:

- `fail2ban` — automatyczne banowanie.
- `conntrack` lub `conntrack-tools` — aktywne połączenia i statystyki sieciowe.
- `lnav` — zaawansowana analiza logów z wielu plików.

W Arch Linux i pochodnych:

```bash
sudo pacman -S fail2ban conntrack-tools lnav
```

---

## Instalacja

Oficjalne archiwum jest dostarczane w formacie `.tar.gz`. Przed instalacją sprawdź jego integralność:

```bash
sha256sum omega-fire.tar.gz
```

> ⚠️ **Te trzy metody służą do pierwszej instalacji.** Jeśli `~/omega-fire` już istnieje (aktualizacja poprzedniej wersji), użyj sekcji [Aktualizacja](#aktualizacja) poniżej — nigdy nie uruchamiaj tych poleceń ponownie z wnętrza istniejącego katalogu `omega-fire`: `tar` próbowałby utworzyć zagnieżdżony `omega-fire/omega-fire/` i zakończyłby się błędami uprawnień, jeśli ten katalog należy do roota (częste, gdy wcześniejsze rozpakowanie zostało przez pomyłkę wykonane z `sudo tar`).

### Metoda 1 — skrypt instalacyjny

```bash
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Wygląda na to, że jesteś już w katalogu omega-fire — zobacz sekcję Aktualizacja w README." >&2; exit 1; }
[ -d omega-fire ] && echo "ℹ️ Już tu rozpakowano, krok pominięty." || tar -xzf omega-fire.tar.gz
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire już istnieje, przeniesienie pominięte." || mv omega-fire ~/
cd ~/omega-fire/
chmod +x install.sh
./install.sh
```

Uruchamianie:

```bash
./omega-fire.sh
```

Jeśli alias został zainstalowany, otwórz nowy terminal i użyj:

```bash
fire
```

### Metoda 2 — odporna pełna instalacja

To polecenie można uruchomić ponownie: pomija już wykonane kroki.

```bash
([ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Wygląda na to, że jesteś już w katalogu omega-fire — zobacz sekcję Aktualizacja w README." >&2; exit 1; }; [ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire już istnieje, rozpakowanie pominięte." || (tar -xzf omega-fire.tar.gz && mv omega-fire ~/)) && cd ~/omega-fire/ && ([ -d .venv ] && echo "ℹ️ .venv już istnieje, krok pominięty." || python3 -m venv .venv) && source .venv/bin/activate && ([ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib || true) && pip install -r requirements.txt && chmod +x omega-fire.sh && mkdir -p var && (getent group omega-fire >/dev/null 2>&1 && echo "ℹ️ Grupa omega-fire już istnieje." || sudo groupadd omega-fire) && (groups "$USER" 2>/dev/null | grep -qw omega-fire && echo "ℹ️ $USER jest już członkiem grupy omega-fire." || sudo usermod -aG omega-fire "$USER") && sudo chgrp -R omega-fire var && sudo chmod -R 2775 var && echo "✅ Omega-Fire zainstalowany. Uruchom ./omega-fire.sh."
```

### Metoda 3 — szczegółowa instalacja

```bash
# 0. Sprawdzić, że nie uruchamiamy z wnętrza istniejącego omega-fire
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Wygląda na to, że jesteś już w katalogu omega-fire — zobacz sekcję Aktualizacja w README." >&2; exit 1; }

# 1. Rozpakować
[ -d omega-fire ] && echo "ℹ️ Już tu rozpakowano, krok pominięty." || tar -xzf omega-fire.tar.gz

# 2. Przenieść do katalogu domowego
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire już istnieje, przeniesienie pominięte." || mv omega-fire ~/

# 3. Wejść do projektu
cd ~/omega-fire/

# 4. Utworzyć środowisko wirtualne
[ -d .venv ] && echo "ℹ️ .venv już istnieje, tworzenie pominięte." || python3 -m venv .venv

# 5. Zainstalować zależności (dołączona omega-lib, jeśli obecna, przed requirements.txt)
source .venv/bin/activate
[ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib
pip install -r requirements.txt

# 6. Nadać uprawnienia wykonywania programowi startowemu
chmod +x omega-fire.sh

# 7. Przygotować var/ dla roota i bieżącego użytkownika
mkdir -p var
getent group omega-fire >/dev/null 2>&1 || sudo groupadd omega-fire
groups "$USER" 2>/dev/null | grep -qw omega-fire || sudo usermod -aG omega-fire "$USER"
sudo chgrp -R omega-fire var
sudo chmod -R 2775 var

# 8. Uruchomić
./omega-fire.sh
```

`vendor/omega-lib/` jest obecna tylko w oficjalnym archiwum (`build-release.sh` dołącza ją automatycznie, ponieważ omega-lib nie jest opublikowana w PyPI); w klonie deweloperskim zainstaluj ją osobno z jej własnego repozytorium (`pip install -e sciezka/do/omega-lib`).

Dedykowana grupa i bit `setgid` pozwalają rootowi i użytkownikowi współdzielić pliki tworzone w `var/` bez otwierania uprawnień dla całego systemu. Może być potrzebne ponowne zalogowanie lub `newgrp omega-fire`, aby od razu korzystać z przynależności do grupy.

### Aktualizacja

Jeśli `~/omega-fire` już istnieje (poprzednia instalacja), **nigdy nie uruchamiaj ponownie poleceń instalacyjnych z wnętrza tego katalogu**: `tar` próbowałby utworzyć zagnieżdżony `omega-fire/omega-fire/` i zakończyłby się niepowodzeniem, zwykle kaskadą błędów « Brak dostępu », jeśli katalog należy do `root` (częste, gdy wcześniejsze rozpakowanie zostało przez pomyłkę wykonane z `sudo tar`).

Zalecana procedura, z dowolnego katalogu **innego niż `~/omega-fire`** (zwykle z samego `~`):

```bash
# 1. Sprawdzić stan i właściciela istniejącej instalacji
ls -ld ~/omega-fire

# 2. Odłożyć starą instalację na bok zamiast ją nadpisywać
sudo mv ~/omega-fire ~/omega-fire.old-$(date +%Y%m%d)

# 3. Rozpakować nowe archiwum bezpośrednio do katalogu domowego
tar -xzf omega-fire.tar.gz -C ~/

# 4. Zainstalować ponownie (odtwarza venv, ponownie instaluje zależności, ponownie ustawia uprawnienia var/)
cd ~/omega-fire
chmod +x install.sh
./install.sh

# 5. Uruchomić
./omega-fire.sh
```

Krok 4 (`./install.sh`) automatycznie wykrywa taką sytuację (brak bazy danych `var/db/` tutaj, katalog `~/omega-fire.old-RRRRMMDD` znaleziony tuż obok) i **sam odzyskuje** `config/omega-fire.conf`, bazę danych, blocklistę, kopie zapasowe, eksporty i zrzuty ekranu ze starej instalacji — bez pytań, bez ręcznych kroków. Poza punktami od 1 do 5 powyżej nie trzeba nic więcej robić, niezależnie od tego, co zawierała Twoja poprzednia instalacja.

Jeśli obok leży kilka katalogów przypominających starą instalację (niejednoznaczność), `install.sh` niczego nie zgaduje: wyświetla ich ścieżki i zachęca do samodzielnego uruchomienia `sudo ./migrate-state.sh <katalog>` po ustaleniu właściwego źródła.

Po zatwierdzeniu nowej instalacji stary katalog `~/omega-fire.old-RRRRMMDD` można usunąć (`sudo rm -rf ~/omega-fire.old-RRRRMMDD`).

### Alias Bash lub Zsh

```bash
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.bashrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.bashrc
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.zshrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.zshrc
```

Następnie przeładuj powłokę:

```bash
source ~/.bashrc 2>/dev/null || source ~/.zshrc
```

### Ikony i symbole Nerd Fonts

Jeśli ikony nie są dostępne, zainstaluj symbole Nerd Fonts:

```bash
mkdir -p ~/.local/share/fonts
curl -fLo /tmp/NerdFontsSymbolsOnly.zip \
  https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip
unzip -o /tmp/NerdFontsSymbolsOnly.zip -d ~/.local/share/fonts
fc-cache -fv
```

---

## Użytkowanie

### Uruchamianie

```bash
cd ~/omega-fire
./omega-fire.sh

# lub po prostu, jeśli alias został utworzony:
fire
```

Program startowy:

1. Sprawdza uprawnienia roota i w razie potrzeby uruchamia się ponownie przez `sudo`.
2. Wykrywa `.venv`, `venv` lub systemowy Python.
3. Ustawia `PYTHONPATH` na `src/`.
4. Uruchamia `python -m omega_fire` — domyślnie interfejs **Textual**.

Aby zamiast tego uruchomić stary interfejs Rich (sekwencyjne wpisywanie numerów):

```bash
./omega-fire.sh --legacy-cli
```

### Ogólny przebieg

1. Ekran startowy (splash), a następnie ostrzeżenie, jeśli terminal jest za mały.
2. Wykrywanie możliwości systemu (dedykowany, nieblokujący ekran).
3. Menu główne: 8 sekcji tematycznych (1-8) oraz ustawienia (9).
4. Wybór sekcji, a następnie akcji — każda akcja otwiera formularz, którego wszystkie wymagane pola są walidowane przed przejściem dalej.
5. Wyraźne potwierdzenie przed każdą wrażliwą lub destrukcyjną operacją (flush, czyszczenie, przywracanie...).
6. Wykonywanie wolnych operacji w tle (interfejs pozostaje użyteczny podczas oczekiwania), a następnie powrót do menu z podsumowaniem wyniku.

### Nawigacja

- Strzałki w górę/w dół: przesuwanie kursora po liście lub menu.
- Tab / Shift+Tab: przechodzenie między polami formularza.
- Enter: wybór lub zatwierdzenie.
- Kliknięcie wiersza tabeli: zaznacza go i wstępnie wypełnia odpowiednie pola (źródło do przypięcia, docelowy jail itd.).
- `Esc`: powrót do poprzedniego ekranu (na ekranie głównym prosi o potwierdzenie wyjścia).
- `a`: pomoc kontekstowa — opisuje bieżącą akcję albo wszystkie akcje bieżącej sekcji, jeśli żaden ekran akcji nie jest jeszcze otwarty.
- `t`: przejście do następnego motywu, bez potwierdzenia.
- `r`: ponowne wykrycie rozmiaru i rodziny terminala.
- `s`: otwarcie ustawień (motyw, profil renderowania).
- `q` / `Ctrl+Q`: wyjście, z potwierdzeniem.

#### Szczególne cechy ekranu lnav (5.9 / 8.6)

`lnav` jest osadzony w pseudoterminalu z trwałym nagłówkiem/stopką Omega-Fire wokół własnego widoku, aby uniknąć kolizji między jego natywnymi skrótami a skrótami Omega-Fire:

- Strzałki ↑↓: nawigacja po logach (natywny skrót `lnav`, przekazywany bez zmian).
- Strzałki ←→: przewijanie w poziomie długich wierszy (natywny skrót `lnav`).
- `g` / `G`: przejście na początek / koniec (natywny skrót `lnav`).
- `Ctrl+C`: zaznaczenie bieżącego wiersza i skopiowanie go do schowka systemowego (zastępuje natywne polecenie kopiowania `lnav`, które na niektórych systemach może się zawieszać).
- małe `t`: następny motyw, tylko dla tego widoku (wielkie `T` pozostaje natywnym skrótem `lnav` do wyświetlania czasu między wierszami).
- `Ctrl+Q`: powrót do Omega-Fire (poprawnie zamyka `lnav`, bez wychodzenia z aplikacji).

---

## Motywy i terminale

Dziesięć motywów `omega-*` jest wspólnych z resztą pakietu OMEGA:

```text
omega-base       omega-dark       omega-light
omega-neon       omega-burn       omega-pink
omega-hack       omega-contrast   omega-mono
omega-minimal
```

- Przełączaj motywy klawiszem `t` lub wybierz jeden bezpośrednio w ustawieniach (`s`).
- Wybrany motyw jest zapamiętywany i przywracany przy następnym uruchomieniu.
- Omega-Fire automatycznie dostosowuje złożoność wizualną (ramki, splash, gęstość informacji) do wykrytego terminala za pomocą **profilu renderowania**: Pełny, Standardowy, Ograniczony lub Mono (tylko ASCII). Profil można ręcznie nadpisać w ustawieniach.

| Minimalny rozmiar | Profil | Typowe terminale |
|---|---|---|
| 120×32 lub więcej | Pełny | Ghostty, Alacritty, WezTerm, Kitty |
| 100×28 lub więcej | Standardowy | Konsole, GNOME Terminal, Terminator, xfce4-terminal |
| 80×24 lub więcej | Ograniczony | urxvt, xterm, nowoczesny SSH |
| poniżej 80×24 | Mono (tylko ASCII) | Linux TTY, stary SSH |

Poniżej 80×24 uruchomienie jest odrzucane (wymagany minimalny rozmiar); zmień rozmiar terminala i uruchom ponownie albo użyj `r` po zmianie rozmiaru, jeśli wyświetlanie nie odświeżyło się automatycznie.

---

## Konfiguracja

Konfigurację szczegółową można dostosować w:

```text
omega-fire/config/omega-fire.conf
```

Może ona określać w szczególności:

- ścieżki logów;
- serwery i źródła monitoringu;
- dostępne backendy lub własne ścieżki;
- środowiska do analizy;
- parametry dostosowane do konkretnej instalacji.

Konfiguracja jest odczytywana ponownie przy restarcie lub podczas ręcznego ponownego skanowania (menu 1.3 lub 7.4).

Ten plik jest całkowicie opcjonalny (aplikacja działa bez niego normalnie, korzystając ze zmiennych środowiskowych) i **wyłączony z archiwum dystrybucyjnego** — aktualizacja nigdy go po cichu nie nadpisuje, a `install.sh` w razie potrzeby sam automatycznie odzyskuje go ze starej instalacji (zobacz « Aktualizacja » wyżej).

### Ścieżki wewnętrzne i ścieżki systemowe

Domyślnie Omega-Fire pracuje we własnym katalogu:

```text
var/exports/       # katalog wewnątrz projektu
/var/exports/      # bezwzględna ścieżka systemowa
```

Początkowy `/` ma więc znaczenie. Importy i eksporty do systemu muszą być wyraźnie zlecone przez użytkownika.

---

## Backendy i zgodność

Omega-Fire wykrywa komponenty i włącza tylko funkcje możliwe do użycia.

| Komponent | Rola | Status |
|---|---|---|
| nftables | Nowoczesna zapora IPv4/IPv6 | Zalecany |
| iptables | Zapora IPv4 | Zgodny |
| ip6tables | Zapora IPv6 z iptables | Zgodny, jeśli dostępny |
| Fail2Ban | Jaile i automatyczne bany | Opcjonalny |
| conntrack | Aktywne połączenia | Opcjonalny |
| lnav | Zaawansowana analiza logów | Opcjonalny |
| systemd, runit, OpenRC | Zarządzanie usługami | Automatyczne wykrywanie |
| Docker, VNC, serwery | Wykryte aplikacje i usługi | Zależnie od instalacji |

### IPv4 i IPv6

Obie rodziny adresów są obsługiwane przez zgodne backendy:

- nftables: IPv4 i IPv6 w trybie dual stack;
- iptables/ip6tables: zależnie od dostępnych plików binarnych;
- Fail2Ban: zależnie od konfiguracji jaila i systemu.

Długie, skrócone, lokalne, mieszane formaty IPv6, z zerami i w notacji CIDR są obsługiwane przez odpowiednie komponenty.

---

## Trwałość, logi i eksporty

### Trwałość

- SQLite przez `sqlite3`.
- Tabele dotyczące banów, reguł, audytów i snapshotów.
- Wersjonowane migracje stosowane automatycznie.
- Archiwa pełnego stanu w formacie `.tar.gz`.
- Przypięcia (ulubione źródła logów) i ostatnia historia zapisywane w JSON (`var/runtime/`), przetrwają restart.

### Logi

- Tekstowy log aplikacji: `var/logs/app.log`.
- Strukturalny log audytu JSON zawierający m.in. `event_type`, `actor`, `action`, `result` i `details`.

### Eksporty

Eksporty są dostępne w JSON, TXT i HTML, z kilkoma motywami CSS dla raportów HTML.

---

## Bezpieczeństwo

Omega-Fire działa na krytycznych komponentach systemu i należy go używać ostrożnie.

- Uruchomienie wymaga uprawnień roota przez `sudo`.
- Flush, ogólne czyszczenie i zastosowanie polityki mogą być destrukcyjne.
- Predefiniowana polityka uruchamia automatyczną kopię zapasową przed zmianą.
- Przed każdą istotną zmianą wykonaj ręczną kopię zapasową.
- Po każdej operacji sprawdzaj rzeczywisty stan zapory, jaili i połączeń.
- Najpierw testuj na maszynie lub celu jednorazowego użytku.
- Do testów IPv4 używaj sieci dokumentacyjnych RFC 5737: `192.0.2.0/24`, `198.51.100.0/24` i `203.0.113.0/24`.
- Sprawdzaj eksporty i snapshoty przed przywróceniem ich na maszynie produkcyjnej.
- Nie nadawaj katalogowi `var/` szerszych uprawnień niż to konieczne.

---

## Testy i jakość

Projekt ma historyczny zestaw 152 testów jednostkowych, napisany przed migracją do Textual: obejmuje domenę biznesową, orkiestrację (`application/`), infrastrukturę i interfejs Rich (`interfaces/cli/`), ale **nie obejmuje jeszcze `interfaces/tui/`** (domyślnego interfejsu Textual). To archiwum nie zawiera katalogu `tests/`: pobierz go z repozytorium deweloperskiego, jeśli chcesz go uruchomić.

```bash
source .venv/bin/activate
python -m unittest discover tests/unit -v
```

Ponieważ architektura warstwowa ściśle oddziela domenę biznesową od prezentacji (`domain/`, `application/`, `ports/` jako `Protocol`, zobacz [Architektura](#architektura)), ten zestaw pozostaje ważny bez zmian mimo migracji: jedynie nowszy interfejs Textual nie ma jeszcze własnego pokrycia testami.

Jeśli współtworzysz projekt, zainstaluj narzędzia jakości zadeklarowane (w komentarzu) w `requirements.txt`:

```bash
pip install pytest pytest-cov black flake8 mypy
```

Narzędzia dostępne po instalacji:

```bash
black .
flake8 .
mypy src/
pytest --cov
```

---

## Stan projektu

### Elementy działające

- Zunifikowany TUI Textual dla głównych mechanizmów bezpieczeństwa sieci, walidowane formularze, motywy i pomoc kontekstowa wspólne z pakietem OMEGA.
- Historyczny interfejs Rich zachowany jako rozwiązanie zapasowe (`--legacy-cli`).
- Automatyczne wykrywanie możliwości.
- Zarządzanie dostępnymi backendami.
- Obsługa IPv4/IPv6 zależnie od obecnych narzędzi.
- Logowanie aplikacji i audyt.
- Kopia zapasowa i przywracanie.
- Eksporty JSON, TXT i HTML.
- Dashboard i statystyki odświeżane w tle bez blokowania interfejsu.
- Udokumentowana architektura warstwowa.

### Znane ograniczenia

- Zestaw testów (152) nie obejmuje jeszcze interfejsu Textual (`interfaces/tui/`), napisanego po nim (zobacz [Testy i jakość](#testy-i-jakość)).
- Mechanizm `ExecutionPlan`/`PipelineStep` jest częściowo nadal obecny w projekcie.
- Dokładna dostępność funkcji zależy od plików binarnych, usług, uprawnień i konfiguracji maszyny hosta.
- Historyczny interfejs Rich (`--legacy-cli`) nie jest już osią aktywnego rozwoju; jest zachowany, dopóki interfejs Textual nie stanie się w pełni niezawodny w rzeczywistych warunkach.

---

## Odinstalowanie

Jeśli dane pozostały w katalogu projektu:

```bash
sudo rm -rf ~/omega-fire
```

Usuń ręcznie pliki wyeksportowane gdzie indziej, ewentualne aliasy `fire` dodane w `~/.bashrc` lub `~/.zshrc`, a także dedykowaną grupę, jeśli nie jest już używana:

```bash
sudo groupdel omega-fire
```

Wykonaj to ostatnie polecenie tylko wtedy, gdy żaden inny plik ani usługa nie zależy od tej grupy.

---

## Licencja

Omega-Fire jest rozpowszechniany na licencji **MIT**. Pełny tekst znajdziesz w pliku [`LICENSE`](../../../LICENSE).

---

> **Omega-Fire — Obserwować, sterować, audytować, zabezpieczać.**
>
> Zunifikowany interfejs TUI dla nftables, iptables, ip6tables, Fail2Ban, logów i monitoringu sieci.
