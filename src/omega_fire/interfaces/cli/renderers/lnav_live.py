# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Rendu live de l'analyse lnav (menu 8.6).

Encapsule lnav dans un pty avec un header/footer Omega-Fire persistants
autour (header/footer à nous, distincts des propres barres internes de
lnav) et interception de touches avant transmission. Mécanisme validé
empiriquement pendant un spike (voir referentiel_violations_actions.md
§87 pour le détail des blocages trouvés et corrigés en cours de route :
négociation de capacités terminal, découpage de séquences d'échappement,
performance du rendu, ordre des arguments de redimensionnement, etc.).

Conforme à la charte d'architecture Omega-Fire :
- Aucune couleur hardcodée -- tout passe par theme_registry.get_style()
- Aucun subprocess ici (délégué à infrastructure/lnav/pty_session.py)
- Rendu en écriture ANSI directe (pas de Rich Live) : un redraw complet
  de l'écran à chaque frame s'est révélé beaucoup trop coûteux sur un
  grand terminal (mesuré : ~900ms sur 271x55) -- on ne redessine que les
  lignes réellement modifiées (pyte.Screen.dirty).
"""
from __future__ import annotations

import base64
import os
import re
import select
import shutil
import signal
import sys
import termios
import time
import tty
from pathlib import Path
from typing import Optional

import pyte
from rich.console import Console

from omega_fire.interfaces.cli.themes.registry import theme_registry
from omega_fire.infrastructure.lnav import (
    TerminalResponder,
    kill_lnav,
    relay_osc52,
    resize_pty,
    spawn_lnav,
)

HEADER_ROWS = 1
FOOTER_ROWS = 3  # séparateur + raccourcis + statut, comme le footer classique de l'appli (renderers/frame.py)

CSI = "\x1b["
ALT_SCREEN_ON = CSI + "?1049h"
ALT_SCREEN_OFF = CSI + "?1049l"
HIDE_CURSOR = CSI + "?25l"
SHOW_CURSOR = CSI + "?25h"
CLEAR_SCREEN = CSI + "2J"

MENU_LABEL = "8.6 Visualiser les logs serveurs (lnav)"

MAX_DRAIN_SECONDS = 0.02  # plafond dur : on rend la main au clavier au
                          # moins toutes les 20ms, même si lnav continue
                          # d'écrire (horloge d'en-tête, curseur...).


def move_to(row: int, col: int = 1) -> str:
    return f"{CSI}{row};{col}H"


def pad_line(text: str, width: int) -> str:
    return text[:width].ljust(width)


# Couleurs de colonnes : lnav colore déjà chaque champ (IP, méthode, statut,
# user-agent...) avec sa propre palette 256/truecolor -- mais on ne reprend
# pas ces couleurs brutes telles quelles (charte : aucune couleur hardcodée,
# tout passe par theme_registry). On classe la couleur native de chaque
# segment dans une petite famille de teintes, puis on réassocie chaque
# famille à un style theme_registry déjà existant. Ça préserve la
# distinction entre colonnes que fait lnav (des couleurs différentes = des
# champs différents) tout en restant intégralement piloté par le thème actif.
_NAMED_HUES = {
    "red": "red", "green": "green", "yellow": "yellow", "blue": "blue",
    "magenta": "magenta", "cyan": "cyan", "white": "neutral", "black": "neutral",
    "default": "neutral",
}

HUE_TO_STYLE = {
    "red": "text.danger",
    "orange": "text.warning",
    "yellow": "text.warning",
    "green": "action.success",
    "cyan": "text.info",
    "blue": "text.link",
    "magenta": "text.heading",
    "neutral": "text.main",
}


def classify_hue(fg: str) -> str:
    """Classe une couleur pyte (nom ou hex 6 caractères) dans une famille
    de teinte grossière, pour la réassocier ensuite à un style theme_registry."""
    if fg in _NAMED_HUES:
        return _NAMED_HUES[fg]
    if len(fg) != 6:
        return "neutral"
    try:
        r, g, b = int(fg[0:2], 16), int(fg[2:4], 16), int(fg[4:6], 16)
    except ValueError:
        return "neutral"
    mx, mn = max(r, g, b), min(r, g, b)
    if mx - mn < 24:
        return "neutral"
    if mx == r and g >= b:
        return "orange" if g > 100 else "red"
    if mx == r:
        return "magenta"
    if mx == g:
        return "yellow" if r > 140 else "green"
    return "cyan" if g > r else "blue"


def chrome_bar_style():
    """Style pour les barres internes de lnav (breadcrumb en haut, barre
    de statut en bas) -- volontairement pas en vidéo inversée brute (bloc
    plein en couleur vive, signalé trop agressif à l'usage), donc fond
    sombre explicite ("bg.header") + texte clair ("text.heading") plutôt
    qu'un simple `reverse`."""
    from rich.style import Style
    bg = theme_registry.get_style("bg.header").color
    return theme_registry.get_style("text.heading") + Style(bgcolor=bg, bold=True)


def compute_baseline_bg(screen: "pyte.Screen", cols: int) -> str:
    """Devine le fond "normal" du contenu de lnav (pas nos barres à nous,
    pas les barres internes lnav, pas la ligne courante), en prenant le
    fond le plus fréquent parmi les cellules non vides de tout l'écran.

    Nécessaire car certains thèmes lnav (ex. "eldar", configuré ici sur
    /root/.config/lnav/config.json sur au moins une machine) peignent un
    fond explicite (ex. noir) sur tout le texte normal, au lieu de laisser
    le fond "default" du terminal comme le fait le thème lnav par défaut.
    Sans ça, `ch.bg != "default"` classe alors CHAQUE ligne de log comme
    "surlignée", écrasant toute la coloration par teinte sous un seul
    style uniforme (constaté : menu 8.6 qui s'affiche en une seule couleur
    sur une machine où root a ce thème lnav actif, alors que la même
    version de lnav/même code fonctionne normalement ailleurs)."""
    counts: dict[str, int] = {}
    for y in range(len(screen.display)):
        row = screen.buffer[y]
        for col in range(cols):
            ch = row.get(col)
            if ch is None or not ch.data or ch.data == " ":
                continue
            counts[ch.bg] = counts.get(ch.bg, 0) + 1
    if not counts:
        return "default"
    return max(counts, key=counts.get)


def render_row_colored(screen: "pyte.Screen", y: int, cols: int, baseline_bg: str = "default") -> str:
    """Construit une ligne ANSI colorée via theme_registry, en regroupant
    les colonnes consécutives qui partagent le même style (même famille de
    teinte + état surligné) en un seul segment stylé.

    Surbrillance des barres internes lnav : détectée via une vraie couleur
    de fond différente à la fois de "default" et du fond de base calculé
    par compute_baseline_bg (le fond du contenu normal, qui varie selon le
    thème lnav actif) -- pas l'attribut ANSI "reverse", vérifié
    empiriquement pendant le spike, lnav n'utilise pas `reverse` pour ça."""
    buffer_row = screen.buffer[y]
    default = screen.default_char
    segments: list[tuple[str, str]] = []
    current_text: list[str] = []
    current_key: Optional[str] = None

    for col in range(cols):
        ch = buffer_row.get(col, default)
        highlighted = ch.reverse or (ch.bg != "default" and ch.bg != baseline_bg)
        key = f"{classify_hue(ch.fg)}|{highlighted}"
        if key != current_key:
            if current_text:
                segments.append(("".join(current_text), current_key))
            current_text = []
            current_key = key
        current_text.append(ch.data if ch.data else " ")
    if current_text:
        segments.append(("".join(current_text), current_key))

    out = []
    for text, key in segments:
        hue, highlighted_s = key.split("|")
        style = chrome_bar_style() if highlighted_s == "True" else theme_registry.get_style(HUE_TO_STYLE[hue])
        out.append(style.render(text))
    return "".join(out)


_BREADCRUMB_ISO_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T(\d{2}:\d{2}:\d{2})")


def extract_current_line_text(screen: "pyte.Screen") -> Optional[str]:
    """Retrouve le texte brut de la ligne actuellement focalisée par lnav.

    lnav a sa propre commande native pour marquer + copier ('m' puis 'c'),
    mais 'c' invoque `xclip -i -selection clipboard` sans jamais fermer le
    tube d'entrée (EOF) -- xclip reste bloqué en attente indéfiniment et
    bloque lnav avec lui (constaté empiriquement pendant cette session,
    reproductible). On copie donc nous-mêmes, sans jamais envoyer 'c' à
    lnav.

    Pas de surbrillance de fond fiable pour repérer "la ligne courante"
    (essayé, s'est avéré être les propres barres de lnav -- voir §88) : le
    breadcrumb de lnav affiche l'horodatage ISO exact de la ligne
    actuellement focalisée ("LOG ▼ : 2026-07-11T04:19:43.000000 : ..."),
    qui correspond toujours à l'horodatage (même heure:minute:seconde)
    affiché en clair sur une des lignes de contenu -- corrélation vérifiée
    empiriquement plusieurs fois pendant le spike, sur différents formats."""
    lines = screen.display
    breadcrumb_idx = None
    hms = None
    for i, line in enumerate(lines):
        m = _BREADCRUMB_ISO_TS_RE.search(line)
        if m and "：" in line:
            breadcrumb_idx = i
            hms = m.group(1)
            break
    if hms is None:
        return None
    for i, line in enumerate(lines):
        if i != breadcrumb_idx and hms in line:
            # "│" en bordure = indicateur de défilement de lnav (jeu de
            # caractères VT100 traduit), pas du contenu -- retiré pour ne
            # copier que le texte de log utile.
            return line.strip().strip("│").strip()
    return None


def osc52_copy(text: str) -> bytes:
    """Séquence OSC 52 : demande au terminal de placer `text` dans le
    presse-papier système. Mécanisme standard (tmux, vim, la plupart des
    émulateurs de terminal modernes le supportent) -- écrite et envoyée
    par nous, jamais via le `c` interne de lnav."""
    b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return f"\x1b]52;c;{b64}\x07".encode()


def render_lnav_live(log_paths: list[Path], console: Optional[Console] = None) -> None:
    """Encapsule lnav sur `log_paths` (fusionnés automatiquement par lnav
    si plusieurs) dans le terminal courant, avec header/footer Omega-Fire
    persistants. Bloquant jusqu'à Ctrl-Q ou fermeture de lnav.

    Doit être appelé depuis un vrai terminal interactif (stdin/stdout un
    tty) -- pas de mode automatisé ici, contrairement au spike qui avait
    un --test dédié pour la validation sans clavier réel."""
    console = console or Console()

    out_fd = sys.stdout.fileno()
    term_cols, term_rows = shutil.get_terminal_size()
    inner_rows = max(term_rows - HEADER_ROWS - FOOTER_ROWS, 5)

    master_fd, pid = spawn_lnav(inner_rows, term_cols, log_paths)
    screen = pyte.Screen(term_cols, inner_rows)
    stream = pyte.Stream(screen)
    # pyte a la table de correspondance VT100 (jeu de caractères spécial
    # "graphiques" -- bordures/traits que lnav dessine) mais l'ignore par
    # défaut en mode UTF-8, en supposant que l'appli enverrait directement
    # les vrais caractères Unicode. lnav utilise encore le changement de
    # charset legacy (ESC ( 0 ... ESC ( B) même en UTF-8. Comme on décode
    # nous-mêmes l'UTF-8 avant de nourrir le stream (jamais de bytes bruts
    # ici), désactiver ce mode ne casse pas les vrais caractères UTF-8.
    stream.use_utf8 = False
    responder = TerminalResponder(master_fd, inner_rows, term_cols)

    baseline_bg = "default"

    stdin_fd = sys.stdin.fileno()
    old_term = termios.tcgetattr(stdin_fd)
    # setraw (pas setcbreak) : cbreak laisse ISIG actif, donc Ctrl-C
    # génèrerait un vrai SIGINT sur notre propre process au lieu d'être
    # transmis en octets à lnav. En raw, toutes les touches, signaux
    # compris, redeviennent de simples octets à transmettre.
    tty.setraw(stdin_fd)

    def draw_chrome(cols: int, rows: int) -> None:
        # Même convention que interfaces/cli/renderers/frame.py : header =
        # titre + thème + contexte, footer = séparateur + raccourcis par
        # segments type "[touche] action". Les barres internes de lnav
        # (breadcrumb, statut) sont traitées à part dans
        # render_row_colored (chrome_bar_style) -- pas de rapport avec ce
        # header/footer à nous, qui encadrent lnav de l'extérieur.
        title_style = theme_registry.get_style("menu.title")
        muted_style = theme_registry.get_style("text.muted")
        heading_style = theme_registry.get_style("text.heading")
        link_style = theme_registry.get_style("text.link")
        border_style = theme_registry.get_style("border.default")

        theme_name = theme_registry.get_active().display_name

        header_plain = f"🛡  OMEGA-FIRE  │  Thème: {theme_name}  │  {MENU_LABEL}"
        header_line = (
            title_style.render("🛡  OMEGA-FIRE")
            + muted_style.render(f"  │  Thème: {theme_name}  │  ")
            + heading_style.render(MENU_LABEL)
            + muted_style.render(" " * max(cols - len(header_plain), 0))
        )

        sep_line = border_style.render("─" * cols)

        shortcuts_plain = (
            "📋 Analyse lnav  │  [↑↓] Naviguer  │  [←→] Défiler  │  [g/G] Début/Fin  │  "
            "[Ctrl-C] Marquer+Copier  │  [t]hème  │  [Ctrl-Q] Quitter"
        )
        shortcuts_line = (
            muted_style.render("📋 Analyse lnav  │  ")
            + link_style.render("[↑↓] Naviguer")
            + muted_style.render("  │  ")
            + link_style.render("[←→] Défiler")
            + muted_style.render("  │  ")
            + link_style.render("[g/G] Début/Fin")
            + muted_style.render("  │  ")
            + link_style.render("[Ctrl-C] Marquer+Copier")
            + muted_style.render("  │  ")
            + link_style.render("[t]hème")
            + muted_style.render("  │  ")
            + link_style.render("[Ctrl-Q] Quitter")
            + muted_style.render(" " * max(cols - len(shortcuts_plain), 0))
        )

        names = ", ".join(p.name for p in log_paths)
        status_line = muted_style.render(pad_line(f"Fichiers ({len(log_paths)}) : {names}", cols))

        buf = (
            move_to(1) + header_line
            + move_to(rows - 2) + sep_line
            + move_to(rows - 1) + shortcuts_line
            + move_to(rows) + status_line
        )
        os.write(out_fd, buf.encode())

    def full_redraw(cols: int, rows: int) -> None:
        nonlocal baseline_bg
        baseline_bg = compute_baseline_bg(screen, cols)
        buf = [CLEAR_SCREEN]
        for y in range(len(screen.display)):
            buf.append(move_to(HEADER_ROWS + 1 + y) + render_row_colored(screen, y, cols, baseline_bg))
        os.write(out_fd, "".join(buf).encode())
        draw_chrome(cols, rows)
        screen.dirty.clear()

    def diff_redraw(cols: int) -> int:
        # Cœur du correctif de performance : ne redessiner que les lignes
        # que pyte a marquées modifiées (screen.dirty), au lieu d'un
        # effacement + redessin complet à chaque frame.
        if not screen.dirty:
            return 0
        display = screen.display  # une seule évaluation : c'est une
                                   # propriété qui recalcule tout l'écran
                                   # à chaque accès, pas une liste mise en
                                   # cache -- l'appeler deux fois par ligne
                                   # dans la boucle a ete la cause d'un
                                   # ralentissement mesuré pendant le spike.
        buf = []
        for y in sorted(screen.dirty):
            if 0 <= y < len(display):
                buf.append(move_to(HEADER_ROWS + 1 + y) + render_row_colored(screen, y, cols, baseline_bg))
        n = len(buf)
        os.write(out_fd, "".join(buf).encode())
        screen.dirty.clear()
        return n

    def handle_resize(signum, frame):
        nonlocal term_cols, term_rows, inner_rows
        term_cols, term_rows = shutil.get_terminal_size()
        inner_rows = max(term_rows - HEADER_ROWS - FOOTER_ROWS, 5)
        # Screen.resize(lines, columns) -- ordre inverse du constructeur
        # Screen(columns, lines), piège déjà rencontré pendant le spike.
        screen.resize(inner_rows, term_cols)
        resize_pty(master_fd, pid, inner_rows, term_cols)
        responder.update_size(inner_rows, term_cols)
        full_redraw(term_cols, term_rows)

    signal.signal(signal.SIGWINCH, handle_resize)

    os.write(out_fd, (ALT_SCREEN_ON + HIDE_CURSOR).encode())
    # Nombre de redraws complets à faire au démarrage avant de basculer sur
    # le diff_redraw léger habituel : au tout premier affichage, lnav n'a
    # souvent rendu qu'un état transitoire (indexation du fichier pas
    # terminée) -- baseline_bg calculé à ce moment-là peut être faux et
    # resterait figé indéfiniment côté diff_redraw sinon (constaté : menu
    # 8.6 qui démarre en monochrome et ne redevient coloré qu'après un
    # redimensionnement, qui force justement un nouveau full_redraw).
    settle_redraws_remaining = 5

    try:
        while True:
            r, _, _ = select.select([master_fd, stdin_fd], [], [], 0.05)

            # Priorité au clavier : on vide tout ce qui est en attente
            # côté stdin d'abord et on le transmet immédiatement, avant
            # même de regarder la sortie de lnav.
            if stdin_fd in r:
                key = os.read(stdin_fd, 4096)

                if b"\x11" in key:  # Ctrl-Q : interceptée, jamais transmise à lnav
                    break

                if b"\x03" in key:
                    # Ctrl-C : interceptée, jamais transmise à lnav telle
                    # quelle. NE JAMAIS envoyer "c" à lnav : sa commande
                    # native de copie invoque `xclip -i -selection
                    # clipboard` sans jamais fermer le tube d'entrée --
                    # xclip reste bloqué indéfiniment et bloque lnav avec
                    # lui (constaté empiriquement, reproductible à chaque
                    # fois). On envoie seulement "m" (marque cosmétique,
                    # sans blocage constaté) et on copie nous-mêmes le
                    # texte de la ligne courante (extract_current_line_text)
                    # via OSC 52, sans jamais passer par lnav pour ça.
                    os.write(master_fd, b"m")
                    current_line = extract_current_line_text(screen)
                    if current_line:
                        os.write(out_fd, osc52_copy(current_line))
                    key = key.replace(b"\x03", b"")

                if b"t" in key:
                    # [t]hème minuscule : même mécanisme que le dashboard
                    # réel (renderers/dashboard.py). Interceptée, jamais
                    # transmise à lnav. Le "T" majuscule N'EST PAS touché
                    # ici et repart tel quel vers lnav : c'est son propre
                    # raccourci natif pour afficher/masquer le temps
                    # écoulé entre les lignes -- lui prendre 't' ET 'T'
                    # aurait bloqué cette fonction native de lnav.
                    themes_list = theme_registry.get_theme_names()
                    if themes_list:
                        current = theme_registry.get_active().name
                        next_idx = (themes_list.index(current) + 1) % len(themes_list) if current in themes_list else 0
                        theme_registry.set_active(themes_list[next_idx], silent=True)
                        full_redraw(term_cols, term_rows)
                    key = key.replace(b"t", b"")

                if key:
                    os.write(master_fd, key)

            if master_fd in r:
                got_data = False
                drain_deadline = time.monotonic() + MAX_DRAIN_SECONDS
                while time.monotonic() < drain_deadline:
                    try:
                        data = os.read(master_fd, 65536)
                    except OSError:
                        data = b""
                    if not data:
                        break
                    got_data = True
                    responder.feed(data)
                    relay_osc52(data, out_fd)
                    stream.feed(data.decode("utf-8", errors="replace"))
                    more, _, _ = select.select([master_fd], [], [], 0.002)
                    if master_fd not in more:
                        break

                if not got_data:
                    break  # pty fermé (lnav a quitté)

                if settle_redraws_remaining > 0:
                    full_redraw(term_cols, term_rows)
                    settle_redraws_remaining -= 1
                else:
                    diff_redraw(term_cols)
    finally:
        os.write(out_fd, (SHOW_CURSOR + ALT_SCREEN_OFF).encode())
        termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_term)
        signal.signal(signal.SIGWINCH, signal.SIG_DFL)
        kill_lnav(pid)
        try:
            os.close(master_fd)
        except OSError:
            pass
