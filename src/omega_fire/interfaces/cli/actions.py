# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Actions for Omega-Fire CLI menus.

Bridges the interface (interfaces/cli/) to the application use cases (application/).
Each action is a callable that:
- Receives a context (registry, console, container, etc.)
- Calls an application/ use case
- NEVER calls backends directly (respects the charter)
- Uses renderers for display (dashboard, tables, logs_live, monitoring_live)

Conforms to Omega-Fire architecture charter:
- No business logic in the UI
- No direct backend calls
- Uses application/ use cases via ports/
- Uses renderers for display
"""
from __future__ import annotations
import time
import shutil
import ipaddress
import os
import json
from datetime import datetime
from typing import Any, Callable, Optional, List, Tuple
from rich.console import Console, Group
from rich.panel import Panel
from rich import box
from rich.table import Table
from rich.text import Text

from omega_fire.core.capability_registry import CapabilityRegistry
from omega_fire.interfaces.cli.themes.registry import theme_registry
from omega_fire.interfaces.cli.renderers.gauge import gauge_status
from omega_fire.interfaces.cli.prompts import (
    pause_prompt,
    PromptCancelled,
    PromptManager,
    is_cancel_word,
    is_quit_word,
    is_step_cancel_word,
)
from omega_fire.interfaces.cli.renderers.frame import render_frame, FrameMode
from omega_fire.interfaces.cli.views.log_stats_view import show_log_stats_dashboard
from omega_fire.shared.parsing import extract_ips
from omega_fire.infrastructure.config.paths import APP_LOG_PATH, AUDIT_LOG_PATH
from omega_fire.application.commands.rotate_logs import RotateLogsCommand, RotateLogsRequest
from omega_fire.application.commands.restore_backup import RestoreBackupCommand, RestoreBackupRequest
from omega_fire.application.commands.purge_backups import PurgeBackupsCommand
from omega_fire.application.commands.sync_backends import SyncBackendsCommand
from omega_fire.application.commands.backup_state import BackupStateCommand, BackupStateRequest
from omega_fire.application.commands.restore_state import RestoreStateCommand, RestoreStateRequest
from omega_fire.application.commands.export_f2b_report import (
    ExportF2bReportCommand,
    ExportF2bReportRequest,
)

#-----------------------------------------------------------------------------------

# ==============================================================================
# IMPORT DES CHEMINS CENTRALISÉS D'INFRASTRUCTURE
# ==============================================================================
from typing import List, Any
import json
from rich.console import Console

from omega_fire.infrastructure.config.paths import (
    BLOCKLIST_DIR,
    EXPORTS_DIR,
    BACKUPS_DIR,
    LOGS_DIR,
    CACHE_DIR,
    RUNTIME_DIR,
    DEFAULT_BLOCKLIST_FILE,
    DEFAULT_F2B_BLOCKLIST_FILE,
    DEFAULT_PINNED_FILES,
    _PROJECT_ROOT,
)

# Helpers de conversion pour la rétrocompatibilité des menus CLI
BLOCKLIST_DIR_STR = str(BLOCKLIST_DIR)
EXPORTS_DIR_STR = str(EXPORTS_DIR)
BACKUPS_DIR_STR = str(BACKUPS_DIR)

# Stockage global des automatisations de rotation (chargement au démarrage)
auto_file = RUNTIME_DIR / "scheduled_rotations.json"

if auto_file.exists():
    try:
        with open(auto_file, "r", encoding="utf-8") as f:
            SCHEDULED_AUTOMATIONS: list[dict[str, Any]] = json.load(f)
    except Exception:
        SCHEDULED_AUTOMATIONS = []
else:
    SCHEDULED_AUTOMATIONS = []

# Stockage global des automatisations de restauration (chargement au démarrage)
restore_auto_file = RUNTIME_DIR / "scheduled_restores.json"

if restore_auto_file.exists():
    try:
        with open(restore_auto_file, "r", encoding="utf-8") as f:
            SCHEDULED_RESTORES: list[dict[str, Any]] = json.load(f)
    except Exception:
        SCHEDULED_RESTORES = []
else:
    SCHEDULED_RESTORES = []

# Stockage global des règles de purge automatique (chargement au démarrage)
purge_auto_file = RUNTIME_DIR / "scheduled_purges.json"

if purge_auto_file.exists():
    try:
        with open(purge_auto_file, "r", encoding="utf-8") as f:
            SCHEDULED_PURGES: list[dict[str, Any]] = json.load(f)
    except Exception:
        SCHEDULED_PURGES = []
else:
    SCHEDULED_PURGES = []    
    

# 1. Instanciation de la console
console = Console()
# ----------------------------------------------------------------------
# Context object passed to all actions
# ----------------------------------------------------------------------
class ActionContext:
    """Context passed to every action."""
    
    def __init__(
        self,
        capability_registry: Any,
        console: Console,
        container: Any = None,
        state: Any = None,
    ):
        self.capability_registry = capability_registry
        self.console = console
        self.container = container
        self.state = state


# ----------------------------------------------------------------------
# Moteur d'exécution universel pour les actions (Cadres + Prompt + Entrée)
# ----------------------------------------------------------------------
def _execute_action_flow(
    ctx: ActionContext,
    title: str,
    action_logic: Callable[[List[Any]], None],
    pause_at_end: bool = True,
) -> None:
    """
    Rendu d'action universel et stable :
    - En-tête officiel affiché une seule fois avec la largeur actuelle du terminal
    - Exécution en direct des interactions de l'action
    - Cartouche d'information/status en bas
    - Aucune largeur rigide pour éviter les chevauchements lors des redimensionnements
    - Logging d'audit automatique en fin d'exécution
    """
    from rich.panel import Panel
    from rich.text import Text
    from omega_fire.interfaces.cli.renderers.frame import Frame
    from omega_fire.interfaces.cli.themes.registry import theme_registry
    from omega_fire.interfaces.cli.renderers.styles import get_terminal_width

    # 1. Calcul de la largeur au moment précis de l'affichage
    term_width = get_terminal_width()
    inner_width = max(term_width - 4, 40)
    frame = Frame(ctx.console)

    # 2. EN-TÊTE OFFICIEL UNIQUE
    ctx.console.print()
    ctx.console.print(frame._render_header(title))
    ctx.console.print(frame._render_separator(inner_width))
    ctx.console.print()

    # --- 2b. CADRE DE TITRE D'ACTION (Anti-débordement & Thème strict) ---
    style_border = theme_registry.get_style("border.default")
    style_text = theme_registry.get_style("text.heading")

    box_width = min(inner_width, 64)
    inner_box_width = box_width - 2  # Espace disponible entre │ et │

    # 1. Nettoyage et formatage du titre sans '═══' (pour ne pas casser le cadre)
    clean_title = title.strip().upper()
    
    # 2. espace des lettres que si le titre est court (< 20 car.) pour éviter d'exploser la largeur
    if len(clean_title) < 20:
        raw_content = f"─── {' '.join(clean_title)} ───"
    else:
        raw_content = f"─── {clean_title} ───"

    # 3. Tronquage de sécurité si le titre reste plus large que le cadre
    if len(raw_content) > inner_box_width:
        raw_content = raw_content[: inner_box_width - 3] + "..."

    # 4. Centrage parfait à l'intérieur du cadre
    centered_content = raw_content.center(inner_box_width)

    top_border = "┌" + "─" * inner_box_width + "┐"
    content_line = "│" + centered_content + "│"
    bottom_border = "└" + "─" * inner_box_width + "┘"

    # Construction avec les styles du thème strict (sans appel à _title pour éviter la pollution '═══')
    action_box = Text()
    
    # 1. Bordure supérieure
    action_box.append(f"{top_border}\n", style=style_border)
    
    # 2. Ligne centrale : │ (bordure) + TITRE (texte) + │ (bordure)
    action_box.append("│", style=style_border)
    action_box.append(centered_content, style=style_text)
    action_box.append("│\n", style=style_border)
    
    # 3. Bordure inférieure
    action_box.append(bottom_border, style=style_border)

    ctx.console.print(action_box)
    ctx.console.print()

    # 3. EXÉCUTION EN DIRECT DE L'ACTION + AUDIT AUTOMATIQUE
    buffered: List[Any] = []
    status = "success"
    error_details = None

    try:
        action_logic(buffered)
    except Exception as e:
        status = "failure"
        error_details = str(e)
        raise e
    finally:
        # ─── 1. JOURNAL APPLICATIF (app.log : Texte brut lisible) ───
        try:
            app_logger = None
            if hasattr(ctx, "container") and ctx.container:
                app_logger = getattr(ctx.container, "app_logger", None)
            elif hasattr(ctx, "app_logger"):
                app_logger = getattr(ctx, "app_logger", None)

            if app_logger:
                if status == "success":
                    app_logger.info(f"Action '{title}' exécutée avec succès.")
                else:
                    app_logger.error(f"Échec lors de l'exécution de l'action '{title}' : {error_details}")
        except Exception:
            pass

        # ─── 2. JOURNAL D'AUDIT (audit.log : JSON structuré) ───
        try:
            audit_logger = None
            if hasattr(ctx, "container") and ctx.container:
                audit_logger = getattr(ctx.container, "audit_logger", None)
            elif hasattr(ctx, "audit_logger"):
                audit_logger = getattr(ctx, "audit_logger", None)

            if audit_logger:
                details = {}
                if error_details:
                    details["error"] = error_details

                audit_logger.log_event(
                    event_type="action_execution",
                    actor="cli:admin",
                    action=title,
                    result=status,
                    details=details,
                )
        except Exception:
            pass

    if buffered:
        for item in buffered:
            ctx.console.print(item)

    # 4. CARTOUCHE D'INFORMATION / STATUS EN BAS
    if pause_at_end:
        current_width = max(get_terminal_width() - 4, 40)
        
        info_content = Text()
        info_content.append_text(_success("Action terminée\n"))
        info_content.append_text(_info("Appuyez sur [Entrée] pour revenir au menu..."))

        border_style = theme_registry.get_style("border.accent")

        info_panel = Panel(
            info_content,
            title="[ Information / Navigation ]",
            title_align="left",
            border_style=border_style,
            padding=(0, 2),
            expand=True,  # S'adapte dynamiquement à la largeur du terminal sans chevauchement
        )

        ctx.console.print()
        ctx.console.print(info_panel)
        ctx.console.print(frame._render_separator(current_width))
        ctx.console.print()

        # Purge du buffer clavier avant d'attendre une saisie : sans ça,
        # toute touche tapée pendant un `gauge_status` (scan bloquant,
        # ex. menu 4.9) reste bufferisée côté TTY et se rejoue ici (voire
        # dans le prompt du menu suivant), donnant l'impression qu'une
        # touche comme [q] "relance" l'action précédente. Même mécanisme
        # que keybindings.py::_getch() / splash.py, jamais appliqué ici
        # jusqu'à présent (référentiel §82.5).
        from omega_fire.interfaces.cli.keybindings import _flush_stdin
        _flush_stdin()

        # Attente d'entrée unique
        ctx.console.input()
# ----------------------------------------------------------------------
# Helpers de formatage (respectent theme_registry)
# ----------------------------------------------------------------------
def _title(text: str) -> Text:
    """Formate un titre avec le style heading du thème."""
    style = theme_registry.get_style("text.heading")
    return Text(f"═══ {text} ═══", style=style)


def _success(text: str) -> Text:
    """Formate un message de succès avec le style action.success."""
    style = theme_registry.get_style("action.success")
    return Text(f"✔ {text}", style=style)


def _error(text: str) -> Text:
    """Formate un message d'erreur avec le style action.error."""
    style = theme_registry.get_style("action.error")
    return Text(f"❌ {text}", style=style)


def _warning(text: str) -> Text:
    """Formate un avertissement avec le style action.warning."""
    style = theme_registry.get_style("action.warning")
    return Text(f"⚠ {text}", style=style)


def _info(text: str) -> Text:
    """Formate une information avec le style text.info."""
    style = theme_registry.get_style("text.info")
    return Text(text, style=style)


def _muted(text: str) -> Text:
    """Formate un texte atténué avec le style text.muted."""
    style = theme_registry.get_style("text.muted")
    return Text(text, style=style)


def _extract_valid_ips(text: str) -> set[str]:
    """Extrait les adresses IP valides (IPv4 ou IPv6) d'un texte libre.

    Réutilise shared/parsing.py::extract_ips() (extraction permissive,
    gère nativement les deux familles — corrigée référentiel §49 pour la
    notation IPv6 compressée "::") puis valide strictement chaque
    candidat via ipaddress.ip_address() : l'extraction permissive laisse
    passer de faux positifs (ex: un horodatage "12:30:00" a la forme
    d'une IPv6 tronquée), filtrés ici avant d'être proposés à l'action.
    Remplace 4 copies locales d'un regex IPv4-only (référentiel §49,
    plan IPv6 Phase A) — même mécanisme utilisé pour l'import de listes
    (2.2/2.4) et l'extraction depuis un fichier de blocklist.

    Retourne la forme CANONIQUE de chaque IP (str(ipaddress.ip_address(...)),
    pas la sous-chaîne brute extraite (référentiel §62) : une IPv6 admet
    plusieurs écritures équivalentes (casse, compression "::", zéros de
    tête) — sans cette normalisation, deux imports de la même IP sous des
    formes différentes sont traités comme deux entrées distinctes, et la
    comparaison exacte SQL ("WHERE ip = ?", BanRepository) ne les
    retrouve jamais l'une par rapport à l'autre.
    """
    valid: set[str] = set()
    for candidate in extract_ips(text):
        try:
            valid.add(str(ipaddress.ip_address(candidate)))
        except ValueError:
            continue
    return valid


# ----------------------------------------------------------------------
# Choix du thème CSS pour les exports HTML (5 thèmes, défaut Omega-base)
# ----------------------------------------------------------------------
HTML_EXPORT_THEMES: dict[str, str] = {
    "1": "omega-base",
    "2": "omega-burn",
    "3": "omega-neon",
    "4": "light-basic",
    "5": "light-alt",
}
HTML_EXPORT_THEME_LABELS: dict[str, str] = {
    "omega-base": "Omega-base (sombre bleu nuit / cyan — défaut)",
    "omega-burn": "Omega-burn (sombre braise rouge-orangé)",
    "omega-neon": "Omega-neon (sombre cyberpunk cyan/magenta)",
    "light-basic": "Light-basic (clair sobre, rapport professionnel)",
    "light-alt": "Light-alt (clair papier crème / vert forêt)",
}


def _prompt_html_theme(ctx: ActionContext, allow_cancel: bool = False) -> str:
    """Propose le choix du thème CSS pour un export HTML.

    Retourne toujours une valeur valide (défaut "omega-base" sur saisie
    vide ou invalide) — l'ancienne justification « un export déjà engagé
    ne doit pas être interrompu pour un choix cosmétique » a été
    explicitement révisée le 2026-08-16 : l'utilisateur veut q/annuler
    utilisable partout, y compris ici. allow_cancel reste à False par
    défaut pour ne rien casser chez les appelants pas encore migrés
    (mécanisme identique à PromptManager.ask_text(allow_cancel=...)) —
    lève PromptCancelled si True et qu'un mot-clé d'annulation est saisi.
    """
    ctx.console.print()
    ctx.console.print(_info("  Thème de l'export HTML :"))
    for key, name in HTML_EXPORT_THEMES.items():
        ctx.console.print(_info(f"  [{key}] {HTML_EXPORT_THEME_LABELS[name]}"))
    choice = ctx.console.input(_info("Choix du thème [1] (ou 'annuler') : " if allow_cancel else "Choix du thème [1] : ")).strip()
    if allow_cancel and is_cancel_word(choice):
        raise PromptCancelled("html_theme")
    return HTML_EXPORT_THEMES.get(choice or "1", "omega-base")

# ----------------------------------------------------------------------
# Menu 0 — Quitter
# ----------------------------------------------------------------------
import sys
def action_quit(ctx: ActionContext) -> None:
    """Action de sortie déclenchée par la touche Entrée du menu."""
    from rich import box
    from rich.align import Align
    from omega_fire.interfaces.cli.renderers.styles import get_terminal_width

    dialog_width = min(get_terminal_width() - 10, 60)

    question_panel = Panel(
        Align.center(_warning("Voulez-vous vraiment quitter Omega-Fire ?")),
        border_style=theme_registry.get_style("border.accent"),
        box=box.ROUNDED,
        padding=(1, 3),
        width=dialog_width,
    )
    ctx.console.print()
    ctx.console.print(Align.center(question_panel))
    ctx.console.print()

    prompt_text = "Confirmer (o/N) : "
    term_w = get_terminal_width()
    box_left_margin = max((term_w - dialog_width) // 2, 0)
    prompt_pad = box_left_margin + max((dialog_width - len(prompt_text)) // 2, 0)

    try:
        response = ctx.console.input(" " * prompt_pad + f"[text.info]{prompt_text}[/text.info]").strip().lower()
    except (EOFError, KeyboardInterrupt):
        response = 'o'
    ctx.console.print()

    if response in ['o', 'oui', 'y', 'yes']:
        confirm_panel = Panel(
            Align.center(_success("Fermeture de l'application... Au revoir !")),
            title="[ Session terminée ]",
            title_align="center",
            border_style=theme_registry.get_style("border.accent"),
            box=box.ROUNDED,
            padding=(1, 3),
            width=dialog_width,
        )
        ctx.console.print(Align.center(confirm_panel))
        ctx.console.print()
        if ctx.state is not None:
            ctx.state.running = False
        else:
            sys.exit(0)
    else:
        cancel_panel = Panel(
            Align.center(_muted("Opération annulée.")),
            title="[ Session conservée ]",
            title_align="left",
            border_style=theme_registry.get_style("border.default"),
            box=box.ROUNDED,
            padding=(1, 3),
            width=dialog_width,
        )
        ctx.console.print(Align.center(cancel_panel))
        ctx.console.print()

# ----------------------------------------------------------------------
# Menu 1 — État des capacités & diagnostics
# ----------------------------------------------------------------------
def action_1_1_show_registry(ctx: ActionContext) -> None:
    """1.1 — Afficher le registre des capacités."""
    def logic(out: List[Any]):
        from omega_fire.interfaces.cli.renderers.capability_view import get_all_capabilities
        with gauge_status(ctx.console, "Lecture du registre..."):
            result = get_all_capabilities(ctx.capability_registry)
        ctx.console.print(result)

    _execute_action_flow(ctx, "1.1 Registre des capacités", logic)

def action_1_2_capability_detail(ctx: ActionContext) -> None:
    """1.2 — Détail d'une capacité."""
    def logic(out: List[Any]):
        from omega_fire.interfaces.cli.renderers.capability_view import get_capability_detail
        from omega_fire.core.enums import CapabilityStatus
        
        capabilities = ctx.capability_registry.list_all()
        if not capabilities:
            out.append(_warning("Aucune capacité enregistrée dans le système."))
            return
        
        # 1. Message d'introduction stylisé
        out.append(_info("Capacités disponibles dans le registre :"))
        out.append("")

        # 2. Affichage de la liste de choix avec gestion robuste des enums
        for i, cap in enumerate(capabilities, 1):
            # Normalisation en majuscules du statut (pour éviter les problèmes de casse)
            raw_status = cap.status.value if hasattr(cap.status, "value") else str(cap.status)
            status_name = str(raw_status).upper()
            
            # Badge de statut universel selon la valeur réelle
            if status_name in ("AVAILABLE", "CAPABILITYSTATUS.AVAILABLE"):
                badge = _success("AVAILABLE")
            elif status_name in ("DEGRADED", "CAPABILITYSTATUS.DEGRADED"):
                badge = _warning("DEGRADED")
            elif status_name in ("MISSING", "CAPABILITYSTATUS.MISSING"):
                badge = _error("MISSING")
            else:
                badge = _muted("DISQUALIFIED")

            # Construction de la ligne : [1] CAPACITE — STATUT
            line = Text()
            line.append_text(_info(f"  [{i}] "))
            line.append(cap.id.upper(), style=theme_registry.get_style("text.main"))
            line.append(" — ", style=theme_registry.get_style("text.muted"))
            line.append_text(badge)
            
            out.append(line)
        
        out.append("")
        
        # Impression du buffer pour que l'utilisateur voie la liste avant de saisir
        for item in out:
            ctx.console.print(item)
        out.clear()

        # 3. Prompt de saisie utilisateur
        choice = ctx.console.input(_info("Saisissez le numéro ou l'ID de la capacité : ")).strip()
        if not choice:
            out.append(_muted("Opération annulée."))
            return
        
        # 4. Récupération et affichage du panneau détaillé
        try:
            cap_id = capabilities[int(choice) - 1].id if choice.isdigit() and 1 <= int(choice) <= len(capabilities) else choice
            with gauge_status(ctx.console, "Analyse de la capacité..."):
                detail_renderable = get_capability_detail(ctx.capability_registry, cap_id)

            out.append("")
            out.append(detail_renderable)
        except Exception as e:
            out.append(_error(f"Erreur : {str(e)}"))

    _execute_action_flow(ctx, "1.2 Détail d'une capacité", logic)

def action_1_3_rescan(ctx: ActionContext) -> None:
    """1.3 — Re-scanner le système."""
    def logic(out: List[Any]):
        if not ctx.container:
            ctx.console.print(_error("Conteneur de dépendances non disponible (container is None)."))
            return

        confirm = ctx.console.input(
            _info("Relancer un scan complet du système (nftables, iptables, fail2ban, systemd) ? (O/n, ou 'annuler') : ")
        ).strip().lower()
        if is_cancel_word(confirm) or (confirm and confirm not in ("o", "oui", "y", "yes")):
            ctx.console.print(_muted("Scan annulé."))
            return

        ctx.console.print()
        ctx.console.print(Text("  Scan du système en cours", style=theme_registry.get_style("text.heading")))
        ctx.console.print(Text("  Analyse des services installés (nftables, iptables, fail2ban, systemd)", style=theme_registry.get_style("text.info")))
        ctx.console.print(Text("  Cela ne prendra qu'un instant", style=theme_registry.get_style("text.muted")))
        ctx.console.print()

        try:
            scanner = ctx.container.scanner if hasattr(ctx.container, "scanner") else None
            if scanner is None:
                ctx.console.print(_error("Impossible de récupérer la sonde 'CapabilityScanner' depuis le conteneur."))
                return

            # scan() peuple déjà directement le registre associé au
            # scanner (voir SystemScanner.__init__ : self._registry =
            # registry) — aucun appel supplémentaire à
            # update_from_scan()/register_all() n'est nécessaire ni
            # même disponible sur CapabilityRegistry.
            with gauge_status(ctx.console, "Scan en cours..."):
                scan_results = scanner.scan()

            registered = scan_results.get("capabilities_registered", 0)
            available = scan_results.get("capabilities_available", 0)
            degraded = scan_results.get("capabilities_degraded", 0)
            missing = scan_results.get("capabilities_missing", 0)
            disqualified = scan_results.get("capabilities_disqualified", 0)
            scan_errors = scan_results.get("errors", [])

            ctx.console.print(_success("\nScan système effectué avec succès !"))
            ctx.console.print(_info(f"  • Composants / Sondes analysés : {registered}"))
            ctx.console.print(_info(f"  • Disponibles : {available}  |  Dégradés : {degraded}  |  "
                                     f"Manquants : {missing}  |  Disqualifiés : {disqualified}"))
            ctx.console.print(_info("  • Registre des capacités : Mis à jour"))

            if scan_errors:
                ctx.console.print()
                ctx.console.print(_warning(f"{len(scan_errors)} erreur(s) partielle(s) rencontrée(s) pendant le scan :"))
                for err in scan_errors[:5]:
                    ctx.console.print(_error(f"  • {err}"))
                if len(scan_errors) > 5:
                    ctx.console.print(_muted(f"  ... et {len(scan_errors) - 5} autre(s)."))

        except Exception as e:
            ctx.console.print(_error(f"Échec lors du rescan : {str(e)}"))
    _execute_action_flow(ctx, "1.3 Re-scan du système", logic)

def action_1_4_recent_diagnostics(ctx: ActionContext) -> None:
    """1.4 — Voir les diagnostics récents."""
    def logic(out: List[Any]):
        from omega_fire.interfaces.cli.renderers.capability_view import get_diagnostics
        result = get_diagnostics(ctx.capability_registry)
        ctx.console.print(result)

    _execute_action_flow(ctx, "1.4 Diagnostics récents", logic)

def action_1_5_app_log(ctx: ActionContext) -> None:
    """1.5 — Voir le journal applicatif."""
    def logic(out: List[Any]):
        from datetime import datetime, timedelta
        from omega_fire.infrastructure.config.paths import APP_LOG_PATH
        from omega_fire.interfaces.cli.themes.registry import theme_registry
        from rich.box import ROUNDED
        from rich.text import Text

        def _get_app_logger_instance():
            """Résout l'AppLogger via le conteneur pour accéder à
            clear()/delete_oldest() — jamais d'accès direct au fichier
            depuis actions.py pour la purge (contrairement à la lecture
            d'affichage ci-dessous, déjà en place et hors périmètre de
            ce chantier)."""
            if not ctx.container:
                return None
            try:
                return ctx.container.app_logger
            except Exception:
                return None

        def _do_manage_log() -> None:
            app_logger = _get_app_logger_instance()
            if app_logger is None:
                ctx.console.print(_error("Logger applicatif indisponible."))
                return

            ctx.console.print()
            ctx.console.print(_title("Gestion du journal applicatif"))
            ctx.console.print(_info("  [1] Supprimer les entrées de + de 30 jours"))
            ctx.console.print(_info("  [2] Supprimer les entrées de + de 120 jours"))
            ctx.console.print(_info("  [3] Supprimer les entrées antérieures à une date précise"))
            ctx.console.print(_info("  [4] Supprimer les N entrées les plus anciennes"))
            ctx.console.print(_muted("  [0] Annuler"))

            choice = ctx.console.input(_info("\nVotre choix : ")).strip()
            if not choice or is_step_cancel_word(choice) or is_quit_word(choice):
                ctx.console.print(_muted("Gestion annulée."))
                return

            older_than = None
            removal_label = ""

            if choice == "1":
                older_than = datetime.now() - timedelta(days=30)
                removal_label = "les entrées de plus de 30 jours"
            elif choice == "2":
                older_than = datetime.now() - timedelta(days=120)
                removal_label = "les entrées de plus de 120 jours"
            elif choice == "3":
                raw_date = ctx.console.input(
                    _info("Date limite (format JJ/MM/AAAA, ou 'annuler') : ")
                ).strip()
                if not raw_date or is_step_cancel_word(raw_date) or is_quit_word(raw_date):
                    ctx.console.print(_muted("Gestion annulée."))
                    return
                try:
                    older_than = datetime.strptime(raw_date, "%d/%m/%Y")
                except ValueError:
                    ctx.console.print(_error("Format de date invalide (attendu : JJ/MM/AAAA)."))
                    return
                removal_label = f"les entrées antérieures au {raw_date}"
            elif choice == "4":
                raw_count = ctx.console.input(
                    _info("Nombre d'entrées les plus anciennes à supprimer (ou 'annuler') : ")
                ).strip()
                if not raw_count or is_step_cancel_word(raw_count) or is_quit_word(raw_count):
                    ctx.console.print(_muted("Gestion annulée."))
                    return
                if not raw_count.isdigit() or int(raw_count) <= 0:
                    ctx.console.print(_error("Nombre invalide."))
                    return
                count = int(raw_count)
            else:
                ctx.console.print(_error("Choix invalide."))
                return

            ctx.console.print()
            if choice == "4":
                ctx.console.print(_warning(f"Vous allez supprimer les {count} entrées les plus anciennes."))
            else:
                ctx.console.print(_warning(f"Vous allez supprimer {removal_label}."))

            confirm = ctx.console.input(_warning("Confirmer la suppression ? [o/N] : ")).strip().lower()
            if confirm not in ("o", "oui", "y", "yes"):
                ctx.console.print(_info("Suppression annulée."))
                return

            try:
                if choice == "4":
                    removed = app_logger.delete_oldest(count)
                else:
                    removed = app_logger.clear(older_than=older_than)
            except Exception as e:
                ctx.console.print(_error(f"Erreur lors de la suppression : {e}"))
                return

            ctx.console.print(_success(f"{removed} entrée(s) supprimée(s)."))

        # ─── 0. Point d'entrée : consulter ou gérer ───
        ctx.console.print(_info("  [1]  Consulter le journal"))
        ctx.console.print(_info("  [2] 🗑️  Gérer / Purger le journal"))
        ctx.console.print(_muted("  [0/q] ↩️  Retour"))

        entry_choice = ctx.console.input(_info("\nVotre choix [1] : ")).strip() or "1"
        if is_quit_word(entry_choice) or is_step_cancel_word(entry_choice):
            return
        if entry_choice == "2":
            _do_manage_log()
            return
        elif entry_choice != "1":
            ctx.console.print(_error("Choix invalide."))
            return

        # ─── 1. Menu de filtres & Choix du nombre de lignes ───
        ctx.console.print(_info("\nOptions d'affichage :"))
        ctx.console.print(_info("  [1] 50 dernières lignes (Recommandé)"), highlight=False)
        ctx.console.print(_info("  [2] 100 dernières lignes"), highlight=False)
        ctx.console.print(_info("  [3] Nombre personnalisé"), highlight=False)
        ctx.console.print(_muted("  [0/q] Annuler"), highlight=False)

        choice = ctx.console.input(_info("\nChoix [1/2/3] (Défaut: 1) : ")).strip() or "1"
        if is_quit_word(choice) or is_step_cancel_word(choice):
            ctx.console.print(_muted("Opération annulée."))
            return

        if choice == "2":
            max_lines = 100
        elif choice == "3":
            raw_input = ctx.console.input(_info("Nombre de lignes souhaité (ou 'annuler') : ")).strip()
            if is_step_cancel_word(raw_input) or is_quit_word(raw_input):
                ctx.console.print(_muted("Opération annulée."))
                return
            max_lines = int(raw_input) if raw_input.isdigit() and int(raw_input) > 0 else 50
        else:
            max_lines = 50

        keyword = ctx.console.input(_info("Filtrer par mot-clé (Entrée = aucun, 'annuler' = abandonner) : ")).strip()
        if is_step_cancel_word(keyword) or is_quit_word(keyword):
            ctx.console.print(_muted("Opération annulée."))
            return

        # ─── 2. Lecture performante du fichier journal ───
        lines = []
        if APP_LOG_PATH.exists():
            try:
                with open(APP_LOG_PATH, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
            except Exception as e:
                ctx.console.print(_error(f"Erreur lors de la lecture du journal : {e}"))
                return
        else:
            ctx.console.print(_warning(f"Le fichier journal '{APP_LOG_PATH}' n'existe pas encore."))
            return

        # ─── 3. Filtrage & Extraction des lignes récentes ───
        if keyword:
            lines = [l for l in lines if keyword.lower() in l.lower()]

        recent_lines = lines[-max_lines:]

        if not recent_lines:
            ctx.console.print()
            ctx.console.print(_warning("Aucune entrée ne correspond aux critères."))
            return

        # ─── 4. Affichage dans un tableau conforme à Frame (pagination
        # automatique centralisée — cf. interfaces/cli/renderers/pager.py) ───
        style_border = theme_registry.get_style("border.default")
        style_heading = theme_registry.get_style("text.heading")
        style_main = theme_registry.get_style("text.main")
        style_muted = theme_registry.get_style("text.muted")
        style_error = theme_registry.get_style("action.error")
        style_warning = theme_registry.get_style("action.warning")

        table = Table(
            box=ROUNDED,
            border_style=style_border,
            header_style=style_heading,
            expand=True,
        )
        table.add_column("Entrée du Journal Applicatif", style=style_main)

        for line in recent_lines:
            text = Text()
            if "[ERROR]" in line or "[CRITICAL]" in line:
                text.append(line, style=style_error)
            elif "[WARNING]" in line:
                text.append(line, style=style_warning)
            elif "]: " in line:
                parts = line.split("]: ", 1)
                text.append(f"{parts[0]}]: ", style=style_muted)
                text.append(parts[1], style=style_main)
            else:
                text.append(line, style=style_main)

            table.add_row(text)

        ctx.console.print()
        ctx.console.print(_info(f"{len(recent_lines)} entrée(s) affichée(s) :"))
        ctx.console.print(table)

        ctx.console.print()
        ctx.console.print(_muted(f"Source : {APP_LOG_PATH} ({len(recent_lines)} lignes traitées)"))

    _execute_action_flow(ctx, "1.5 Journal applicatif", logic)

def action_1_6_search_diagnostics(ctx: ActionContext) -> None:
    """1.6 — Rechercher dans les diagnostics."""
    def logic(out: List[Any]):
        query = ctx.console.input(_info("Mot-clé de recherche (ou 'annuler') : ")).strip()
        if not query or is_cancel_word(query):
            ctx.console.print(_muted("Recherche annulée."))
            return

        ctx.console.print(_muted(f"\nRecherche de '{query}' en cours..."))

        try:
            # 1. Recherche dans le Registre de Capacités / Diagnostics Système
            from omega_fire.interfaces.cli.renderers.capability_view import search_diagnostics
            registry_results = search_diagnostics(ctx.capability_registry, keyword=query)

            # 2. Recherche dans le Journal d'Application (App Log)
            from omega_fire.application.queries.app_log import read_app_log

            audit_port = None
            if ctx.container:
                try:
                    audit_port = ctx.container.get_audit_port()
                except Exception:
                    pass

            log_res = read_app_log(audit_port=audit_port, keyword=query)

            # Extraction forcée de la liste réelle d'entrées
            if hasattr(log_res, "entries"):
                raw_entries = log_res.entries
            elif hasattr(log_res, "logs"):
                raw_entries = log_res.logs
            elif isinstance(log_res, list):
                raw_entries = log_res
            else:
                raw_entries = []

            # 3. Empilage dans la liste 'out' pour _execute_action_flow
            out.append("")

            # A. Rendu du Tableau des Capacités / Diagnostics
            if registry_results:
                out.append(registry_results)
                out.append("")

            # B. Rendu du Journal applicatif
            if raw_entries:
                out.append(_success(f"Journal d'application : {len(raw_entries)} entrée(s) trouvée(s)"))
                out.append("")

                formatted_lines = []
                for entry in raw_entries[:15]:
                    if isinstance(entry, dict):
                        ts = entry.get("timestamp", entry.get("time", ""))
                        lvl = entry.get("level", "INFO")
                        msg = entry.get("message", entry.get("msg", str(entry)))
                        formatted_lines.append(f"  [{ts}] [{lvl}] {msg}" if ts else f"  [{lvl}] {msg}")
                    elif hasattr(entry, "message"):
                        formatted_lines.append(f"  {getattr(entry, 'message')}")
                    else:
                        formatted_lines.append(f"  {str(entry)}")

                # On transmet une liste de chaînes simples à 'out'
                # Chaque chaîne devient une ligne propre dans _execute_action_flow
                for line in formatted_lines:
                    out.append(line)

            if not registry_results and not raw_entries:
                out.append(_warning(f"Aucun diagnostic ni journal trouvé pour '{query}'."))

        except Exception as e:
            out.append(_error(f"Erreur lors de la recherche : {str(e)}"))

    _execute_action_flow(ctx, "1.6 Recherche diagnostics", logic)

def action_1_7_export_state(ctx: ActionContext) -> None:
    """1.7 — Exporter l'état système (JSON/HTML/TXT)."""
    def logic(out: List[Any]):
        from datetime import datetime
        from pathlib import Path

        # 1. Sélection du format avec le helper de thème (zéro couleur hardcodée)
        ctx.console.print(_info("Sélectionnez le format d'exportation :"))

        formats = [
            ("1", "JSON", "données brutes structurées"),
            ("2", "HTML", "rapport visuel lisible [défaut]"),
            ("3", "TXT",  "rapport texte brut"),
        ]

        for num, fmt_label, desc in formats:
            line = Text()
            line.append_text(_info(f"  [{num}] "))
            line.append(f"{fmt_label:<5}", style=theme_registry.get_style("text.main"))
            line.append(" — ", style=theme_registry.get_style("text.muted"))
            line.append(desc, style=theme_registry.get_style("text.muted"))
            ctx.console.print(line)
        ctx.console.print(_muted("  [0] Annuler"))

        choice = ctx.console.input(_info("\nVotre choix (1-3, défaut: 2, ou 'annuler') : ")).strip()
        if is_cancel_word(choice):
            ctx.console.print(_muted("Export annulé."))
            return

        format_map = {"1": "json", "2": "html", "3": "txt"}
        fmt = format_map.get(choice, "html")
        if fmt == "html":
            try:
                theme_name = _prompt_html_theme(ctx, allow_cancel=True)
            except PromptCancelled:
                ctx.console.print(_muted("Export annulé."))
                return
        else:
            theme_name = "omega-base"

        # 2. Génération du chemin par défaut
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_dir = Path(EXPORTS_DIR)
        default_path = default_dir / f"rapport_systeme_{timestamp}.{fmt}"

        # Information du chemin avec le style du thème (au lieu de [bold])
        path_info = Text()
        path_info.append_text(_info("\nChemin par défaut : "))
        path_info.append(str(default_path), style=theme_registry.get_style("text.heading"))
        ctx.console.print(path_info)

        user_path = ctx.console.input(
            _info("Appuyez sur Entrée pour valider, saisissez un autre chemin, ou 'annuler' : ")
        ).strip()
        if is_cancel_word(user_path):
            ctx.console.print(_muted("Export annulé."))
            return

        final_path = str(Path(user_path) if user_path else default_path)

        ctx.console.print(_muted(f"\nGénération du rapport [{fmt.upper()}] en cours..."))

        # 3. Exécution du plan d'exportation
        try:
            from omega_fire.application.commands.export_report import plan_export_report

            plan = plan_export_report(
                report_name="Rapport d'état système Omega-Fire",
                format=fmt,
                destination=final_path,
                registry=ctx.capability_registry,
                theme_name=theme_name,
            )

            for step in plan.steps:
                if step.execute:
                    step.execute()

            ctx.console.print()
            ctx.console.print(_success("Rapport exporté avec succès !"))
            ctx.console.print(_info(f"  • Fichier généré : {final_path}"))

        except Exception as e:
            ctx.console.print(_error(f"Échec de l'exportation : {str(e)}"))

    _execute_action_flow(ctx, "1.7 Exporter l'état système", logic)
# ----------------------------------------------------------------------
# Menu 2 — Gestion des IPs (Blacklist unifiée)
# ----------------------------------------------------------------------
def action_2_1_ban_ip(ctx: ActionContext) -> None:
    """2.1 — Bannir une seule IP, sur tous les backends détectés par défaut."""
    def logic(out: List[Any]):
        import ipaddress
        from omega_fire.application.commands.ban_ip_all_backends import (
            BanIpToAllBackendsCommand,
            BanIpAllBackendsRequest,
        )

        if not ctx.container:
            ctx.console.print(_error("Conteneur non disponible."))
            return

        ctx.console.print(_title("Bannissement d'une IP Unique"))
        ctx.console.print()

        # 1. Saisie et validation de l'IP — reboucle sur une saisie
        # invalide au lieu d'annuler toute l'action (référentiel §48).
        while True:
            ip = ctx.console.input(_info("Adresse IP à bannir (ou 'annuler') : ")).strip()
            if not ip or is_cancel_word(ip):
                ctx.console.print(_muted("Opération annulée."))
                return
            try:
                # Normalisation vers la forme canonique (référentiel §62) —
                # une IPv6 tapée en majuscules/forme non compressée doit
                # correspondre exactement à celle stockée en base par un
                # ban/unban antérieur (comparaison SQL "WHERE ip = ?").
                ip = str(ipaddress.ip_address(ip))
                break
            except ValueError:
                ctx.console.print(_error(f"Format d'adresse IP invalide : '{ip}'. Réessaie, ou 'annuler' pour sortir."))

        # 2. Détection des backends disponibles
        supported_backends = []
        for b_name in ("nftables", "iptables", "ip6tables", "fail2ban"):
            try:
                if ctx.container.get_firewall_port(b_name) is not None:
                    supported_backends.append(b_name)
            except Exception:
                continue

        if not supported_backends:
            ctx.console.print(_error("Aucun backend disponible pour le bannissement."))
            return

        if len(supported_backends) == 1:
            target_backends = list(supported_backends)
            ctx.console.print(_info(f"\nBackend cible : {supported_backends[0]} (seul backend disponible)"))
        else:
            ctx.console.print(_info("\nBackends disponibles :"))
            ctx.console.print(_info(
                f"  [Entrée] Bannir sur tous ({', '.join(supported_backends)}) — Recommandé"
            ), highlight=False)
            for idx, b_name in enumerate(supported_backends, start=1):
                ctx.console.print(_info(f"  [{idx}] Cibler uniquement {b_name} (diagnostic)"))
            ctx.console.print(_info("  [0] Annuler"))

            choice = ctx.console.input(_info("\nVotre choix : ")).strip()
            if is_cancel_word(choice):
                ctx.console.print(_muted("Opération annulée."))
                return
            elif not choice:
                target_backends = list(supported_backends)
            elif choice.isdigit() and 1 <= int(choice) <= len(supported_backends):
                target_backends = [supported_backends[int(choice) - 1]]
                ctx.console.print(_warning(
                    f"\nCiblage diagnostic : bannissement uniquement sur {target_backends[0]}. "
                    f"Si un autre backend est actif, l'IP pourrait rester accessible via ce dernier."
                ))
            else:
                ctx.console.print(_error("Choix invalide."))
                return

        # 3. Commentaire
        comment = ctx.console.input(_info("\nCommentaire (ou 'annuler') : ")).strip()
        if is_cancel_word(comment):
            ctx.console.print(_muted("Opération annulée."))
            return

        # 4. Récapitulatif et confirmation finale — dernier point de sortie,
        # garanti quel que soit le chemin emprunté avant.
        ctx.console.print()
        ctx.console.print(_info(f"IP : {ip}"))
        ctx.console.print(_info(f"Backend(s) : {', '.join(target_backends)}"))
        ctx.console.print(_info(f"Commentaire : {comment or '(aucun)'}"))
        confirm = ctx.console.input(_info("\nConfirmez-vous le bannissement ? [o/N] : ")).strip().lower()
        if confirm not in ("o", "oui", "y", "yes"):
            ctx.console.print(_info("Opération annulée."))
            return

        # 5. Résolution des adapters et exécution
        adapters: dict[str, Any] = {}
        for b_name in target_backends:
            try:
                adapters[b_name] = ctx.container.get_firewall_port(b_name)
            except Exception:
                adapters[b_name] = None

        result = BanIpToAllBackendsCommand(adapters, getattr(ctx.container, "ban_repository", None)).execute(
            BanIpAllBackendsRequest(ips=[ip], comment=comment, target_backends=target_backends)
        )

        # 6. Rapport par backend
        ctx.console.print()
        for backend, outcome in result.outcomes.items():
            if outcome.banned:
                ctx.console.print(_success(f"[{backend}] ✔ IP {ip} bannie avec succès."))
            elif outcome.already_banned:
                ctx.console.print(_warning(f"[{backend}] ⚠️ IP {ip} déjà bannie (aucun doublon ajouté)."))
            for failed_ip, reason in outcome.errors:
                ctx.console.print(_error(f"[{backend}] ❌ Échec pour {failed_ip} : {reason}"))

    _execute_action_flow(ctx, "2.1 Bannir une IP", logic)

def action_2_2_ban_list(ctx: ActionContext) -> None:
    """2.2 — Bannir une liste d'IPs (toutes sources), sur tous les backends détectés par défaut."""
    def logic(out: List[Any]):
        import os
        import re
        from rich import box
        from rich.table import Table
        from omega_fire.interfaces.cli.themes.registry import theme_registry
        from omega_fire.application.commands.ban_ip_all_backends import (
            BanIpToAllBackendsCommand,
            BanIpAllBackendsRequest,
        )

        def _safe_extract(filepath: str) -> set[str]:
            if not os.path.exists(filepath):
                ctx.console.print(_error(f"Le fichier '{filepath}' n'existe pas."))
                return set()
            try:
                with open(filepath, "rb") as f:
                    header = f.read(1024)
                    if header.startswith(b"%PDF") or b"\x00" in header:
                        ctx.console.print(_error("Le fichier sélectionné est binaire/PDF (attendu : fichier texte)."))
                        return set()
            except Exception as e:
                ctx.console.print(_error(f"Erreur de lecture binaire : {e}"))
                return set()

            ips = set()
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line_str = line.strip()
                        if line_str and not line_str.startswith("#"):
                            ips |= _extract_valid_ips(line_str)
            except Exception as e:
                ctx.console.print(_error(f"Erreur de lecture texte : {e}"))
                return set()

            return ips

        if not ctx.container:
            ctx.console.print(_error("Conteneur non disponible."))
            return

        # 1. Menu d'approvisionnement
        ctx.console.print(_title("Bannissement par Liste d'IPs"))
        ctx.console.print()
        ctx.console.print(_info("Choisissez la méthode d'approvisionnement :"))
        ctx.console.print(_info("  [1] ✍️  Saisie manuelle d'IPs (séparées par espaces/virgules)"))
        ctx.console.print(_info(f"  [2] 🖹 Charger le fichier par défaut ({DEFAULT_BLOCKLIST_FILE.name})"))
        ctx.console.print(_info(f"  [3] 🖺  Charger le fichier Fail2ban par défaut ({DEFAULT_F2B_BLOCKLIST_FILE.name})"))
        ctx.console.print(_info("  [4] 🖿  Parcourir / Sélectionner un fichier dans var/blocklist/"))
        ctx.console.print(_info("  [5] 🖈   Choisir / Gérer un fichier ÉPINGLÉ"))
        ctx.console.print(_info("  [6] ⌨️  Saisir un chemin de fichier personnalisé"))
        ctx.console.print(_info("  [0] ↩️  Annuler et revenir au menu"))
        ctx.console.print()

        mode_choice = ctx.console.input(_info("Votre choix [1] (ou 'annuler') : ")).strip() or "1"
        if is_cancel_word(mode_choice):
            ctx.console.print(_muted("Opération annulée."))
            return

        extracted_ips: set[str] = set()
        source_label = ""

        # Épingles persistées, même mécanisme que 5.2/4.4 (voir leur
        # commentaire) — bug réel corrigé le 2026-09-04 : ctx.pinned_export_files
        # n'était qu'un attribut en mémoire sur ActionContext, jamais
        # sauvegardé sur disque, perdu à chaque redémarrage.
        from omega_fire.infrastructure.storage.files.json_store import JsonStore
        from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand

        pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )
        pinned_files = pinned_command.list_paths()

        if mode_choice == "1":
            raw_ips = ctx.console.input(_info("Saisissez les IPs à bannir (ou 'annuler') : ")).strip()
            if not raw_ips or is_cancel_word(raw_ips):
                ctx.console.print(_muted("Opération annulée."))
                return
            extracted_ips = _extract_valid_ips(raw_ips)
            source_label = "Saisie manuelle"

        elif mode_choice == "2":
            source_label = f"Fichier {DEFAULT_BLOCKLIST_FILE.name}"
            extracted_ips = _safe_extract(str(DEFAULT_BLOCKLIST_FILE))

        elif mode_choice == "3":
            source_label = f"Fichier {DEFAULT_F2B_BLOCKLIST_FILE.name}"
            extracted_ips = _safe_extract(str(DEFAULT_F2B_BLOCKLIST_FILE))

        elif mode_choice == "4":
            if not os.path.exists(BLOCKLIST_DIR_STR):
                ctx.console.print(_error(f"Dossier '{BLOCKLIST_DIR_STR}' introuvable."))
                return
            all_files = [f for f in sorted(os.listdir(BLOCKLIST_DIR_STR)) if os.path.isfile(os.path.join(BLOCKLIST_DIR_STR, f))]
            if not all_files:
                ctx.console.print(_warning("Aucun fichier trouvé dans var/blocklist/."))
                return

            ctx.console.print(_info("\nFichiers disponibles :"))
            for idx, fname in enumerate(all_files, start=1):
                ctx.console.print(_info(f"  [{idx}] {fname}"))
            ctx.console.print(_info("  [0] Annuler"))

            f_idx = ctx.console.input(_info("\nNuméro du fichier (ou 'annuler') : ")).strip()
            if is_cancel_word(f_idx):
                ctx.console.print(_muted("Opération annulée."))
                return
            if not f_idx.isdigit() or not (1 <= int(f_idx) <= len(all_files)):
                ctx.console.print(_error("Sélection invalide."))
                return

            selected_file = all_files[int(f_idx) - 1]
            source_label = f"Fichier '{selected_file}'"
            extracted_ips = _safe_extract(os.path.join(BLOCKLIST_DIR_STR, selected_file))

        elif mode_choice == "5":
            ctx.console.print(_title("Fichiers Épinglés"))
            if pinned_files:
                for idx, path in enumerate(pinned_files, start=1):
                    ctx.console.print(_info(f"  [{idx}] {path}"))
            else:
                ctx.console.print(_info("  (Aucune épingle configurée)"))

            ctx.console.print(_info("\n  [A] Ajouter une nouvelle épingle"))
            ctx.console.print(_info("  [0] Retour / Annuler"))

            p_sel = ctx.console.input(_info("\nChoix : ")).strip().upper()
            if is_cancel_word(p_sel):
                ctx.console.print(_muted("Opération annulée."))
                return

            if p_sel == "A":
                new_pin = ctx.console.input(_info("Chemin complet du fichier à épingler (ou 'annuler') : ")).strip()
                if not new_pin or is_cancel_word(new_pin):
                    ctx.console.print(_muted("Opération annulée."))
                    return
                if os.path.exists(new_pin):
                    add_result = pinned_command.add_path(new_pin)
                    if add_result.success:
                        ctx.console.print(_success(f"Fichier '{new_pin}' épinglé."))
                    target_path = new_pin
                else:
                    ctx.console.print(_error("Fichier introuvable."))
                    return
            elif p_sel.isdigit() and 1 <= int(p_sel) <= len(pinned_files):
                target_path = pinned_files[int(p_sel) - 1]
            else:
                ctx.console.print(_warning("Choix d'épingle invalide."))
                return

            source_label = f"Épingle '{os.path.basename(target_path)}'"
            extracted_ips = _safe_extract(target_path)

        elif mode_choice == "6":
            target_path = ctx.console.input(_info("Saisissez le chemin complet du fichier (ou 'annuler') : ")).strip()
            if not target_path or is_cancel_word(target_path):
                ctx.console.print(_muted("Opération annulée."))
                return
            source_label = f"Fichier libre '{os.path.basename(target_path)}'"
            extracted_ips = _safe_extract(target_path)

        else:
            ctx.console.print(_error("Choix invalide."))
            return

        unique_ips = sorted(list(extracted_ips))
        if not unique_ips:
            ctx.console.print(_warning("Aucune adresse IP valide trouvée dans la source."))
            return

        ctx.console.print(_success(f"✔ {len(unique_ips)} IP(s) unique(s) extraite(s) ({source_label})."))

        # 2. Détection des backends disponibles
        supported_backends = []
        for b_name in ("nftables", "iptables", "ip6tables", "fail2ban"):
            try:
                if ctx.container.get_firewall_port(b_name) is not None:
                    supported_backends.append(b_name)
            except Exception:
                continue

        if not supported_backends:
            ctx.console.print(_error("Aucun backend disponible pour le bannissement."))
            return

        ctx.console.print()
        if len(supported_backends) == 1:
            target_backends = list(supported_backends)
            ctx.console.print(_info(f"Backend cible : {supported_backends[0]} (seul backend disponible)"))
        else:
            ctx.console.print(_info("Backends disponibles :"))
            ctx.console.print(_info(
                f"  [Entrée] Bannir sur tous ({', '.join(supported_backends)}) — Recommandé"
            ), highlight=False)
            for idx, b_name in enumerate(supported_backends, start=1):
                ctx.console.print(_info(f"  [{idx}] Cibler uniquement {b_name} (diagnostic)"))
            ctx.console.print(_info("  [0] Annuler"))

            choice_b = ctx.console.input(_info("\nVotre choix : ")).strip()
            if is_cancel_word(choice_b):
                ctx.console.print(_muted("Opération annulée."))
                return
            elif not choice_b:
                target_backends = list(supported_backends)
            elif choice_b.isdigit() and 1 <= int(choice_b) <= len(supported_backends):
                target_backends = [supported_backends[int(choice_b) - 1]]
                ctx.console.print(_warning(
                    f"\nCiblage diagnostic : bannissement uniquement sur {target_backends[0]}."
                ))
            else:
                ctx.console.print(_error("Choix invalide."))
                return

        comment = ctx.console.input(_info("\nCommentaire optionnel (ou 'annuler') : ")).strip()
        if is_cancel_word(comment):
            ctx.console.print(_muted("Opération annulée."))
            return

        # 3. Récapitulatif et confirmation finale
        ctx.console.print()
        ctx.console.print(_info(f"IPs à bannir : {len(unique_ips)}"))
        ctx.console.print(_info(f"Backend(s) : {', '.join(target_backends)}"))
        confirm = ctx.console.input(_info("\nConfirmez-vous le bannissement ? [o/N] : ")).strip().lower()
        if confirm not in ("o", "oui", "y", "yes"):
            ctx.console.print(_info("Opération annulée."))
            return

        # 4. Résolution des adapters et exécution
        adapters: dict[str, Any] = {}
        for b_name in target_backends:
            try:
                adapters[b_name] = ctx.container.get_firewall_port(b_name)
            except Exception:
                adapters[b_name] = None

        result = BanIpToAllBackendsCommand(adapters, getattr(ctx.container, "ban_repository", None)).execute(
            BanIpAllBackendsRequest(ips=unique_ips, comment=comment, target_backends=target_backends)
        )

        # 5. Tableau de Diagnostic par backend
        for backend, outcome in result.outcomes.items():
            diag_table = Table(
                title=f"Rapport de Bannissement Groupé -> [{backend}]",
                show_header=True,
                header_style=theme_registry.get_style("table.header"),
                border_style=theme_registry.get_style("border.accent"),
                box=box.SQUARE,
                expand=False,
                padding=(0, 1),
            )
            diag_table.add_column("Métrique / Indicateur", style=theme_registry.get_style("text.main"), width=32)
            diag_table.add_column("Valeur", justify="right", style=theme_registry.get_style("text.info"), width=16)

            diag_table.add_row("Source des adresses", source_label)
            diag_table.add_row("IPs identifiées (Source)", str(len(unique_ips)))
            diag_table.add_row("Nouvelles IPs bannies", str(len(outcome.banned)))
            diag_table.add_row("IPs déjà bannies (Ignorées)", str(len(outcome.already_banned)))
            diag_table.add_row("Échecs / Erreurs de traitement", str(len(outcome.errors)))

            ctx.console.print()
            ctx.console.print(diag_table)

            for failed_ip, reason in outcome.errors:
                ctx.console.print(_error(f"  ❌ [{backend}] {failed_ip} : {reason}"))

        ctx.console.print()
        ctx.console.print(_success("✔ Opération de bannissement terminée."))

    _execute_action_flow(ctx, "2.2 Bannir une liste d'IPs", logic)

def action_2_3_unban_ip(ctx: ActionContext) -> None:
    """2.3 — Débannir une seule IP, sur tous les backends détectés par défaut."""
    def logic(out: List[Any]):
        import ipaddress
        from omega_fire.application.commands.unban_ip_all_backends import (
            UnbanIpToAllBackendsCommand,
            UnbanIpAllBackendsRequest,
        )

        if not ctx.container:
            ctx.console.print(_error("Conteneur non disponible."))
            return

        ctx.console.print(_title("Débannissement d'une IP Unique"))
        ctx.console.print()

        # 1. Saisie et validation de l'IP — reboucle sur une saisie
        # invalide au lieu d'annuler toute l'action (référentiel §48).
        while True:
            ip_input = ctx.console.input(_info("Adresse IP à débannir (ou 'annuler') : ")).strip()
            if not ip_input or is_cancel_word(ip_input):
                ctx.console.print(_muted("Opération annulée."))
                return
            try:
                # Normalisation vers la forme canonique (référentiel §62) —
                # doit correspondre exactement à la forme stockée en base
                # par le ban correspondant (comparaison SQL "WHERE ip = ?"
                # dans BanRepository.mark_removed_by_ip()).
                ip_input = str(ipaddress.ip_address(ip_input))
                break
            except ValueError:
                ctx.console.print(_error(f"Format d'adresse IP invalide : '{ip_input}'. Réessaie, ou 'annuler' pour sortir."))

        # 2. Détection des backends disponibles
        supported_backends = []
        for b_name in ("nftables", "iptables", "ip6tables", "fail2ban"):
            try:
                if ctx.container.get_firewall_port(b_name) is not None:
                    supported_backends.append(b_name)
            except Exception:
                continue

        if not supported_backends:
            ctx.console.print(_error("Aucun backend disponible pour le débannissement."))
            return

        if len(supported_backends) == 1:
            target_backends = list(supported_backends)
            ctx.console.print(_info(f"\nBackend cible : {supported_backends[0]} (seul backend disponible)"))
        else:
            ctx.console.print(_info("\nBackends disponibles :"))
            ctx.console.print(_info(
                f"  [Entrée] Débannir sur tous ({', '.join(supported_backends)}) — Recommandé"
            ), highlight=False)
            for idx, b_name in enumerate(supported_backends, start=1):
                ctx.console.print(_info(f"  [{idx}] Cibler uniquement {b_name} (diagnostic)"))
            ctx.console.print(_info("  [0] Annuler"))

            choice = ctx.console.input(_info("\nVotre choix : ")).strip()
            if is_cancel_word(choice):
                ctx.console.print(_muted("Opération annulée."))
                return
            elif not choice:
                target_backends = list(supported_backends)
            elif choice.isdigit() and 1 <= int(choice) <= len(supported_backends):
                target_backends = [supported_backends[int(choice) - 1]]
                ctx.console.print(_warning(
                    f"\nCiblage diagnostic : débannissement uniquement sur {target_backends[0]}. "
                    f"Si l'IP est aussi bannie sur un autre backend, elle restera bloquée malgré "
                    f"cette opération."
                ))
            else:
                ctx.console.print(_error("Choix invalide."))
                return

        # 3. Récapitulatif et confirmation finale
        ctx.console.print()
        ctx.console.print(_info(f"IP : {ip_input}"))
        ctx.console.print(_info(f"Backend(s) : {', '.join(target_backends)}"))
        confirm = ctx.console.input(_info("\nConfirmez-vous le débannissement ? [o/N] : ")).strip().lower()
        if confirm not in ("o", "oui", "y", "yes"):
            ctx.console.print(_info("Opération annulée."))
            return

        # 4. Résolution des adapters et exécution
        adapters: dict[str, Any] = {}
        for b_name in target_backends:
            try:
                adapters[b_name] = ctx.container.get_firewall_port(b_name)
            except Exception:
                adapters[b_name] = None

        result = UnbanIpToAllBackendsCommand(adapters, getattr(ctx.container, "ban_repository", None)).execute(
            UnbanIpAllBackendsRequest(ips=[ip_input], target_backends=target_backends)
        )

        # 5. Rapport par backend
        ctx.console.print()
        for backend, outcome in result.outcomes.items():
            if outcome.unbanned:
                ctx.console.print(_success(f"[{backend}] ✔ IP {ip_input} débannie avec succès."))
            elif outcome.already_free:
                ctx.console.print(_warning(f"[{backend}] ⚠️ IP {ip_input} n'était pas bannie (déjà libre)."))
            for failed_ip, reason in outcome.errors:
                ctx.console.print(_error(f"[{backend}] ❌ Échec pour {failed_ip} : {reason}"))

    _execute_action_flow(ctx, "2.3 Débannir une IP", logic)

def action_2_4_unban_list(ctx: ActionContext) -> None:
    """2.4 — Débannir une liste d'IPs (toutes sources), sur tous les backends détectés par défaut."""
    def logic(out: List[Any]):
        import os
        import re
        from rich import box
        from rich.table import Table
        from omega_fire.interfaces.cli.themes.registry import theme_registry
        from omega_fire.application.commands.unban_ip_all_backends import (
            UnbanIpToAllBackendsCommand,
            UnbanIpAllBackendsRequest,
        )

        def _safe_extract(filepath: str) -> set[str]:
            if not os.path.exists(filepath):
                ctx.console.print(_error(f"Le fichier '{filepath}' n'existe pas."))
                return set()
            try:
                with open(filepath, "rb") as f:
                    header = f.read(1024)
                    if header.startswith(b"%PDF") or b"\x00" in header:
                        ctx.console.print(_error("Le fichier sélectionné est binaire/PDF (attendu : fichier texte)."))
                        return set()
            except Exception as e:
                ctx.console.print(_error(f"Erreur de lecture binaire : {e}"))
                return set()

            ips = set()
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line_str = line.strip()
                        if line_str and not line_str.startswith("#"):
                            ips |= _extract_valid_ips(line_str)
            except Exception as e:
                ctx.console.print(_error(f"Erreur de lecture texte : {e}"))
                return set()

            return ips

        if not ctx.container:
            ctx.console.print(_error("Conteneur non disponible."))
            return

        # 1. Sélection de la source
        ctx.console.print(_title("Débannissement par Liste d'IPs"))
        ctx.console.print()
        ctx.console.print(_info("Choisissez la source de la liste à débannir :"))
        ctx.console.print(_info("  [1] ✍️  Saisie manuelle d'IPs (séparées par espaces/virgules)"))
        ctx.console.print(_info(f"  [2] 🖹 Charger le fichier par défaut ({DEFAULT_BLOCKLIST_FILE.name})"))
        ctx.console.print(_info(f"  [3] 🖹 Charger le fichier Fail2ban par défaut ({DEFAULT_F2B_BLOCKLIST_FILE.name})"))
        ctx.console.print(_info("  [4] 🖿  Parcourir / Sélectionner un fichier dans var/blocklist/"))
        ctx.console.print(_info("  [5] 🖈  Choisir / Gérer un fichier ÉPINGLÉ"))
        ctx.console.print(_info("  [6] ⌨️  Saisir un chemin de fichier personnalisé"))
        ctx.console.print(_info("  [0] ↩️  Annuler et revenir au menu"))
        ctx.console.print()

        mode_choice = ctx.console.input(_info("Votre choix [1] (ou 'annuler') : ")).strip() or "1"
        if is_cancel_word(mode_choice):
            ctx.console.print(_muted("Opération annulée."))
            return

        extracted_ips: set[str] = set()
        source_label = ""

        from omega_fire.infrastructure.storage.files.json_store import JsonStore
        from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand

        pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )
        pinned_files = pinned_command.list_paths()

        if mode_choice == "1":
            raw_ips = ctx.console.input(_info("Saisissez les IPs à débannir (ou 'annuler') : ")).strip()
            if not raw_ips or is_cancel_word(raw_ips):
                ctx.console.print(_muted("Opération annulée."))
                return
            extracted_ips = _extract_valid_ips(raw_ips)
            source_label = "Saisie manuelle"

        elif mode_choice == "2":
            source_label = f"Fichier {DEFAULT_BLOCKLIST_FILE.name}"
            extracted_ips = _safe_extract(str(DEFAULT_BLOCKLIST_FILE))

        elif mode_choice == "3":
            source_label = f"Fichier {DEFAULT_F2B_BLOCKLIST_FILE.name}"
            extracted_ips = _safe_extract(str(DEFAULT_F2B_BLOCKLIST_FILE))

        elif mode_choice == "4":
            if not os.path.exists(BLOCKLIST_DIR_STR):
                ctx.console.print(_error(f"Dossier '{BLOCKLIST_DIR_STR}' introuvable."))
                return
            all_files = [f for f in sorted(os.listdir(BLOCKLIST_DIR_STR)) if os.path.isfile(os.path.join(BLOCKLIST_DIR_STR, f))]
            if not all_files:
                ctx.console.print(_warning("Aucun fichier trouvé dans var/blocklist/."))
                return

            ctx.console.print(_info("\nFichiers disponibles :"))
            for idx, fname in enumerate(all_files, start=1):
                ctx.console.print(_info(f"  [{idx}] {fname}"))
            ctx.console.print(_info("  [0] Annuler"))

            f_idx = ctx.console.input(_info("\nNuméro du fichier (ou 'annuler') : ")).strip()
            if is_cancel_word(f_idx):
                ctx.console.print(_muted("Opération annulée."))
                return
            if not f_idx.isdigit() or not (1 <= int(f_idx) <= len(all_files)):
                ctx.console.print(_error("Sélection invalide."))
                return

            selected_file = all_files[int(f_idx) - 1]
            source_label = f"Fichier '{selected_file}'"
            extracted_ips = _safe_extract(os.path.join(BLOCKLIST_DIR_STR, selected_file))

        elif mode_choice == "5":
            ctx.console.print(_title("Fichiers Épinglés"))
            if pinned_files:
                for idx, path in enumerate(pinned_files, start=1):
                    ctx.console.print(_info(f"  [{idx}] {path}"))
            else:
                ctx.console.print(_info("  (Aucune épingle configurée)"))

            ctx.console.print(_info("\n  [A] Ajouter une nouvelle épingle"))
            ctx.console.print(_info("  [0] Retour / Annuler"))

            p_sel = ctx.console.input(_info("\nChoix : ")).strip().upper()
            if is_cancel_word(p_sel):
                ctx.console.print(_muted("Opération annulée."))
                return

            if p_sel == "A":
                new_pin = ctx.console.input(_info("Chemin complet du fichier à épingler (ou 'annuler') : ")).strip()
                if not new_pin or is_cancel_word(new_pin):
                    ctx.console.print(_muted("Opération annulée."))
                    return
                if os.path.exists(new_pin):
                    add_result = pinned_command.add_path(new_pin)
                    if add_result.success:
                        ctx.console.print(_success(f"Fichier '{new_pin}' épinglé."))
                    target_path = new_pin
                else:
                    ctx.console.print(_error("Fichier introuvable."))
                    return
            elif p_sel.isdigit() and 1 <= int(p_sel) <= len(pinned_files):
                target_path = pinned_files[int(p_sel) - 1]
            else:
                ctx.console.print(_warning("Choix d'épingle invalide."))
                return

            source_label = f"Épingle '{os.path.basename(target_path)}'"
            extracted_ips = _safe_extract(target_path)

        elif mode_choice == "6":
            target_path = ctx.console.input(_info("Saisissez le chemin complet du fichier (ou 'annuler') : ")).strip()
            if not target_path or is_cancel_word(target_path):
                ctx.console.print(_muted("Opération annulée."))
                return
            source_label = f"Fichier libre '{os.path.basename(target_path)}'"
            extracted_ips = _safe_extract(target_path)

        else:
            ctx.console.print(_error("Choix invalide."))
            return

        unique_ips = sorted(list(extracted_ips))
        if not unique_ips:
            ctx.console.print(_warning("Aucune adresse IP valide trouvée dans la source."))
            return

        ctx.console.print(_success(f"✔ {len(unique_ips)} IP(s) unique(s) identifiée(s) ({source_label})."))

        # 2. Détection des backends disponibles
        supported_backends = []
        for b_name in ("nftables", "iptables", "ip6tables", "fail2ban"):
            try:
                if ctx.container.get_firewall_port(b_name) is not None:
                    supported_backends.append(b_name)
            except Exception:
                continue

        if not supported_backends:
            ctx.console.print(_error("Aucun backend disponible pour le débannissement."))
            return

        ctx.console.print()
        if len(supported_backends) == 1:
            target_backends = list(supported_backends)
            ctx.console.print(_info(f"Backend cible : {supported_backends[0]} (seul backend disponible)"))
        else:
            ctx.console.print(_info("Backends disponibles :"))
            ctx.console.print(_info(
                f"  [Entrée] Débannir sur tous ({', '.join(supported_backends)}) — Recommandé"
            ), highlight=False)
            for idx, b_name in enumerate(supported_backends, start=1):
                ctx.console.print(_info(f"  [{idx}] Cibler uniquement {b_name} (diagnostic)"))
            ctx.console.print(_info("  [0] Annuler"))

            choice_b = ctx.console.input(_info("\nVotre choix : ")).strip()
            if is_cancel_word(choice_b):
                ctx.console.print(_muted("Opération annulée."))
                return
            elif not choice_b:
                target_backends = list(supported_backends)
            elif choice_b.isdigit() and 1 <= int(choice_b) <= len(supported_backends):
                target_backends = [supported_backends[int(choice_b) - 1]]
                ctx.console.print(_warning(
                    f"\nCiblage diagnostic : débannissement uniquement sur {target_backends[0]}. "
                    f"Une IP bannie ailleurs resterait bloquée malgré cette opération."
                ))
            else:
                ctx.console.print(_error("Choix invalide."))
                return

        # 3. Récapitulatif et confirmation finale
        ctx.console.print()
        ctx.console.print(_info(f"IPs à débannir : {len(unique_ips)}"))
        ctx.console.print(_info(f"Backend(s) : {', '.join(target_backends)}"))
        confirm = ctx.console.input(_info("\nConfirmez-vous le débannissement ? [o/N] : ")).strip().lower()
        if confirm not in ("o", "oui", "y", "yes"):
            ctx.console.print(_info("Opération annulée."))
            return

        # 4. Résolution des adapters et exécution
        adapters: dict[str, Any] = {}
        for b_name in target_backends:
            try:
                adapters[b_name] = ctx.container.get_firewall_port(b_name)
            except Exception:
                adapters[b_name] = None

        ctx.console.print(_info(f"\nTraitement du débannissement en cours sur {', '.join(target_backends)}..."))

        result = UnbanIpToAllBackendsCommand(adapters, getattr(ctx.container, "ban_repository", None)).execute(
            UnbanIpAllBackendsRequest(ips=unique_ips, target_backends=target_backends)
        )

        # 5. Tableau de Diagnostic par backend
        total_errors = 0
        for backend, outcome in result.outcomes.items():
            diag_table = Table(
                title=f"Rapport de Débannissement Groupé -> [{backend}]",
                show_header=True,
                header_style=theme_registry.get_style("table.header"),
                border_style=theme_registry.get_style("border.accent"),
                box=box.SQUARE,
                expand=False,
                padding=(0, 1),
            )
            diag_table.add_column("Métrique / Indicateur", style=theme_registry.get_style("text.main"), width=32)
            diag_table.add_column("Valeur", justify="right", style=theme_registry.get_style("text.info"), width=16)

            diag_table.add_row("Source des adresses", source_label)
            diag_table.add_row("IPs identifiées (Source)", str(len(unique_ips)))
            diag_table.add_row("IPs débannies avec succès", str(len(outcome.unbanned)))
            diag_table.add_row("IPs déjà libres (Ignorées)", str(len(outcome.already_free)))
            diag_table.add_row("Échecs / Erreurs de traitement", str(len(outcome.errors)))

            ctx.console.print()
            ctx.console.print(diag_table)

            for failed_ip, reason in outcome.errors:
                ctx.console.print(_error(f"  ❌ [{backend}] {failed_ip} : {reason}"))
            total_errors += len(outcome.errors)

        ctx.console.print()
        if total_errors == 0:
            ctx.console.print(_success("✔ Opération de débannissement terminée avec succès."))
        else:
            ctx.console.print(_warning(f"⚠️ Opération terminée avec {total_errors} erreur(s) réelle(s)."))

    _execute_action_flow(ctx, "2.4 Débannir une liste d'IPs", logic)

def action_2_5_list_banned(ctx: ActionContext) -> None:
    """2.5 — Lister les IP bannies."""
    def logic(out: List[Any]):
        from rich.table import Table
        from rich.text import Text
        from omega_fire.interfaces.cli.themes.registry import theme_registry

        if not ctx.container:
            ctx.console.print(_error("Conteneur non disponible."))
            return

        # 1. Détection dynamique des backends disponibles
        supported_backends = ["nftables", "iptables", "ip6tables"]
        try:
            if ctx.container.get_firewall_port("fail2ban") is not None:
                supported_backends.append("fail2ban")
        except Exception:
            pass  # Fail2ban non disponible/enregistré

        # 2. Présentation du sous-menu numéroté
        ctx.console.print(_info("\nBackends disponibles :"))
        ctx.console.print(_info("  [0] Tous les backends"))
        for idx, b_name in enumerate(supported_backends, start=1):
            ctx.console.print(_info(f"  [{idx}] {b_name}"))
        ctx.console.print(_muted("  [q] Annuler"))

        choice = ctx.console.input(
            _info(f"\nSélectionnez le backend (0-{len(supported_backends)}) [0 = Tous], ou 'q' pour annuler : ")
        ).strip()
        # "0" signifie déjà "tous les backends" ici — l'annulation utilise
        # un mot distinct (q/annuler/quit) pour ne pas changer ce sens.
        if choice.lower() in ("q", "quit", "annuler"):
            ctx.console.print(_muted("Opération annulée."))
            return

        # 3. Traitement de la sélection
        target_backends = []
        if not choice or choice == "0" or choice.lower() in ["tous", "all"]:
            target_backends = supported_backends
        elif choice.isdigit():
            idx_chosen = int(choice) - 1
            if 0 <= idx_chosen < len(supported_backends):
                target_backends = [supported_backends[idx_chosen]]
            else:
                ctx.console.print(_error("Choix invalide."))
                return
        else:
            if choice.lower() in supported_backends:
                target_backends = [choice.lower()]
            else:
                ctx.console.print(_error(f"Backend inconnu ou non disponible : '{choice}'."))
                return

        # 4. Collecte sécurisée des adresses bannies
        all_bans: List[dict] = []

        for b_name in target_backends:
            try:
                adapter = ctx.container.get_firewall_port(b_name)
                if not adapter:
                    continue

                bans = []
                if hasattr(adapter, "list_bans"):
                    bans = adapter.list_bans()
                elif hasattr(adapter, "list_banned_ips"):
                    bans = adapter.list_banned_ips()
                elif hasattr(adapter, "get_banned_ips"):
                    bans = adapter.get_banned_ips()

                for item in bans:
                    if isinstance(item, dict):
                        all_bans.append({
                            "ip": item.get("ip", "Inconnu"),
                            "backend": b_name,
                            "comment": item.get("comment", "-") or item.get("source", "-"),
                        })
                    elif hasattr(item, "ip"):
                        all_bans.append({
                            "ip": item.ip,
                            "backend": b_name,
                            "comment": getattr(item, "comment", "-") or "-",
                        })
                    else:
                        all_bans.append({
                            "ip": str(item),
                            "backend": b_name,
                            "comment": "-",
                        })
            except Exception:
                # Évite qu'un échec sur un backend n'empêche l'affichage des autres
                continue

        if not all_bans:
            ctx.console.print(_info("\nAucune IP bannie trouvée."))
            return

        # 5. Récupération des styles du thème
        border_s = theme_registry.get_style("border.default")
        title_s = theme_registry.get_style("text.heading")
        header_s = theme_registry.get_style("menu.selected")
        ip_s = theme_registry.get_style("action.error")
        backend_s = theme_registry.get_style("menu.item")
        comment_s = theme_registry.get_style("text.muted")

        # 6. Construction et affichage de la table Rich
        table = Table(
            title=Text(" IPs BANNIES ", style=title_s),
            border_style=border_s,
            header_style=header_s,
            expand=True,
            show_lines=False
        )

        table.add_column("Adresse IP", justify="left")
        table.add_column("Backend", justify="center")
        table.add_column("Source / Commentaire", justify="left")

        for entry in all_bans:
            table.add_row(
                Text(entry["ip"], style=ip_s),
                Text(entry["backend"], style=backend_s),
                Text(entry["comment"], style=comment_s)
            )

        ctx.console.print()
        ctx.console.print(table)

    _execute_action_flow(ctx, "2.5 Lister les IP bannies", logic)

def action_2_6_sync_backends(ctx: ActionContext) -> None:
    """2.6 — Synchroniser les backends."""
    def logic(out: List[Any]):
        if not ctx.container:
            ctx.console.print(_error("Conteneur non disponible."))
            return

        # 1. Détection des backends
        supported_backends = ["nftables", "iptables", "ip6tables"]
        try:
            if ctx.container.get_firewall_port("fail2ban") is not None:
                supported_backends.append("fail2ban")
        except Exception:
            pass

        # 2. Sous-menu numéroté
        ctx.console.print(_info("\nBackends à synchroniser :"))
        ctx.console.print(_info("  [0] Tous les backends"))
        for idx, b_name in enumerate(supported_backends, start=1):
            ctx.console.print(_info(f"  [{idx}] {b_name}"))
        ctx.console.print(_muted("  [q] Annuler"))

        choice = ctx.console.input(
            _info(f"\nSélectionnez (0-{len(supported_backends)}) [0 = Tous], ou 'q' pour annuler : ")
        ).strip()
        # "0" signifie déjà "tous les backends" ici — l'annulation utilise
        # un mot distinct (q/annuler/quit) pour ne pas changer ce sens.
        if choice.lower() in ("q", "quit", "annuler"):
            ctx.console.print(_muted("Opération annulée."))
            return

        if not choice or choice == "0":
            target_backends = supported_backends
        elif choice.isdigit():
            idx_chosen = int(choice) - 1
            if 0 <= idx_chosen < len(supported_backends):
                target_backends = [supported_backends[idx_chosen]]
            else:
                ctx.console.print(_error("Choix invalide."))
                return
        else:
            if choice.lower() in supported_backends:
                target_backends = [choice.lower()]
            else:
                ctx.console.print(_error(f"Backend inconnu : '{choice}'."))
                return

        # 3. Résolution des adapters et exécution de la réconciliation
        adapters = {}
        for b_name in supported_backends:
            try:
                adapters[b_name] = ctx.container.get_firewall_port(b_name)
            except Exception:
                adapters[b_name] = None

        command = SyncBackendsCommand(adapters=adapters)
        result = command.execute(target_backends=target_backends)

        # 4. Affichage du résultat
        if not any(o.added_count or o.errors for o in result.outcomes) and result.total_added == 0:
            ctx.console.print(_info("\nAucune IP bannie à synchroniser."))
            return

        for outcome in result.outcomes:
            if outcome.errors:
                for err in outcome.errors:
                    ctx.console.print(_error(f"  ❌ [{outcome.backend}] Échec pour {err}"))
            if outcome.added_count > 0:
                ctx.console.print(_success(f"  [+] [{outcome.backend}] {outcome.added_count} IP(s) manquante(s) ajoutée(s)."))
            elif not outcome.errors:
                ctx.console.print(_info(f"  • [{outcome.backend}] Déjà à jour (0 IP à ajouter)."))

        if result.total_added == 0:
            ctx.console.print(_info("\n✔ Tous les backends ciblés étaient déjà parfaitement synchronisés."))
        else:
            ctx.console.print(_success(f"\n[+] Synchronisation terminée : {result.total_added} IP(s) au total ont été réalignées."))

    _execute_action_flow(ctx, "2.6 Synchroniser les backends", logic)

def action_2_7_import_file(ctx: ActionContext) -> None:
    """2.7 — Gérer les fichiers Blocklist (importer, créer, éditer, bannir)."""
    def logic(out: List[Any]):
        from rich.box import ROUNDED
        from rich.table import Table
        from omega_fire.infrastructure.storage.files.text_store import TextStore
        from omega_fire.application.commands.manage_blocklist_file import ManageBlocklistFileCommand
        from omega_fire.application.commands.ban_ip_all_backends import (
            BanIpToAllBackendsCommand,
            BanIpAllBackendsRequest,
        )

        if not ctx.container:
            ctx.console.print(_error("Conteneur non disponible."))
            return

        store = TextStore(BLOCKLIST_DIR)
        manager = ManageBlocklistFileCommand(store)

        style_border = theme_registry.get_style("border.default")
        style_heading = theme_registry.get_style("text.heading")
        style_muted = theme_registry.get_style("text.muted")
        style_main = theme_registry.get_style("text.main")
        style_success = theme_registry.get_style("action.success")
        style_warning = theme_registry.get_style("action.warning")

        def _pause() -> None:
            pause_prompt(ctx.console)

        def _show_content(file_name: str) -> None:
            content = manager.load_file(file_name)
            if not content.success:
                ctx.console.print(_error(content.message))
                return

            ctx.console.print()
            ctx.console.print(_title(f"Contenu de {file_name}"))

            if content.valid_ips:
                ip_table = Table(box=ROUNDED, border_style=style_border, header_style=style_heading, expand=True)
                ip_table.add_column("IP / Réseau valide", style=style_success)
                for ip in content.valid_ips:
                    ip_table.add_row(ip)
                ctx.console.print(ip_table)
            else:
                ctx.console.print(_info("Aucune IP valide dans ce fichier."))

            if content.rejected_lines:
                ctx.console.print()
                rej_table = Table(
                    title="Lignes à corriger",
                    title_style=style_warning,
                    box=ROUNDED, border_style=style_border, header_style=style_heading, expand=True,
                )
                rej_table.add_column("Ligne", style=style_muted, justify="center", width=6)
                rej_table.add_column("Contenu brut", style=style_main)
                rej_table.add_column("Raison", style=style_warning)
                for line in content.rejected_lines:
                    rej_table.add_row(str(line.line_number), line.raw, line.reason or "")
                ctx.console.print(rej_table)

        def _add_ip(file_name: str) -> None:
            ip_input = ctx.console.input(_info("IP ou réseau CIDR à ajouter (ou 'annuler') : ")).strip()
            if not ip_input or is_cancel_word(ip_input):
                ctx.console.print(_muted("Opération annulée."))
                return
            comment = ctx.console.input(_info("Commentaire (optionnel, ou 'annuler') : ")).strip()
            if is_cancel_word(comment):
                ctx.console.print(_muted("Opération annulée."))
                return
            result = manager.add_ip(file_name, ip_input, comment)
            if result.success:
                ctx.console.print(_success(result.message))
            else:
                ctx.console.print(_error(result.message))

        def _remove_ip(file_name: str) -> None:
            ip_input = ctx.console.input(_info("IP ou réseau CIDR à retirer (ou 'annuler') : ")).strip()
            if not ip_input or is_cancel_word(ip_input):
                ctx.console.print(_muted("Opération annulée."))
                return
            result = manager.remove_ip(file_name, ip_input)
            if result.success:
                ctx.console.print(_success(result.message))
            else:
                ctx.console.print(_error(result.message))

        def _rename(file_name: str) -> Optional[str]:
            new_name = ctx.console.input(_info(f"Nouveau nom pour '{file_name}' (ou 'annuler') : ")).strip()
            if not new_name or is_cancel_word(new_name):
                ctx.console.print(_muted("Opération annulée."))
                return None
            result = manager.rename_file(file_name, new_name)
            if result.success:
                ctx.console.print(_success(result.message))
                return new_name
            ctx.console.print(_error(result.message))
            return None

        def _delete(file_name: str) -> bool:
            confirm = ctx.console.input(
                _warning(f"Confirmez-vous la suppression de '{file_name}' ? [o/N] : ")
            ).strip().lower()
            if confirm not in ("o", "oui", "y", "yes"):
                ctx.console.print(_info("Suppression annulée."))
                return False
            result = manager.delete_file(file_name)
            if result.success:
                ctx.console.print(_success(result.message))
                return True
            ctx.console.print(_error(result.message))
            return False

        def _ban_from_file(file_name: str) -> None:
            content = manager.load_file(file_name)
            if not content.success:
                ctx.console.print(_error(content.message))
                return
            if not content.valid_ips:
                ctx.console.print(_warning("Aucune IP valide à bannir dans ce fichier."))
                return

            ctx.console.print()
            ctx.console.print(_title(f"Bannissement depuis fichier géré — {file_name}"))
            ctx.console.print(_success(f"{len(content.valid_ips)} IP(s) valide(s) prête(s) à être bannie(s)."))
            if content.rejected_lines:
                ctx.console.print(_warning(
                    f"{len(content.rejected_lines)} ligne(s) ignorée(s) (invalides) — voir option [1] pour le détail."
                ))

            supported_backends = []
            for b_name in ("nftables", "iptables", "ip6tables", "fail2ban"):
                try:
                    if ctx.container.get_firewall_port(b_name) is not None:
                        supported_backends.append(b_name)
                except Exception:
                    continue

            if not supported_backends:
                ctx.console.print(_error("Aucun backend disponible pour le bannissement."))
                return

            ctx.console.print()
            if len(supported_backends) == 1:
                target_backends = list(supported_backends)
                ctx.console.print(_info(f"Backend cible : {supported_backends[0]} (seul backend disponible)"))
            else:
                ctx.console.print(_info("Backends disponibles :"))
                ctx.console.print(_info(
                    f"  [Entrée] Bannir sur tous ({', '.join(supported_backends)}) — Recommandé"
                ), highlight=False)
                for idx, b_name in enumerate(supported_backends, start=1):
                    ctx.console.print(_info(f"  [{idx}] Cibler uniquement {b_name} (diagnostic)"))
                ctx.console.print(_info("  [0] Annuler"))

                b_choice = ctx.console.input(_info("\nVotre choix : ")).strip()
                if is_cancel_word(b_choice):
                    ctx.console.print(_muted("Bannissement annulé."))
                    return
                elif not b_choice:
                    target_backends = list(supported_backends)
                elif b_choice.isdigit() and 1 <= int(b_choice) <= len(supported_backends):
                    target_backends = [supported_backends[int(b_choice) - 1]]
                else:
                    ctx.console.print(_error("Choix invalide."))
                    return

            comment = ctx.console.input(_info("\nCommentaire optionnel (ou 'annuler') : ")).strip()
            if is_cancel_word(comment):
                ctx.console.print(_muted("Bannissement annulé."))
                return

            ctx.console.print()
            ctx.console.print(_info(f"IPs à bannir : {len(content.valid_ips)}"))
            ctx.console.print(_info(f"Backend(s) : {', '.join(target_backends)}"))
            confirm = ctx.console.input(_info("\nConfirmez-vous le bannissement ? [o/N] : ")).strip().lower()
            if confirm not in ("o", "oui", "y", "yes"):
                ctx.console.print(_info("Bannissement annulé."))
                return

            adapters: dict[str, Any] = {}
            for b_name in target_backends:
                try:
                    adapters[b_name] = ctx.container.get_firewall_port(b_name)
                except Exception:
                    adapters[b_name] = None

            result = BanIpToAllBackendsCommand(adapters, getattr(ctx.container, "ban_repository", None)).execute(
                BanIpAllBackendsRequest(ips=content.valid_ips, comment=comment, target_backends=target_backends)
            )

            for backend, outcome in result.outcomes.items():
                diag_table = Table(
                    title=f"Rapport de Bannissement -> [{backend}]",
                    title_style=style_heading,
                    box=ROUNDED, border_style=style_border, header_style=style_heading, expand=False,
                )
                diag_table.add_column("Métrique", style=style_main, width=28)
                diag_table.add_column("Valeur", justify="right", style=style_success, width=12)
                diag_table.add_row("IPs identifiées (fichier)", str(len(content.valid_ips)))
                diag_table.add_row("Nouvelles IPs bannies", str(len(outcome.banned)))
                diag_table.add_row("IPs déjà bannies", str(len(outcome.already_banned)))
                diag_table.add_row("Échecs", str(len(outcome.errors)))
                ctx.console.print()
                ctx.console.print(diag_table)
                for failed_ip, reason in outcome.errors:
                    ctx.console.print(_error(f"  ❌ [{backend}] {failed_ip} : {reason}"))

        def _import_external_file() -> Optional[str]:
            """Importe un fichier depuis un chemin absolu arbitraire vers
            var/blocklist/ — copie, jamais déplacement, source intacte."""
            source_path = ctx.console.input(
                _info("Chemin complet du fichier à importer (ou 'annuler') : ")
            ).strip()
            if not source_path or is_cancel_word(source_path):
                ctx.console.print(_muted("Import annulé."))
                return None

            from pathlib import Path
            default_dest = Path(source_path).name

            dest_name = ctx.console.input(
                _info(f"Nom du fichier de destination [{default_dest}] (ou 'annuler') : ")
            ).strip()
            if is_cancel_word(dest_name):
                ctx.console.print(_muted("Import annulé."))
                return None
            dest_name = dest_name or default_dest

            result = manager.import_from_path(source_path, dest_name)
            if result.success:
                ctx.console.print(_success(result.message))
                if result.rejected_lines:
                    ctx.console.print(_warning(
                        f"{len(result.rejected_lines)} ligne(s) invalide(s) ignorée(s) à l'import."
                    ))
                return dest_name
            ctx.console.print(_error(result.message))
            return None

        def _file_submenu(file_name: str) -> None:
            current_name = file_name
            while True:
                ctx.console.print()
                ctx.console.print(_title(f"Fichier : {current_name}"))
                ctx.console.print(_info("  [1]  Afficher le contenu"))
                ctx.console.print(_info("  [2] ✚  Ajouter une IP"))
                ctx.console.print(_info("  [3] ✖ Retirer une IP"))
                ctx.console.print(_info("  [4] ✏️  Renommer ce fichier"))
                ctx.console.print(_info("  [5] 🗑️  Supprimer ce fichier"))
                ctx.console.print(_info("  [6] 󱁝  Bannir le contenu de ce fichier"))
                ctx.console.print(_info("  [0] ↩️  Retour à la liste des fichiers"))

                sub_choice = ctx.console.input(_info("\nVotre choix (ou 'annuler') : ")).strip()

                if not sub_choice or is_cancel_word(sub_choice):
                    return
                elif sub_choice == "1":
                    _show_content(current_name)
                    _pause()
                elif sub_choice == "2":
                    _add_ip(current_name)
                    _pause()
                elif sub_choice == "3":
                    _remove_ip(current_name)
                    _pause()
                elif sub_choice == "4":
                    renamed = _rename(current_name)
                    if renamed:
                        current_name = renamed
                    _pause()
                elif sub_choice == "5":
                    if _delete(current_name):
                        _pause()
                        return
                    _pause()
                elif sub_choice == "6":
                    _ban_from_file(current_name)
                    _pause()
                else:
                    ctx.console.print(_error("Choix invalide."))

        # ─── Boucle principale : liste des fichiers ───
        while True:
            ctx.console.print(_title("Gestion des fichiers Blocklist"))
            ctx.console.print()

            files = manager.list_files()

            if files:
                overview = Table(box=ROUNDED, border_style=style_border, header_style=style_heading, expand=True)
                overview.add_column("N°", style=style_muted, justify="center", width=4)
                overview.add_column("Fichier", style=style_main)
                overview.add_column("IPs valides", justify="center", style=style_success)
                overview.add_column("À corriger", justify="center", style=style_warning)

                previews = []
                for f in files:
                    content = manager.load_file(f.name)
                    previews.append(f.name)
                    overview.add_row(
                        str(len(previews)),
                        f.name,
                        str(len(content.valid_ips)) if content.success else "-",
                        str(len(content.rejected_lines)) if content.success and content.rejected_lines else "-",
                    )
                ctx.console.print(overview)
            else:
                previews = []
                ctx.console.print(_info("Aucun fichier dans var/blocklist/ pour le moment."))

            ctx.console.print()
            ctx.console.print(_info("  [I] 🗂️ Importer un fichier existant (depuis un autre dossier)"))
            ctx.console.print(_info("  [N] 🖉 Créer un nouveau fichier vide"))
            ctx.console.print(_info("  [0] ↩️  Retour au menu"))

            choice = ctx.console.input(_info("\nSélectionnez un fichier (numéro), [I], [N] ou [0] : ")).strip()

            if not choice or is_cancel_word(choice):
                return

            if choice.upper() == "I":
                imported_name = _import_external_file()
                _pause()
                if imported_name:
                    _file_submenu(imported_name)
                continue

            if choice.upper() == "N":
                new_name = ctx.console.input(_info("Nom du nouveau fichier (ex: custom.txt), ou 'annuler' : ")).strip()
                if not new_name or is_cancel_word(new_name):
                    ctx.console.print(_muted("Création annulée."))
                    _pause()
                    continue
                create_result = manager.create_file(new_name)
                if create_result.success:
                    ctx.console.print(_success(create_result.message))
                else:
                    ctx.console.print(_error(create_result.message))
                _pause()
                continue

            if not choice.isdigit() or not (1 <= int(choice) <= len(previews)):
                ctx.console.print(_error("Choix invalide."))
                _pause()
                continue

            _file_submenu(previews[int(choice) - 1])

    _execute_action_flow(ctx, "2.7 Gérer les fichiers Blocklist", logic)

def action_2_8_export_file(ctx: ActionContext) -> None:
    """2.8 — Exporter les IP bannies."""
    def logic(out: List[Any]):
        import os
        import re
        from datetime import datetime
        from rich import box
        from rich.table import Table
        from omega_fire.interfaces.cli.themes.registry import theme_registry

        if not ctx.container:
            ctx.console.print(_error("Conteneur non disponible."))
            return

        supported_backends = ["nftables", "iptables", "ip6tables"]
        try:
            if ctx.container.get_firewall_port("fail2ban") is not None:
                supported_backends.append("fail2ban")
        except Exception:
            pass

        default_folder = str(BLOCKLIST_DIR)
        default_file = str(DEFAULT_BLOCKLIST_FILE)

        # Initialisation centralisée des ÉPINGLES
        from omega_fire.infrastructure.storage.files.json_store import JsonStore
        from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand

        pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )
        pinned_files = pinned_command.list_paths()

        # Historique des fichiers RÉCENTS d'export — persisté (même bug de
        # fond que les épingles : ctx.recent_export_files n'était qu'un
        # attribut en mémoire sur ActionContext, jamais sauvegardé sur
        # disque, perdu à chaque redémarrage).
        recent_store = JsonStore(RUNTIME_DIR)
        RECENT_EXPORT_FILES_PATH = "recent_export_files.json"
        if recent_store.exists(RECENT_EXPORT_FILES_PATH):
            try:
                recent_files = recent_store.load(RECENT_EXPORT_FILES_PATH)
            except Exception:
                recent_files = []
        else:
            recent_files = []

        file_path = None
        write_mode = "w"  # Mode par défaut : 'w' (écraser)

        while True:
            current_target = file_path or default_file

            ctx.console.print(_title("Exportation de blocklist"))
            ctx.console.print(_info(f"Fichier cible : {current_target}\n"))
            ctx.console.print(_info("  [1] Exporter vers ce fichier"))
            ctx.console.print(_info("  [2] Générer une sauvegarde horodatée (Backup)"))
            ctx.console.print(_info("  [3] Parcourir / Choisir un fichier existant (Paginé)"))
            ctx.console.print(_info("  [4] Choisir un fichier récent"))
            ctx.console.print(_info("  [5] Saisir un chemin manuellement"))
            ctx.console.print(_info("  [6] Gérer / Choisir parmi les fichiers épinglés"))
            ctx.console.print(_info("  [0] Annuler et revenir au menu principal"))

            choice = ctx.console.input(_info("\nChoix [1] : ")).strip()

            if choice == "0":
                ctx.console.print(_info("\nAction annulée."))
                return

            if not choice or choice == "1":
                file_path = current_target
                
                # --- Sous-menu Mode d'écriture ---
                ctx.console.print(_title("Mode d'écriture dans le fichier"))
                ctx.console.print(_info("  [1] Écraser le fichier (Remplace tout) [Par défaut]"))
                ctx.console.print(_info("  [2] Rajouter (Ajoute à la fin sans vérifier)"))
                ctx.console.print(_info("  [3] Incrémenter (Ajoute uniquement les IP manquantes)"))
                ctx.console.print(_info("  [0] Retour"))

                m_choice = ctx.console.input(_info("\nChoix mode [1] : ")).strip()
                if m_choice == "0":
                    file_path = None
                    continue
                elif m_choice == "2":
                    write_mode = "a"
                elif m_choice == "3":
                    write_mode = "inc"
                else:
                    write_mode = "w"
                break

            elif choice == "2":
                ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                file_path = os.path.join(default_folder, f"blocklist_backup_{ts}.txt")
                write_mode = "w"
                break

            elif choice == "3":
                if not os.path.exists(default_folder):
                    ctx.console.print(_error(f"Dossier '{default_folder}' introuvable."))
                    continue

                all_files = [
                    f for f in os.listdir(default_folder) 
                    if os.path.isfile(os.path.join(default_folder, f))
                ]
                all_files.sort(
                    key=lambda x: os.path.getmtime(os.path.join(default_folder, x)), 
                    reverse=True
                )

                if not all_files:
                    ctx.console.print(_info("Dossier vide."))
                    continue

                # Liste complète, numérotation globale — la pagination à
                # l'écran est désormais automatique (cf. pager.py), plus
                # besoin d'une navigation [N]/[P] dédiée par page.
                ctx.console.print(_title(f"Fichiers dans {default_folder}"))
                for idx, fname in enumerate(all_files, start=1):
                    filepath = os.path.join(default_folder, fname)
                    mtime = os.path.getmtime(filepath)
                    date_str = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y %H:%M:%S")
                    ctx.console.print(_info(f"  [{idx}] {fname} ({date_str})"))

                ctx.console.print(_info("\n[R] Retour"))
                nav_choice = ctx.console.input(_info("Sélectionnez un fichier ou [R] : ")).strip().upper()

                if nav_choice.isdigit():
                    file_idx = int(nav_choice) - 1
                    if 0 <= file_idx < len(all_files):
                        file_path = os.path.join(default_folder, all_files[file_idx])

                if file_path:
                    # Demander le mode pour le fichier sélectionné
                    ctx.console.print(_title("Mode d'écriture"))
                    ctx.console.print(_info("  [1] Écraser [Par défaut]"))
                    ctx.console.print(_info("  [2] Rajouter"))
                    ctx.console.print(_info("  [3] Incrémenter (Nouvelles IP uniquement)"))
                    ctx.console.print(_info("  [0] Retour"))
                    m_choice = ctx.console.input(_info("\nChoix mode [1] : ")).strip()
                    if m_choice == "0":
                        file_path = None
                        continue
                    elif m_choice == "2":
                        write_mode = "a"
                    elif m_choice == "3":
                        write_mode = "inc"
                    else:
                        write_mode = "w"
                    break

            elif choice == "4":
                if not recent_files:
                    ctx.console.print(_info("Aucun historique récent."))
                    continue
                ctx.console.print(_title("Fichiers récents"))
                for idx, path in enumerate(recent_files, start=1):
                    ctx.console.print(_info(f"  [{idx}] {path}"))
                ctx.console.print(_info("  [0] Annuler"))
                r_choice = ctx.console.input(_info("\nSélectionnez un numéro : ")).strip()
                if r_choice == "0":
                    continue
                if r_choice.isdigit() and 0 <= int(r_choice) - 1 < len(recent_files):
                    file_path = recent_files[int(r_choice) - 1]
                    write_mode = "w"
                    break

            elif choice == "5":
                u_path = ctx.console.input(_info("Chemin complet (ou 'annuler') : ")).strip()
                if u_path and not is_cancel_word(u_path):
                    file_path = u_path
                    write_mode = "w"
                    break

            # --- NOUVEAU MENU [6] : Gestion des Fichiers Épinglés ---
            elif choice == "6":
                ctx.console.print(_title("Gestion des fichiers épinglés"))
                if pinned_files:
                    for idx, path in enumerate(pinned_files, start=1):
                        ctx.console.print(_info(f"  [{idx}] {path}"))
                else:
                    ctx.console.print(_info("  (Aucun fichier épinglé)"))
                
                ctx.console.print()
                ctx.console.print(_info("  [A] Épingler un nouveau fichier (saisie manuelle)"))
                if pinned_files:
                    ctx.console.print(_info("  [D] Retirer un fichier des épingles"))
                ctx.console.print(_info("  [0] Annuler et revenir au menu principal"))

                pin_choice = ctx.console.input(_info("\nChoix (Numéro de fichier ou A/D/0) : ")).strip().upper()

                if pin_choice == "0":
                    continue

                elif pin_choice == "A":
                    new_pin = ctx.console.input(_info("Chemin complet du fichier à épingler (ou 'annuler') : ")).strip()
                    if new_pin and not is_cancel_word(new_pin):
                        try:
                            folder = os.path.dirname(new_pin)
                            if folder and not os.path.exists(folder):
                                os.makedirs(folder, exist_ok=True)
                            if not os.path.exists(new_pin):
                                with open(new_pin, "w", encoding="utf-8") as f:
                                    f.write("# OmegaFire Blocklist\n")

                            add_result = pinned_command.add_path(new_pin)
                            if add_result.success:
                                ctx.console.print(_success(f"✔ Fichier '{new_pin}' épinglé et prêt."))
                        except Exception as e:
                            ctx.console.print(_error(f"Erreur création épingle : {e}"))
                    continue

                elif pin_choice.isdigit() and 0 <= int(pin_choice) - 1 < len(pinned_files):
                    file_path = pinned_files[int(pin_choice) - 1]

                    # Choix du mode d'écriture pour l'épingle sélectionnée
                    ctx.console.print(_title(f"Mode d'écriture pour : {file_path}"))
                    ctx.console.print(_info("  [1] Écraser le fichier [Par défaut]"))
                    ctx.console.print(_info("  [2] Rajouter à la fin"))
                    ctx.console.print(_info("  [3] Incrémenter (Nouvelles IP uniquement)"))
                    ctx.console.print(_info("  [0] Annuler / Retour"))

                    m_choice = ctx.console.input(_info("\nChoix mode [1] : ")).strip()
                    if m_choice == "0":
                        file_path = None
                        continue
                    elif m_choice == "2":
                        write_mode = "a"
                    elif m_choice == "3":
                        write_mode = "inc"
                    else:
                        write_mode = "w"
                    break

        # Mise à jour de l'historique récent
        if file_path and file_path not in recent_files:
            recent_files.insert(0, file_path)
            recent_files = recent_files[:5]
            try:
                recent_store.save(RECENT_EXPORT_FILES_PATH, recent_files)
            except Exception:
                pass

        # --- Sélection Backends ---
        ctx.console.print(_title("Backends à exporter"))
        ctx.console.print(_info("  [0] Tous les backends"))
        for idx, b_name in enumerate(supported_backends, start=1):
            ctx.console.print(_info(f"  [{idx}] {b_name}"))

        b_choice = ctx.console.input(_info(f"\nChoix (0-{len(supported_backends)}) [0] : ")).strip()
        if not b_choice or b_choice == "0" or is_cancel_word(b_choice):
            target_backends = supported_backends
        elif b_choice.isdigit() and 1 <= int(b_choice) <= len(supported_backends):
            target_backends = [supported_backends[int(b_choice) - 1]]
        else:
            ctx.console.print(_error("Choix invalide."))
            return

        # --- Collecte des IP depuis les backends ---
        new_items: dict[str, str] = {}  # ip -> line_to_write

        for b_name in target_backends:
            try:
                adapter = ctx.container.get_firewall_port(b_name)
            except Exception:
                continue
            if not adapter:
                continue
            try:
                bans = getattr(adapter, "list_bans", lambda: [])() or getattr(adapter, "list_banned_ips", lambda: [])()
            except Exception:
                # Backend détecté mais interrogation refusée (ex: accès
                # noyau non privilégié) — ignoré proprement, comme le fait
                # déjà le reste du fichier pour ce même type d'appel (2.5,
                # 2.6, 2.9) plutôt que de faire planter tout l'export.
                continue
            for item in bans:
                ip = item.get("ip") if isinstance(item, dict) else getattr(item, "ip", str(item))
                comment = item.get("comment", "") if isinstance(item, dict) else getattr(item, "comment", "")
                if ip:
                    clean_ip = str(ip).split("/")[0].strip()
                    line = f"{clean_ip} # [{b_name}] {comment}".strip() if comment else f"{clean_ip} # [{b_name}]"
                    new_items[clean_ip] = line

        if not new_items:
            ctx.console.print(_info("\nAucune IP à exporter."))
            return

        # --- Traitement de l'écriture selon le mode & Diagnostic final ---
        already_present_count = 0
        added_count = 0
        error_count = 0
        mode_label = "Inconnu"

        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if write_mode == "w":
                mode_label = "Écraser"
                lines_to_write = [f"# OmegaFire Export - {now_str}"]
                lines_to_write.extend(new_items.values())
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines_to_write) + "\n")
                added_count = len(new_items)
                already_present_count = 0

            elif write_mode == "a":
                mode_label = "Rajouter"
                lines_to_write = [f"\n# OmegaFire Rajout - {now_str}"]
                lines_to_write.extend(new_items.values())
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write("\n".join(lines_to_write) + "\n")
                added_count = len(new_items)
                already_present_count = 0

            elif write_mode == "inc":
                mode_label = "Incrémenter"
                existing_ips = set()
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    existing_ips = _extract_valid_ips(content)

                # Filtrage : séparer les IP déjà présentés des nouvelles
                to_add = [line for ip, line in new_items.items() if ip not in existing_ips]
                already_present_count = len(new_items) - len(to_add)
                added_count = len(to_add)

                if to_add:
                    lines_to_write = [f"\n# OmegaFire Incrément - {now_str}"]
                    lines_to_write.extend(to_add)
                    with open(file_path, "a", encoding="utf-8") as f:
                        f.write("\n".join(lines_to_write) + "\n")

        except Exception as e:
            error_count = len(new_items)
            ctx.console.print(_error(f"\nErreur écriture : {str(e)}"))

        # --- RAPPORT DE SYNTHÈSE / RÉSUMÉ DES ACTIONS ---
        diag_table = Table(
            title="Rapport d'exportation de Blocklist",
            show_header=True,
            header_style=theme_registry.get_style("table.header"),
            border_style=theme_registry.get_style("border.accent"),
            box=box.SQUARE,
            expand=False,
            padding=(0, 1),
        )
        diag_table.add_column("Métrique", style=theme_registry.get_style("text.main"), width=28)
        diag_table.add_column("Valeur", justify="right", style=theme_registry.get_style("text.info"), width=12)

        diag_table.add_row("Fichier cible", os.path.basename(file_path))
        diag_table.add_row("Mode d'écriture", mode_label)
        diag_table.add_row("IPs collectées (Source)", str(len(new_items)))
        diag_table.add_row("IPs déjà présentes", str(already_present_count))
        diag_table.add_row("Nouvelles IPs écrites", str(added_count))
        diag_table.add_row("Échecs / Erreurs", str(error_count))

        ctx.console.print()
        ctx.console.print(diag_table)
        ctx.console.print()

        if error_count == 0:
            ctx.console.print(_success(f"✔ Exportation terminée avec succès dans '{file_path}'."))
        else:
            ctx.console.print(_error(f"✖ Une erreur est survenue lors de l'exportation."))

    _execute_action_flow(ctx, "2.8 Exporter les IP bannies", logic)

def action_2_9_flush_backends(ctx: ActionContext) -> None:
    """2.9 — Vider (Flush) la liste des IP bannies, sur tous les backends détectés par défaut."""
    def logic(out: List[Any]):
        from omega_fire.application.commands.unban_ip_all_backends import (
            UnbanIpToAllBackendsCommand,
            UnbanIpAllBackendsRequest,
        )

        if not ctx.container:
            ctx.console.print(_error("Conteneur non disponible."))
            return

        # 1. Détection dynamique des backends
        supported_backends = []
        for b_name in ("nftables", "iptables", "ip6tables", "fail2ban"):
            try:
                if ctx.container.get_firewall_port(b_name) is not None:
                    supported_backends.append(b_name)
            except Exception:
                continue

        if not supported_backends:
            ctx.console.print(_error("Aucun backend disponible pour le flush."))
            return

        # 2. Choix : tous par défaut, ou un backend spécifique (diagnostic)
        # — même convention que 2.1/2.2/2.3/2.4 : [Entrée] tous, [1..N]
        # ciblage, [0] annuler.
        ctx.console.print(_title("--- Vider la liste des IP bannies (Débannissement global) ---"))
        ctx.console.print(_info(
            f"  [Entrée] TOUS les backends détectés ({', '.join(supported_backends)}) — Recommandé"
        ), highlight=False)
        for idx, b_name in enumerate(supported_backends, start=1):
            ctx.console.print(_info(f"  [{idx}] Seul le backend : {b_name} (diagnostic)"))
        ctx.console.print(_info("  [0] Annuler"))

        choice = ctx.console.input(_info("\nVotre choix : ")).strip()

        if is_cancel_word(choice):
            ctx.console.print(_info("\nAction annulée."))
            return

        if not choice:
            target_backends = list(supported_backends)
            target_label = "TOUS LES BACKENDS (" + ", ".join(supported_backends) + ")"
        elif choice.isdigit() and 1 <= int(choice) <= len(supported_backends):
            target_backends = [supported_backends[int(choice) - 1]]
            target_label = (
                f"le backend '{target_backends[0]}' uniquement (diagnostic — "
                f"une IP bannie ailleurs resterait bloquée malgré cette purge)"
            )
        else:
            ctx.console.print(_error("Choix invalide."))
            return

        # 3. Confirmation
        ctx.console.print(_warning(f"\n⚠️  ATTENTION : Vous allez débannir TOUTES les adresses IP sur : {target_label}"))
        ctx.console.print(_info("👉 Vos règles de filtrage principales (ports autorisés, accès SSH, etc.) RESTERONT INTACTES."))

        confirm = ctx.console.input(_warning("\nConfirmez-vous le débannissement complet ? (o/N) : ")).strip().lower()

        if confirm not in ("o", "oui", "y", "yes"):
            ctx.console.print(_info("\nOpération annulée par l'utilisateur."))
            return

        # 4. Résolution des adapters et collecte de l'union des IPs bannies
        adapters: dict[str, Any] = {}
        for b_name in target_backends:
            try:
                adapters[b_name] = ctx.container.get_firewall_port(b_name)
            except Exception:
                adapters[b_name] = None

        all_banned_ips: set[str] = set()
        for b_name in target_backends:
            adapter = adapters.get(b_name)
            if adapter is None:
                continue
            try:
                raw_bans = []
                if hasattr(adapter, "list_bans"):
                    raw_bans = adapter.list_bans()
                elif hasattr(adapter, "list_banned_ips"):
                    raw_bans = adapter.list_banned_ips()

                for item in raw_bans:
                    ip = item.get("ip") if isinstance(item, dict) else getattr(item, "ip", None)
                    if ip:
                        all_banned_ips.add(str(ip).split("/")[0].strip())
            except Exception:
                continue

        if not all_banned_ips:
            ctx.console.print(_info("\nAucune IP bannie trouvée sur les backends ciblés."))
            return

        # 5. Exécution
        result = UnbanIpToAllBackendsCommand(adapters, getattr(ctx.container, "ban_repository", None)).execute(
            UnbanIpAllBackendsRequest(ips=sorted(all_banned_ips), target_backends=target_backends)
        )

        # 6. Rapport par backend
        flushed_count = 0
        for backend, outcome in result.outcomes.items():
            ctx.console.print()
            if outcome.unbanned:
                ctx.console.print(_success(f"[{backend}] [+] {len(outcome.unbanned)} IP(s) débannie(s)."))
                flushed_count += 1
            elif outcome.already_free and not outcome.errors:
                ctx.console.print(_info(f"[{backend}] • Aucune IP à débannir (déjà vide)."))
                flushed_count += 1
            for failed_ip, reason in outcome.errors:
                ctx.console.print(_error(f"[{backend}] ❌ Échec pour {failed_ip} : {reason}"))

        ctx.console.print()
        if flushed_count > 0:
            ctx.console.print(_success(f"[+] Purge effectuée avec succès sur {flushed_count}/{len(target_backends)} backend(s)."))
        else:
            ctx.console.print(_error("❌ Échec : Aucun backend n'a été vidé."))

    _execute_action_flow(ctx, "2.9 Vider les IP bannies", logic)

def action_3_1_create_advanced_rule(ctx: ActionContext) -> None:
    """3.1 — Créer une règle avancée (iptables / nftables)."""

    def logic(out: List[Any]):
        from omega_fire.application.commands.create_rule_all_backends import (
            CreateRuleToAllBackendsCommand,
            CreateRuleAllBackendsRequest,
        )
        from omega_fire.infrastructure.probe.network_probe import list_network_interfaces

        def prompt_cancel(msg: str) -> Optional[str]:
            """Helper de saisie sécurisée avec possibilité d'annulation."""
            val = ctx.console.input(_info(f"{msg} (ou 'q' pour annuler) : ")).strip()
            if val.lower() in ("q", "quit", "exit", "cancel"):
                return None
            return val

        def print_choice(num: str, label: str) -> None:
            """Affiche un choix de menu aux couleurs strictes du thème."""
            style_num = theme_registry.get_style("text.muted")
            style_label = theme_registry.get_style("text.main")

            t = Text()
            t.append("  [", style=style_num)
            t.append(num, style=style_num)
            t.append("] ", style=style_num)
            t.append(label, style=style_label)
            ctx.console.print(t)

        if not hasattr(ctx, "container") or not ctx.container or not hasattr(ctx.container, "rule_repository"):
            ctx.console.print(_error("Le conteneur ou le dépôt de règles n'est pas disponible."))
            return

        # ─── ÉTAPE 1 : Détection des backends disponibles (via capability_registry) ───
        # ─── ÉTAPE 1 : Détection des backends disponibles ───
        # Par défaut, la règle est créée sur TOUS les backends détectés
        # (cohérent avec le menu 3.4) — un profil restrictif actif sur un
        # seul backend n'annule jamais une règle ACCEPT posée sur l'autre
        # seulement, et une règle créée sur un seul backend pourrait donc
        # sembler active en 3.3 sans avoir d'effet réel si l'autre backend
        # bloque toujours ce trafic (deux chaînes au même hook = intersection,
        # jamais union). Un ciblage sur un seul backend reste possible pour
        # du diagnostic, à la responsabilité explicite de l'utilisateur.
        available_backends = []
        if hasattr(ctx, "capability_registry") and ctx.capability_registry:
            if ctx.capability_registry.is_available("nftables"):
                available_backends.append("nftables")
            if ctx.capability_registry.is_available("iptables"):
                available_backends.append("iptables")

        if not available_backends:
            ctx.console.print(_error(
                "Aucun backend firewall n'est disponible pour la création de règles "
                "(nftables et iptables non détectés)."
            ))
            return

        if len(available_backends) == 1:
            target_backends = list(available_backends)
            ctx.console.print(_info(f"\nBackend cible : {available_backends[0]} (seul backend disponible)\n"))
        else:
            ctx.console.print(_info("Backends pare-feu disponibles sur le système :"))
            ctx.console.print(_info(
                f"  [Entrée] Appliquer aux deux backends ({', '.join(available_backends)}) — Recommandé"
            ), highlight=False)
            for idx, b in enumerate(available_backends, start=1):
                print_choice(str(idx), f"Cibler uniquement {b} (diagnostic)")
            print_choice("0", "Annuler et revenir au menu")

            backend_choice = ctx.console.input(_info("\nVotre choix : ")).strip()

            if backend_choice == "0":
                ctx.console.print(_warning("\nOpération annulée."))
                return
            elif not backend_choice:
                target_backends = list(available_backends)
                ctx.console.print(_success(f"\nBackends cibles : {', '.join(target_backends)}\n"))
            else:
                try:
                    selected_idx = int(backend_choice) - 1
                    if not (0 <= selected_idx < len(available_backends)):
                        ctx.console.print(_error("Choix de backend invalide. Annulation."))
                        return
                    target_backends = [available_backends[selected_idx]]
                except ValueError:
                    ctx.console.print(_error("Saisie invalide. Annulation."))
                    return

                ctx.console.print(_warning(
                    f"\nCiblage diagnostic : la règle ne sera créée que sur {target_backends[0]}. "
                    f"Si un autre backend est actif, le comportement réel du système pourrait "
                    f"différer de ce qui est affiché pour ce backend seul — vérification à votre charge.\n"
                ))

        # ─── ÉTAPE 2 : Informations de base ───
        rule_name = ""
        while not rule_name:
            res = prompt_cancel("Nom de la règle (ex: BLOCK_SSH_ATTACKS)")
            if res is None:
                ctx.console.print(_warning("\nCréation de règle annulée."))
                return
            rule_name = res.strip().upper()
            if not rule_name:
                ctx.console.print(_warning("Le nom de la règle ne peut pas être vide."))

        description = prompt_cancel("Description (optionnel)")
        if description is None:
            ctx.console.print(_warning("\nCréation de règle annulée."))
            return

        # ─── ÉTAPE 3 : Action et Chaîne/Table ───
        ctx.console.print(_info("\nAction de la règle :"))
        print_choice("1", "🔒 DROP (Bloquer silencieusement - Défaut)")
        print_choice("2", "⛔ REJECT (Rejeter avec notification)")
        print_choice("3", "✔ ACCEPT (Autoriser)")
        print_choice("0", "↩️ Annuler")

        action_choice = prompt_cancel("Choix de l'action")
        if action_choice is None or action_choice == "0":
            ctx.console.print(_warning("\nCréation de règle annulée."))
            return
        action_map = {"2": "REJECT", "3": "ACCEPT"}
        rule_action = action_map.get(action_choice, "DROP")

        ctx.console.print(_info("\nChaîne / Flux :"))
        print_choice("1", "← INPUT (Trafic entrant - Défaut)")
        print_choice("2", "↔ FORWARD (Trafic routé/transitant)")
        print_choice("3", "→ OUTPUT (Trafic sortant)")
        print_choice("0", "↩️ Annuler")

        chain_choice = prompt_cancel("Choix de la chaîne")
        if chain_choice is None or chain_choice == "0":
            ctx.console.print(_warning("\nCréation de règle annulée."))
            return
        chain_map = {"2": "FORWARD", "3": "OUTPUT"}
        rule_chain = chain_map.get(chain_choice, "INPUT")

        # ─── ÉTAPE 4 : Critères réseau avec validation stricte ───
        ctx.console.print(_info("\nCritères réseau (Laissez vide pour 'TOUT/ANY') :"))

        proto_input = prompt_cancel("Protocole [tcp/udp/icmp/all, défaut: tcp]")
        if proto_input is None:
            ctx.console.print(_warning("\nCréation de règle annulée."))
            return
        protocol = proto_input.lower() if proto_input else "tcp"
        if protocol not in ("tcp", "udp", "icmp", "all"):
            ctx.console.print(_error("Protocole non reconnu. Annulation."))
            return

        src_ip = None
        while True:
            src_input = prompt_cancel("IP/Subnet Source (ex: 192.168.1.50 ou 10.0.0.0/24)")
            if src_input is None:
                ctx.console.print(_warning("\nCréation de règle annulée."))
                return
            if not src_input:
                break
            try:
                ipaddress.ip_network(src_input, strict=False)
                src_ip = src_input
                break
            except ValueError:
                ctx.console.print(_error("Adresse IP ou sous-réseau invalide (Format attendu : X.X.X.X ou X.X.X.X/YY)."))

        dst_ip = None
        while True:
            dst_input = prompt_cancel("IP/Subnet Destination (ex: 192.168.1.1)")
            if dst_input is None:
                ctx.console.print(_warning("\nCréation de règle annulée."))
                return
            if not dst_input:
                break
            try:
                ipaddress.ip_network(dst_input, strict=False)
                dst_ip = dst_input
                break
            except ValueError:
                ctx.console.print(_error("Adresse IP ou sous-réseau invalide."))

        dst_port = None
        if protocol in ("tcp", "udp"):
            while True:
                port_input = prompt_cancel("Port Destination (ex: 22, 80, 443)")
                if port_input is None:
                    ctx.console.print(_warning("\nCréation de règle annulée."))
                    return
                if not port_input:
                    break
                if port_input.isdigit() and 1 <= int(port_input) <= 65535:
                    dst_port = int(port_input)
                    break
                else:
                    ctx.console.print(_error("Le port doit être un entier valide compris entre 1 et 65535."))

        # ─── Interface réseau : détection système + choix + saisie manuelle ───
        detected_interfaces = list_network_interfaces()
        iface = None

        if detected_interfaces:
            ctx.console.print(_info("\nInterfaces réseau détectées sur ce système :"))
            for idx, name in enumerate(detected_interfaces, start=1):
                print_choice(str(idx), name)
            print_choice("m", "Saisir manuellement")
            print_choice("", "[Entrée] ANY (toutes interfaces)")

            iface_choice = prompt_cancel("Choix de l'interface")
            if iface_choice is None:
                ctx.console.print(_warning("\nCréation de règle annulée."))
                return

            if not iface_choice:
                iface = None
            elif iface_choice.lower() == "m":
                manual_input = prompt_cancel("Nom de l'interface (saisie libre)")
                if manual_input is None:
                    ctx.console.print(_warning("\nCréation de règle annulée."))
                    return
                iface = manual_input or None
                if iface and iface not in detected_interfaces:
                    ctx.console.print(_warning(
                        f"Interface '{iface}' non détectée sur ce système — la règle sera "
                        "créée mais pourrait ne pas être effective si l'interface n'existe pas."
                    ))
            elif iface_choice.isdigit() and 1 <= int(iface_choice) <= len(detected_interfaces):
                iface = detected_interfaces[int(iface_choice) - 1]
            else:
                ctx.console.print(_error("Choix invalide. Annulation."))
                return
        else:
            ctx.console.print(_warning(
                "\nDétection automatique des interfaces indisponible sur ce système."
            ))
            manual_input = prompt_cancel("Nom de l'interface (saisie libre, ou vide pour ANY)")
            if manual_input is None:
                ctx.console.print(_warning("\nCréation de règle annulée."))
                return
            iface = manual_input or None
            if iface:
                ctx.console.print(_warning(
                    f"Interface '{iface}' non vérifiable — la règle sera créée mais pourrait "
                    "ne pas être effective si l'interface n'existe pas."
                ))

        # ─── ÉTAPE 5 : Récapitulatif stylisé selon le thème ───
        ctx.console.print()

        from rich import box

        border_st = theme_registry.get_style("border.primary")
        header_st = theme_registry.get_style("text.heading")
        label_st = theme_registry.get_style("text.muted")
        value_st = theme_registry.get_style("text.main")

        summary_table = Table(
            title="[ Récapitulatif de la règle ]",
            title_style=header_st,
            box=box.SQUARE,
            border_style=border_st,
            header_style=header_st,
            expand=True,
            show_lines=False
        )

        summary_table.add_column("Paramètre", style=label_st)
        summary_table.add_column("Valeur", style=value_st)

        summary_table.add_row("Nom de la règle", rule_name)
        summary_table.add_row("Description", description or "N/A")
        summary_table.add_row("Backend(s) pare-feu", ", ".join(target_backends))
        summary_table.add_row("Action", rule_action)
        summary_table.add_row("Chaîne", rule_chain)
        summary_table.add_row("Protocole", protocol.upper())
        summary_table.add_row("IP Source", src_ip or "ANY (Toutes)")
        summary_table.add_row("IP Destination", dst_ip or "ANY (Toutes)")
        summary_table.add_row("Port Destination", str(dst_port) if dst_port else "ANY (Tous)")
        summary_table.add_row("Interface", iface or "ANY (Toutes)")

        ctx.console.print(summary_table)
        ctx.console.print()

        # ─── ÉTAPE 6 : Confirmation finale ───
        confirm = ctx.console.input(_info("Confirmez-vous l'enregistrement de cette règle ? [o/N] : ")).strip().lower()
        if confirm not in ("o", "oui", "y", "yes"):
            ctx.console.print(_warning("\nCréation de la règle annulée par l'utilisateur."))
            return

        # ─── ÉTAPE 7 : Création + application via CreateRuleToAllBackendsCommand ───
        multi_request = CreateRuleAllBackendsRequest(
            name=rule_name,
            action=rule_action,
            chain=rule_chain,
            protocol=protocol,
            source_cidr=src_ip,
            dest_cidr=dst_ip,
            dst_port=dst_port,
            interface=iface,
            description=description,
            target_backends=target_backends,
        )

        rule_adapters: dict[str, Any] = {}
        for target_backend in target_backends:
            try:
                rule_adapters[target_backend] = ctx.container.get_firewall_port(target_backend)
            except Exception:
                rule_adapters[target_backend] = None

        multi_result = CreateRuleToAllBackendsCommand(
            ctx.container.rule_repository, rule_adapters
        ).execute(multi_request)

        ctx.console.print()
        for outcome in multi_result.outcomes:
            if hasattr(ctx.container, "app_logger") and ctx.container.app_logger:
                ctx.container.app_logger.info(
                    f"Règle '{rule_name}' ({rule_action} {protocol}/{dst_port or 'ANY'}) "
                    f"créée sur {outcome.backend} (appliquée: {outcome.applied})."
                )
            if outcome.success and outcome.applied:
                ctx.console.print(_success(f"[{outcome.backend}] {outcome.message}"))
            elif outcome.success:
                ctx.console.print(_warning(f"[{outcome.backend}] {outcome.message}"))
            else:
                ctx.console.print(_error(f"[{outcome.backend}] {outcome.message}"))

    _execute_action_flow(ctx, "3.1 Créer une règle avancée", logic)

def action_3_2_delete_rule(ctx: ActionContext) -> None:
    """3.2 — Supprimer une règle de pare-feu."""

    def logic(out: List[Any]):
        from omega_fire.application.queries.list_persisted_rules import ListPersistedRulesQuery
        from omega_fire.application.queries.find_equivalent_rules import (
            FindEquivalentRulesQuery,
            FindEquivalentRulesRequest,
        )
        from omega_fire.application.commands.delete_rule import DeleteRuleCommand, DeleteRuleRequest

        if not hasattr(ctx, "container") or not ctx.container or not hasattr(ctx.container, "rule_repository"):
            ctx.console.print(_error("Le conteneur ou le dépôt de règles n'est pas disponible."))
            return

        # ─── ÉTAPE 1 : Récupération des règles persistées ───
        with gauge_status(ctx.console, "Lecture des règles..."):
            list_result = ListPersistedRulesQuery(ctx.container.rule_repository).execute()
        if not list_result.success:
            ctx.console.print(_error(list_result.message))
            return
        domain_rules = list_result.rules

        if not domain_rules:
            ctx.console.print(_warning("Aucune règle enregistrée en base de données."))
            return

        # Index par ID sur les objets domaine COMPLETS (protocole, source
        # CIDR inclus) — nécessaire pour la détection de règles sœurs
        # ci-dessous, contrairement à target_list qui ne garde que les
        # champs utiles à l'affichage.
        domain_rules_by_id = {
            getattr(r, "rule_id", None): r
            for r in domain_rules
            if getattr(r, "rule_id", None) is not None
        }

        # Séparation : Règles Omega-Fire vs Règles Système importées
        omega_rules = []
        system_rules = []

        for r in domain_rules:
            r_id = getattr(r, "rule_id", None) or getattr(r, "id", None)
            comment = r.comment or ""
            is_system = getattr(r, "origin", "imported") == "imported"

            item = {
                "id": r_id,
                "name": comment or f"Règle #{r_id}",
                "chain": str(getattr(r, "chain", "INPUT")).upper(),
                "action": str(getattr(r, "action", "ACCEPT")).upper(),
                "port": str(r.port_start) if r.port_start else "ANY",
                "backend": getattr(r, "backend", "nftables"),
                "is_system": is_system,
                "enabled": bool(getattr(r, "enabled", True)),
            }
            if is_system:
                system_rules.append(item)
            else:
                omega_rules.append(item)

        # Règles inactives, tous périmètres confondus — calculé une fois ici
        # pour l'option de nettoyage automatique (référentiel §85) : sur un
        # système avec beaucoup de règles importées, l'essentiel peut être
        # inactif (hérité d'une remontée système), rendant la sélection
        # manuelle ID par ID impraticable.
        inactive_rules = [r for r in (omega_rules + system_rules) if not r["enabled"]]

        # ─── ÉTAPE 2 : Choix du filtre d'affichage ───
        ctx.console.print(_info("Options de suppression :"))
        ctx.console.print(_info(f"  [1] Voir uniquement les règles Omega-Fire ({len(omega_rules)})"), highlight=False)
        ctx.console.print(_info(f"  [2] Voir les règles importées du système ({len(system_rules)})"), highlight=False)
        ctx.console.print(_info(f"  [3] Voir TOUTES les règles ({len(domain_rules)})"), highlight=False)
        if inactive_rules:
            ctx.console.print(_warning(f"  [4] 🧹 Nettoyer automatiquement les règles INACTIVES ({len(inactive_rules)})"), highlight=False)
        ctx.console.print(_muted("  [0] Annuler"))

        choice = ctx.console.input(_info("\nChoix [1/2/3/4] (Défaut: 1), ou '0' pour annuler : ")).strip() or "1"
        if choice.lower() in ("0", "q", "quit", "annuler"):
            ctx.console.print(_muted("Opération annulée."))
            return

        if choice == "4" and inactive_rules:
            _bulk_delete_inactive_rules(ctx, inactive_rules)
            return

        if choice == "1":
            target_list = omega_rules
            list_title = "Règles Omega-Fire (Locales)"
        elif choice == "2":
            target_list = system_rules
            list_title = "Règles Système / UFW (Importées)"
        else:
            target_list = omega_rules + system_rules
            list_title = "Toutes les règles"

        if not target_list:
            ctx.console.print(_warning("Aucune règle dans la catégorie sélectionnée."))
            return

        # ─── ÉTAPE 3 : Construction du tableau 100% conforme à Frame ───
        from rich.box import ROUNDED
        from rich.text import Text

        style_border = theme_registry.get_style("border.default")
        style_heading = theme_registry.get_style("text.heading")
        style_muted = theme_registry.get_style("text.muted")
        style_main = theme_registry.get_style("text.main")
        style_error = theme_registry.get_style("action.error")
        style_success = theme_registry.get_style("action.success")
        style_warning = theme_registry.get_style("action.warning")

        table = Table(
            box=ROUNDED,
            border_style=style_border,
            header_style=style_heading,
            expand=True,
        )
        table.add_column("ID BDD", style=style_muted, justify="center", width=8)
        table.add_column("Origine", justify="center", width=12)
        table.add_column("Nom / Commentaire", style=style_main)
        table.add_column("Chaîne", style=style_muted, justify="center", width=10)
        table.add_column("Action", justify="center", width=8)
        table.add_column("Port", style=style_main, justify="center", width=8)
        table.add_column("État", justify="center", width=8)

        for r in target_list:
            origin_badge = Text("SYSTÈME", style=style_warning) if r["is_system"] else Text("OMEGA", style=style_success)
            act_style = style_error if r["action"] in ("DROP", "REJECT") else style_success
            status_text = Text("ACTIF", style=style_success) if r["enabled"] else Text("INACTIF", style=style_muted)

            table.add_row(
                str(r["id"]),
                origin_badge,
                r["name"],
                r["chain"],
                Text(r["action"], style=act_style),
                r["port"],
                status_text,
            )

        ctx.console.print()
        ctx.console.print(_info(f"{list_title} :"))
        ctx.console.print(table)

        # ─── ÉTAPE 4 : Saisie et suppression (un ou plusieurs IDs, séparés par virgule) ───
        # ─── ÉTAPE 4 : Saisie des IDs à supprimer ───
        rule_ids_str = ctx.console.input(
            _info("\nEntrez le(s) ID(s) de(s) règle(s) à supprimer, séparé(s) par une virgule "
                  "(ex: 12,15,18) ou Entrée pour annuler : ")
        ).strip()
        if not rule_ids_str:
            ctx.console.print(_info("Suppression annulée."))
            return

        raw_ids = [part.strip() for part in rule_ids_str.split(",") if part.strip()]
        target_ids: List[int] = []
        invalid_entries: List[str] = []

        for raw_id in raw_ids:
            try:
                target_ids.append(int(raw_id))
            except ValueError:
                invalid_entries.append(raw_id)

        if invalid_entries:
            ctx.console.print(_error(
                f"ID(s) invalide(s) ignoré(s) : {', '.join(invalid_entries)} (doivent être des nombres)."
            ))

        if not target_ids:
            ctx.console.print(_error("Aucun ID valide fourni. Annulation."))
            return

        # ─── ÉTAPE 4.5 : Détection de règles sœurs sur d'autres backends ───
        # Pour chaque règle ciblée, vérifie si une règle équivalente existe
        # sur un AUTRE backend (même intention : chaîne, action, protocole,
        # port, source). Purement informatif — jamais de suppression
        # automatique décidée par le logiciel : l'utilisateur choisit
        # explicitement s'il retire la règle partout (par défaut,
        # cohérence) ou seulement ici (diagnostic, à ses risques).
        ids_to_delete: List[int] = []
        already_considered: set[int] = set()

        for target_id in target_ids:
            if target_id in already_considered:
                continue
            already_considered.add(target_id)
            ids_to_delete.append(target_id)

            domain_rule = domain_rules_by_id.get(target_id)
            if domain_rule is None:
                # ID inconnu : sera signalé comme échec par DeleteRuleCommand
                # lui-même à l'étape suivante, pas la peine de dupliquer ici.
                continue

            protocol_str = domain_rule.protocol.value if domain_rule.protocol else "ALL"

            equiv_result = FindEquivalentRulesQuery(ctx.container.rule_repository).execute(
                FindEquivalentRulesRequest(
                    exclude_backend=domain_rule.backend,
                    chain=domain_rule.chain.value,
                    action=domain_rule.action.value,
                    protocol=protocol_str,
                    port_start=domain_rule.port_start,
                    source_cidr=domain_rule.source_cidr,
                )
            )

            if not equiv_result.success or not equiv_result.rules:
                continue

            siblings = [
                s for s in equiv_result.rules
                if s.rule_id not in already_considered and s.rule_id not in target_ids
            ]
            if not siblings:
                continue

            ctx.console.print()
            for sibling in siblings:
                ctx.console.print(_warning(
                    f"La règle #{target_id} ({domain_rule.backend}) existe aussi sur "
                    f"{sibling.backend} (ID #{sibling.rule_id})."
                ))

            sibling_choice = ctx.console.input(
                _info(
                    "[Entrée] Supprimer aussi sur ce(s) backend(s) (recommandé, cohérence) "
                    "/ [n] Ne retirer que celle-ci (diagnostic) : "
                )
            ).strip().lower()

            for sibling in siblings:
                already_considered.add(sibling.rule_id)
                if sibling_choice not in ("n", "non", "no"):
                    ids_to_delete.append(sibling.rule_id)

        # ─── ÉTAPE 5 : Exécution des suppressions ───
        success_count = 0
        failure_count = 0

        for delete_id in ids_to_delete:
            domain_rule = domain_rules_by_id.get(delete_id)
            firewall_adapter = None
            if domain_rule is not None:
                try:
                    firewall_adapter = ctx.container.get_firewall_port(domain_rule.backend)
                except Exception:
                    firewall_adapter = None

            delete_result = DeleteRuleCommand(ctx.container.rule_repository, firewall_adapter).execute(
                DeleteRuleRequest(rule_id=delete_id)
            )
            if delete_result.success:
                success_count += 1
                ctx.console.print(_success(delete_result.message))
            else:
                failure_count += 1
                ctx.console.print(_error(delete_result.message))

        if len(ids_to_delete) > 1:
            ctx.console.print()
            ctx.console.print(_info(f"Résumé : {success_count} supprimée(s), {failure_count} échec(s)."))

    _execute_action_flow(ctx, "3.2 Supprimer une règle", logic)


def _bulk_delete_inactive_rules(ctx: ActionContext, inactive_rules: list) -> None:
    """Nettoyage en masse des règles INACTIVES (option [4] de 3.2) —
    chemin dédié, distinct de la suppression manuelle par ID : pas de
    détection de règles sœurs (qui demanderait une confirmation par
    règle, impraticable sur des centaines/milliers d'entrées héritées
    d'une remontée système), pas de ligne imprimée par règle supprimée
    (uniquement un résumé agrégé à la fin) — référentiel §85.
    """
    from omega_fire.application.commands.delete_rule import DeleteRuleCommand, DeleteRuleRequest

    by_origin = {"OMEGA": 0, "SYSTÈME": 0}
    by_backend: dict[str, int] = {}
    for r in inactive_rules:
        by_origin["SYSTÈME" if r["is_system"] else "OMEGA"] += 1
        by_backend[r["backend"]] = by_backend.get(r["backend"], 0) + 1

    ctx.console.print()
    ctx.console.print(_warning(f"⚠️  {len(inactive_rules)} règle(s) INACTIVE(S) trouvée(s) :"))
    ctx.console.print(_info(f"    Origine : {by_origin['OMEGA']} Omega-Fire, {by_origin['SYSTÈME']} système importées"))
    ctx.console.print(_info(f"    Backend : {', '.join(f'{k}={v}' for k, v in by_backend.items())}"))
    ctx.console.print()
    ctx.console.print(_warning("Suppression réelle et immédiate sur le(s) backend(s) — aucune règle ACTIVE n'est concernée."))

    confirm = ctx.console.input(_warning(f"\nSupprimer ces {len(inactive_rules)} règle(s) inactive(s) ? (o/N) : ")).strip().lower()
    if confirm not in ("o", "oui", "y", "yes"):
        ctx.console.print(_muted("Nettoyage annulé."))
        return

    success_count = 0
    failure_count = 0
    failures: list[str] = []

    with gauge_status(ctx.console, f"Suppression de {len(inactive_rules)} règle(s) inactive(s)..."):
        for r in inactive_rules:
            # Adapter volontairement jamais résolu ici : une règle "inactive"
            # (enabled=False) ne l'est QUE parce que sync_rules_from_backends
            # l'a constatée absente du noyau au dernier scan (seule voie qui
            # positionne enabled=False, cf. référentiel §85) — external_ref
            # y reste renseigné (valeur historique), donc passer un adapter
            # réel ici déclencherait une tentative de retrait noyau vouée à
            # l'échec (rien à retirer, c'est déjà parti), ce qui ferait
            # échouer ET annuler le nettoyage de l'entrée en base par
            # sécurité anti-orphelin de DeleteRuleCommand — contre-productif
            # pour ce chemin précis. En passant None, DeleteRuleCommand
            # nettoie directement la base (branche "adapter indisponible").
            delete_result = DeleteRuleCommand(ctx.container.rule_repository, firewall_adapter=None).execute(
                DeleteRuleRequest(rule_id=r["id"])
            )
            if delete_result.success:
                success_count += 1
            else:
                failure_count += 1
                failures.append(f"#{r['id']} : {delete_result.message}")

    ctx.console.print()
    ctx.console.print(_success(f"✔ Nettoyage terminé : {success_count} règle(s) supprimée(s)."))
    if failure_count:
        ctx.console.print(_error(f"❌ {failure_count} échec(s) :"))
        for line in failures[:20]:
            ctx.console.print(_error(f"    {line}"))
        if failure_count > 20:
            ctx.console.print(_muted(f"    ... et {failure_count - 20} autre(s)."))


def action_3_3_list_rules(ctx: ActionContext) -> None:
    """3.3 — Lister les règles de pare-feu détaillées."""

    def logic(out: List[Any]):
        from omega_fire.application.queries.list_persisted_rules import ListPersistedRulesQuery
        from omega_fire.application.commands.sync_rules_from_backends import (
            SyncRulesFromBackendsCommand,
            SyncRulesRequest,
        )

        if not hasattr(ctx, "container") or not ctx.container or not hasattr(ctx.container, "rule_repository"):
            ctx.console.print(_error("Le conteneur ou le dépôt de règles n'est pas disponible."))
            return

        # ─── ÉTAPE 0 : Synchronisation depuis les backends disponibles ───
        backends: dict[str, Any] = {}
        for backend_name in ("nftables", "iptables", "ip6tables"):
            try:
                adapter = ctx.container.get_firewall_port(backend_name)
                if adapter is not None:
                    backends[backend_name] = adapter
            except Exception:
                # Backend non détecté / non disponible : on l'ignore proprement,
                # conformément au principe de mode dégradé (une capacité MISSING
                # n'est jamais traitée comme disponible).
                continue

        if backends:
            with gauge_status(ctx.console, "Synchronisation des backends..."):
                sync_result = SyncRulesFromBackendsCommand(ctx.container.rule_repository).execute(
                    SyncRulesRequest(backends=backends)
                )
            if sync_result.success:
                ctx.console.print(_success(sync_result.message))
            else:
                ctx.console.print(_warning(sync_result.message))
        else:
            ctx.console.print(_warning("Aucun backend firewall disponible pour la synchronisation."))

        ctx.console.print()

        # ─── ÉTAPE 1 : Récupération des règles persistées ───
        list_result = ListPersistedRulesQuery(ctx.container.rule_repository).execute()
        if not list_result.success:
            ctx.console.print(_error(list_result.message))
            return
        rules = list_result.rules

        if not rules:
            ctx.console.print(_warning("Aucune règle pare-feu enregistrée ou active sur le système."))
            return

        # ─── ÉTAPE 2 : Construction du tableau 100% conforme à Frame ───
        ctx.console.print(_info("Liste globale des règles (Noyau Linux + BDD) :"))
        ctx.console.print()

        from rich.box import ROUNDED
        from rich.text import Text

        style_border = theme_registry.get_style("border.default")
        style_heading = theme_registry.get_style("text.heading")
        style_muted = theme_registry.get_style("text.muted")
        style_main = theme_registry.get_style("text.main")
        style_error = theme_registry.get_style("action.error")
        style_success = theme_registry.get_style("action.success")
        style_warning = theme_registry.get_style("action.warning")

        rules_table = Table(
            box=ROUNDED,
            border_style=style_border,
            header_style=style_heading,
            expand=True,
        )

        rules_table.add_column("ID", style=style_muted, justify="center", width=4)
        rules_table.add_column("Backend", style=style_heading, width=10)
        rules_table.add_column("Origine", justify="center", width=10)
        rules_table.add_column("Nom / Description", style=style_main)
        rules_table.add_column("Chaîne", style=style_muted, justify="center", width=9)
        rules_table.add_column("Action", justify="center", width=8)
        rules_table.add_column("Proto", style=style_muted, justify="center", width=6)
        rules_table.add_column("Port", style=style_main, justify="center", width=7)
        # width=40 : couvre une IPv6 complète avec /CIDR (jusqu'à 43
        # caractères, ex. "xxxx:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx/128")
        # — 15 (IPv4 max) ne suffisait plus (référentiel §52, plan IPv6
        # Phase C). La colonne "Nom / Description" (sans largeur fixe)
        # absorbe l'espace supplémentaire.
        rules_table.add_column("IP Source", style=style_main, width=40)
        rules_table.add_column("IP Dest.", style=style_main, width=40)
        rules_table.add_column("État", justify="center", width=8)

        for r in rules:
            chain_str = r.chain.value.upper() if hasattr(r.chain, "value") else str(r.chain or "INPUT").upper()
            action_str = r.action.value.upper() if hasattr(r.action, "value") else str(r.action or "ACCEPT").upper()
            proto_str = r.protocol.value.upper() if r.protocol and hasattr(r.protocol, "value") else "ALL"
            port_str = str(r.port_start) if r.port_start else "ANY"
            name_str = r.comment or f"Règle #{r.rule_id}"

            act_style = style_error if action_str in ("DROP", "REJECT") else style_success
            status_text = Text("ACTIF", style=style_success) if r.enabled else Text("INACTIF", style=style_muted)

            origin_badge = (
                Text("SYSTÈME", style=style_warning)
                if r.origin == "imported"
                else Text("OMEGA", style=style_success)
            )
            backend_style = style_warning if r.origin == "imported" else style_heading

            rules_table.add_row(
                str(r.rule_id),
                Text(r.backend, style=backend_style),
                origin_badge,
                name_str,
                chain_str,
                Text(action_str, style=act_style),
                proto_str,
                port_str,
                r.source_cidr or "ANY",
                r.dest_cidr or "ANY",
                status_text,
            )

        ctx.console.print(rules_table)

    _execute_action_flow(ctx, "3.3 Lister les règles", logic)
    
def action_3_4_apply_preset(ctx: ActionContext) -> None:
    """3.4 — Appliquer une politique prédéfinie."""

    def logic(out: List[Any]):
        import json
        from rich.box import ROUNDED
        from rich.text import Text
        from omega_fire.domain.rules.presets import list_presets, get_preset
        from omega_fire.application.commands.apply_preset import state_file_for
        from omega_fire.application.commands.apply_preset_all_backends import (
            ApplyPresetToAllBackendsCommand,
            ApplyPresetAllBackendsRequest,
        )

        if not hasattr(ctx, "container") or not ctx.container:
            ctx.console.print(_error("Le conteneur n'est pas disponible."))
            return

        def print_choice(num: str, label: str) -> None:
            style_num = theme_registry.get_style("text.muted")
            style_label = theme_registry.get_style("text.main")
            t = Text()
            t.append("  [", style=style_num)
            t.append(num, style=style_num)
            t.append("] ", style=style_num)
            t.append(label, style=style_label)
            ctx.console.print(t)

        
        # ─── ÉTAPE 0 : Lecture de l'état actif (les deux backends) ───
        # Les deux fichiers d'état sont lus indépendamment (jamais un seul
        # "premier trouvé") : depuis que les profils s'appliquent aux deux
        # backends simultanément, ils devraient normalement toujours
        # correspondre — sauf résidu d'une application ciblée antérieure à
        # ce changement, ou test manuel. Une divergence est affichée
        # explicitement plutôt que masquée.
        backend_states: dict[str, Optional[str]] = {}
        for candidate_backend in ("nftables", "iptables", "ip6tables"):
            candidate_state_file = state_file_for(candidate_backend)
            if candidate_state_file.exists():
                try:
                    data = json.loads(candidate_state_file.read_text(encoding="utf-8"))
                    backend_states[candidate_backend] = data.get("active_preset")
                except Exception:
                    backend_states[candidate_backend] = None
            else:
                backend_states[candidate_backend] = None

        style_border = theme_registry.get_style("border.default")
        style_heading = theme_registry.get_style("text.heading")
        style_main = theme_registry.get_style("text.main")
        style_muted = theme_registry.get_style("text.muted")
        style_success = theme_registry.get_style("action.success")
        style_warning = theme_registry.get_style("action.warning")

        # ─── ÉTAPE 1 : Affichage de l'état actif ───
        distinct_keys = {v for v in backend_states.values() if v}

        if not distinct_keys:
            ctx.console.print(_info("Profil actuellement ACTIF : Aucun (état antérieur / règles personnalisées)"))
        elif len(distinct_keys) == 1:
            active_key = next(iter(distinct_keys))
            preset_obj = get_preset(active_key)
            active_name = preset_obj.name if preset_obj else active_key
            applied_on = [b for b, k in backend_states.items() if k == active_key]
            ctx.console.print(_success(
                f"Profil actuellement ACTIF : {active_name} (sur {', '.join(applied_on)})"
            ))
        else:
            ctx.console.print(_warning("Profils actifs DIVERGENTS entre backends (résidu antérieur ?) :"))
            for b, k in backend_states.items():
                if k:
                    preset_obj = get_preset(k)
                    name = preset_obj.name if preset_obj else k
                    ctx.console.print(_warning(f"  • {b} : {name}"))
                else:
                    ctx.console.print(_muted(f"  • {b} : aucun profil tracké"))

        ctx.console.print()

        # ─── ÉTAPE 2 : Présentation des profils ───
        preset_table = Table(
            box=ROUNDED,
            border_style=style_border,
            header_style=style_heading,
            expand=True,
        )
        preset_table.add_column("Choix", style=style_muted, justify="center", width=7)
        preset_table.add_column("Statut", justify="center", width=10)
        preset_table.add_column("Profil", style=style_heading, width=18)
        preset_table.add_column("Description", style=style_main)
        preset_table.add_column("Politique", style=style_muted, justify="center", width=18)

        for preset in list_presets():
            is_active = preset.key in distinct_keys
            status_badge = Text("ACTIF", style=style_success) if is_active else Text("—", style=style_muted)
            preset_table.add_row(
                f"[{preset.key}]",
                status_badge,
                preset.name,
                preset.description,
                preset.policy_label,
            )

        ctx.console.print(preset_table)


        ctx.console.print()

        # ─── ÉTAPE 3 : Choix utilisateur ───
        choice = ctx.console.input(_info("Choix [1-9 + Entrée] (ou Entrée vide pour annuler) : ")).strip().upper()

        if not choice:
            ctx.console.print(_info("Opération annulée."))
            return

        # ─── OPTIONS ───
        if choice not in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
            ctx.console.print(_error("Choix invalide."))
            return

        selected_preset = get_preset(choice)
        if selected_preset is None:
            ctx.console.print(_error("Profil introuvable."))
            return

        # ─── ÉTAPE 4 : Détection des backends disponibles ───
        # Plus de choix : un profil s'applique désormais à TOUS les
        # backends détectés simultanément, pour qu'il reste représentatif
        # de l'état réel du système (voir application_all_backends.py).
        available_backends = []
        if hasattr(ctx, "capability_registry") and ctx.capability_registry:
            if ctx.capability_registry.is_available("nftables"):
                available_backends.append("nftables")
            if ctx.capability_registry.is_available("iptables"):
                available_backends.append("iptables")

        if not available_backends:
            ctx.console.print(_error(
                "Aucun backend firewall n'est disponible pour appliquer un profil "
                "(nftables et iptables non détectés)."
            ))
            return

        ctx.console.print(_info(
            f"\nCe profil sera appliqué sur TOUS les backends détectés : "
            f"{', '.join(available_backends)}."
        ))

        # ─── ÉTAPE 5 : Confirmation ───
        ctx.console.print()
        ctx.console.print(_warning(
            f"ATTENTION : L'application du profil '{selected_preset.name}' va REMPLACER "
            f"l'intégralité des règles actuellement actives sur CHAQUE backend détecté "
            f"({', '.join(available_backends)})."
        ))
        ctx.console.print(_info(
            "Une sauvegarde complète de l'état actuel (règles, IPs bannies, jails) sera "
            "automatiquement tentée avant l'application — consultable et restaurable ensuite "
            "via le menu 7.2 (Restaurer un état). Vous pouvez aussi la déclencher vous-même à "
            "tout moment via le menu 7.1 (Sauvegarder l'état complet)."
        ))
        confirm = ctx.console.input(_info("Confirmez-vous le basculement ? [o/N] : ")).strip().lower()
        if confirm not in ("o", "oui", "y", "yes"):
            ctx.console.print(_info("Application annulée."))
            return

        # ─── ÉTAPE 6 : Application via ApplyPresetToAllBackendsCommand ───
        preset_adapters = {}
        try:
            preset_adapters["nftables"] = ctx.container.get_firewall_port("nftables")
        except Exception:
            preset_adapters["nftables"] = None
        try:
            preset_adapters["iptables"] = ctx.container.get_firewall_port("iptables")
        except Exception:
            preset_adapters["iptables"] = None
        try:
            preset_adapters["ip6tables"] = ctx.container.get_firewall_port("ip6tables")
        except Exception:
            preset_adapters["ip6tables"] = None
        try:
            preset_adapters["fail2ban"] = ctx.container.get_fail2ban_port()
        except Exception:
            preset_adapters["fail2ban"] = None

        try:
            preset_persistence_port = ctx.container.get_persistence_port()
        except Exception:
            preset_persistence_port = None

        preset_rule_repository = getattr(ctx.container, "rule_repository", None)

        multi_result = ApplyPresetToAllBackendsCommand(
            adapters=preset_adapters,
            persistence_port=preset_persistence_port,
            rule_repository=preset_rule_repository,
        ).execute(
            ApplyPresetAllBackendsRequest(preset=selected_preset)
        )

        ctx.console.print()
        if multi_result.snapshot_warning:
            ctx.console.print(_warning(multi_result.snapshot_warning))

        for outcome in multi_result.outcomes:
            if outcome.success:
                if hasattr(ctx.container, "app_logger") and ctx.container.app_logger:
                    ctx.container.app_logger.info(
                        f"Profil '{selected_preset.name}' appliqué sur {outcome.backend}."
                    )
                ctx.console.print(_success(f"[{outcome.backend}] {outcome.message}"))
            else:
                ctx.console.print(_error(f"[{outcome.backend}] {outcome.message}"))

    _execute_action_flow(ctx, "3.4 Appliquer une politique prédéfinie", logic)

# ----------------------------------------------------------------------
# Menu 4 — Gestion Fail2ban
# ----------------------------------------------------------------------
def action_4_1_jails_status(ctx: ActionContext) -> None:
    """4.1 — Analyse et État des jails (via application/queries/jail_status.py, Phase 2)."""
    def logic(out: List[Any]):
        from rich import box
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        from omega_fire.application.queries.jail_status import get_jail_status
        from omega_fire.interfaces.cli.renderers.styles import get_terminal_width
        from omega_fire.interfaces.cli.keybindings import _flush_stdin

        fail2ban_port = None
        if ctx.container:
            try:
                fail2ban_port = ctx.container.get_fail2ban_port()
            except Exception:
                pass

        with gauge_status(ctx.console, "Scan des jails en cours..."):
            res = get_jail_status(fail2ban_port=fail2ban_port)

        # Purge du buffer clavier après un scan bloquant, avant la boucle de
        # saisie qui suit — même mécanisme que le correctif de
        # _execute_action_flow() (référentiel §82.5), nécessaire ici aussi
        # car cette action a sa propre boucle (pause_at_end=False).
        _flush_stdin()

        if not res.jails:
            ctx.console.print()
            ctx.console.print(_error(res.message or "Impossible de communiquer avec le service Fail2ban."))
            ctx.console.print(_info("Vérifiez que le service est démarré sur la machine : systemctl status fail2ban"))
            return

        def render_jails_table() -> None:
            table = Table(
                show_header=True,
                header_style=theme_registry.get_style("table.header"),
                border_style=theme_registry.get_style("border.accent"),
                box=box.SQUARE,
                expand=False,
                show_lines=False,
                padding=(0, 1),
            )

            table.add_column("N°", justify="right", style=theme_registry.get_style("text.info"), width=4, no_wrap=True)
            table.add_column("Nom", style=theme_registry.get_style("text.main"), width=12, no_wrap=True)
            table.add_column("Statut", style=theme_registry.get_style("text.info"), width=8, no_wrap=True)
            table.add_column("Bannis", justify="right", style=theme_registry.get_style("text.danger"), width=7, no_wrap=True)
            table.add_column("Filtre", style=theme_registry.get_style("text.main"), width=12, no_wrap=True)
            table.add_column("Log Path", style=theme_registry.get_style("text.muted"), width=25, no_wrap=True)
            table.add_column("Max Retry", justify="right", style=theme_registry.get_style("text.main"), width=9, no_wrap=True)
            table.add_column("Ban Time", justify="right", style=theme_registry.get_style("text.main"), width=9, no_wrap=True)

            for idx, jail in enumerate(res.jails, start=1):
                status_text = Text("Actif", style=theme_registry.get_style("status.available")) if jail.active else Text("Inactif", style=theme_registry.get_style("text.muted"))
                table.add_row(
                    str(idx),
                    jail.name,
                    status_text,
                    str(jail.banned_count),
                    jail.filter or "N/A",
                    jail.log_path or "N/A",
                    str(jail.max_retry),
                    f"{jail.ban_time}s",
                )

            panel = Panel(
                table,
                title="Jails Fail2ban",
                title_align="left",
                border_style=theme_registry.get_style("border.default"),
                padding=(0, 1),
                width=120,
            )

            ctx.console.print()
            ctx.console.print(panel)

        def render_ip_grid(ips: list[str]) -> None:
            """Grille multi-colonnes numérotée — même rendu que 4.2, pour
            garder une présentation cohérente entre "voir les IPs bannies"
            (4.1) et "choisir une IP à bannir/débannir" (4.2)."""
            if not ips:
                ctx.console.print(_muted("Aucune IP actuellement bannie."))
                return

            # jail.banned_ips contient des objets IPAddress (shared/networking.py),
            # pas des chaînes brutes — str() systématique avant toute mesure de
            # longueur ou affichage.
            ip_strs = [str(ip) for ip in ips]

            max_ip_len = max((len(s) for s in ip_strs), default=15)
            max_num_len = len(str(len(ip_strs)))
            cell_width = max_num_len + 3 + max_ip_len + 2
            available_width = max(get_terminal_width() - 6, cell_width)
            num_cols = max(1, min(3, available_width // cell_width))

            grid = Table(
                show_header=True,
                header_style=theme_registry.get_style("table.header"),
                border_style=theme_registry.get_style("border.accent"),
                box=box.SQUARE,
                expand=False,
                padding=(0, 1),
            )
            for col_idx in range(num_cols):
                grid.add_column(f"N° / IP (Col {col_idx + 1})", style=theme_registry.get_style("action.error"), width=cell_width)

            for i in range(0, len(ip_strs), num_cols):
                row_cells = []
                for j in range(num_cols):
                    if i + j < len(ip_strs):
                        row_cells.append(f"[{i + j + 1}] {ip_strs[i + j]}")
                    else:
                        row_cells.append("")
                grid.add_row(*row_cells)

            ctx.console.print(grid)

        render_jails_table()

        # --- Sous-menu d'analyse : localiser une/des IP(s) avant de les
        # traiter via 4.2 (bannir/débannir) ---
        while True:
            ctx.console.print()
            ctx.console.print(_title("Analyse des jails"))
            ctx.console.print(_info("  [1] Lister les IP d'un jail"))
            ctx.console.print(_info("  [2] Lister les IP de tous les jails"))
            ctx.console.print(_info("  [3] Vérifier si une IP est présente dans un jail"))
            ctx.console.print(_muted("  [0/q] Quitter"))

            choice = ctx.console.input(_info("\nVotre choix : ")).strip().lower()

            if choice in ("0", "q", ""):
                return

            elif choice == "1":
                num = ctx.console.input(_info(f"Numéro du jail (1-{len(res.jails)}, 'annuler' pour revenir) : ")).strip()
                if is_cancel_word(num):
                    continue
                if not num.isdigit() or not (1 <= int(num) <= len(res.jails)):
                    ctx.console.print(_warning("Numéro invalide."))
                    continue
                jail = res.jails[int(num) - 1]
                ctx.console.print()
                ctx.console.print(_info(f"IP(s) bannie(s) dans '{jail.name}' (Total : {jail.banned_count}) :"))
                render_ip_grid(jail.banned_ips)

            elif choice == "2":
                for jail in res.jails:
                    ctx.console.print()
                    ctx.console.print(_info(f"— {jail.name} ({jail.banned_count} IP(s) bannie(s)) —"))
                    render_ip_grid(jail.banned_ips)

            elif choice == "3":
                target_ip = ctx.console.input(_info("Adresse IP à rechercher ('annuler' pour revenir) : ")).strip()
                if is_cancel_word(target_ip):
                    continue
                try:
                    ipaddress.ip_address(target_ip)
                except ValueError:
                    ctx.console.print(_error("Format d'adresse IP invalide."))
                    continue

                found_in = [
                    jail.name for jail in res.jails
                    if any(str(ip) == target_ip for ip in jail.banned_ips)
                ]
                ctx.console.print()
                if found_in:
                    ctx.console.print(_success(
                        f"✔ {target_ip} trouvée dans {len(found_in)} jail(s) : {', '.join(found_in)}"
                    ))
                    ctx.console.print(_info("Utilisez le menu 4.2 (Bannir/Débannir) pour la retirer."))
                else:
                    ctx.console.print(_warning(f"{target_ip} n'a été trouvée dans aucun jail actif."))

            else:
                ctx.console.print(_error("Choix invalide."))

    _execute_action_flow(ctx, "4.1 Analyse et État des jails", logic, pause_at_end=False)

def action_4_2_jail_ban_unban(ctx: ActionContext) -> None:
    """4.2 — Bannir/Débannir dans un jail (Multi-IPs, pagination multi-colonnes et option [0] Annuler)."""
    def logic(out: List[Any]):
        import ipaddress
        from rich import box
        from rich.table import Table
        from rich.text import Text

        prompt_mgr = PromptManager(ctx.console)

        fail2ban_port = None
        if ctx.container:
            try:
                fail2ban_port = ctx.container.get_fail2ban_port()
            except Exception:
                pass

        jails_info: list[dict] = []

        # 1. Collecte temps réel des Jails détectés et de leurs IPs (via le port officiel)
        if fail2ban_port:
            try:
                with gauge_status(ctx.console, "Collecte des jails..."):
                    jail_names = fail2ban_port.list_jails()
                    for name in jail_names:
                        try:
                            status = fail2ban_port.get_jail_status(name)
                        except Exception:
                            status = {}
                        jails_info.append({
                            "name": name,
                            "banned_ips": status.get("banned_ips", []),
                        })
            except Exception:
                jails_info = []

        if not jails_info:
            ctx.console.print(_error("Impossible de communiquer avec le service Fail2ban."))
            return

        # 2. Affichage du tableau des Jails avec option [0]
        ctx.console.print(_info("Sélectionnez le Jail cible :"))
        ctx.console.print()

        table = Table(
            show_header=True,
            header_style=theme_registry.get_style("table.header"),
            border_style=theme_registry.get_style("border.accent"),
            box=box.SQUARE,
            expand=False,
            padding=(0, 1),
        )
        table.add_column("N°", style=theme_registry.get_style("text.info"), width=4, justify="right")
        table.add_column("Nom du Jail", style=theme_registry.get_style("text.main"), width=20)
        table.add_column("Statut", style=theme_registry.get_style("text.info"), width=10, justify="center")
        table.add_column("IPs Bannies", style=theme_registry.get_style("text.danger"), width=12, justify="right")

        for idx, jail in enumerate(jails_info, start=1):
            status_badge = Text("Détecté", style=theme_registry.get_style("status.available"))
            banned_count = len(jail.get("banned_ips", []))
            table.add_row(str(idx), jail["name"], status_badge, str(banned_count))

        ctx.console.print(table)
        ctx.console.print()

        # 3. Choix du Jail
        choice_jail = prompt_mgr.ask_text(_info(f"Votre choix (0-{len(jails_info)}) [0] : ")).strip() or "0"
        if is_cancel_word(choice_jail):
            ctx.console.print(_muted("Opération annulée."))
            return

        if not choice_jail.isdigit() or not (1 <= int(choice_jail) <= len(jails_info)):
            ctx.console.print(_warning(f"Choix invalide ('{choice_jail}'). Opération annulée."))
            return

        selected_jail_data = jails_info[int(choice_jail) - 1]
        selected_jail = selected_jail_data["name"]

        # 4. Affichage MULTI-COLONNES des IPs bannies (numérotation globale,
        # pagination à l'écran désormais automatique — cf. pager.py)
        currently_banned: list[str] = selected_jail_data.get("banned_ips", [])

        ctx.console.print()
        if currently_banned:
            ctx.console.print(_info(f"IP(s) bannie(s) dans '{selected_jail}' (Total : {len(currently_banned)}) :"))

            # Nombre de colonnes et largeur de cellule calculés dynamiquement
            # à partir de la longueur réelle des IPs affichées et de la
            # largeur du terminal — un tableau à 3 colonnes de 24 (IPv4 max)
            # coupait une IPv6 (référentiel §52, plan IPv6 Phase C). Une
            # liste 100% IPv4 retombe naturellement sur 3 colonnes comme
            # avant ce correctif.
            from omega_fire.interfaces.cli.renderers.styles import get_terminal_width

            max_ip_len = max((len(ip) for ip in currently_banned), default=15)
            max_num_len = len(str(len(currently_banned)))
            cell_width = max_num_len + 3 + max_ip_len + 2  # "[N] " + IP + marge
            available_width = max(get_terminal_width() - 6, cell_width)
            num_cols = max(1, min(3, available_width // cell_width))

            grid_table = Table(
                show_header=True,
                header_style=theme_registry.get_style("table.header"),
                border_style=theme_registry.get_style("border.accent"),
                box=box.SQUARE,
                expand=False,
                padding=(0, 1),
            )
            for col_idx in range(num_cols):
                grid_table.add_column(
                    f"N° / IP (Col {col_idx + 1})",
                    style=theme_registry.get_style("action.error"),
                    width=cell_width,
                )

            for i in range(0, len(currently_banned), num_cols):
                row_cells = []
                for j in range(num_cols):
                    if i + j < len(currently_banned):
                        global_num = i + j + 1
                        ip_val = currently_banned[i + j]
                        row_cells.append(f"[{global_num}] {ip_val}")
                    else:
                        row_cells.append("")
                grid_table.add_row(*row_cells)

            ctx.console.print(grid_table)
        else:
            ctx.console.print(_muted(f"Aucune IP actuellement bannie dans le jail '{selected_jail}'."))

        # 5. Choix Action
        ctx.console.print()
        ctx.console.print(_info("Sélectionnez l'action à effectuer :"))
        ctx.console.print(_info("  [1] Bannir une/des IP(s)"))
        ctx.console.print(_info("  [2] Débannir une/des IP(s)"))
        ctx.console.print(_info("  [0] Annuler et retourner au menu"))
        ctx.console.print()

        choice_action = prompt_mgr.ask_text(_info("Votre choix (0-2) [0] : ")).strip() or "0"
        if is_cancel_word(choice_action):
            ctx.console.print(_muted("Opération annulée."))
            return

        if choice_action not in ["1", "2"]:
            ctx.console.print(_warning("Option d'action invalide. Veuillez choisir 1 ou 2."))
            return

        action_type = "ban" if choice_action == "1" else "unban"
        action_verb = "bannir" if action_type == "ban" else "débannir"

        # 6. Saisie multiple (IPs séparées par virgules ou N° d'index)
        ctx.console.print()
        prompt_msg = f"Saisissez la ou les IP(s) à {action_verb} (séparées par virgules ou N° d'index, '0' pour annuler) : " if (action_type == "unban" and currently_banned) else f"Adresse(s) IP à {action_verb} (séparées par virgules, '0' pour annuler) : "
        try:
            raw_input = prompt_mgr.ask_text(_info(prompt_msg), allow_cancel=True).strip()
        except PromptCancelled:
            ctx.console.print(_muted("Opération annulée."))
            return

        if not raw_input:
            ctx.console.print(_muted("Opération annulée."))
            return

        raw_items = [item.strip() for item in raw_input.split(",") if item.strip()]
        target_ips: list[str] = []

        # Resolution et validation des IPs / Index — une entrée invalide
        # (numéro hors plage ou format d'IP incorrect) est ignorée seule,
        # le reste du lot continue d'être traité (référentiel §48 : avant
        # ce correctif, une seule entrée invalide annulait tout le lot,
        # y compris les entrées déjà validées).
        for item in raw_items:
            if is_cancel_word(item):
                ctx.console.print(_muted("Opération annulée."))
                return

            resolved_ip = item
            if action_type == "unban" and item.isdigit():
                num_idx = int(item) - 1
                if 0 <= num_idx < len(currently_banned):
                    resolved_ip = currently_banned[num_idx]
                else:
                    ctx.console.print(_warning(f"Le numéro [{item}] ne correspond à aucune IP bannie dans '{selected_jail}' — ignoré."))
                    continue

            try:
                ipaddress.ip_address(resolved_ip)
            except ValueError:
                ctx.console.print(_error(f"Format d'adresse IP invalide : '{item}'. Doit être une IP valide (ex: 192.168.1.50) — ignoré."))
                continue

            if resolved_ip not in target_ips:
                target_ips.append(resolved_ip)

        if not target_ips:
            ctx.console.print(_warning("Aucune entrée valide dans la saisie — opération annulée."))
            return

        ctx.console.print()

        # 7. Exécution et rapport de bilan
        banned_set = set(currently_banned)
        success_count = 0
        skipped_count = 0

        for ip in target_ips:
            if action_type == "ban" and ip in banned_set:
                ctx.console.print(_warning(f"• IP {ip} : Déjà bannie dans '{selected_jail}'."))
                skipped_count += 1
                continue

            if action_type == "unban" and ip not in banned_set:
                ctx.console.print(_warning(f"• IP {ip} : Absente de la liste des bannis du jail '{selected_jail}'."))
                skipped_count += 1
                continue

            executed_successfully = False
            error_detail = ""

            try:
                if action_type == "ban":
                    from omega_fire.application.commands.jail_ban import JailBanCommand, JailBanRequest
                    cmd_result = JailBanCommand(fail2ban_port).execute(
                        JailBanRequest(jail_name=selected_jail, ip=ip)
                    )
                else:
                    from omega_fire.application.commands.jail_unban import JailUnbanCommand, JailUnbanRequest
                    cmd_result = JailUnbanCommand(fail2ban_port).execute(
                        JailUnbanRequest(jail_name=selected_jail, ip=ip)
                    )
                executed_successfully = cmd_result.success
                error_detail = cmd_result.message or ""
            except Exception as e:
                executed_successfully = False
                error_detail = str(e)

            if executed_successfully:
                msg_action = "bannie" if action_type == "ban" else "débannie"
                ctx.console.print(_success(f"✔ IP {ip} {msg_action} avec succès dans '{selected_jail}'."))
                success_count += 1
            else:
                suffix = f" ({error_detail})" if error_detail else ""
                ctx.console.print(_error(f"✖ IP {ip} : Échec de l'action Fail2ban.{suffix}"))

        ctx.console.print()
        ctx.console.print(_info(f"Bilan : {success_count} IP(s) traitée(s) avec succès, {skipped_count} ignorée(s)."))

    _execute_action_flow(ctx, "4.2 Bannir / Débannir dans un jail", logic)

def action_4_3_jail_transfer(ctx: ActionContext) -> None:
    """4.3 — Transfert / Import / Export IPs (Jails, Backends, Fichiers & Épingles)."""
    def logic(out: List[Any]):
        import os
        import re
        import subprocess
        from rich import box
        from rich.table import Table
        from rich.text import Text
        from omega_fire.application.queries.jail_status import get_jail_status
        from omega_fire.shared.networking import IPAddress
        from omega_fire.domain.ip_blacklist.exceptions import IPAlreadyBannedError

        prompt_mgr = PromptManager(ctx.console)

        DEFAULT_FILE_PATH = str(DEFAULT_F2B_BLOCKLIST_FILE)
        DEFAULT_NFT_IPT_PATH = str(DEFAULT_BLOCKLIST_FILE)

        # Initialisation centralisée des ÉPINGLES
        from omega_fire.infrastructure.storage.files.json_store import JsonStore
        from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand

        pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )

        fail2ban_port = None
        if ctx.container:
            try:
                fail2ban_port = ctx.container.get_fail2ban_port()
            except Exception:
                pass

        nftables_port = None
        iptables_port = None
        ip6tables_port = None
        if ctx.container:
            try:
                nftables_port = ctx.container.get_firewall_port("nftables")
            except Exception:
                pass
            try:
                iptables_port = ctx.container.get_firewall_port("iptables")
            except Exception:
                pass
            try:
                ip6tables_port = ctx.container.get_firewall_port("ip6tables")
            except Exception:
                pass

        # -------------------------------------------------------------------------
        # ÉTAPE 0 : TABLEAU D'ÉTAT INITIAL GLOBAL
        # -------------------------------------------------------------------------
        with gauge_status(ctx.console, "Scan des jails en cours..."):
            jail_status_result = get_jail_status(fail2ban_port=fail2ban_port)

        jails_info: list[dict] = [
            {
                "name": j.name,
                "active": j.active,
                "banned_ips": sorted({str(ip) for ip in j.banned_ips}),
            }
            for j in jail_status_result.jails
        ]

        total_f2b_ips = 0
        for j in jails_info:
            if j.get("active", False):
                total_f2b_ips += len(j.get("banned_ips", []))

        nft_count = 0
        if nftables_port is not None:
            try:
                nft_count = len(nftables_port.list_bans())
            except Exception:
                pass

        ipt_count = 0
        if iptables_port is not None:
            try:
                ipt_count = len(iptables_port.list_bans())
            except Exception:
                pass

        ipt6_count = 0
        if ip6tables_port is not None:
            try:
                ipt6_count = len(ip6tables_port.list_bans())
            except Exception:
                pass

        file_count = 0
        if os.path.exists(DEFAULT_FILE_PATH):
            try:
                with open(DEFAULT_FILE_PATH, "r", encoding="utf-8") as f:
                    file_count = len(_extract_valid_ips(f.read()))
            except Exception:
                pass

        file_nft_ipt_count = 0
        if os.path.exists(DEFAULT_NFT_IPT_PATH):
            try:
                with open(DEFAULT_NFT_IPT_PATH, "r", encoding="utf-8") as f:
                    file_nft_ipt_count = len(_extract_valid_ips(f.read()))
            except Exception:
                pass

        ctx.console.print(_title("Transfert & Interopérabilité des IPs"))
        ctx.console.print()

        summary_table = Table(
            title="État des Backends & Infrastructures",
            show_header=True,
            header_style=theme_registry.get_style("table.header"),
            border_style=theme_registry.get_style("border.accent"),
            box=box.SQUARE,
            expand=False,
            padding=(0, 1),
        )
        summary_table.add_column("Backend / Service", style=theme_registry.get_style("text.main"), width=28)
        summary_table.add_column("Détail / Jails", style=theme_registry.get_style("text.info"), width=22)
        summary_table.add_column("IPs Bannies", justify="right", style=theme_registry.get_style("text.danger"), width=12)

        summary_table.add_row("Fail2ban", f"{len(jails_info)} Jail(s) actif(s)", str(total_f2b_ips))
        summary_table.add_row("nftables", "inet filter blackhole", str(nft_count))
        summary_table.add_row("iptables", "Chaîne INPUT (DROP)", str(ipt_count))
        summary_table.add_row("ip6tables", "Chaîne INPUT (DROP)", str(ipt6_count))
        summary_table.add_row("Fichier par défaut (F2B)", os.path.basename(DEFAULT_FILE_PATH), str(file_count))
        summary_table.add_row("Fichier par défaut (NFT-IPT)", os.path.basename(DEFAULT_NFT_IPT_PATH), str(file_nft_ipt_count))

        ctx.console.print(summary_table)
        ctx.console.print()

        # -------------------------------------------------------------------------
        # ÉTAPE 1 : CHOIX DE LA SOURCE DE COLLECTE (Jails, Backends, Unifié, Fichiers, Épingles)
        # -------------------------------------------------------------------------
        ctx.console.print(_info("Sélectionnez la SOURCE de collecte des IPs :"))
        ctx.console.print(_info("  [1] 󰦝 Jail Fail2ban (Temps réel)"))
        ctx.console.print(_info("  [2] 󱁝 Pare-feu nftables (Set blackhole)"))
        ctx.console.print(_info("  [3] 󰂪 Pare-feu iptables (Chaîne INPUT)"))
        ctx.console.print(_info("  [4]  Fichier Texte / Chemin manuel"))
        ctx.console.print(_info("  [5] 🖈 Gestion / Choisir parmi les fichiers ÉPINGLÉS"))
        ctx.console.print(_info("  [6] 󱁞 TOUS les backends réunis (nft, ipt, ip6t et tous les jails Fail2ban)"))
        ctx.console.print(_info("  [7] 󰂪 Pare-feu ip6tables (Chaîne INPUT)"))
        ctx.console.print(_info("  [0] ↩️ Annuler et retourner au menu principal"))
        ctx.console.print()

        source_type_choice = prompt_mgr.ask_text(_info("Votre choix (0-7) [1] : ")).strip() or "1"
        if is_cancel_word(source_type_choice):
            ctx.console.print(_muted("Opération annulée."))
            return

        source_label = ""
        collected_ips: set[str] = set()

        # --- SOURCE 1 : JAIL FAIL2BAN ---
        if source_type_choice == "1":
            if not jails_info:
                ctx.console.print(_error("Aucun jail disponible ou service Fail2ban inassignable."))
                return

            ctx.console.print()
            ctx.console.print(_info("Sélectionnez le Jail source :"))
            table_jails = Table(
                show_header=True,
                header_style=theme_registry.get_style("table.header"),
                border_style=theme_registry.get_style("border.accent"),
                box=box.SQUARE,
                expand=False,
                padding=(0, 1),
            )
            table_jails.add_column("N°", style=theme_registry.get_style("text.info"), width=4, justify="right")
            table_jails.add_column("Nom du Jail", style=theme_registry.get_style("text.main"), width=20)
            table_jails.add_column("Statut", style=theme_registry.get_style("text.info"), width=10, justify="center")
            table_jails.add_column("IPs Bannies", style=theme_registry.get_style("text.danger"), width=12, justify="right")

            for idx, jail in enumerate(jails_info, start=1):
                is_active = jail.get("active", False)
                status_badge = Text("Actif", style=theme_registry.get_style("status.available")) if is_active else Text("Inactif", style=theme_registry.get_style("text.muted"))
                banned_count = len(jail.get("banned_ips", []))
                table_jails.add_row(str(idx), jail["name"], status_badge, str(banned_count))

            ctx.console.print(table_jails)
            ctx.console.print()

            choice_input = prompt_mgr.ask_text(_info("Votre choix (N°, Nom ou '0' pour annuler) [0] : ")).strip() or "0"
            if is_cancel_word(choice_input):
                ctx.console.print(_muted("Opération annulée."))
                return

            selected_jail_data = None
            if choice_input.isdigit():
                idx_num = int(choice_input)
                if 1 <= idx_num <= len(jails_info):
                    selected_jail_data = jails_info[idx_num - 1]
            else:
                for jail in jails_info:
                    if jail["name"].lower() == choice_input.lower():
                        selected_jail_data = jail
                        break

            if not selected_jail_data:
                ctx.console.print(_warning(f"Jail '{choice_input}' introuvable. Opération annulée."))
                return

            source_label = f"Jail '{selected_jail_data['name']}'"
            collected_ips = set(selected_jail_data.get("banned_ips", []))

        # --- SOURCE 2 : NFTABLES ---
        elif source_type_choice == "2":
            source_label = "Pare-feu nftables (blackhole)"
            if nftables_port is None:
                ctx.console.print(_error("Port nftables indisponible."))
                return
            try:
                collected_ips = {b.ip for b in nftables_port.list_bans()}
            except Exception as e:
                ctx.console.print(_error(f"Erreur de lecture nftables : {e}"))
                return

        # --- SOURCE 3 : IPTABLES ---
        elif source_type_choice == "3":
            source_label = "Pare-feu iptables (INPUT)"
            if iptables_port is None:
                ctx.console.print(_error("Port iptables indisponible."))
                return
            try:
                collected_ips = {b.ip.split("/")[0] for b in iptables_port.list_bans()}
            except Exception as e:
                ctx.console.print(_error(f"Erreur de lecture iptables : {e}"))
                return

        # --- SOURCE 7 : IP6TABLES ---
        elif source_type_choice == "7":
            source_label = "Pare-feu ip6tables (INPUT)"
            if ip6tables_port is None:
                ctx.console.print(_error("Port ip6tables indisponible."))
                return
            try:
                collected_ips = {b.ip.split("/")[0] for b in ip6tables_port.list_bans()}
            except Exception as e:
                ctx.console.print(_error(f"Erreur de lecture ip6tables : {e}"))
                return

        # --- SOURCE 4 : FICHIER TEXTE MANUEL ---
        elif source_type_choice == "4":
            try:
                src_file = prompt_mgr.ask_text(_info("Saisissez le chemin du fichier source : "), allow_cancel=True).strip()
            except PromptCancelled:
                src_file = ""
            if not src_file:
                ctx.console.print(_muted("Opération annulée."))
                return
            if not os.path.exists(src_file):
                ctx.console.print(_error(f"Fichier source '{src_file}' introuvable."))
                return
            source_label = f"Fichier '{src_file}'"
            try:
                with open(src_file, "r", encoding="utf-8") as f:
                    content = f.read()
                collected_ips = _extract_valid_ips(content)
            except Exception as e:
                ctx.console.print(_error(f"Erreur lecture fichier source : {e}"))
                return

        # --- SOURCE 5 : GESTION & SÉLECTION DES ÉPINGLÉS ---
        elif source_type_choice == "5":
            ctx.console.print()
            ctx.console.print(_title("Gestion & Sélection des fichiers épinglés"))
            pinned_list = pinned_command.list_paths()

            if pinned_list:
                for idx, path in enumerate(pinned_list, start=1):
                    ctx.console.print(_info(f"   [{idx}] {path}"))
            else:
                ctx.console.print(_info("   (Aucune épingle configurée)"))

            ctx.console.print()
            ctx.console.print(_info("   [A] ✚ Épingler un nouveau fichier (saisie manuelle)"))
            if pinned_list:
                ctx.console.print(_info("   [D] ✖ Retirer un fichier des épingles"))
            ctx.console.print(_info("   [0] ↩️ Annuler et retourner au menu principal"))
            ctx.console.print()

            pin_choice = prompt_mgr.ask_text(_info("Choix (Numéro de fichier ou A/D/0) : ")).strip().upper()

            if is_cancel_word(pin_choice):
                ctx.console.print(_muted("Opération annulée."))
                return

            elif pin_choice == "A":
                try:
                    new_pin = prompt_mgr.ask_text(_info("Chemin complet du fichier à épingler : "), allow_cancel=True).strip()
                except PromptCancelled:
                    new_pin = ""
                if new_pin:
                    try:
                        folder = os.path.dirname(new_pin)
                        if folder and not os.path.exists(folder):
                            os.makedirs(folder, exist_ok=True)
                        if not os.path.exists(new_pin):
                            with open(new_pin, "w", encoding="utf-8") as f:
                                f.write("# OmegaFire Blocklist\n")

                        add_result = pinned_command.add_path(new_pin)
                        if add_result.success:
                            ctx.console.print(_success(f"✔ Fichier '{new_pin}' épinglé et prêt."))
                        src_file = new_pin
                    except Exception as e:
                        ctx.console.print(_error(f"Erreur création épingle : {e}"))
                        return
                else:
                    ctx.console.print(_muted("Opération annulée."))
                    return

            elif pin_choice == "D" and pinned_list:
                del_idx = ctx.console.input(_info("Numéro de l'épingle à retirer : ")).strip()
                if del_idx.isdigit() and 1 <= int(del_idx) <= len(pinned_list):
                    remove_result = pinned_command.remove_path(pinned_list[int(del_idx) - 1])
                    if remove_result.success:
                        ctx.console.print(_success(remove_result.message))
                    else:
                        ctx.console.print(_error(remove_result.message))
                else:
                    ctx.console.print(_error("Numéro d'épingle invalide."))
                return

            elif pin_choice.isdigit() and 1 <= int(pin_choice) <= len(pinned_list):
                src_file = pinned_list[int(pin_choice) - 1]
            else:
                ctx.console.print(_warning("Option d'épingle invalide. Opération annulée."))
                return

            if not os.path.exists(src_file):
                ctx.console.print(_error(f"Le fichier épinglé '{src_file}' n'existe pas encore sur le disque."))
                return

            source_label = f"Épingle '{src_file}'"
            try:
                with open(src_file, "r", encoding="utf-8") as f:
                    content = f.read()
                collected_ips = _extract_valid_ips(content)
            except Exception as e:
                ctx.console.print(_error(f"Erreur lecture épingle : {e}"))
                return

        # --- SOURCE 6 : TOUS LES BACKENDS RÉUNIS (NFT, IPT, IP6T & FAIL2BAN) ---
        elif source_type_choice == "6":
            source_label = "Tous les Backends réunis (nftables, iptables, ip6tables & Fail2ban)"
            ctx.console.print(_info("Collecte en cours sur l'ensemble des infrastructures..."))

            # 1. Fail2ban
            for j in jails_info:
                collected_ips.update(j.get("banned_ips", []))

            # 2. nftables
            if nftables_port is not None:
                try:
                    collected_ips.update(b.ip for b in nftables_port.list_bans())
                except Exception:
                    pass

            # 3. iptables
            if iptables_port is not None:
                try:
                    collected_ips.update(b.ip.split("/")[0] for b in iptables_port.list_bans())
                except Exception:
                    pass

            # 4. ip6tables
            if ip6tables_port is not None:
                try:
                    collected_ips.update(b.ip.split("/")[0] for b in ip6tables_port.list_bans())
                except Exception:
                    pass

        banned_ips = sorted(list(collected_ips))
        if not banned_ips:
            ctx.console.print()
            ctx.console.print(_warning(f"La source {source_label} ne contient aucune IP bannie à transférer."))
            return

        ctx.console.print(_success(f"✔ {len(banned_ips)} IP(s) unique(s) collectée(s) depuis {source_label}."))

        # -------------------------------------------------------------------------
        # ÉTAPE 2 : CHOIX DE LA DESTINATION (Jails, Pare-feu, Fichiers, Épingles)
        # -------------------------------------------------------------------------
        ctx.console.print()
        ctx.console.print(_info("Sélectionnez la DESTINATION du transfert :"))
        ctx.console.print(_info("  [1] 󱁝 Jail Fail2ban (Bannir dans un jail actif)"))
        ctx.console.print(_info("  [2] 󰦝 Pare-feu nftables (Set blackhole)"))
        ctx.console.print(_info("  [3] 󰂪 Pare-feu iptables (Chaîne INPUT)"))
        ctx.console.print(_info(f"  [4] 🖹 Fichier texte par défaut ({DEFAULT_FILE_PATH})"))
        ctx.console.print(_info("  [5] 🗂️ Chemin manuel personnalisé"))
        ctx.console.print(_info("  [6] ☰ Gestion / Choisir parmi les fichiers épinglés"))
        ctx.console.print(_info("  [7] 󰂪 Pare-feu ip6tables (Chaîne INPUT)"))
        ctx.console.print(_info("  [0] ↩️ Annuler et retourner au menu principal"))
        ctx.console.print()

        choice_dest = prompt_mgr.ask_text(_info("Votre choix (0-7) [1] : ")).strip() or "1"
        if is_cancel_word(choice_dest):
            ctx.console.print(_muted("Opération annulée."))
            return

        target_mode = ""
        target_path = ""
        target_jail_name = ""

        # DESTINATION 1 : JAIL FAIL2BAN
        if choice_dest == "1":
            target_mode = "fail2ban_jail"
            if not jails_info:
                ctx.console.print(_error("Aucun Jail Fail2ban disponible."))
                return

            ctx.console.print()
            ctx.console.print(_info("Sélectionnez le Jail cible :"))
            table_dest_jails = Table(
                show_header=True,
                header_style=theme_registry.get_style("table.header"),
                border_style=theme_registry.get_style("border.accent"),
                box=box.SQUARE,
                expand=False,
                padding=(0, 1),
            )
            table_dest_jails.add_column("N°", style=theme_registry.get_style("text.info"), width=4, justify="right")
            table_dest_jails.add_column("Nom du Jail", style=theme_registry.get_style("text.main"), width=20)
            table_dest_jails.add_column("Statut", style=theme_registry.get_style("text.info"), width=10, justify="center")
            table_dest_jails.add_column("IPs Bannies", style=theme_registry.get_style("text.danger"), width=12, justify="right")

            for idx, jail in enumerate(jails_info, start=1):
                is_active = jail.get("active", False)
                status_badge = Text("Actif", style=theme_registry.get_style("status.available")) if is_active else Text("Inactif", style=theme_registry.get_style("text.muted"))
                banned_count = len(jail.get("banned_ips", []))
                table_dest_jails.add_row(str(idx), jail["name"], status_badge, str(banned_count))

            ctx.console.print(table_dest_jails)
            ctx.console.print()

            choice_jail_dest = prompt_mgr.ask_text(_info("Votre choix (N°, Nom ou '0' pour annuler) [0] : ")).strip() or "0"
            if is_cancel_word(choice_jail_dest):
                ctx.console.print(_muted("Opération annulée."))
                return

            dest_jail_data = None
            if choice_jail_dest.isdigit():
                idx_num = int(choice_jail_dest)
                if 1 <= idx_num <= len(jails_info):
                    dest_jail_data = jails_info[idx_num - 1]
            else:
                for jail in jails_info:
                    if jail["name"].lower() == choice_jail_dest.lower():
                        dest_jail_data = jail
                        break

            if not dest_jail_data:
                ctx.console.print(_warning("Jail cible invalide. Opération annulée."))
                return

            target_jail_name = dest_jail_data["name"]

        elif choice_dest == "2":
            target_mode = "nftables"
        elif choice_dest == "3":
            target_mode = "iptables"
        elif choice_dest == "7":
            target_mode = "ip6tables"
        elif choice_dest == "4":
            target_mode = "file"
            target_path = DEFAULT_FILE_PATH
        elif choice_dest == "5":
            target_mode = "file"
            try:
                target_path = prompt_mgr.ask_text(_info("Chemin complet du fichier ('0' pour annuler) : "), allow_cancel=True).strip()
            except PromptCancelled:
                target_path = ""
            if not target_path:
                ctx.console.print(_muted("Opération annulée."))
                return

        # DESTINATION 6 : ÉPINGLES EN DESTINATION
        elif choice_dest == "6":
            target_mode = "file"
            ctx.console.print()
            ctx.console.print(_title("Gestion des fichiers épinglés"))
            pinned_list = pinned_command.list_paths()

            if pinned_list:
                for idx, path in enumerate(pinned_list, start=1):
                    ctx.console.print(_info(f"   [{idx}] {path}"))
            else:
                ctx.console.print(_info("   (Aucune épingle configurée)"))

            ctx.console.print()
            ctx.console.print(_info("   [A] ✚ Épingler un nouveau fichier (saisie manuelle)"))
            if pinned_list:
                ctx.console.print(_info("   [D] ✖ Retirer un fichier des épingles"))
            ctx.console.print(_info("   [0] ↩️ Annuler et retourner au menu principal"))
            ctx.console.print()

            pin_choice = prompt_mgr.ask_text(_info("Choix (Numéro de fichier ou A/D/0) : ")).strip().upper()

            if is_cancel_word(pin_choice):
                ctx.console.print(_muted("Opération annulée."))
                return

            elif pin_choice == "A":
                try:
                    new_pin = prompt_mgr.ask_text(_info("Chemin complet du fichier à épingler : "), allow_cancel=True).strip()
                except PromptCancelled:
                    new_pin = ""
                if new_pin:
                    add_result = pinned_command.add_path(new_pin)
                    if add_result.success:
                        ctx.console.print(_success(f"✔ Fichier '{new_pin}' épinglé."))
                    target_path = new_pin
                else:
                    ctx.console.print(_muted("Opération annulée."))
                    return

            elif pin_choice == "D" and pinned_list:
                del_idx = ctx.console.input(_info("Numéro de l'épingle à retirer : ")).strip()
                if del_idx.isdigit() and 1 <= int(del_idx) <= len(pinned_list):
                    remove_result = pinned_command.remove_path(pinned_list[int(del_idx) - 1])
                    if remove_result.success:
                        ctx.console.print(_success(remove_result.message))
                    else:
                        ctx.console.print(_error(remove_result.message))
                else:
                    ctx.console.print(_error("Numéro d'épingle invalide."))
                return

            elif pin_choice.isdigit() and 1 <= int(pin_choice) <= len(pinned_list):
                target_path = pinned_list[int(pin_choice) - 1]
            else:
                ctx.console.print(_warning("Option invalide. Opération annulée."))
                return
        else:
            ctx.console.print(_warning("Option de destination invalide. Opération annulée."))
            return

        # -------------------------------------------------------------------------
        # ÉTAPE 3 : EXÉCUTION & DIAGNOSTIC DES EFFETS
        # -------------------------------------------------------------------------

        # --- CAS A : DESTINATION JAIL FAIL2BAN ---
        if target_mode == "fail2ban_jail":
            ctx.console.print()
            ctx.console.print(_info(f"Injection dans le Jail Fail2ban : {target_jail_name}"))

            # Réutilise le snapshot déjà récupéré à l'ÉTAPE 0 (dest_jail_data
            # vient de jails_info) — évite un second appel fail2ban-client
            # redondant pour la même information (référentiel §2/§32).
            current_jail_banned = set(dest_jail_data.get("banned_ips", []))

            added_count = 0
            already_present = 0
            failed_count = 0

            for ip in banned_ips:
                if ip in current_jail_banned:
                    already_present += 1
                    continue

                executed_successfully = False
                if fail2ban_port:
                    try:
                        from omega_fire.application.commands.jail_ban import JailBanCommand, JailBanRequest
                        res = JailBanCommand(fail2ban_port).execute(
                            JailBanRequest(jail_name=target_jail_name, ip=ip)
                        )
                        executed_successfully = getattr(res, "success", False)
                    except Exception:
                        executed_successfully = False
                else:
                    try:
                        cmd = ["fail2ban-client", "set", target_jail_name, "banip", ip]
                        exec_res = subprocess.run(cmd, capture_output=True, text=True)
                        executed_successfully = (exec_res.returncode == 0)
                    except Exception:
                        executed_successfully = False

                if executed_successfully:
                    added_count += 1
                else:
                    failed_count += 1

            diag_table = Table(
                title=f"Rapport d'injection Fail2ban ({target_jail_name})",
                show_header=True,
                header_style=theme_registry.get_style("table.header"),
                border_style=theme_registry.get_style("border.accent"),
                box=box.SQUARE,
                expand=False,
                padding=(0, 1),
            )
            diag_table.add_column("Métrique", style=theme_registry.get_style("text.main"), width=25)
            diag_table.add_column("Valeur", justify="right", style=theme_registry.get_style("text.info"), width=25)

            diag_table.add_row("Source", source_label)
            diag_table.add_row("Jail Cible", target_jail_name)
            diag_table.add_row("IPs collectées (Source)", str(len(banned_ips)))
            diag_table.add_row("IPs déjà bannies (Ignorées)", str(already_present))
            diag_table.add_row("Nouvelles IPs bannies", str(added_count))
            diag_table.add_row("Échecs de bannissement", str(failed_count))

            ctx.console.print()
            ctx.console.print(diag_table)
            ctx.console.print()
            ctx.console.print(_success(f"✔ Transfert vers le jail '{target_jail_name}' terminé ({added_count} bannies, {already_present} ignorées)."))
            return

        # --- CAS B : FICHIER TEXTE ---
        elif target_mode == "file":
            ctx.console.print()
            ctx.console.print(_info(f"Fichier cible : {target_path}"))
            ctx.console.print(_info("Sélectionnez le mode d'écriture :"))
            ctx.console.print(_info("  [1] ✖ Écraser (Remplacer totalement le fichier)"))
            ctx.console.print(_info("  [2] ✚ Rajouter (Ajouter à la fin sans vérifier)"))
            ctx.console.print(_info("  [3] 🗘 Incrémenter (Ajouter uniquement les IPs manquantes) [Par défaut]"))
            ctx.console.print(_info("  [0] Annuler"))
            ctx.console.print()

            write_choice = prompt_mgr.ask_text(_info("Votre choix (0-3) [3] : ")).strip() or "3"
            if is_cancel_word(write_choice):
                ctx.console.print(_muted("Opération annulée."))
                return

            if write_choice not in ["1", "2", "3"]:
                ctx.console.print(_warning("Mode d'écriture invalide. Opération annulée."))
                return

            overwrite = (write_choice == "1")
            append_raw = (write_choice == "2")

            try:
                folder_path = os.path.dirname(target_path)
                if folder_path and not os.path.exists(folder_path):
                    os.makedirs(folder_path, exist_ok=True)
                    ctx.console.print(_muted(f"Dossier parent créé : {folder_path}"))

                existing_ips = set()
                if os.path.exists(target_path) and not overwrite:
                    with open(target_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    existing_ips = _extract_valid_ips(content)

                source_ips_set = set(banned_ips)

                if overwrite:
                    final_ips = sorted(list(source_ips_set))
                    new_added = len(final_ips)
                    already_present = 0
                    mode_str = "Écraser"
                elif append_raw:
                    final_ips = sorted(list(existing_ips.union(source_ips_set)))
                    new_added = len(banned_ips)
                    already_present = 0
                    mode_str = "Rajouter (Brut)"
                else:
                    new_ips_set = source_ips_set - existing_ips
                    final_ips = sorted(list(existing_ips.union(source_ips_set)))
                    new_added = len(new_ips_set)
                    already_present = len(banned_ips) - new_added
                    mode_str = "Incrémenter"

                with open(target_path, "w" if overwrite else "a", encoding="utf-8") as f:
                    if overwrite:
                        f.write(f"# Omega-Fire Blocklist - Source: {source_label}\n")
                        for ip in final_ips:
                            f.write(f"{ip}\n")
                    else:
                        f.write(f"\n# Omega-Fire Append/Inc - Source: {source_label}\n")
                        ips_to_append = banned_ips if append_raw else sorted(list(source_ips_set - existing_ips))
                        for ip in ips_to_append:
                            f.write(f"{ip}\n")

                diag_table = Table(
                    title="Rapport de Transfert Fichier",
                    show_header=True,
                    header_style=theme_registry.get_style("table.header"),
                    border_style=theme_registry.get_style("border.accent"),
                    box=box.SQUARE,
                    expand=False,
                    padding=(0, 1),
                )
                diag_table.add_column("Métrique", style=theme_registry.get_style("text.main"), width=25)
                diag_table.add_column("Valeur", justify="right", style=theme_registry.get_style("text.info"), width=25)

                diag_table.add_row("Source", source_label)
                diag_table.add_row("Mode d'écriture", mode_str)
                diag_table.add_row("IPs collectées (Source)", str(len(banned_ips)))
                diag_table.add_row("IPs déjà présentes", str(already_present))
                diag_table.add_row("Nouvelles IPs écrites", str(new_added))

                ctx.console.print()
                ctx.console.print(diag_table)
                ctx.console.print()
                ctx.console.print(_success(f"✔ Transfert effectué avec succès dans '{target_path}'."))
                return

            except Exception as e:
                ctx.console.print(_error(f"Erreur d'écriture dans le fichier : {e}"))
                return

        # --- CAS C : NFTABLES ---
        elif target_mode == "nftables":
            ctx.console.print()
            ctx.console.print(_info("Structure cible : Table inet filter, Set blackhole"))

            if nftables_port is None:
                ctx.console.print(_error("Port nftables indisponible."))
                return

            # Pas de création manuelle de table/set ici : ban_single_ip()
            # s'en charge (_ensure_blackhole_set), et crée en plus la
            # chaîne "input" + la règle de filtrage "ip saddr @blackhole
            # drop" — que l'ancien code de cette fonction ne créait
            # jamais, laissant les IPs enregistrées dans le set sans
            # jamais être réellement filtrées sur un système où cette
            # chaîne n'existait pas encore.
            try:
                existing_nft_ips = {b.ip for b in nftables_port.list_bans()}
            except Exception:
                existing_nft_ips = set()

            added_count = 0
            already_present = 0
            failed_count = 0

            for ip in banned_ips:
                if ip in existing_nft_ips:
                    already_present += 1
                    continue

                try:
                    nftables_port.ban_single_ip(IPAddress(ip), reason=source_label)
                    added_count += 1
                except IPAlreadyBannedError:
                    already_present += 1
                except Exception:
                    failed_count += 1

            diag_table = Table(
                title="Rapport de Transfert nftables",
                show_header=True,
                header_style=theme_registry.get_style("table.header"),
                border_style=theme_registry.get_style("border.accent"),
                box=box.SQUARE,
                expand=False,
                padding=(0, 1),
            )
            diag_table.add_column("Métrique", style=theme_registry.get_style("text.main"), width=25)
            diag_table.add_column("Valeur", justify="right", style=theme_registry.get_style("text.info"), width=25)

            diag_table.add_row("Source", source_label)
            diag_table.add_row("IPs collectées", str(len(banned_ips)))
            diag_table.add_row("IPs déjà présentes (Ignorées)", str(already_present))
            diag_table.add_row("Nouvelles IPs injectées", str(added_count))
            diag_table.add_row("Échecs d'injection", str(failed_count))

            ctx.console.print()
            ctx.console.print(diag_table)
            ctx.console.print()

            if failed_count > 0:
                ctx.console.print(_warning(f"⚠️ Transfert nftables terminé avec {failed_count} échec(s)."))
            else:
                ctx.console.print(_success(f"✔ Transfert nftables terminé avec succès ({added_count} injectée(s), {already_present} ignorée(s))."))
            return

        # --- CAS D : IPTABLES ---
        elif target_mode == "iptables":
            ctx.console.print()
            ctx.console.print(_info("Destination : Chaîne INPUT de iptables"))
            ctx.console.print(_info("Sélectionnez le mode d'injection :"))
            ctx.console.print(_info("  [1] Réinitialiser / Écraser la chaîne (Attention: Vide la chaîne avant d'injecter)"))
            ctx.console.print(_info("  [2] Incrémenter (Vérifie chaque règle et n'ajoute que les nouvelles IPs) [Par défaut]"))
            ctx.console.print(_info("  [0] Annuler"))
            ctx.console.print()

            ipt_choice = prompt_mgr.ask_text(_info("Votre choix (0-2) [2] : ")).strip() or "2"
            if is_cancel_word(ipt_choice):
                ctx.console.print(_muted("Opération annulée."))
                return

            if ipt_choice not in ["1", "2"]:
                ctx.console.print(_warning("Option invalide. Opération annulée."))
                return

            if iptables_port is None:
                ctx.console.print(_error("Port iptables indisponible."))
                return

            flush_first = (ipt_choice == "1")
            added_count = 0
            already_present = 0
            failed_count = 0

            if flush_first:
                iptables_port.flush_chain("INPUT")
                existing_ipt_ips = set()
            else:
                try:
                    existing_ipt_ips = {b.ip.split("/")[0] for b in iptables_port.list_bans()}
                except Exception:
                    existing_ipt_ips = set()

            for ip in banned_ips:
                if ip in existing_ipt_ips:
                    already_present += 1
                    continue

                try:
                    iptables_port.ban_single_ip(IPAddress(ip), reason=source_label)
                    added_count += 1
                except IPAlreadyBannedError:
                    already_present += 1
                except Exception:
                    failed_count += 1

            diag_table = Table(
                title="Rapport de Transfert iptables",
                show_header=True,
                header_style=theme_registry.get_style("table.header"),
                border_style=theme_registry.get_style("border.accent"),
                box=box.SQUARE,
                expand=False,
                padding=(0, 1),
            )
            diag_table.add_column("Métrique", style=theme_registry.get_style("text.main"), width=25)
            diag_table.add_column("Valeur", justify="right", style=theme_registry.get_style("text.info"), width=25)

            diag_table.add_row("Source", source_label)
            diag_table.add_row("Mode sélectionné", "Réinitialiser" if flush_first else "Incrémenter")
            diag_table.add_row("IPs collectées", str(len(banned_ips)))
            diag_table.add_row("IPs déjà présentes (Ignorées)", str(already_present))
            diag_table.add_row("Nouvelles IPs injectées", str(added_count))
            diag_table.add_row("Échecs d'injection", str(failed_count))

            ctx.console.print()
            ctx.console.print(diag_table)
            ctx.console.print()
            ctx.console.print(_success(f"✔ Transfert iptables terminé ({added_count} règles ajoutées, {already_present} doublons ignorés)."))

        # --- CAS E : IP6TABLES ---
        elif target_mode == "ip6tables":
            ctx.console.print()
            ctx.console.print(_info("Destination : Chaîne INPUT de ip6tables"))
            ctx.console.print(_info("Sélectionnez le mode d'injection :"))
            ctx.console.print(_info("  [1] Réinitialiser / Écraser la chaîne (Attention: Vide la chaîne avant d'injecter)"))
            ctx.console.print(_info("  [2] Incrémenter (Vérifie chaque règle et n'ajoute que les nouvelles IPs) [Par défaut]"))
            ctx.console.print(_info("  [0] Annuler"))
            ctx.console.print()

            ipt6_choice = prompt_mgr.ask_text(_info("Votre choix (0-2) [2] : ")).strip() or "2"
            if is_cancel_word(ipt6_choice):
                ctx.console.print(_muted("Opération annulée."))
                return

            if ipt6_choice not in ["1", "2"]:
                ctx.console.print(_warning("Option invalide. Opération annulée."))
                return

            if ip6tables_port is None:
                ctx.console.print(_error("Port ip6tables indisponible."))
                return

            flush_first = (ipt6_choice == "1")
            added_count = 0
            already_present = 0
            failed_count = 0

            if flush_first:
                ip6tables_port.flush_chain("INPUT")
                existing_ipt6_ips = set()
            else:
                try:
                    existing_ipt6_ips = {b.ip.split("/")[0] for b in ip6tables_port.list_bans()}
                except Exception:
                    existing_ipt6_ips = set()

            for ip in banned_ips:
                if ip in existing_ipt6_ips:
                    already_present += 1
                    continue

                try:
                    # ip6tables_port.ban_single_ip() lève IPFamilyMismatchError
                    # (référentiel §53) pour une IPv4 — attendu et normal ici :
                    # une source mixte (choix 6 "tous backends réunis", ou
                    # nftables qui est dual-stack) peut contenir des IPv4,
                    # qui n'ont simplement rien à faire sur ip6tables. Compté
                    # comme un échec parmi d'autres, pas une erreur bloquante.
                    ip6tables_port.ban_single_ip(IPAddress(ip), reason=source_label)
                    added_count += 1
                except IPAlreadyBannedError:
                    already_present += 1
                except Exception:
                    failed_count += 1

            diag_table = Table(
                title="Rapport de Transfert ip6tables",
                show_header=True,
                header_style=theme_registry.get_style("table.header"),
                border_style=theme_registry.get_style("border.accent"),
                box=box.SQUARE,
                expand=False,
                padding=(0, 1),
            )
            diag_table.add_column("Métrique", style=theme_registry.get_style("text.main"), width=25)
            diag_table.add_column("Valeur", justify="right", style=theme_registry.get_style("text.info"), width=25)

            diag_table.add_row("Source", source_label)
            diag_table.add_row("Mode sélectionné", "Réinitialiser" if flush_first else "Incrémenter")
            diag_table.add_row("IPs collectées", str(len(banned_ips)))
            diag_table.add_row("IPs déjà présentes (Ignorées)", str(already_present))
            diag_table.add_row("Nouvelles IPs injectées", str(added_count))
            diag_table.add_row("Échecs d'injection", str(failed_count))

            ctx.console.print()
            ctx.console.print(diag_table)
            ctx.console.print()
            ctx.console.print(_success(f"✔ Transfert ip6tables terminé ({added_count} règles ajoutées, {already_present} doublons ignorés)."))

    _execute_action_flow(ctx, "4.3 Transfert / Import / Export IPs (Jails, Backends, Fichiers)", logic)

def action_4_4_create_jail(ctx: ActionContext) -> None:
    """4.4 — Création et configuration d'un Jail Fail2ban (Totalement automatisé)."""
    def logic(out: List[Any]):
        import os
        import re
        from rich import box
        from rich.table import Table
        from omega_fire.interfaces.cli.themes.registry import theme_registry
        from omega_fire.application.queries.jail_status import get_jail_status
        from omega_fire.domain.fail2ban.filters import generate_default_http_filter

        prompt_mgr = PromptManager(ctx.console)

        # -------------------------------------------------------------------------
        # ÉTAPE 0 : INSPECTION DES JAILS EXISTANTS
        # -------------------------------------------------------------------------
        fail2ban_port = None
        if ctx.container:
            try:
                fail2ban_port = ctx.container.get_fail2ban_port()
            except Exception:
                pass

        with gauge_status(ctx.console, "Scan des jails existants..."):
            existing_jails = get_jail_status(fail2ban_port=fail2ban_port).jails

        existing_names = [j.name.lower() for j in existing_jails]

        ctx.console.print(_title("Création & Activation de Jail Fail2ban"))
        ctx.console.print()

        # Tableau des Jails Actuels
        jails_table = Table(
            title="Jails Fail2ban actuellement configurés",
            show_header=True,
            header_style=theme_registry.get_style("table.header"),
            border_style=theme_registry.get_style("border.accent"),
            box=box.SQUARE,
            expand=False,
            padding=(0, 1),
        )
        jails_table.add_column("Nom du Jail", style=theme_registry.get_style("text.main"), width=24)
        jails_table.add_column("Statut", style=theme_registry.get_style("text.info"), width=12, justify="center")
        jails_table.add_column("IPs Bannies", style=theme_registry.get_style("text.danger"), width=12, justify="right")

        if existing_jails:
            for j in existing_jails:
                jails_table.add_row(j.name, "Actif" if j.active else "Inactif", str(j.banned_count))
        else:
            jails_table.add_row("(Aucun jail actif détecté)", "Inactif", "0")

        ctx.console.print(jails_table)
        ctx.console.print()

        # -------------------------------------------------------------------------
        # ÉTAPE 1 : CHOIX DU MODE
        # -------------------------------------------------------------------------
        ctx.console.print(_info("Choisissez le mode de création :"))
        ctx.console.print(_info("  [1] ✍️  Création d'un Jail sur-mesure (Assistant pas-à-pas)"))
        ctx.console.print(_info("  [2] 📋 Utiliser un Modèle / Preset (Caddy, Lighttpd, Nginx, Apache, SSH, Syslog...)"))
        ctx.console.print(_info("  [0] Annuler et retourner au menu principal"))
        ctx.console.print()

        mode_choice = prompt_mgr.ask_text(_info("Votre choix (0-2) [1] : ")).strip() or "1"
        if is_cancel_word(mode_choice):
            ctx.console.print(_muted("Opération annulée."))
            return

        jail_name = ""
        log_path = ""
        filter_name = ""
        port_spec = ""
        max_retry = "5"
        find_time = "10m"
        ban_time = "1h"

        # --- MODE 2 : PRESETS ---
        if mode_choice == "2":
            from omega_fire.infrastructure.storage.files.json_store import JsonStore
            from omega_fire.application.commands.manage_jail_presets import ManageJailPresetsCommand
            from omega_fire.infrastructure.config.paths import RUNTIME_DIR

            preset_command = ManageJailPresetsCommand(JsonStore(RUNTIME_DIR))

            while True:
                ctx.console.print()
                ctx.console.print(_title("Sélection d'un modèle de Jail"))

                presets = preset_command.list_presets()

                preset_table = Table(
                    show_header=True,
                    header_style=theme_registry.get_style("table.header"),
                    border_style=theme_registry.get_style("border.accent"),
                    box=box.SQUARE,
                    expand=False,
                    padding=(0, 1),
                )
                preset_table.add_column("N°", style=theme_registry.get_style("text.info"), width=4, justify="right")
                preset_table.add_column("Nom du Preset", style=theme_registry.get_style("text.main"), width=22)
                preset_table.add_column("Description / Cible", style=theme_registry.get_style("text.info"), width=48)

                for idx, p in enumerate(presets, start=1):
                    preset_table.add_row(str(idx), p["name"], p["desc"])

                ctx.console.print(preset_table)
                ctx.console.print()
                ctx.console.print(_info("  [A] ✚  Ajouter un modèle à cette liste"))
                ctx.console.print(_info("  [R] ✖  Retirer un modèle de cette liste"))
                ctx.console.print()

                p_choice = prompt_mgr.ask_text(_info("Sélectionnez le N° de modèle (ou '0' pour annuler) : ")).strip()
                if is_cancel_word(p_choice):
                    ctx.console.print(_muted("Opération annulée."))
                    return

                if p_choice.upper() == "A":
                    ctx.console.print()
                    ctx.console.print(_title("Ajout d'un modèle de Jail"))
                    ctx.console.print(_muted("'annuler' à tout moment pour abandonner l'ajout."))
                    field_prompts = [
                        ("name", "Nom du preset (identifiant, ex: my-app-access)"),
                        ("desc", "Description courte (affichée dans la liste)"),
                        ("log", "Chemin du fichier de log"),
                        ("port", "Port(s) ciblé(s) (ex: http,https ou ssh)"),
                        ("filter", "Nom du filtre Fail2ban"),
                        ("retry", "Max Retry"),
                        ("find", "Findtime (ex: 10m)"),
                        ("ban", "Bantime (ex: 1h)"),
                    ]
                    new_preset: dict[str, str] = {}
                    cancelled = False
                    for field_key, label in field_prompts:
                        try:
                            new_preset[field_key] = prompt_mgr.ask_text(_info(f"{label} : "), allow_cancel=True).strip()
                        except PromptCancelled:
                            cancelled = True
                            break
                    if cancelled:
                        ctx.console.print(_muted("Ajout annulé."))
                        continue

                    add_result = preset_command.add_preset(new_preset)
                    if add_result.success:
                        ctx.console.print(_success(add_result.message))
                    else:
                        ctx.console.print(_error(add_result.message))
                    continue

                if p_choice.upper() == "R":
                    if not presets:
                        ctx.console.print(_warning("La liste est déjà vide."))
                        continue
                    try:
                        rem_choice = prompt_mgr.ask_text(
                            _info("N° du modèle à retirer de la liste (ou 'annuler') : "),
                            allow_cancel=True,
                        ).strip()
                    except PromptCancelled:
                        continue
                    if rem_choice.isdigit() and 1 <= int(rem_choice) <= len(presets):
                        remove_result = preset_command.remove_preset(presets[int(rem_choice) - 1]["name"])
                        if remove_result.success:
                            ctx.console.print(_success(remove_result.message))
                        else:
                            ctx.console.print(_error(remove_result.message))
                    else:
                        ctx.console.print(_error("Numéro invalide."))
                    continue

                if p_choice.isdigit() and 1 <= int(p_choice) <= len(presets):
                    sel_preset = presets[int(p_choice) - 1]
                    break

                ctx.console.print(_warning(f"Choix invalide ('{p_choice}')."))

            jail_name = sel_preset["name"]
            log_path = sel_preset["log"]
            filter_name = sel_preset["filter"]
            port_spec = sel_preset["port"]
            max_retry = sel_preset["retry"]
            find_time = sel_preset["find"]
            ban_time = sel_preset["ban"]

            if jail_name.lower() in existing_names:
                jail_name = f"{jail_name}-custom"

        # --- MODE 1 : SUR-MESURE ---
        else:
            ctx.console.print()
            ctx.console.print(_title("Assistant de création sur-mesure"))
            ctx.console.print()
            ctx.console.print(_muted("Ce nom identifie le jail dans Fail2ban (lettres, chiffres, tirets) — obligatoire, 'annuler' pour quitter l'assistant."))

            while True:
                try:
                    jail_name = prompt_mgr.ask_text(_info("1. Nom du Jail (ex: my-app-jail) : "), allow_cancel=True).strip()
                except PromptCancelled:
                    ctx.console.print(_muted("Opération annulée."))
                    return
                if not jail_name:
                    ctx.console.print(_warning("⚠ Un nom est requis pour continuer."))
                    continue
                if jail_name.lower() in existing_names:
                    ctx.console.print(_error(f"Un Jail nommé '{jail_name}' existe déjà sur le système. Choisissez un autre nom."))
                    continue
                jail_name = re.sub(r'[^a-zA-Z0-9_-]', '', jail_name)
                break

            from omega_fire.infrastructure.storage.files.json_store import JsonStore
            from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand
            from omega_fire.infrastructure.config.paths import RUNTIME_DIR

            pinned_command = ManagePinnedLogPathsCommand(JsonStore(RUNTIME_DIR))

            while True:
                pinned_paths = pinned_command.list_paths()

                ctx.console.print()
                ctx.console.print(_info("2. Sélection du fichier de Log à surveiller :"))
                if pinned_paths:
                    for idx, path in enumerate(pinned_paths, start=1):
                        exists_tag = "[Présent]" if os.path.exists(path) else "[Absent]"
                        ctx.console.print(_info(f"  [{idx}] {path} {exists_tag}"))
                else:
                    ctx.console.print(_muted("  (Aucun chemin épinglé pour l'instant.)"))
                ctx.console.print(_info("  [M] Saisir un chemin personnalisé manuellement (une seule fois)"))
                ctx.console.print(_info("  [A] ✚  Ajouter un chemin à cette liste"))
                ctx.console.print(_info("  [R] ✖  Retirer un chemin de cette liste"))
                ctx.console.print()

                log_choice = prompt_mgr.ask_text(_info("Votre choix [1] : ")).strip() or "1"
                if is_cancel_word(log_choice):
                    ctx.console.print(_muted("Opération annulée."))
                    return

                if log_choice.upper() == "A":
                    try:
                        new_path = prompt_mgr.ask_text(
                            _info("Chemin complet à ajouter à la liste (ou 'annuler') : "),
                            allow_cancel=True,
                        ).strip()
                    except PromptCancelled:
                        new_path = ""
                    if new_path:
                        add_result = pinned_command.add_path(new_path)
                        if add_result.success:
                            ctx.console.print(_success(add_result.message))
                        else:
                            ctx.console.print(_error(add_result.message))
                    continue

                if log_choice.upper() == "R":
                    if not pinned_paths:
                        ctx.console.print(_warning("La liste est déjà vide."))
                        continue
                    try:
                        rem_choice = prompt_mgr.ask_text(
                            _info("N° du chemin à retirer de la liste (ou 'annuler') : "),
                            allow_cancel=True,
                        ).strip()
                    except PromptCancelled:
                        continue
                    if rem_choice.isdigit() and 1 <= int(rem_choice) <= len(pinned_paths):
                        remove_result = pinned_command.remove_path(pinned_paths[int(rem_choice) - 1])
                        if remove_result.success:
                            ctx.console.print(_success(remove_result.message))
                        else:
                            ctx.console.print(_error(remove_result.message))
                    else:
                        ctx.console.print(_error("Numéro invalide."))
                    continue

                if log_choice.isdigit() and 1 <= int(log_choice) <= len(pinned_paths):
                    log_path = pinned_paths[int(log_choice) - 1]
                    break

                # Toute autre saisie (dont [M]) => saisie manuelle ponctuelle,
                # jamais ajoutée à la liste (comportement identique à avant).
                try:
                    log_path = prompt_mgr.ask_text(_info("Chemin complet du fichier de log : "), allow_cancel=True).strip()
                except PromptCancelled:
                    log_path = ""
                if not log_path:
                    ctx.console.print(_muted("Opération annulée."))
                    return
                break

            ctx.console.print()
            port_spec = prompt_mgr.ask_text(_info("3. Ports concernés (ex: http,https ou ssh ou 80,443) [http,https] : ")).strip() or "http,https"
            if is_cancel_word(port_spec):
                ctx.console.print(_muted("Opération annulée."))
                return

            ctx.console.print()
            filter_name = prompt_mgr.ask_text(_info(f"4. Nom du filtre Fail2ban [Défaut: {jail_name}] : ")).strip() or jail_name
            if is_cancel_word(filter_name):
                ctx.console.print(_muted("Opération annulée."))
                return

            ctx.console.print()
            ctx.console.print(_title("Configuration des Règles de Bannissement"))

            ctx.console.print(_info("• Max Retry (Nombre d'échecs tolérés avant bannissement) :"))
            max_retry = prompt_mgr.ask_text(_info("  Max Retry [5] : ")).strip() or "5"
            if is_cancel_word(max_retry):
                ctx.console.print(_muted("Opération annulée."))
                return

            ctx.console.print(_info("• Findtime (Fenêtre de temps où les échecs sont comptabilisés, ex: 10m, 1h) :"))
            find_time = prompt_mgr.ask_text(_info("  Findtime [10m] : ")).strip() or "10m"
            if is_cancel_word(find_time):
                ctx.console.print(_muted("Opération annulée."))
                return

            ctx.console.print(_info("• Bantime (Durée du bannissement de l'IP, ex: 1h, 24h, 1w) :"))
            ban_time = prompt_mgr.ask_text(_info("  Bantime [1h] : ")).strip() or "1h"
            if is_cancel_word(ban_time):
                ctx.console.print(_muted("Opération annulée."))
                return

        # -------------------------------------------------------------------------
        # ÉTAPE 2 : CONFIRMATION
        # -------------------------------------------------------------------------
        config_filepath = f"/etc/fail2ban/jail.d/{jail_name}.conf"

        ctx.console.print()
        recap_table = Table(
            title="Récapitulatif de la configuration du nouveau Jail",
            show_header=True,
            header_style=theme_registry.get_style("table.header"),
            border_style=theme_registry.get_style("border.accent"),
            box=box.SQUARE,
            expand=False,
            padding=(0, 1),
        )
        recap_table.add_column("Paramètre", style=theme_registry.get_style("text.main"), width=28)
        recap_table.add_column("Valeur retenue", style=theme_registry.get_style("text.info"), width=42)

        recap_table.add_row("Nom du Jail", jail_name)
        recap_table.add_row("Fichier de configuration", config_filepath)
        recap_table.add_row("Log surveillé", log_path)
        recap_table.add_row("Ports cibles", port_spec)
        recap_table.add_row("Filtre appliqué", filter_name)
        recap_table.add_row("Max Retry (Tentatives)", max_retry)
        recap_table.add_row("Findtime (Période)", find_time)
        recap_table.add_row("Bantime (Durée de ban)", ban_time)

        ctx.console.print(recap_table)
        ctx.console.print()

        confirm = prompt_mgr.ask_text(_info("Valider et installer ce nouveau Jail ? (o/N) [N] : ")).strip().lower()
        if confirm not in ["o", "oui", "y", "yes"]:
            ctx.console.print(_muted("Création annulée."))
            return

        # -------------------------------------------------------------------------
        # ÉTAPE 3 : CRÉATION DU JAIL (FILTRE + CONFIGURATION + ACTIVATION)
        # -------------------------------------------------------------------------
        try:
            if fail2ban_port is None:
                raise RuntimeError("Port Fail2ban indisponible (conteneur non initialisé).")

            # 1. CRÉATION AUTOMATIQUE DU FILTRE S'IL N'EXISTE PAS SUR LE DISQUE
            # Génération du contenu par domain/fail2ban/filters.py, écriture
            # par l'adaptateur (via le port) — plus de contenu ni d'I/O
            # disque construits à la main ici (référentiel §5).
            filter_content = generate_default_http_filter(jail_name)
            if fail2ban_port.write_filter(filter_name, filter_content):
                ctx.console.print(_success(f"✔ Filtre automatique créé dans '/etc/fail2ban/filter.d/{filter_name}.conf'."))

            # 2. CRÉATION DU JAIL — fichier log, jail.d et rechargement/
            # activation du service sont désormais entièrement gérés par
            # l'adaptateur (référentiel §33) : plus de subprocess ni d'I/O
            # disque manuels ici. find_time/ban_time restent passés tels
            # que saisis (syntaxe humaine fail2ban acceptée, ex: "10m",
            # "1h" — fail2ban les interprète nativement à l'écriture ;
            # create_jail() relit toujours l'état réel après coup).
            created_info = fail2ban_port.create_jail(
                jail_name,
                filter_name,
                log_path,
                max_retry=max_retry,
                ban_time=ban_time,
                find_time=find_time,
                port=port_spec,
            )
            ctx.console.print(_success(f"✔ Configuration Jail enregistrée dans '{config_filepath}'."))
            if created_info.active:
                ctx.console.print(_success(f"✔ Service Fail2ban rechargé. Le jail '{jail_name}' est désormais ACTIF !"))
            else:
                ctx.console.print(_warning(f"Configuration écrite mais le jail '{jail_name}' n'apparaît pas encore actif."))

        except Exception as e:
            ctx.console.print(_error(f"Erreur lors de l'installation du Jail : {e}"))

    _execute_action_flow(ctx, "4.4 Création et configuration de Jail Fail2ban", logic)

def action_4_5_delete_jail(ctx: ActionContext) -> None:
    """4.5 — Suppression propre et arrêt d'un Jail Fail2ban."""
    def logic(out: List[Any]):
        from rich import box
        from rich.table import Table
        from omega_fire.interfaces.cli.themes.registry import theme_registry
        from omega_fire.application.queries.jail_status import get_jail_status

        prompt_mgr = PromptManager(ctx.console)

        ctx.console.print(_title("Suppression et Désactivation de Jail Fail2ban"))
        ctx.console.print()

        # -------------------------------------------------------------------------
        # ÉTAPE 1 : INSPECTION ET DÉTECTION DES JAILS CONFIGURÉS SUR LE DISQUE
        # -------------------------------------------------------------------------
        # Récupération du port en premier : le scan disque passe désormais
        # par l'adaptateur (Fail2banPort.list_configured_jail_files, référentiel
        # §80) au lieu d'un os.listdir() direct ici — sans port disponible,
        # aucun scan n'est possible.
        fail2ban_port = None
        if ctx.container:
            try:
                fail2ban_port = ctx.container.get_fail2ban_port()
            except Exception:
                pass

        jail_files: dict[str, str] = {}
        if fail2ban_port is not None:
            try:
                jail_files = dict(fail2ban_port.list_configured_jail_files())
            except Exception:
                jail_files = {}

        # 2. Récupération du statut actif via la requête unique (Phase 2)
        with gauge_status(ctx.console, "Scan des jails en cours..."):
            status_result = get_jail_status(fail2ban_port=fail2ban_port)

        active_jails_info: dict[str, int] = {}
        for j in status_result.jails:
            active_jails_info[j.name] = j.banned_count
            if j.name not in jail_files:
                jail_files[j.name] = f"/etc/fail2ban/jail.d/{j.name}.conf"

        if not jail_files:
            ctx.console.print(_warning("Aucun Jail personnalisé ou actif n'a été trouvé dans '/etc/fail2ban/jail.d/'."))
            return

        sorted_jail_names = sorted(list(jail_files.keys()))

        # -------------------------------------------------------------------------
        # ÉTAPE 2 : AFFICHAGE DU TABLEAU DES JAILS SUPPRIMABLES
        # -------------------------------------------------------------------------
        del_table = Table(
            title="Jails configurés disponibles pour la suppression",
            show_header=True,
            header_style=theme_registry.get_style("table.header"),
            border_style=theme_registry.get_style("border.accent"),
            box=box.SQUARE,
            expand=False,
            padding=(0, 1),
        )
        del_table.add_column("N°", style=theme_registry.get_style("text.info"), width=4, justify="right")
        del_table.add_column("Nom du Jail", style=theme_registry.get_style("text.main"), width=24)
        del_table.add_column("Statut", style=theme_registry.get_style("text.info"), width=12, justify="center")
        del_table.add_column("IPs Bannies", style=theme_registry.get_style("text.danger"), width=12, justify="right")
        del_table.add_column("Fichier Source", style=theme_registry.get_style("text.muted"), width=35)

        for idx, j_name in enumerate(sorted_jail_names, start=1):
            is_active = j_name in active_jails_info
            status_str = "Actif" if is_active else "Inactif"
            banned_str = str(active_jails_info.get(j_name, 0)) if is_active else "-"
            f_path = jail_files[j_name]
            del_table.add_row(str(idx), j_name, status_str, banned_str, f_path)

        ctx.console.print(del_table)
        ctx.console.print()

        ctx.console.print(_info("  [0] Annuler et revenir au menu principal"))
        ctx.console.print()

        # -------------------------------------------------------------------------
        # ÉTAPE 3 : SÉLECTION ET CONFIRMATION DE LA SUPPRESSION
        # -------------------------------------------------------------------------
        sel_choice = prompt_mgr.ask_text(_info("Sélectionnez le N° du Jail à supprimer : ")).strip()
        if is_cancel_word(sel_choice) or not sel_choice.isdigit():
            ctx.console.print(_muted("Opération annulée."))
            return

        sel_idx = int(sel_choice) - 1
        if not (0 <= sel_idx < len(sorted_jail_names)):
            ctx.console.print(_error("Numéro de Jail invalide."))
            return

        target_jail = sorted_jail_names[sel_idx]
        target_conf_file = jail_files[target_jail]

        ctx.console.print()
        ctx.console.print(_warning(f"⚠️  Attention : Vous allez supprimer définitivement le Jail '{target_jail}'."))
        ctx.console.print(_info(f"    • Fichier de configuration impacté : {target_conf_file}"))
        
        confirm = ctx.console.input(_info("\nÊtes-vous sûr de vouloir continuer ? (O/n) : ")).strip().lower()
        if confirm not in ["o", "oui", "y", "yes"]:
            ctx.console.print(_muted("Suppression annulée."))
            return

        # -------------------------------------------------------------------------
        # ÉTAPE 4 : SUPPRESSION VIA LE PORT (arrêt, fichiers .conf/.local,
        # filtre associé, rechargement — tout géré par l'adaptateur,
        # référentiel §35)
        # -------------------------------------------------------------------------
        ctx.console.print()
        ctx.console.print(_info(f"Arrêt et nettoyage du Jail '{target_jail}'..."))

        try:
            if fail2ban_port is None:
                raise RuntimeError("Port Fail2ban indisponible (conteneur non initialisé).")
            fail2ban_port.delete_jail(target_jail)
            ctx.console.print(_success(f"✔ Jail '{target_jail}' arrêté et supprimé (configuration et filtre associé le cas échéant)."))
            ctx.console.print(_success(f"✔ Service Fail2ban rechargé. Le jail '{target_jail}' n'existe plus !"))
        except Exception as e:
            ctx.console.print(_error(f"Erreur lors de la suppression du Jail : {e}"))
            return

    _execute_action_flow(ctx, "4.5 Suppression et Désactivation de Jail Fail2ban", logic)

def action_4_6_clear_jail(ctx: ActionContext) -> None:
    """4.6 — Vider toutes les adresses IP bannies d'un Jail Fail2ban."""
    def logic(out: List[Any]):
        from rich import box
        from rich.table import Table
        from omega_fire.interfaces.cli.themes.registry import theme_registry
        from omega_fire.application.queries.jail_status import get_jail_status

        prompt_mgr = PromptManager(ctx.console)

        ctx.console.print(_title("Vider les IPs d'un Jail Fail2ban"))
        ctx.console.print()

        # -------------------------------------------------------------------------
        # ÉTAPE 1 : INSPECTION ET RÉCUPÉRATION DES JAILS ACTIFS ET DE LEURS IPS
        # -------------------------------------------------------------------------
        fail2ban_port = None
        if ctx.container:
            try:
                fail2ban_port = ctx.container.get_fail2ban_port()
            except Exception:
                pass

        with gauge_status(ctx.console, "Scan des jails en cours..."):
            status_result = get_jail_status(fail2ban_port=fail2ban_port)

        if not status_result.jails:
            ctx.console.print(_error(status_result.message or "Impossible de contacter Fail2ban."))
            return

        active_jails_info: list[dict] = [
            {
                "name": j.name,
                "banned_ips": [str(ip) for ip in j.banned_ips],
                "count": j.banned_count,
            }
            for j in status_result.jails
        ]

        # -------------------------------------------------------------------------
        # ÉTAPE 2 : AFFICHAGE DU TABLEAU DES JAILS ET DU NOMBRE D'IPS
        # -------------------------------------------------------------------------
        clear_table = Table(
            title="État des Jails et adresses IP actuellement bannies",
            show_header=True,
            header_style=theme_registry.get_style("table.header"),
            border_style=theme_registry.get_style("border.accent"),
            box=box.SQUARE,
            expand=False,
            padding=(0, 1),
        )
        clear_table.add_column("N°", style=theme_registry.get_style("text.info"), width=4, justify="right")
        clear_table.add_column("Nom du Jail", style=theme_registry.get_style("text.main"), width=24)
        clear_table.add_column("IPs Bannies", style=theme_registry.get_style("text.danger"), width=14, justify="right")
        clear_table.add_column("Statut d'occupation", style=theme_registry.get_style("text.info"), width=25)

        for idx, j_info in enumerate(active_jails_info, start=1):
            cnt = j_info["count"]
            occ_str = "Vide (0 IP)" if cnt == 0 else f"{cnt} IP(s) à réinitialiser"
            clear_table.add_row(str(idx), j_info["name"], str(cnt), occ_str)

        ctx.console.print(clear_table)
        ctx.console.print()

        ctx.console.print(_info("  [0] Annuler et revenir au menu principal"))
        ctx.console.print()

        # -------------------------------------------------------------------------
        # ÉTAPE 3 : SÉLECTION DU JAIL À VIDER
        # -------------------------------------------------------------------------
        sel_choice = prompt_mgr.ask_text(_info("Sélectionnez le N° du Jail à vider : ")).strip()
        if is_cancel_word(sel_choice) or not sel_choice.isdigit():
            ctx.console.print(_muted("Opération annulée."))
            return

        sel_idx = int(sel_choice) - 1
        if not (0 <= sel_idx < len(active_jails_info)):
            ctx.console.print(_error("Numéro de Jail invalide."))
            return

        target_jail_info = active_jails_info[sel_idx]
        target_jail = target_jail_info["name"]
        ip_count = target_jail_info["count"]

        if ip_count == 0:
            ctx.console.print(_info(f"\nLe jail '{target_jail}' est déjà totalement vide (0 IP bannie)."))
            return

        # -------------------------------------------------------------------------
        # ÉTAPE 4 : CONFIRMATION, DÉBANISSEMENT ET RECHARGEMENT DU CACHE MEMOIRE
        # -------------------------------------------------------------------------
        ctx.console.print()
        ctx.console.print(_warning(f"Vous allez débannir {ip_count} IP(s) du Jail '{target_jail}'."))
        confirm = prompt_mgr.ask_text(_info("Confirmer le vidage des IPs ? (o/N) [N] : ")).strip().lower()
        if confirm not in ["o", "oui", "y", "yes"]:
            ctx.console.print(_muted("Opération annulée."))
            return

        ctx.console.print()
        ctx.console.print(_info(f"Vidage des IPs du Jail '{target_jail}' en cours..."))

        # Débannissement en un seul appel groupé (Fail2banAdapter.flush_jail(),
        # référentiel §2/§32) — remplace la boucle IP par IP + le reload
        # manuels : flush_jail() fait déjà `unbanip <ip1> <ip2> ...` en un
        # lot (aucun reload nécessaire, unbanip prend effet immédiatement
        # dans le cache mémoire de Fail2ban) et retourne le nombre réel
        # d'IPs débannies (pas une estimation optimiste par retour 0).
        try:
            unbanned_count = fail2ban_port.flush_jail(target_jail)
        except Exception as e:
            ctx.console.print(_error(f"Échec du vidage du Jail '{target_jail}' : {e}"))
            return

        # 3. Confirmation finale
        ctx.console.print(_success(f"✔ Le Jail '{target_jail}' a été totalement vidé ({unbanned_count} IP(s) retirée(s))."))

    _execute_action_flow(ctx, "4.6 Vider les IPs d'un Jail Fail2ban", logic)

def action_4_7_purge_all_jails(ctx: ActionContext) -> None:
    """4.7 — Purge générale : Vider les adresses IP de TOUS les Jails Fail2ban."""
    def logic(out: List[Any]):
        from rich import box
        from rich.table import Table
        from omega_fire.interfaces.cli.themes.registry import theme_registry
        from omega_fire.application.queries.jail_status import get_jail_status

        prompt_mgr = PromptManager(ctx.console)

        ctx.console.print(_title("Purge générale des Jails Fail2ban"))
        ctx.console.print()

        # -------------------------------------------------------------------------
        # ÉTAPE 1 : INSPECTION ET INVENTAIRE DE TOUTES LES IPS BANIES SUR LE SYSTÈME
        # -------------------------------------------------------------------------
        fail2ban_port = None
        if ctx.container:
            try:
                fail2ban_port = ctx.container.get_fail2ban_port()
            except Exception:
                pass

        with gauge_status(ctx.console, "Scan des jails en cours..."):
            status_result = get_jail_status(fail2ban_port=fail2ban_port)

        if not status_result.jails:
            ctx.console.print(_error(status_result.message or "Impossible de contacter le service Fail2ban."))
            return

        jails_data: list[dict] = [
            {"name": j.name, "count": j.banned_count}
            for j in status_result.jails
        ]
        total_banned_ips = status_result.total_banned_ips

        # -------------------------------------------------------------------------
        # ÉTAPE 2 : TABLEAU DU DIAGNOSTIC AVANT PURGE
        # -------------------------------------------------------------------------
        purge_table = Table(
            title="Inventaire avant Purge Globale",
            show_header=True,
            header_style=theme_registry.get_style("table.header"),
            border_style=theme_registry.get_style("border.accent"),
            box=box.SQUARE,
            expand=False,
            padding=(0, 1),
        )
        purge_table.add_column("Nom du Jail", style=theme_registry.get_style("text.main"), width=24)
        purge_table.add_column("IPs Bannies", style=theme_registry.get_style("text.danger"), width=14, justify="right")
        purge_table.add_column("Statut", style=theme_registry.get_style("text.info"), width=25)

        for j_info in jails_data:
            cnt = j_info["count"]
            status_desc = "Nettoyage requis" if cnt > 0 else "Déjà vide"
            purge_table.add_row(j_info["name"], str(cnt), status_desc)

        ctx.console.print(purge_table)
        ctx.console.print()

        if total_banned_ips == 0:
            ctx.console.print(_info("Tous les Jails sont déjà vides (0 IP bannie sur l'ensemble du système)."))
            return

        # -------------------------------------------------------------------------
        # ÉTAPE 3 : DEMANDE DE CONFIRMATION EXPLICITE
        # -------------------------------------------------------------------------
        ctx.console.print(_warning(f"⚠️  ATTENTION : Vous allez débannir un total de {total_banned_ips} IP(s) sur {len(jails_data)} Jail(s)."))
        confirm = prompt_mgr.ask_text(_info("Êtes-vous sûr de vouloir exécuter la purge globale ? (O/n) : ")).strip().lower()
        if is_cancel_word(confirm) or confirm not in ["o", "oui", "y", "yes"]:
            ctx.console.print(_muted("Purge générale annulée."))
            return

        # -------------------------------------------------------------------------
        # ÉTAPE 4 : PURGE EFFECTIVE (Fail2banAdapter.flush_all_jails, Phase 1B)
        # -------------------------------------------------------------------------
        ctx.console.print()
        ctx.console.print(_info("Purge globale en cours..."))

        try:
            purged_count = fail2ban_port.flush_all_jails()
        except Exception as e:
            ctx.console.print(_error(f"Erreur lors de la purge globale : {e}"))
            return

        ctx.console.print()
        ctx.console.print(_success(f"✔ Purge générale terminée avec succès : {purged_count} IP(s) débannie(s)."))

    _execute_action_flow(ctx, "4.7 Purge générale : vider tous les jails", logic)

def action_4_8_export_jail(ctx: ActionContext) -> None:
    """4.8 — Extraire et exporter les adresses IP d'un Jail (JSON, TXT, HTML)."""
    def logic(out: List[Any]):
        import os
        import json
        from datetime import datetime
        from rich import box
        from rich.table import Table
        from omega_fire.interfaces.cli.themes.registry import theme_registry
        from omega_fire.application.queries.jail_status import get_jail_status

        prompt_mgr = PromptManager(ctx.console)

        ctx.console.print(_title("Exportation des IPs d'un Jail Fail2ban"))
        ctx.console.print()

        # -------------------------------------------------------------------------
        # ÉTAPE 1 : INSPECTION DES JAILS ET RÉCUPÉRATION DES IPS BANNIES
        # -------------------------------------------------------------------------
        fail2ban_port = None
        if ctx.container:
            try:
                fail2ban_port = ctx.container.get_fail2ban_port()
            except Exception:
                pass

        with gauge_status(ctx.console, "Scan des jails en cours..."):
            status_result = get_jail_status(fail2ban_port=fail2ban_port)

        if not status_result.jails:
            ctx.console.print(_error(status_result.message or "Impossible de contacter Fail2ban."))
            return

        active_jails_info: list[dict] = [
            {
                "name": j.name,
                "banned_ips": sorted({str(ip) for ip in j.banned_ips}),
                "count": len({str(ip) for ip in j.banned_ips}),
            }
            for j in status_result.jails
        ]

        # -------------------------------------------------------------------------
        # ÉTAPE 2 : SÉLECTION DU JAIL
        # -------------------------------------------------------------------------
        j_table = Table(
            title="Jails Fail2ban disponibles pour l'exportation",
            show_header=True,
            header_style=theme_registry.get_style("table.header"),
            border_style=theme_registry.get_style("border.accent"),
            box=box.SQUARE,
            expand=False,
            padding=(0, 1),
        )
        j_table.add_column("N°", style=theme_registry.get_style("text.info"), width=4, justify="right")
        j_table.add_column("Nom du Jail", style=theme_registry.get_style("text.main"), width=24)
        j_table.add_column("IPs Bannies", style=theme_registry.get_style("text.danger"), width=12, justify="right")

        for idx, j in enumerate(active_jails_info, start=1):
            j_table.add_row(str(idx), j["name"], str(j["count"]))

        ctx.console.print(j_table)
        ctx.console.print()

        sel_choice = prompt_mgr.ask_text(_info("Sélectionnez le N° du Jail à exporter (ou '0' pour annuler) : ")).strip()
        if is_cancel_word(sel_choice) or not sel_choice.isdigit():
            ctx.console.print(_muted("Opération annulée."))
            return

        sel_idx = int(sel_choice) - 1
        if not (0 <= sel_idx < len(active_jails_info)):
            ctx.console.print(_error("Numéro de Jail invalide."))
            return

        target_jail = active_jails_info[sel_idx]
        jail_name = target_jail["name"]
        ips_list = target_jail["banned_ips"]

        if not ips_list:
            ctx.console.print(_warning(f"Le Jail '{jail_name}' ne contient aucune IP bannie à exporter."))
            return

        # -------------------------------------------------------------------------
        # ÉTAPE 3 : CHOIX DU FORMAT DE SORTIE
        # -------------------------------------------------------------------------
        ctx.console.print()
        ctx.console.print(_title("Format d'exportation"))
        ctx.console.print(_info("  [1] JSON (Brut structuré)"))
        ctx.console.print(_info("  [2] TXT  (Format texte brut - 1 IP par ligne, réinjectable)"))
        ctx.console.print(_info("  [3] HTML (Rapport visuel stylisé sur 3 colonnes)"))
        ctx.console.print()

        fmt_choice = prompt_mgr.ask_text(_info("Choix du format [1] : ")).strip() or "1"
        if is_cancel_word(fmt_choice):
            ctx.console.print(_muted("Opération annulée."))
            return

        ext_map = {"1": "json", "2": "txt", "3": "html"}
        file_ext = ext_map.get(fmt_choice, "json")

        # -------------------------------------------------------------------------
        # ÉTAPE 4 : DÉFINITION DYNAMIQUE DU CHEMIN (Relatif à Omega-Fire)
        # -------------------------------------------------------------------------
        # Récupère le dossier racine de l'application (ex: .../omega-fire)
       
        
        default_filepath = str(EXPORTS_DIR / f"list-{jail_name}-f2b.{file_ext}")

        ctx.console.print()
        ctx.console.print(_info(f"Chemin de sortie par défaut : {default_filepath}"))
        try:
            custom_path = prompt_mgr.ask_text(
                _info("Appuyez sur [Entrée] pour valider ou saisissez un chemin personnalisé (ou 'annuler') : "),
                allow_cancel=True,
            ).strip()
        except PromptCancelled:
            ctx.console.print(_muted("Opération annulée."))
            return

        final_path = custom_path if custom_path else default_filepath

        try:
            target_dir = os.path.dirname(final_path)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
        except Exception as e:
            ctx.console.print(_error(f"Impossible de créer le dossier de destination : {e}"))
            return

        # -------------------------------------------------------------------------
        # ÉTAPE 5 : GÉNÉRATION DU FICHIER SELON LE FORMAT
        # -------------------------------------------------------------------------
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # 1. FORMAT JSON
            if file_ext == "json":
                export_data = {
                    "source": "Omega-Fire",
                    "jail": jail_name,
                    "exported_at": now_str,
                    "total_ips": len(ips_list),
                    "ips": ips_list
                }
                with open(final_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=4, ensure_ascii=False)

            # 2. FORMAT TXT
            elif file_ext == "txt":
                lines = [f"# Omega-Fire Blocklist Export - Jail: {jail_name}", f"# Généré le : {now_str}", f"# Total IPs : {len(ips_list)}", ""]
                lines.extend(ips_list)
                with open(final_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")

            # 3. FORMAT HTML STYLISÉ (Rapport sur 3 colonnes, via template partagé)
            elif file_ext == "html":
                if not ctx.container:
                    ctx.console.print(_error("Conteneur non disponible — export HTML impossible."))
                    return

                # Division des IPs en 3 colonnes
                col_size = (len(ips_list) + 2) // 3
                col1 = ips_list[0:col_size]
                col2 = ips_list[col_size:col_size*2]
                col3 = ips_list[col_size*2:]
                max_rows = max(len(col1), len(col2), len(col3))
                ip_rows = [
                    (
                        col1[r] if r < len(col1) else "",
                        col2[r] if r < len(col2) else "",
                        col3[r] if r < len(col3) else "",
                    )
                    for r in range(max_rows)
                ]

                try:
                    theme_name = _prompt_html_theme(ctx, allow_cancel=True)
                except PromptCancelled:
                    ctx.console.print(_muted("Opération annulée."))
                    return

                exporter = ctx.container.get_exporter_port("html")
                exporter.export_data(
                    {
                        "page_title": f"Exportation Jail Fail2ban - {jail_name}",
                        "heading": f"Rapport d'exportation Jail : {jail_name}",
                        "source_label": "Jail Source",
                        "source_value": jail_name,
                        "generated_at": now_str,
                        "total_ips": len(ips_list),
                        "ip_rows": ip_rows,
                        "theme_name": theme_name,
                    },
                    final_path,
                    template_name="ip_export.html.j2",
                )

            ctx.console.print()
            ctx.console.print(_success(f"✔ Exportation réussie : {len(ips_list)} IP(s) enregistrée(s) dans '{final_path}'."))

        except Exception as e:
            ctx.console.print(_error(f"Erreur lors de l'écriture du fichier d'export : {e}"))

    _execute_action_flow(ctx, "4.8 Exporter les IP d'un jail", logic)
# -------------------------------------------------------------------------
def action_4_9_verify_config(ctx: ActionContext) -> None:
    """4.9 — Vérification complète et diagnostic de la configuration Fail2ban."""
    def logic(out: List[Any]):
        import os
        import re
        import subprocess
        from rich import box
        from rich.table import Table
        from omega_fire.interfaces.cli.themes.registry import theme_registry
        from omega_fire.application.queries.jail_status import get_jail_status

        ctx.console.print(_title("Diagnostic & Configuration Fail2ban"))
        ctx.console.print()

        fail2ban_port = None
        if ctx.container:
            try:
                fail2ban_port = ctx.container.get_fail2ban_port()
            except Exception:
                pass

        # -------------------------------------------------------------------------
        # 1. INSPECTION SYSTÈME & DÉMON
        # -------------------------------------------------------------------------
        f2b_version = "Inconnue"
        service_running = False
        socket_path = "/var/run/fail2ban/fail2ban.sock"
        socket_ok = os.path.exists(socket_path)
        sqlite_db_path = "/var/lib/fail2ban/fail2ban.sqlite3"
        sqlite_size = "Absent"

        if os.path.exists(sqlite_db_path):
            try:
                size_bytes = os.path.getsize(sqlite_db_path)
                sqlite_size = f"{size_bytes / (1024 * 1024):.2f} MB"
            except Exception:
                sqlite_size = "Présent"

        # Version Fail2ban (pas de méthode dédiée sur le port — subprocess conservé)
        try:
            v_res = subprocess.run(["fail2ban-client", "--version"], capture_output=True, text=True)
            if v_res.returncode == 0:
                v_match = re.search(r'v?(\d+\.\d+\.\d+)', v_res.stdout)
                if v_match:
                    f2b_version = v_match.group(1)
                else:
                    f2b_version = v_res.stdout.strip().splitlines()[0]
        except Exception:
            pass

        # Statut du service (Fail2banAdapter.is_available(), même méthode que
        # f2b_report/system_section.py — pas dans le contrat Fail2banPort,
        # mais déjà l'usage établi ailleurs dans le projet)
        if fail2ban_port is not None and hasattr(fail2ban_port, "is_available"):
            try:
                service_running = fail2ban_port.is_available()
            except Exception:
                service_running = False

        # -------------------------------------------------------------------------
        # 2. AUDIT DE LA SYNTAXE CONFIGURATION (Fail2banAdapter.verify_config(), Phase 1B)
        # -------------------------------------------------------------------------
        syntax_ok = False
        syntax_output = ""
        if fail2ban_port is not None and hasattr(fail2ban_port, "verify_config"):
            try:
                syntax_ok, errors = fail2ban_port.verify_config()
                syntax_output = "OK (Aucune erreur de syntaxe détectée)" if syntax_ok else ("\n".join(errors) or "Erreur de configuration")
            except Exception as e:
                syntax_output = f"Impossible de tester la syntaxe : {e}"
        else:
            syntax_output = "Port Fail2banPort non disponible."

        # -------------------------------------------------------------------------
        # 3. EXTRACTION ET DIAGNOSTIC DES JAILS DISPONIBLES ET ACTIFS
        # -------------------------------------------------------------------------
        active_jails_data: dict[str, dict] = {}
        if service_running:
            with gauge_status(ctx.console, "Scan des jails en cours..."):
                status_result = get_jail_status(fail2ban_port=fail2ban_port)
            active_jails_data = {j.name: {"banned": j.banned_count} for j in status_result.jails}

        # Inspection des fichiers de configuration /etc/fail2ban/jail.d/
        jail_files_info: list[dict] = []
        jail_d_dir = "/etc/fail2ban/jail.d"
        
        if os.path.exists(jail_d_dir):
            for fname in sorted(os.listdir(jail_d_dir)):
                if fname.endswith(".conf") or fname.endswith(".local"):
                    fpath = os.path.join(jail_d_dir, fname)
                    j_name_from_file = fname.rsplit(".", 1)[0]
                    
                    # Lecture minimale du fichier pour extraire logpath et filter
                    filter_found = "Inconnu"
                    logpath_found = "Inconnu"
                    maxretry_found = "-"
                    findtime_found = "-"
                    bantime_found = "-"

                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            content = f.read()

                            # Extraction nom entre crochet si présent
                            sec_match = re.search(r'\[([^\]]+)\]', content)
                            if sec_match and sec_match.group(1) not in ["DEFAULT", "INCLUDES"]:
                                j_name_from_file = sec_match.group(1).strip()

                            f_match = re.search(r'^\s*filter\s*=\s*(.+)$', content, re.MULTILINE)
                            if f_match:
                                filter_found = f_match.group(1).strip()

                            l_match = re.search(r'^\s*logpath\s*=\s*(.+)$', content, re.MULTILINE)
                            if l_match:
                                logpath_found = l_match.group(1).strip()

                            mr_match = re.search(r'^\s*maxretry\s*=\s*(.+)$', content, re.MULTILINE)
                            if mr_match:
                                maxretry_found = mr_match.group(1).strip()

                            ft_match = re.search(r'^\s*findtime\s*=\s*(.+)$', content, re.MULTILINE)
                            if ft_match:
                                findtime_found = ft_match.group(1).strip()

                            bt_match = re.search(r'^\s*bantime\s*=\s*(.+)$', content, re.MULTILINE)
                            if bt_match:
                                bantime_found = bt_match.group(1).strip()
                    except Exception:
                        pass

                    # Vérifications sur le disque
                    filter_exists = False
                    if filter_found != "Inconnu":
                        filt_file = f"/etc/fail2ban/filter.d/{filter_found}.conf"
                        filt_file_loc = f"/etc/fail2ban/filter.d/{filter_found}.local"
                        filter_exists = os.path.exists(filt_file) or os.path.exists(filt_file_loc)

                    log_exists = os.path.exists(logpath_found) if logpath_found != "Inconnu" else False
                    is_active = j_name_from_file in active_jails_data

                    jail_files_info.append({
                        "name": j_name_from_file,
                        "file": fname,
                        "active": is_active,
                        "banned": active_jails_data.get(j_name_from_file, {}).get("banned", 0),
                        "filter": filter_found,
                        "filter_ok": filter_exists,
                        "logpath": logpath_found,
                        "log_ok": log_exists,
                        "params": f"{maxretry_found} r / {findtime_found} / {bantime_found}"
                    })

        # -------------------------------------------------------------------------
        # 4. AFFICHAGE DES TABLES RICH THÉMATISÉES
        # -------------------------------------------------------------------------

        # Table 1 : Métriques Système
        sys_table = Table(
            title="État du Service & Environnement Fail2ban",
            show_header=True,
            header_style=theme_registry.get_style("table.header"),
            border_style=theme_registry.get_style("border.accent"),
            box=box.SQUARE,
            expand=False,
            padding=(0, 1),
        )
        sys_table.add_column("Composant / Indicateur", style=theme_registry.get_style("text.main"), width=32)
        sys_table.add_column("Valeur / État", style=theme_registry.get_style("text.info"), width=38)

        sys_table.add_row("Version de Fail2ban", f2b_version)
        sys_table.add_row("Statut du Démon", "Actif (En exécution)" if service_running else "Inactif / Déconnecté")
        sys_table.add_row("Socket Unix (/var/run/fail2ban/)", "Accessible" if socket_ok else "Inaccessible / Absent")
        sys_table.add_row("Base SQLite (/var/lib/fail2ban/)", sqlite_size)
        sys_table.add_row("Test de syntaxe global (-t)", "Valide" if syntax_ok else "Erreur détectée")

        ctx.console.print(sys_table)
        ctx.console.print()

        # Table 2 : Diagnostic des Jails
        j_table = Table(
            title="Audit des Jails configurés et Dépendances",
            show_header=True,
            header_style=theme_registry.get_style("table.header"),
            border_style=theme_registry.get_style("border.accent"),
            box=box.SQUARE,
            expand=False,
            padding=(0, 1),
        )
        j_table.add_column("Nom Jail", style=theme_registry.get_style("text.main"), width=18)
        j_table.add_column("Statut", style=theme_registry.get_style("text.info"), width=10, justify="center")
        j_table.add_column("IPs Ban", style=theme_registry.get_style("text.danger"), width=8, justify="right")
        j_table.add_column("Filtre Source", style=theme_registry.get_style("text.main"), width=20)
        j_table.add_column("Log Surveillé", style=theme_registry.get_style("text.main"), width=28)
        j_table.add_column("Règles (r/find/ban)", style=theme_registry.get_style("text.info"), width=18)

        total_banned_global = 0

        if jail_files_info:
            for item in jail_files_info:
                st_str = "Actif" if item["active"] else "Inactif"
                ban_str = str(item["banned"]) if item["active"] else "-"
                if item["active"]:
                    total_banned_global += item["banned"]

                f_str = item["filter"] + (" (OK)" if item["filter_ok"] else " (Absent)")
                l_str = item["logpath"] + (" (OK)" if item["log_ok"] else " (Introuvable)")

                j_table.add_row(item["name"], st_str, ban_str, f_str, l_str, item["params"])
        else:
            j_table.add_row("(Aucun)", "Inactif", "0", "-", "-", "-")

        ctx.console.print(j_table)
        ctx.console.print()

        # -------------------------------------------------------------------------
        # 5. BILAN GLOBAL DU DIAGNOSTIC
        # -------------------------------------------------------------------------
        ctx.console.print(_title("Bilan du Diagnostic de Santé"))

        if service_running:
            ctx.console.print(_success("✔ Le service Fail2ban est actif et répond correctement au socket."))
        else:
            ctx.console.print(_error("❌ Le service Fail2ban ne répond pas. Vérifiez s'il est démarré."))

        if syntax_ok:
            ctx.console.print(_success("✔ La vérification de syntaxe 'fail2ban-client -t' a réussi."))
        else:
            ctx.console.print(_error(f"❌ Erreur de syntaxe dans la configuration : {syntax_output}"))

        missing_filters = [i["filter"] for i in jail_files_info if not i["filter_ok"] and i["filter"] != "Inconnu"]
        if missing_filters:
            ctx.console.print(_warning(f"⚠️  Certains filtres sont introuvables dans filter.d : {', '.join(set(missing_filters))}"))
        else:
            ctx.console.print(_success("✔ Tous les filtres déclarés sont bien présents dans /etc/fail2ban/filter.d/."))

        missing_logs = [i["logpath"] for i in jail_files_info if not i["log_ok"] and i["logpath"] != "Inconnu"]
        if missing_logs:
            ctx.console.print(_warning(f"⚠️  Certains journaux surveillés n'existent pas sur le disque : {', '.join(set(missing_logs))}"))
        else:
            ctx.console.print(_success("✔ Tous les fichiers journaux cibles existent physiquement."))

        ctx.console.print(_info(f"\nSynthèse globale : {len(jail_files_info)} Jail(s) répertorié(s), {len(active_jails_data)} actif(s), {total_banned_global} IP(s) actuellement bannie(s)."))

    _execute_action_flow(ctx, "4.9 Vérification de la configuration Fail2ban", logic)
# HELPER INTERNE DE GESTION DE SERVICE SYSTEME (Start/Stop/Restart/Status/Enable/Disable)
def _manage_fail2ban_service(ctx: ActionContext, action: str) -> None:
    """Exécute la gestion de service Fail2ban (status, start, stop, restart, enable, disable).

    Passe entièrement par Fail2banPort (Fail2banServiceController, qui
    détecte systemd/openrc/runit) — aucun subprocess ni détection de
    système d'init ici, conforme à la charte (interfaces/ ne doit
    jamais appeler de binaire externe directement).
    """
    fail2ban_port = None
    if ctx.container:
        try:
            fail2ban_port = ctx.container.get_fail2ban_port()
        except Exception:
            pass

    if fail2ban_port is None:
        ctx.console.print(_error("Port Fail2ban indisponible (conteneur non initialisé)."))
        return

    if action == "status":
        if fail2ban_port.is_service_active():
            ctx.console.print(_success("✔ Service Fail2ban ACTIF / EN COURS DE FONCTIONNEMENT"))
        else:
            ctx.console.print(_warning("⚠️ Service Fail2ban INACTIF ou DÉSACTIVÉ"))

        if fail2ban_port.is_service_enabled():
            ctx.console.print(_success("✔ Persistance au démarrage : ACTIVÉE (Enabled)"))
        else:
            ctx.console.print(_warning("✗ Persistance au démarrage : NON ACTIVÉE (Disabled)"))
        return

    operations = {
        "start": (fail2ban_port.start_service, "démarré"),
        "stop": (fail2ban_port.stop_service, "arrêté"),
        "restart": (fail2ban_port.restart_service, "redémarré"),
        "enable": (fail2ban_port.enable_service, "activé au démarrage du système (persistant)"),
        "disable": (fail2ban_port.disable_service, "désactivé du démarrage du système"),
    }
    if action not in operations:
        ctx.console.print(_error(f"Action inconnue : {action}"))
        return

    op, label = operations[action]
    try:
        op()
        ctx.console.print(_success(f"✔ Service Fail2ban {label} avec succès."))
    except Exception as e:
        ctx.console.print(_error(f"Échec de la commande de service : {e}"))
# -------------------------------------------------------------------------
def action_4_10_manage_fail2ban_service(ctx: ActionContext) -> None:
    """4.10 — Contrôle du service Fail2ban (Statut, Démarrer, Stopper, Redémarrer, Activer/Désactiver au boot)."""
    def logic(out: List[Any]):
        prompt_mgr = PromptManager(ctx.console)

        ctx.console.print(_title("Contrôle et Persistance du Service Fail2ban"))
        ctx.console.print()
        ctx.console.print(_info("Actions disponibles :"))
        ctx.console.print(_info("  [1] 🔍 Vérifier le statut du service & persistance"))
        ctx.console.print(_info("  [2] ▶️  Démarrer le service (Start)"))
        ctx.console.print(_info("  [3] ⏹️  Stopper le service (Stop)"))
        ctx.console.print(_info("  [4] 🗘  Redémarrer le service (Restart)"))
        ctx.console.print(_info("  [5]   Activer le service au démarrage (Enable / Auto-start)"))
        ctx.console.print(_info("  [6] ❌ Désactiver le service au démarrage (Disable)"))
        ctx.console.print(_info("  [0] ↩️  Annuler et revenir au menu"))
        ctx.console.print()

        choice = prompt_mgr.ask_text(_info("Votre choix [1] : ")).strip() or "1"
        if is_cancel_word(choice):
            ctx.console.print(_muted("Opération annulée."))
            return

        if choice == "1":
            _manage_fail2ban_service(ctx, "status")
        elif choice == "2":
            _manage_fail2ban_service(ctx, "start")
        elif choice == "3":
            confirm = prompt_mgr.ask_text(_warning("Confirmez-vous l'ARRÊT du service Fail2ban ? (oui/non) : ")).strip().lower()
            if confirm in ["o", "oui"]:
                _manage_fail2ban_service(ctx, "stop")
            else:
                ctx.console.print(_muted("Arrêt annulé."))
        elif choice == "4":
            confirm = prompt_mgr.ask_text(_info("Confirmez-vous le REDÉMARRAGE du service Fail2ban ? (o/N) : ")).strip().lower()
            if confirm in ["o", "oui"]:
                _manage_fail2ban_service(ctx, "restart")
            else:
                ctx.console.print(_muted("Redémarrage annulé."))
        elif choice == "5":
            _manage_fail2ban_service(ctx, "enable")
        elif choice == "6":
            _manage_fail2ban_service(ctx, "disable")
        else:
            ctx.console.print(_error("Choix invalide."))

    _execute_action_flow(ctx, "4.10 Gestion du service Fail2ban", logic)
# ----------------------------------------------------------------------
# Menu 5 — Gestion des logs
# ----------------------------------------------------------------------
def action_5_1_live_tail(ctx: ActionContext) -> None:
    """5.1 — Visualiser les logs en direct (Live Tail)."""

    def logic(out: List[Any]):
        import urllib.request
        import urllib.error
        import re
        import time
        import json
        from pathlib import Path
        
        # Importation déplacée ici pour garantir la portée dans logic()
        from omega_fire.interfaces.cli.renderers.logs_live import render_logs_live
        from omega_fire.interfaces.cli.themes.registry import theme_registry
        from rich.box import ROUNDED
        from rich.text import Text

        from omega_fire.infrastructure.storage.files.json_store import JsonStore
        from omega_fire.application.commands.manage_live_tail_pins import ManageLiveTailPinsCommand
        from omega_fire.infrastructure.config.paths import RUNTIME_DIR

        prompt_mgr = PromptManager(ctx.console)

        pins_command = ManageLiveTailPinsCommand(JsonStore(RUNTIME_DIR))

        # ─── 1-3. Épingles (défauts + perso, filtrées) et historique ───
        active_pinned = pins_command.list_active_pinned()
        history = pins_command.list_history()

        # Styles du thème
        style_border = theme_registry.get_style("border.default")
        style_heading = theme_registry.get_style("text.heading")
        style_main = theme_registry.get_style("text.main")
        style_muted = theme_registry.get_style("text.muted")

        # ─── 4. Affichage du Tableau Harmonisé ───
        ctx.console.print(_info("Sources de journaux disponibles :"))
        ctx.console.print()

        source_table = Table(
            box=ROUNDED,
            border_style=style_border,
            header_style=style_heading,
            expand=True,
        )
        source_table.add_column("Choix", style=style_muted, justify="center", width=7)
        source_table.add_column("Type / Nom", style=style_heading, width=24)
        source_table.add_column("Chemin / Cible", style=style_main)

        display_items = {}
        idx = 1

        for name, path in active_pinned.items():
            key = str(idx)
            display_items[key] = {"type": "pinned", "name": name, "path": path}
            source_table.add_row(f"[{key}]", f"🖥 {name}", path)
            idx += 1

        for h_path in history[:5]:
            key = str(idx)
            display_items[key] = {"type": "history", "name": "Historique récent", "path": h_path}
            source_table.add_row(f"[{key}]", "🕒 Récent", h_path)
            idx += 1

        ctx.console.print(source_table)
        ctx.console.print(_info("  [M]   Saisie manuelle d'un chemin ou d'une URL HTTP"), highlight=False)
        ctx.console.print(_info("  [G]   Gestion des entrées (Créer / Supprimer / Purger)"), highlight=False)
        ctx.console.print()

        # ─── 5. Saisie du choix ───
        choice = ctx.console.input(_info("Sélectionnez une option (ou Entrée pour annuler) : ")).strip().upper()

        if not choice:
            ctx.console.print(_warning("Opération annulée."))
            return

        # ─── SOUS-MENU [G] : GESTION UNIFIÉE ───
        if choice == "G":
            ctx.console.print()
            ctx.console.print(_info("=== Gestion des Épingles & Historique ==="))
            ctx.console.print(_info("  [1] 🖈 Ajouter une nouvelle épingle"), highlight=False)
            ctx.console.print(_info("  [2] ✖ Supprimer un élément du tableau (Épingle ou Historique)"), highlight=False)
            ctx.console.print(_info("  [3] 🕱 Purger tout le cache (Épingles & Historique)"), highlight=False)
            ctx.console.print(_info("  [0] ↩️  Annuler"), highlight=False)

            try:
                g_choice = prompt_mgr.ask_text(_info("\nChoix [1/2/3/0] : "), allow_cancel=True).strip()
            except PromptCancelled:
                g_choice = None

            if not g_choice:
                ctx.console.print(_muted("Opération annulée."))
                return

            if g_choice == "1":
                try:
                    name = prompt_mgr.ask_text(_info("Nom de l'épingle (ou 'annuler') : "), allow_cancel=True).strip()
                except PromptCancelled:
                    name = None
                if not name:
                    ctx.console.print(_muted("Ajout annulé."))
                    return
                try:
                    path = prompt_mgr.ask_text(_info("Chemin du fichier (ou 'annuler') : "), allow_cancel=True).strip()
                except PromptCancelled:
                    path = None
                if not path:
                    ctx.console.print(_muted("Ajout annulé."))
                    return

                add_result = pins_command.add_pinned(name, path)
                if add_result.success:
                    ctx.console.print(_success(add_result.message))
                else:
                    ctx.console.print(_error(add_result.message))

            elif g_choice == "2":
                if not display_items:
                    ctx.console.print(_warning("Le tableau est vide."))
                    return

                ctx.console.print(_info("\nÉléments actuellement présents dans le tableau :"))
                for num_key, item in display_items.items():
                    badge = "🖥" if item["type"] == "pinned" else "🕒"
                    ctx.console.print(_info(f"  [{num_key}] {badge} {item['name']} -> {item['path']}"), highlight=False)

                try:
                    del_num = prompt_mgr.ask_text(
                        _info("\nNuméro de l'élément à supprimer du tableau (ou 'annuler') : "),
                        allow_cancel=True,
                    ).strip()
                except PromptCancelled:
                    del_num = None
                if not del_num:
                    ctx.console.print(_muted("Suppression annulée."))
                    return

                if del_num in display_items:
                    target_item = display_items[del_num]

                    if target_item["type"] == "pinned":
                        remove_result = pins_command.remove_pinned(target_item["name"])
                    else:
                        remove_result = pins_command.remove_history_entry(target_item["path"])

                    if remove_result.success:
                        ctx.console.print(_success(f"L'entrée [{del_num}] ({target_item['path']}) a été supprimée !"))
                    else:
                        ctx.console.print(_error(remove_result.message))
                else:
                    ctx.console.print(_error("Numéro invalide."))

            elif g_choice == "3":
                pins_command.purge_all()
                ctx.console.print(_success("Historique et épingles purgés avec succès !"))

            else:
                ctx.console.print(_error("Choix invalide."))

            return

        # ─── 6. Résolution de la source ───
        log_source = None
        if choice in display_items:
            log_source = display_items[choice]["path"]
        elif choice == "M":
            try:
                log_source = prompt_mgr.ask_text(
                    _info("\nEntrez le chemin du fichier ou l'URL HTTP (ou 'annuler') : "),
                    allow_cancel=True,
                ).strip()
            except PromptCancelled:
                log_source = None

        if not log_source:
            ctx.console.print(_warning("Source invalide. Opération annulée."))
            return

        # ─── 7. Mise à jour de l'historique ───
        if log_source not in pins_command.list_all_known_paths():
            pins_command.record_history(log_source)

        # ─── 8. LogProvider & Rendu Live Multi-Serveurs (Nginx, Apache, Caddy, Lighttpd) ───
        import json

        class LogProvider:
            def __init__(self, source: str):
                self.source = source
                self._offset = 0
                self._primed = False

            def _parse_generic_line(self, line: str) -> dict:
                line_str = line.strip()
                if not line_str:
                    return None

                # 1. FORMAT JSON (Caddy v2, Envoy, Nginx JSON, Traefik)
                if line_str.startswith("{") and line_str.endswith("}"):
                    try:
                        data = json.loads(line_str)
                        # Extraction flexible des clés JSON courantes
                        size = (
                            data.get("size")
                            or data.get("bytes_sent")
                            or data.get("response_size")
                            or data.get("body_bytes_sent")
                            or data.get("res", {}).get("size", 0)
                            or 0
                        )
                        status = data.get("status") or data.get("status_code") or data.get("res", {}).get("status", 200)
                        latency = data.get("duration") or data.get("latency") or data.get("response_time", 0)
                        if isinstance(latency, float) and latency < 10:  # conversion secondes -> ms si besoin
                            latency = int(latency * 1000)

                        return {
                            "timestamp": str(data.get("ts") or data.get("time") or data.get("timestamp") or "")[:19],
                            "source_ip": str(data.get("client_ip") or data.get("remote_ip") or data.get("ip") or "127.0.0.1"),
                            "method": str(data.get("method") or data.get("req", {}).get("method") or "GET"),
                            "path": str(data.get("uri") or data.get("path") or data.get("req", {}).get("uri") or "/"),
                            "status_code": int(status),
                            "bytes_sent": int(size) if str(size).isdigit() else 0,
                            "user_agent": str(data.get("user_agent") or "Web"),
                            "response_time_ms": int(latency) if str(latency).isdigit() else 25,
                        }
                    except Exception:
                        pass

                # 2. FORMAT TEXTE / CLASSIQUE (Nginx, Apache, Lighttpd, HAProxy)
                # Motif 1 : Format "Combined" avec requêtes entre guillemets
                combined_match = re.search(
                    r'(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>\S+)\s+(?P<path>\S+)[^"]*"\s+(?P<status>\d+)\s+(?P<size>\d+|-)',
                    line_str
                )
                if combined_match:
                    raw_size = combined_match.group("size")
                    bytes_sent = int(raw_size) if raw_size and raw_size.isdigit() else 0

                    # Recherche d'un temps de réponse éventuel en fin de ligne (Nginx $request_time ou Lighttpd)
                    tail = line_str[combined_match.end():].strip().split()
                    latency = 35
                    for token in reversed(tail):
                        clean_token = token.strip('"').replace(".", "")
                        if clean_token.isdigit() and len(clean_token) <= 6:
                            latency = int(clean_token)
                            break

                    return {
                        "timestamp": combined_match.group("time"),
                        "source_ip": combined_match.group("ip"),
                        "method": combined_match.group("method"),
                        "path": combined_match.group("path"),
                        "status_code": int(combined_match.group("status")),
                        "bytes_sent": bytes_sent,
                        "user_agent": "Mozilla/5.0",
                        "response_time_ms": latency,
                    }

                # 3. FALLBACK UNIVERSEL (Extraction heuristique par mots-clés & Regex)
                ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", line_str)
                status_match = re.search(r'\b(200|201|204|301|302|304|400|401|403|404|500|502|503)\b', line_str)
                method_match = re.search(r'\b(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b', line_str)
                
                # Extraction automatique du premier nombre isolé qui ressemble à une taille en octets
                all_numbers = re.findall(r'\b\d+\b', line_str)
                extracted_bytes = 0
                for num in all_numbers:
                    val = int(num)
                    # La taille est généralement un nombre > 0 qui n'est ni un port ni un statut HTTP
                    if val > 0 and val not in (80, 443, 8080, 8443) and val < 100000000 and val != int(status_match.group(0) if status_match else 0):
                        extracted_bytes = val
                        break

                return {
                    "timestamp": "",
                    "source_ip": ip_match.group(0) if ip_match else "N/A",
                    "method": method_match.group(0) if method_match else "LOG",
                    "path": line_str[:60],
                    "status_code": int(status_match.group(0)) if status_match else 200,
                    "bytes_sent": extracted_bytes if extracted_bytes > 0 else len(line_str),
                    "user_agent": "System",
                    "response_time_ms": 15,
                }

            def _read_last_lines(self, path: str, limit: int, chunk_size: int = 65536) -> list[str]:
                """Lit jusqu'à `limit` dernières lignes d'un fichier par blocs
                bornés (chunk_size octets), en partant de la fin — jamais le
                fichier entier en mémoire, même pour l'amorçage initial d'un
                très gros access.log (référentiel §84).
                """
                with open(path, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    file_size = f.tell()
                    pos = file_size
                    data = b""
                    while pos > 0 and data.count(b"\n") <= limit:
                        read_size = min(chunk_size, pos)
                        pos -= read_size
                        f.seek(pos)
                        data = f.read(read_size) + data
                text = data.decode("utf-8", errors="ignore")
                lines = text.splitlines()
                # Si on n'est pas remonté jusqu'au tout début du fichier, la
                # première ligne du bloc peut être tronquée en plein milieu —
                # écartée par précaution (sauf si pos == 0, vrai début de fichier).
                if pos > 0 and lines:
                    lines = lines[1:]
                return lines[-limit:]

            def get_recent_logs(self, limit=50):
                try:
                    if self.source.startswith("http://") or self.source.startswith("https://"):
                        separator = "&" if "?" in self.source else "?"
                        url_fraiche = f"{self.source}{separator}_cb={int(time.time() * 1000)}"
                        with urllib.request.urlopen(url_fraiche, timeout=5) as response:
                            content = response.read().decode("utf-8", errors="ignore")
                            lines = content.splitlines()[-limit:]

                    else:
                        # Amorçage (1er appel) : dernières lignes, lecture bornée.
                        # Appels suivants : lecture incrémentale depuis la
                        # position mémorisée (tail -f) — ne relit plus jamais
                        # le fichier entier. Avant ce correctif, CHAQUE appel
                        # (toutes les 2s, cf. DEFAULT_REFRESH_RATE) rechargeait
                        # tout le fichier via f.readlines(), coût croissant sans
                        # limite sur un access.log volumineux sous trafic réel
                        # (référentiel §84).
                        if not self._primed:
                            lines = self._read_last_lines(self.source, limit)
                            with open(self.source, "rb") as f:
                                f.seek(0, os.SEEK_END)
                                self._offset = f.tell()
                            self._primed = True
                        else:
                            with open(self.source, "rb") as f:
                                f.seek(0, os.SEEK_END)
                                current_size = f.tell()
                                if current_size < self._offset:
                                    # Rotation détectée (fichier tronqué/remplacé
                                    # depuis le dernier appel) : on repart de zéro.
                                    self._offset = 0
                                f.seek(self._offset)
                                new_bytes = f.read()
                                self._offset = f.tell()
                            lines = new_bytes.decode("utf-8", errors="ignore").splitlines()

                    parsed_logs = []
                    for line in lines:
                        parsed = self._parse_generic_line(line)
                        if parsed:
                            parsed_logs.append(parsed)
                    return parsed_logs

                except Exception as e:
                    return [{
                        "timestamp": "",
                        "source_ip": "ERR",
                        "method": "ERR",
                        "path": f"Erreur de lecture ({self.source}) : {e}",
                        "status_code": 500,
                        "bytes_sent": 0,
                        "user_agent": "System/Error",
                        "response_time_ms": 0,
                    }]

        provider = LogProvider(log_source)

        try:
            render_logs_live(
                log_provider=provider,
                console=ctx.console,
                refresh_rate=2.0,
                buffer_size=500,
            )
        except Exception as e:
            ctx.console.print(_error(f"\nErreur dans le live tail : {e}"))

    _execute_action_flow(ctx, "5.1 Live Tail", logic)

def action_5_2_top_ips(ctx: ActionContext) -> None:
    """5.2 — Analyser les IPs (Top N / Analyse de logs & blocklists)."""
    import re
    from pathlib import Path
    from datetime import datetime, timedelta
    from rich import box
    from rich.table import Table

    def logic(out: List[Any]):
        # --- 1. SÉLECTION DU FICHIER LOG / BLOCKLIST ---
        ctx.console.print(_title("1. SOURCE DU LOG OU FICHIER IP"))
        ctx.console.print()  # Ligne d'écart pour séparer les actions des épingles
        ctx.console.print(_muted("🖈 Epinglés :"))

        # Épingles persistées (var/runtime/blocklist_analysis_pinned_paths.json) —
        # bug réel corrigé le 2026-09-04 : utilisait auparavant une simple
        # liste Python en mémoire (DEFAULT_PINNED_FILES_STR), jamais
        # sauvegardée sur disque, perdue à chaque redémarrage. Même
        # mécanisme que le menu 4.4 (ManagePinnedLogPathsCommand), avec
        # ses propres défauts/fichier de stockage.
        from omega_fire.infrastructure.storage.files.json_store import JsonStore
        from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand

        pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )
        pinned_sources = pinned_command.list_paths()
        default_log = str(_PROJECT_ROOT / "var" / "log" / "access.log")
        
        # Liste des épingles (numérotées à partir de 1)
        for i, source in enumerate(pinned_sources, start=1):
            ctx.console.print(_info(f"  [{i}]  {source}"))
            
        ctx.console.print()  # Ligne d'écart pour séparer les actions des épingles
        
        ctx.console.print(_info("  [m] 🖉 Saisir un chemin manuel"))
        ctx.console.print(_info("  [a] 🖈 Ajouter une nouvelle épingle"))
        if pinned_sources:
            ctx.console.print(_info("  [s] 🗑️ Supprimer une épingle"))
        ctx.console.print(_muted("  [0/q] ❌ Annuler"))
            
        choice = ctx.console.input(_info("\nChoix de la source [1] : ")).strip().lower()
        
        if choice in ("0", "q"):
            ctx.console.print(_warning("Analyse annulée."))
            return

        # Saisir un chemin manuel
        if choice == "m":
            user_path = ctx.console.input(_info("Chemin complet du fichier (ex: /var/log/access.log) : ")).strip()
            if user_path.lower() in ("0", "q"):
                return
            selected_file = user_path if user_path else default_log

        # Ajout dynamique d'épingle
        elif choice == "a":
            new_pin = ctx.console.input(_info("Chemin complet du fichier à épingler (ou 'annuler') : ")).strip()
            if new_pin and not is_cancel_word(new_pin) and Path(new_pin).exists():
                add_result = pinned_command.add_path(new_pin)
                selected_file = new_pin
                if add_result.success:
                    ctx.console.print(_success(add_result.message))
                else:
                    ctx.console.print(_error(add_result.message))
            else:
                ctx.console.print(_error("Fichier introuvable. Opération annulée."))
                return

        # Suppression d'une épingle
        elif choice == "s":
            if not pinned_sources:
                ctx.console.print(_error("Aucune épingle à supprimer."))
                return
            del_choice = ctx.console.input(_info(f"Numéro de l'épingle à supprimer (1-{len(pinned_sources)}) : ")).strip()
            if del_choice.isdigit() and 1 <= int(del_choice) <= len(pinned_sources):
                remove_result = pinned_command.remove_path(pinned_sources[int(del_choice) - 1])
                if remove_result.success:
                    ctx.console.print(_success(remove_result.message))
                else:
                    ctx.console.print(_error(remove_result.message))
            else:
                ctx.console.print(_error("Choix invalide."))
            return

        # Sélection d'une épingle par son numéro (1, 2, 3...)
        elif choice.isdigit() and 1 <= int(choice) <= len(pinned_sources):
            selected_file = pinned_sources[int(choice) - 1]
        else:
            selected_file = pinned_sources[0] if pinned_sources else default_log

        # --- CONVERSION DU CHEMIN SÉLECTIONNÉ EN OBJET PATH ---
        log_path = Path(selected_file)

        # --- 2. SÉLECTION DU TOP N ---
        ctx.console.print()
        ctx.console.print(_title("2. NOMBRE D'IPS (TOP N)"))
        ctx.console.print(_info("  [1] Top 10\n  [2] Top 50\n  [3] Top 100\n  [4] Personnalisé"))
        ctx.console.print(_muted("  [q] Annuler"))
        n_choice = ctx.console.input(_info("Choix [1] : ")).strip().lower()
        
        if n_choice == "q":
            return

        n_map = {"1": 10, "2": 50, "3": 100}
        if n_choice in n_map:
            limit_n = n_map[n_choice]
        elif n_choice == "4":
            custom_n = ctx.console.input(_info("Entrez le nombre d'IPs : ")).strip()
            limit_n = int(custom_n) if custom_n.isdigit() and int(custom_n) > 0 else 20
        else:
            limit_n = 10

        # --- 3. SÉLECTION DE LA PÉRIODE ---
        ctx.console.print()
        ctx.console.print(_title("3. PÉRIODE À ANALYSER"))
        ctx.console.print(_info("  [1] Tout le fichier\n  [2] Dernière heure (1h)\n  [3] Dernières 24 heures (24h)\n  [4] Derniers 7 jours (7j)\n  [5] Saisie manuelle (en jours)"))
        ctx.console.print(_muted("  [q] Annuler"))
        period_choice = ctx.console.input(_info("Choix [1] : ")).strip().lower()
        
        if period_choice == "q":
            return

        time_limit = None
        now = datetime.now()
        if period_choice == "2":
            time_limit = now - timedelta(hours=1)
        elif period_choice == "3":
            time_limit = now - timedelta(days=1)
        elif period_choice == "4":
            time_limit = now - timedelta(days=7)
        elif period_choice == "5":
            days_str = ctx.console.input(_info("Saisir le nombre de jours à remonter : ")).strip()
            if days_str.isdigit() and int(days_str) > 0:
                time_limit = now - timedelta(days=int(days_str))

        # --- 4. EXTRACTION ET LECTURE (LOG vs BRUT) ---
        ip_counts = {}
        ip_bytes = {}
        total_occurrences = 0
        is_raw_ip_file = False

        log_pattern = re.compile(
            r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>\S+)\s+(?P<path>\S+)[^"]*"\s+(?P<status>\d+)\s+(?P<size>\d+|-)'
        )

        ctx.console.print()

        try:
            with gauge_status(ctx.console, f"Analyse de '{log_path.name}'..."):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    match = log_pattern.search(line)
                    if match:
                        ip = match.group("ip")
                        raw_time = match.group("time")
                        raw_size = match.group("size")

                        if time_limit:
                            try:
                                date_str = raw_time.split()[0]
                                log_dt = datetime.strptime(date_str, "%d/%b/%Y:%H:%M:%S")
                                if log_dt < time_limit:
                                    continue
                            except ValueError:
                                pass

                        bytes_sent = int(raw_size) if raw_size.isdigit() else 0
                        ip_counts[ip] = ip_counts.get(ip, 0) + 1
                        ip_bytes[ip] = ip_bytes.get(ip, 0) + bytes_sent
                        total_occurrences += 1
                    else:
                        raw_ips = _extract_valid_ips(line)
                        if raw_ips:
                            is_raw_ip_file = True
                            for ip in raw_ips:
                                ip_counts[ip] = ip_counts.get(ip, 0) + 1
                                total_occurrences += 1

        except Exception as e:
            ctx.console.print(_error(f"Erreur lors de la lecture du fichier : {e}"))
            return

        if not ip_counts:
            ctx.console.print(_warning("Aucune IP valide n'a pu être extraite de ce fichier."))
            return

        # --- 5. AFFICHAGE DES RÉSULTATS ---
        sorted_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:limit_n]
        duplicates_count = sum(count - 1 for count in ip_counts.values() if count > 1)

        title_suffix = "(Fichier brut / Blocklist)" if is_raw_ip_file else "(Log serveur)"
        table = Table(
            title=f"Top {len(sorted_ips)} IPs — {log_path.name} {title_suffix}",
            show_header=True,
            header_style=theme_registry.get_style("text.heading"),
            border_style=theme_registry.get_style("border.default"),
            box=box.ROUNDED,
        )

        table.add_column("Rang", justify="right", style=theme_registry.get_style("text.muted"), width=6)
        # width=40 : couvre une IPv6 complète (jusqu'à 39 caractères) —
        # 18 (IPv4 max) ne suffisait plus (référentiel §52, plan IPv6
        # Phase C).
        table.add_column("Adresse IP", style=theme_registry.get_style("text.main"), width=40)
        
        if is_raw_ip_file:
            table.add_column("Occurrences", justify="right", style=theme_registry.get_style("action.warning"), width=14)
            table.add_column("Statut Doublons", justify="center", style=theme_registry.get_style("text.info"), width=16)
        else:
            table.add_column("Requêtes", justify="right", style=theme_registry.get_style("action.success"), width=12)
            table.add_column("% Trafic", justify="right", style=theme_registry.get_style("action.warning"), width=10)
            table.add_column("Volume Total", justify="right", style=theme_registry.get_style("text.info"), width=14)

        def _format_size(size: int) -> str:
            if size > 1024 * 1024:
                return f"{size / (1024 * 1024):.1f} MB"
            elif size > 1024:
                return f"{size / 1024:.1f} KB"
            return f"{size} B"

        for rank, (ip, count) in enumerate(sorted_ips, start=1):
            if is_raw_ip_file:
                status_dup = "⚠️ Doublon" if count > 1 else "💻 Unique"
                table.add_row(f"#{rank}", ip, f"{count}", status_dup)
            else:
                pct = (count / total_occurrences * 100) if total_occurrences > 0 else 0
                vol = _format_size(ip_bytes.get(ip, 0))
                table.add_row(f"#{rank}", ip, f"{count:,}", f"{pct:.1f}%", vol)

        ctx.console.print()
        ctx.console.print(table)

        if is_raw_ip_file:
            if duplicates_count > 0:
                ctx.console.print(_warning(f"Total entrées : {total_occurrences} | IPs uniques : {len(ip_counts)} | Doublons détectés : {duplicates_count}"))
            else:
                ctx.console.print(_success(f"Fichier propre ! Total {len(ip_counts)} IPs uniques sans aucun doublon."))
        else:
            ctx.console.print(_success(f"Analyse terminée ({len(sorted_ips)} IPs affichées sur {total_occurrences} requêtes)."))

    _execute_action_flow(ctx, "5.2 Top IPs", logic)

def action_5_3_remove_ip_logs(ctx: ActionContext) -> None:
    """5.3 — Supprimer une IP d'un fichier source (Blocklist / Logs)."""
    import re
    from pathlib import Path
    from rich import box
    from rich.table import Table

    def logic(out: List[Any]):
        # --- 1. SÉLECTION DU FICHIER SOURCE ---
        ctx.console.print(_title("1. SOURCE DU LOG OU FICHIER IP"))
        ctx.console.print()  # Ligne d'écart
        # Épingles persistées, même mécanisme que 5.2 (voir son commentaire) —
        # bug réel corrigé le 2026-09-04.
        from omega_fire.infrastructure.storage.files.json_store import JsonStore
        from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand

        pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )
        pinned_sources = pinned_command.list_paths()
        default_log = "var/log/access.log"

        # Liste des épingles (numérotées à partir de 1)
        ctx.console.print(_muted("🖈 Epinglés :"))
        for i, source in enumerate(pinned_sources, start=1):
            ctx.console.print(_info(f"  [{i}]  {source}"))

        ctx.console.print()  # Ligne d'écart

        ctx.console.print(_info("  [m] 🖉 Saisir un chemin manuel"))
        ctx.console.print(_info("  [a] 🖈 Ajouter une nouvelle épingle"))
        if pinned_sources:
            ctx.console.print(_info("  [s] 🗑️ Supprimer une épingle"))
        ctx.console.print(_muted("  [0/q] ❌ Annuler"))

        choice = ctx.console.input(_info("\nChoix de la source [1] : ")).strip().lower()

        if choice in ("0", "q"):
            ctx.console.print(_warning("Opération annulée."))
            return

        # Saisie manuelle
        if choice == "m":
            user_path = ctx.console.input(_info("Chemin du fichier (ex: var/blocklist/blocklist.txt) : ")).strip()
            if user_path.lower() in ("0", "q"):
                return
            selected_file = user_path if user_path else default_log

        # Ajout d'épingle
        elif choice == "a":
            new_pin = ctx.console.input(_info("Chemin complet du fichier à épingler (ou 'annuler') : ")).strip()
            if new_pin and not is_cancel_word(new_pin) and Path(new_pin).exists():
                add_result = pinned_command.add_path(new_pin)
                selected_file = new_pin
                if add_result.success:
                    ctx.console.print(_success(add_result.message))
                else:
                    ctx.console.print(_error(add_result.message))
            else:
                ctx.console.print(_error("Fichier introuvable. Opération annulée."))
                return

        # Suppression d'épingle
        elif choice == "s":
            if not pinned_sources:
                ctx.console.print(_error("Aucune épingle à supprimer."))
                return
            del_choice = ctx.console.input(_info(f"Numéro de l'épingle à supprimer (1-{len(pinned_sources)}) : ")).strip()
            if del_choice.isdigit() and 1 <= int(del_choice) <= len(pinned_sources):
                remove_result = pinned_command.remove_path(pinned_sources[int(del_choice) - 1])
                if remove_result.success:
                    ctx.console.print(_success(remove_result.message))
                else:
                    ctx.console.print(_error(remove_result.message))
            else:
                ctx.console.print(_error("Choix invalide."))
            return

        # Sélection par numéro d'épingle
        elif choice.isdigit() and 1 <= int(choice) <= len(pinned_sources):
            selected_file = pinned_sources[int(choice) - 1]
        else:
            selected_file = pinned_sources[0] if pinned_sources else default_log

        # Résolution du chemin
        raw_path = Path(selected_file)
        if raw_path.exists():
            target_path = raw_path
        else:
            target_path = _PROJECT_ROOT / raw_path.relative_to(raw_path.anchor) if raw_path.is_absolute() else _PROJECT_ROOT / raw_path

        if not target_path.exists():
            ctx.console.print(_error(f"Fichier introuvable : {target_path}"))
            return

        # --- 2. SAISIE DE L'IP À SUPPRIMER ---
        ctx.console.print()
        ctx.console.print(_title("2. ADRESSE IP À SUPPRIMER"))
        target_ip = ctx.console.input(_info("Entrez l'adresse IP à retirer : ")).strip()

        if not target_ip or is_cancel_word(target_ip):
            ctx.console.print(_warning("Opération annulée."))
            return

        # Validation basique du format IP (IPv4 ou IPv6)
        try:
            ipaddress.ip_address(target_ip)
        except ValueError:
            ctx.console.print(_error("Format d'adresse IP invalide."))
            return

        # --- 3. ANALYSE DU FICHIER ET COMPTAGE DES OCCURRENCES ---
        ctx.console.print()

        try:
            with gauge_status(ctx.console, f"Analyse de '{target_path.name}'..."):
                with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
        except Exception as e:
            ctx.console.print(_error(f"Impossible de lire le fichier : {e}"))
            return

        matched_lines = []
        cleaned_lines = []

        with gauge_status(ctx.console, f"Recherche de {target_ip}..."):
            for line in lines:
                # On cherche l'IP exact (mot entier pour éviter de matcher 192.168.1.1 dans 192.168.1.10)
                if re.search(rf'\b{re.escape(target_ip)}\b', line):
                    matched_lines.append(line)
                else:
                    cleaned_lines.append(line)

        occurrences = len(matched_lines)

        if occurrences == 0:
            ctx.console.print(_warning(f"L'adresse IP {target_ip} n'a pas été trouvée dans '{target_path.name}'."))
            return

        # --- 4. RÉCAPITULATIF ET CONFIRMATION ---
        ctx.console.print()
        table = Table(
            title=f"Récapitulatif — {target_path.name}",
            show_header=True,
            header_style=theme_registry.get_style("text.heading"),
            border_style=theme_registry.get_style("border.default"),
            box=box.ROUNDED,
        )
        table.add_column("Propriété", style=theme_registry.get_style("text.info"), width=20)
        table.add_column("Valeur", style=theme_registry.get_style("text.main"))

        table.add_row("Fichier cible", str(target_path))
        table.add_row("IP à supprimer", target_ip)
        table.add_row("Occurrences trouvées", Text(str(occurrences), style=theme_registry.get_style("text.warning")))
        table.add_row("Lignes restantes après purge", str(len(cleaned_lines)))

        ctx.console.print(table)
        ctx.console.print()

        confirm = ctx.console.input(_info(f"Confirmer la suppression de {occurrences} occurrence(s) de {target_ip} ? (o/N) : ")).strip().lower()

        if confirm not in ("o", "oui", "y", "yes"):
            ctx.console.print(_warning("Suppression annulée. Aucun fichier n'a été modifié."))
            return

        # --- 5. ÉCRITURE DANS LE FICHIER ---
        try:
            with gauge_status(ctx.console, f"Suppression de {occurrences} occurrence(s)..."):
                with open(target_path, "w", encoding="utf-8") as f:
                    f.writelines(cleaned_lines)
            ctx.console.print(_success(f"Suppression réussie ! {occurrences} occurrence(s) retirée(s) de {target_path.name}."))
        except Exception as e:
            ctx.console.print(_error(f"Erreur lors de l'écriture dans le fichier : {e}"))

    _execute_action_flow(ctx, "5.3 Supprimer IP", logic)

def action_5_4_rotate_logs(ctx: ActionContext) -> None:
    """5.4 — Rotation / Backup des logs."""
    import tarfile
    import json
    from pathlib import Path
    from datetime import datetime
    from rich import box
    from rich.table import Table

    def logic(out: List[Any]):
        auto_file = RUNTIME_DIR / "scheduled_rotations.json"

        # --- 1. SÉLECTION DU MENU PRINCIPAL DU MODULE ---
        ctx.console.print(_title(" ROTATION & BACKUP DES LOGS "))
        ctx.console.print()
        ctx.console.print(_info("  [1] 📦 Créer une sauvegarde manuelle immédiatement"))
        ctx.console.print(_info("  [2] ⚙️  Configurer une automatisation de sauvegarde"))
        ctx.console.print(_info("  [3] 📋 Lister et gérer les automatisations en cours"))
        ctx.console.print(_muted("  [0/q] ❌ Annuler"))

        main_choice = ctx.console.input(_info("\nChoix de l'action [1] : ")).strip().lower()

        if main_choice in ("0", "q"):
            ctx.console.print(_warning("Opération annulée."))
            return

        if main_choice not in ("1", "2", "3"):
            main_choice = "1"

        # --- OPTION 3 : GESTION ET SUPPRESSION DES AUTOMATISATIONS ---
        if main_choice == "3":
            ctx.console.print()
            ctx.console.print(_title("AUTOMATISATIONS EN COURS"))
            
            if not SCHEDULED_AUTOMATIONS:
                ctx.console.print(_warning("Aucune automatisation n'est actuellement configurée."))
                return

            auto_table = Table(
                title="Règles Planifiées Activement",
                show_header=True,
                header_style=theme_registry.get_style("text.heading"),
                border_style=theme_registry.get_style("border.default"),
                box=box.ROUNDED,
            )
            auto_table.add_column("#", style=theme_registry.get_style("text.info"), width=4)
            auto_table.add_column("Source", style=theme_registry.get_style("text.info"))
            auto_table.add_column("Fréquence", style=theme_registry.get_style("text.main"))
            auto_table.add_column("Créée le", style=theme_registry.get_style("text.muted"))

            for idx, item in enumerate(SCHEDULED_AUTOMATIONS, start=1):
                auto_table.add_row(
                    str(idx),
                    item["source_path"],
                    f"{item['interval_label']} ({item['days_interval']}j)",
                    item["created_at"]
                )

            ctx.console.print(auto_table)
            ctx.console.print()
            ctx.console.print(_info("  [d] 🗑️ Supprimer une automatisation"))
            ctx.console.print(_muted("  [0/q] ↩️ Retour"))

            sub_choice = ctx.console.input(_info("\nAction : ")).strip().lower()

            if sub_choice == "d":
                del_idx = ctx.console.input(_info(f"Numéro de la règle à supprimer (1-{len(SCHEDULED_AUTOMATIONS)}) : ")).strip()
                if del_idx.isdigit() and 1 <= int(del_idx) <= len(SCHEDULED_AUTOMATIONS):
                    removed = SCHEDULED_AUTOMATIONS.pop(int(del_idx) - 1)
                    
                    # Sauvegarde sur disque après suppression
                    with open(auto_file, "w", encoding="utf-8") as f:
                        json.dump(SCHEDULED_AUTOMATIONS, f, indent=2, ensure_ascii=False)

                    ctx.console.print(_success(f"Automatisation pour '{removed['source_path']}' supprimée avec succès."))
                else:
                    ctx.console.print(_error("Choix invalide."))
            return

        # --- 2. SÉLECTION DE LA SOURCE (POUR OPTIONS 1 ET 2) ---
        ctx.console.print()
        ctx.console.print(_title("1. SOURCE À SAUVEGARDER"))
        ctx.console.print(_muted("🖈 Epinglés :"))
        # Épingles persistées, même mécanisme que 5.2 (voir son commentaire) —
        # bug réel corrigé le 2026-09-04.
        from omega_fire.infrastructure.storage.files.json_store import JsonStore
        from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand

        pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )
        pinned_sources = pinned_command.list_paths()
        default_log = "var/log/access.log"

        for i, source in enumerate(pinned_sources, start=1):
            ctx.console.print(_info(f"  [{i}]  {source}"))

        ctx.console.print()

        ctx.console.print(_info("  [m] 🖉 Saisir un chemin manuel"))
        ctx.console.print(_info("  [a] 🖈 Ajouter une nouvelle épingle"))
        if pinned_sources:
            ctx.console.print(_info("  [s] 🗑️ Supprimer une épingle"))
        ctx.console.print(_muted("  [0/q] ❌ Annuler"))

        choice = ctx.console.input(_info("\nChoix de la source [1] : ")).strip().lower()

        if choice in ("0", "q"):
            ctx.console.print(_warning("Opération annulée."))
            return

        if choice == "m":
            user_path = ctx.console.input(_info("Chemin du fichier (ex: var/log/access.log) : ")).strip()
            if user_path.lower() in ("0", "q"):
                return
            selected_file = user_path if user_path else default_log

        elif choice == "a":
            new_pin = ctx.console.input(_info("Chemin complet du fichier à épingler (ou 'annuler') : ")).strip()
            if new_pin and not is_cancel_word(new_pin) and Path(new_pin).exists():
                add_result = pinned_command.add_path(new_pin)
                selected_file = new_pin
                if add_result.success:
                    ctx.console.print(_success(add_result.message))
                else:
                    ctx.console.print(_error(add_result.message))
            else:
                ctx.console.print(_error("Fichier introuvable. Opération annulée."))
                return

        elif choice == "s":
            if not pinned_sources:
                ctx.console.print(_error("Aucune épingle à supprimer."))
                return
            del_choice = ctx.console.input(_info(f"Numéro de l'épingle à supprimer (1-{len(pinned_sources)}) : ")).strip()
            if del_choice.isdigit() and 1 <= int(del_choice) <= len(pinned_sources):
                remove_result = pinned_command.remove_path(pinned_sources[int(del_choice) - 1])
                if remove_result.success:
                    ctx.console.print(_success(remove_result.message))
                else:
                    ctx.console.print(_error(remove_result.message))
            else:
                ctx.console.print(_error("Choix invalide."))
            return

        elif choice.isdigit() and 1 <= int(choice) <= len(pinned_sources):
            selected_file = pinned_sources[int(choice) - 1]
        else:
            selected_file = pinned_sources[0] if pinned_sources else default_log

        raw_path = Path(selected_file)
        if raw_path.exists():
            source_path = raw_path
        else:
            source_path = _PROJECT_ROOT / raw_path.relative_to(raw_path.anchor) if raw_path.is_absolute() else _PROJECT_ROOT / raw_path

        if not source_path.exists():
            ctx.console.print(_error(f"Fichier introuvable : {source_path}"))
            return

        # --- DÉVIATION SEGMENT A : SAUVEGARDE MANUELLE (OPTION 1) ---
        if main_choice == "1":
            ctx.console.print()
            ctx.console.print(_title("2. CRÉATION DU BACKUP COMPRESSÉ"))
            ctx.console.print(_muted(f"Compression de '{source_path.name}' vers 'var/backups/'..."))

            command = RotateLogsCommand(persistence_port=ctx.container.get_persistence_port())
            result = command.execute(RotateLogsRequest(
                source_path=str(source_path),
                reason="Sauvegarde manuelle (menu 5.4)",
                keep=10,
            ))

            if not result.success:
                ctx.console.print(_error(f"ÉCHEC DE LA SAUVEGARDE : {result.message}"))
            else:
                src_size = source_path.stat().st_size
                dst_size = result.backup_size_bytes or 0
                ratio = (1 - (dst_size / src_size)) * 100 if src_size > 0 else 0

                table = Table(
                    title="Statut de la Sauvegarde Manuelle",
                    show_header=True,
                    header_style=theme_registry.get_style("text.heading"),
                    border_style=theme_registry.get_style("border.default"),
                    box=box.ROUNDED,
                )
                table.add_column("Propriété", style=theme_registry.get_style("text.info"), width=22)
                table.add_column("Détail / Chemin", style=theme_registry.get_style("text.main"))

                table.add_row("Résultat", _success("RÉUSSI"))
                table.add_row("Fichier Source", str(source_path))
                if result.backup_path:
                    table.add_row("Archive Générée", result.backup_path.name)
                    table.add_row("Chemin Complet", str(result.backup_path))
                table.add_row("Taille Originale", f"{src_size / 1024:.1f} KB")
                table.add_row("Taille Compressée", f"{dst_size / 1024:.1f} KB ({ratio:.1f}% de gain)")
                if result.deleted_count > 0:
                    table.add_row("Rotation appliquée", f"{result.deleted_count} ancienne(s) archive(s) supprimée(s)")

                ctx.console.print()
                ctx.console.print(table)
                ctx.console.print(_success(result.message))

        # --- DÉVIATION SEGMENT B : AUTOMATISATION / PLANIFICATION (OPTION 2) ---
        elif main_choice == "2":
            ctx.console.print()
            ctx.console.print(_title("2. PLANIFICATION DE L'AUTOMATISATION"))
            ctx.console.print(_info("  [1] Toutes les semaines (7 jours)"))
            ctx.console.print(_info("  [2] Tous les mois (~30 jours)"))
            ctx.console.print(_info("  [3] Tous les trimestres (~90 jours)"))
            ctx.console.print(_info("  [4] Tous les semestres (~180 jours)"))
            ctx.console.print(_info("  [5] Tous les ans (~364 jours)"))
            ctx.console.print(_info("  [6] Saisir un temps sur mesure (en jours)"))
            ctx.console.print(_muted("  [0/q] Annuler"))

            auto_choice = ctx.console.input(_info("\nChoix de la fréquence [1] : ")).strip().lower()

            if auto_choice in ("0", "q"):
                ctx.console.print(_warning("Planification annulée."))
                return

            days_map = {
                "1": (7, "Toutes les semaines"),
                "2": (30, "Tous les mois"),
                "3": (90, "Tous les trimestres"),
                "4": (180, "Tous les semestres"),
                "5": (364, "Tous les ans"),
            }

            if auto_choice in days_map:
                days_interval, interval_label = days_map[auto_choice]
            elif auto_choice == "6":
                custom_days = ctx.console.input(_info("Entrez l'intervalle en jours (ex: 15) : ")).strip()
                if custom_days.isdigit() and int(custom_days) > 0:
                    days_interval = int(custom_days)
                    interval_label = f"Tous les {days_interval} jours"
                else:
                    ctx.console.print(_error("Nombre de jours invalide."))
                    return
            else:
                days_interval, interval_label = 7, "Toutes les semaines"

            # 1. Enregistrement en mémoire
            SCHEDULED_AUTOMATIONS.append({
                "source_path": str(source_path),
                "days_interval": days_interval,
                "interval_label": interval_label,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            })

            # 2. Sauvegarde immédiate sur disque
            RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
            with open(auto_file, "w", encoding="utf-8") as f:
                json.dump(SCHEDULED_AUTOMATIONS, f, indent=2, ensure_ascii=False)

            table = Table(
                title="Configuration de la Rotation Automatique",
                show_header=True,
                header_style=theme_registry.get_style("text.heading"),
                border_style=theme_registry.get_style("border.default"),
                box=box.ROUNDED,
            )
            table.add_column("Paramètre", style=theme_registry.get_style("text.info"), width=22)
            table.add_column("Valeur", style=theme_registry.get_style("text.main"))

            table.add_row("Source planifiée", str(source_path))
            table.add_row("Fréquence choisie", f"{interval_label} ({days_interval}j)")
            table.add_row("Dossier de destination", str(BACKUPS_DIR))
            table.add_row("Nom de fichier type", f"backup_{source_path.stem}_YYYYMMDD_HHMMSS_XXX.tar.gz")
            table.add_row("Statut de la Règle", _success("CONFIGURÉE ET ENREGISTRÉE"))

            ctx.console.print()
            ctx.console.print(table)
            ctx.console.print(_success(f"Règle de rotation configurée avec succès pour '{source_path.name}' ({interval_label})."))

    _execute_action_flow(ctx, "5.4 Rotation & Backup Logs", logic)

def action_5_5_restore_backup(ctx: ActionContext) -> None:
    """5.5 — Restaurer un backup."""
    import shutil
    import json
    from pathlib import Path
    from datetime import datetime
    from rich import box
    from rich.table import Table

    def logic(out: List[Any]):
        restore_auto_file = RUNTIME_DIR / "scheduled_restores.json"

        # --- 1. MENU PRINCIPAL DU MODULE RESTAURATION ---
        ctx.console.print(_title("RESTAURATION DES LOGS"))
        ctx.console.print()
        ctx.console.print(_info("  [1] 📦 Restaurer une sauvegarde immédiatement"))
        ctx.console.print(_info("  [2] ⚙️ Configurer une automatisation de restauration"))
        ctx.console.print(_info("  [3] 📋 Lister et gérer les automatisations en cours"))
        ctx.console.print(_muted(" [0/q] ❌ Annuler"))

        main_choice = ctx.console.input(_info("\nChoix de l'action [1] : ")).strip().lower()

        if main_choice in ("0", "q"):
            ctx.console.print(_warning("Opération annulée."))
            return

        backup_dir = BACKUPS_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)

        # --- OPTION 3 : GESTION ET SUPPRESSION DES AUTOMATISATIONS DE RESTAURATION ---
        if main_choice == "3":
            ctx.console.print()
            ctx.console.print(_title("AUTOMATISATIONS DE RESTAURATION EN COURS"))

            if not SCHEDULED_RESTORES:
                ctx.console.print(_warning("Aucune automatisation de restauration n'est actuellement configurée."))
                return

            table = Table(
                title="Règles de Restauration Planifiées",
                show_header=True,
                header_style=theme_registry.get_style("text.heading"),
                border_style=theme_registry.get_style("border.default"),
                box=box.ROUNDED,
            )
            table.add_column("#", style=theme_registry.get_style("text.info"), width=4)
            table.add_column("Stratégie", style=theme_registry.get_style("text.info"))
            table.add_column("Intervalle", style=theme_registry.get_style("text.main"))
            table.add_column("Mode", style=theme_registry.get_style("text.main"))
            table.add_column("Créée le", style=theme_registry.get_style("text.muted"))

            for idx, item in enumerate(SCHEDULED_RESTORES, start=1):
                interval_str = f"{item['days_interval']}j" if item['days_interval'] > 0 else "N/A"
                table.add_row(
                    str(idx),
                    item["strategy_title"],
                    interval_str,
                    item["mode_label"],
                    item["created_at"]
                )

            ctx.console.print(table)
            ctx.console.print()
            ctx.console.print(_info("  [d] 🗑️ Supprimer une automatisation"))
            ctx.console.print(_muted("  [0/q] ↩️ Retour"))

            sub_choice = ctx.console.input(_info("\nAction : ")).strip().lower()

            if sub_choice == "d":
                del_idx = ctx.console.input(_info(f"Numéro de la règle à supprimer (1-{len(SCHEDULED_RESTORES)}) : ")).strip()
                if del_idx.isdigit() and 1 <= int(del_idx) <= len(SCHEDULED_RESTORES):
                    removed = SCHEDULED_RESTORES.pop(int(del_idx) - 1)

                    with open(restore_auto_file, "w", encoding="utf-8") as f:
                        json.dump(SCHEDULED_RESTORES, f, indent=2, ensure_ascii=False)

                    ctx.console.print(_success(f"Automatisation '{removed['strategy_title']}' supprimée avec succès."))
                else:
                    ctx.console.print(_error("Choix invalide."))
            return

        if main_choice not in ("1", "2"):
            main_choice = "1"

        # --- DÉVIATION SEGMENT A : RESTAURATION IMMÉDIATE (OPTION 1) ---
        if main_choice == "1":
            ctx.console.print()
            ctx.console.print(_title("RESTAURER UNE SAUVEGARDE IMMÉDIATEMENT"))

            all_backups = sorted(
                [f for f in backup_dir.glob("backup_*.tar.gz") if f.is_file()],
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )

            if not all_backups:
                ctx.console.print(_error("Aucun fichier de sauvegarde ('backup_*.tar.gz') trouvé dans 'var/backups/'."))
                return

            page_size = 20
            total_items = len(all_backups)
            current_page = 0

            selected_backup: Path | None = None

            while selected_backup is None:
                start_idx = current_page * page_size
                end_idx = min(start_idx + page_size, total_items)
                page_files = all_backups[start_idx:end_idx]

                ctx.console.print(_muted(f"\nSauvegardes disponibles (Page {current_page + 1}/{(total_items - 1) // page_size + 1}) :"))

                for i, bfile in enumerate(page_files, start=start_idx + 1):
                    mtime = datetime.fromtimestamp(bfile.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")
                    size_kb = bfile.stat().st_size / 1024
                    ctx.console.print(_info(f"  [{i}] 📦 {bfile.name} ({mtime} — {size_kb:.1f} KB)"))

                ctx.console.print()
                if end_idx < total_items:
                    ctx.console.print(_info("  [n] ➡️ Page suivante"))
                if current_page > 0:
                    ctx.console.print(_info("  [p] ⬅️ Page précédente"))
                ctx.console.print(_muted("  [0/q] ❌ Annuler"))

                b_choice = ctx.console.input(_info(f"\nSélectionnez une sauvegarde (1-{total_items}) : ")).strip().lower()

                if b_choice in ("0", "q"):
                    ctx.console.print(_warning("Restauration annulée."))
                    return
                elif b_choice == "n" and end_idx < total_items:
                    current_page += 1
                elif b_choice == "p" and current_page > 0:
                    current_page -= 1
                elif b_choice.isdigit() and 1 <= int(b_choice) <= total_items:
                    selected_backup = all_backups[int(b_choice) - 1]
                else:
                    ctx.console.print(_error("Choix invalide."))

            # Mode de restauration
            ctx.console.print()
            ctx.console.print(_title("2. MODE DE RESTAURATION"))
            ctx.console.print()
            ctx.console.print(_info("  [1] ✚ Rajouter (Incrémenter le fichier existant)"))
            ctx.console.print(_info("  [2] 🕱 Écraser (Vos logs actuels seront sauvegardés automatiquement puis remplacés)"))
            ctx.console.print(_muted(" [0] ❌ Annuler"))

            mode_choice = ctx.console.input(_info("\nChoix du mode [1] : ")).strip().lower()

            if mode_choice in ("0", "q"):
                ctx.console.print(_warning("Restauration annulée."))
                return

            mode = "append" if mode_choice != "2" else "overwrite"

            # Détermination du dossier cible selon le nom du fichier archivé
            if "blocklist" in selected_backup.name:
                target_dir = BLOCKLIST_DIR
            elif "export" in selected_backup.name:
                target_dir = EXPORTS_DIR
            else:
                target_dir = LOGS_DIR

            command = RestoreBackupCommand(persistence_port=ctx.container.get_persistence_port())
            restore_result = command.execute(RestoreBackupRequest(
                backup_path=str(selected_backup),
                target_dir=str(target_dir),
                mode=mode,
            ))

            if not restore_result.success:
                ctx.console.print(_error(f"ÉCHEC DE LA RESTAURATION : {restore_result.message}"))
                return

            target_file = restore_result.target_file
            auto_safety_backup = restore_result.safety_backup_path
            action_summary = "Remplacement complet (Écrasement)" if mode == "overwrite" else "Fusion incrémentale (Ajout)"

            table = Table(
                title="Rapport de Restauration",
                show_header=True,
                header_style=theme_registry.get_style("text.heading"),
                border_style=theme_registry.get_style("border.default"),
                box=box.ROUNDED,
            )
            table.add_column("Propriété", style=theme_registry.get_style("text.info"), width=24)
            table.add_column("Détail", style=theme_registry.get_style("text.main"))

            table.add_row("Résultat", _success("RÉUSSI"))
            table.add_row("Archive Restaurée", selected_backup.name)
            table.add_row("Mode Appliqué", action_summary)
            table.add_row("Fichier Cible Affecté", str(target_file))
            if auto_safety_backup:
                table.add_row("Backup de Sécurité Créé", auto_safety_backup.name)

            ctx.console.print()
            ctx.console.print(table)
            ctx.console.print(_success(restore_result.message))
            
        # --- DÉVIATION SEGMENT B : CONFIGURATION AUTOMATISATION (OPTION 2) ---
        elif main_choice == "2":
            ctx.console.print()
            ctx.console.print(_title("CONFIGURATION AUTOMATISATION RESTAURATION"))
            ctx.console.print()
            ctx.console.print(_info("  [1] ⦿ Restauration manuelle ciblée"))
            ctx.console.print(_info("  [2] 🛡 Restauration automatique « Dernier état sain »"))
            ctx.console.print(_info("  [3] ⌛ Planification de purge / rollback périodique"))
            ctx.console.print(_muted("  [0/q] ❌ Annuler"))

            opt_choice = ctx.console.input(_info("\nChoix de la stratégie [1] : ")).strip().lower()

            if opt_choice in ("0", "q"):
                ctx.console.print(_warning("Planification annulée."))
                return

            days_interval = 0
            if opt_choice == "3":
                ctx.console.print()
                ctx.console.print(_info("  [1] Fréquence standard (6 mois / 180 jours)"))
                ctx.console.print(_info("  [2] Saisir une période sur mesure (en jours)"))
                period_sub = ctx.console.input(_info("\nChoix de la période [1] : ")).strip().lower()

                if period_sub == "2":
                    custom_days = ctx.console.input(_info("Entrez le nombre de jours pour le rollback (ex: 90) : ")).strip()
                    if custom_days.isdigit() and int(custom_days) > 0:
                        days_interval = int(custom_days)
                    else:
                        days_interval = 180
                        ctx.console.print(_error("Valeur invalide. Période par défaut (180 jours) appliquée."))
                else:
                    days_interval = 180

            ctx.console.print()
            ctx.console.print(_title("MODE D'APPLICATION DE L'AUTOMATISATION"))
            ctx.console.print(_info("  [1] ✚ Incrémentation (Fusionner les nouvelles données)"))
            ctx.console.print(_info("  [2] 🕱 Écraser (Remplacement complet de la cible)"))
            mode_sub = ctx.console.input(_info("\nChoix du mode [1] : ")).strip().lower()

            selected_mode = "append" if mode_sub != "2" else "overwrite"
            mode_label = "Fusion incrémentale" if selected_mode == "append" else "Écrasement complet"

            strategy_map = {
                "1": ("Restauration manuelle ciblée", "Restaure uniquement l'archive spécifiée depuis var/backups/"),
                "2": ("Dernier état sain", "Recherche et restaure automatiquement la dernière archive valide de la cible"),
                "3": (f"Rollback périodique ({days_interval} jours)", f"Réinitialisation automatique programmée tous les {days_interval} jours"),
            }

            strat_title, strat_desc = strategy_map.get(opt_choice, strategy_map["1"])

            SCHEDULED_RESTORES.append({
                "strategy_id": opt_choice,
                "strategy_title": strat_title,
                "strategy_desc": strat_desc,
                "days_interval": days_interval,
                "mode": selected_mode,
                "mode_label": mode_label,
                "created_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            })

            RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
            with open(restore_auto_file, "w", encoding="utf-8") as f:
                json.dump(SCHEDULED_RESTORES, f, indent=2, ensure_ascii=False)

            table = Table(
                title="Nouvelle Règle d'Automatisation",
                show_header=True,
                header_style=theme_registry.get_style("text.heading"),
                border_style=theme_registry.get_style("border.default"),
                box=box.ROUNDED,
            )
            table.add_column("Paramètre", style=theme_registry.get_style("text.info"), width=24)
            table.add_column("Valeur", style=theme_registry.get_style("text.main"))

            table.add_row("Stratégie Choisie", strat_title)
            table.add_row("Description", strat_desc)
            table.add_row("Mode de Restauration", mode_label)
            table.add_row("Dossier Source Backup", str(BACKUPS_DIR))
            table.add_row("Statut de la Règle", _success("CONFIGURÉE ET ENREGISTRÉE"))

            ctx.console.print()
            ctx.console.print(table)
            ctx.console.print(_success(f"Automatisation enregistrée avec succès ({strat_title} — {mode_label})."))

    _execute_action_flow(ctx, "5.5 Restaurer Backup", logic)

def action_5_6_purge_backups(ctx: ActionContext) -> None:
    """5.6 — Purge et nettoyage des backups."""
    import shutil
    import json
    from pathlib import Path
    from datetime import datetime, timedelta
    from rich import box
    from rich.table import Table

    def logic(out: List[Any]):
        purge_auto_file = RUNTIME_DIR / "scheduled_purges.json"
        backup_dir = BACKUPS_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Helper d'analyse du dossier var/backups/
        all_backups = sorted(
            [f for f in backup_dir.glob("*.tar.gz") if f.is_file()],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        total_files = len(all_backups)
        total_size_bytes = sum(f.stat().st_size for f in all_backups) if all_backups else 0
        total_size_mb = total_size_bytes / (1024 * 1024)

        # Calcul de l'espace disque disponible sur la partition
        disk_usage = shutil.disk_usage(backup_dir)
        free_space_gb = disk_usage.free / (1024 * 1024 * 1024)

        # Détermination des dates du plus récent et du plus ancien
        oldest_str = "-"
        newest_str = "-"
        if all_backups:
            newest_mtime = datetime.fromtimestamp(all_backups[0].stat().st_mtime)
            oldest_mtime = datetime.fromtimestamp(all_backups[-1].stat().st_mtime)
            newest_str = newest_mtime.strftime("%d/%m/%Y %H:%M:%S")
            oldest_str = oldest_mtime.strftime("%d/%m/%Y %H:%M:%S")

        # --- 1. TABLEAU DE STATISTIQUES GLOBAL ---
        ctx.console.print(_title("5.6 PURGE ET NETTOYAGE DES BACKUPS"))
        ctx.console.print()

        stats_table = Table(
            title="Statistiques de Stockage des Backups ('var/backups/')",
            show_header=True,
            header_style=theme_registry.get_style("text.heading"),
            border_style=theme_registry.get_style("border.default"),
            box=box.ROUNDED,
        )
        stats_table.add_column("Indicateur", style=theme_registry.get_style("text.info"), width=28)
        stats_table.add_column("Valeur / État", style=theme_registry.get_style("text.main"))

        stats_table.add_row("Nombre total d'archives", str(total_files))
        stats_table.add_row("Volume total occupé", f"{total_size_mb:.2f} MB ({total_size_bytes / 1024:.1f} KB)")
        stats_table.add_row("Espace libre disque", f"{free_space_gb:.2f} GB")
        stats_table.add_row("Plus ancienne sauvegarde", oldest_str)
        stats_table.add_row("Plus récente sauvegarde", newest_str)

        ctx.console.print(stats_table)
        ctx.console.print()

        # --- 2. MENU D'ACTION DE PURGE ---
        ctx.console.print(_info("  [1] ⏳ Purger par ancienneté (ex: > 30, 90, 180, 365 jours)"))
        ctx.console.print(_info("  [2] ⏱ Purger par quota (Conserver uniquement les N plus récentes)"))
        ctx.console.print(_info("  [3] 🛡️ Purger uniquement les backups automatiques de sécurité ('safety_auto_*')"))
        ctx.console.print(_info("  [4] →  Sélection manuelle ciblée des fichiers à supprimer"))
        ctx.console.print(_info("  [5] ⚙️ Voir / Gérer les règles de purge automatique"))
        ctx.console.print(_muted("  [0/q] ❌ Annuler"))

        main_choice = ctx.console.input(_info("\nChoix du mode de nettoyage [1] : ")).strip().lower()

        if main_choice in ("0", "q"):
            ctx.console.print(_warning("Opération de nettoyage annulée."))
            return

        files_to_delete: list[Path] = []
        action_title = ""

        # --- SEGMENT 1 : PURGE PAR ANCIENNETÉ ---
        if main_choice == "1":
            ctx.console.print()
            ctx.console.print(_title("PURGE PAR ANCIENNETÉ"))
            ctx.console.print(_info("  [1] Plus de 30 jours"))
            ctx.console.print(_info("  [2] Plus de 90 jours"))
            ctx.console.print(_info("  [3] Plus de 180 jours"))
            ctx.console.print(_info("  [4] Plus de 365 jours"))
            ctx.console.print(_info("  [5] Saisir un nombre de jours sur mesure"))
            ctx.console.print(_muted("  [0/q] ❌ Annuler"))

            sub_choice = ctx.console.input(_info("\nChoix de l'âge limite [1] : ")).strip().lower()

            if sub_choice in ("0", "q"):
                ctx.console.print(_warning("Annulé."))
                return

            days_map = {"1": 30, "2": 90, "3": 180, "4": 365}
            if sub_choice in days_map:
                target_days = days_map[sub_choice]
            elif sub_choice == "5":
                custom_days = ctx.console.input(_info("Saisir le nombre de jours limite (ex: 45) : ")).strip()
                if custom_days.isdigit() and int(custom_days) > 0:
                    target_days = int(custom_days)
                else:
                    ctx.console.print(_error("Nombre de jours invalide. Annulation."))
                    return
            else:
                target_days = 30

            cutoff_date = datetime.now() - timedelta(days=target_days)
            files_to_delete = [f for f in all_backups if datetime.fromtimestamp(f.stat().st_mtime) < cutoff_date]
            action_title = f"Purge des archives de plus de {target_days} jours"

        # --- SEGMENT 2 : PURGE PAR QUOTA DE CONSERVATION ---
        elif main_choice == "2":
            ctx.console.print()
            ctx.console.print(_title("PURGE PAR QUOTA DE CONSERVATION"))
            ctx.console.print(_info("  [1] Conserver les 5 plus récentes (supprimer le reste)"))
            ctx.console.print(_info("  [2] Conserver les 10 plus récentes"))
            ctx.console.print(_info("  [3] Conserver les 20 plus récentes"))
            ctx.console.print(_info("  [4] Saisir le nombre sur mesure à conserver"))
            ctx.console.print(_muted("  [0/q] ❌ Annuler"))

            sub_choice = ctx.console.input(_info("\nChoix de la limite [1] : ")).strip().lower()

            if sub_choice in ("0", "q"):
                ctx.console.print(_warning("Annulé."))
                return

            keep_map = {"1": 5, "2": 10, "3": 20}
            if sub_choice in keep_map:
                keep_count = keep_map[sub_choice]
            elif sub_choice == "4":
                custom_keep = ctx.console.input(_info("Nombre d'archives récentes à conserver (ex: 15) : ")).strip()
                if custom_keep.isdigit() and int(custom_keep) >= 0:
                    keep_count = int(custom_keep)
                else:
                    ctx.console.print(_error("Valeur invalide. Annulation."))
                    return
            else:
                keep_count = 5

            if len(all_backups) > keep_count:
                files_to_delete = all_backups[keep_count:]
            action_title = f"Purge par quota (Conservation des {keep_count} plus récentes)"

        # --- SEGMENT 3 : PURGE DES BACKUPS DE SÉCURITÉ AUTOMATIQUES ---
        elif main_choice == "3":
            files_to_delete = [f for f in all_backups if f.name.startswith("safety_auto_")]
            action_title = "Purge des backups temporaires de sécurité ('safety_auto_*')"

        # --- SEGMENT 4 : SÉLECTION MANUELLE CIBLÉE ---
        elif main_choice == "4":
            if not all_backups:
                ctx.console.print(_warning("Aucun fichier disponible pour la suppression."))
                return

            page_size = 20
            current_page = 0
            total_items = len(all_backups)

            while True:
                start_idx = current_page * page_size
                end_idx = min(start_idx + page_size, total_items)
                page_files = all_backups[start_idx:end_idx]

                ctx.console.print(_muted(f"\nFichiers disponibles (Page {current_page + 1}/{(total_items - 1) // page_size + 1}) :"))

                for i, bfile in enumerate(page_files, start=start_idx + 1):
                    mtime = datetime.fromtimestamp(bfile.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")
                    size_kb = bfile.stat().st_size / 1024
                    ctx.console.print(_info(f"  [{i}] 📦 {bfile.name} ({mtime} — {size_kb:.1f} KB)"))

                ctx.console.print()
                if end_idx < total_items:
                    ctx.console.print(_info("  [n] ➡️ Page suivante"))
                if current_page > 0:
                    ctx.console.print(_info("  [p] ⬅️ Page précédente"))
                ctx.console.print(_muted("  [0/q] ❌ Annuler"))

                man_choice = ctx.console.input(_info(f"\nSélectionnez le fichier à supprimer (1-{total_items}) : ")).strip().lower()

                if man_choice in ("0", "q"):
                    ctx.console.print(_warning("Annulé."))
                    return
                elif man_choice == "n" and end_idx < total_items:
                    current_page += 1
                elif man_choice == "p" and current_page > 0:
                    current_page -= 1
                elif man_choice.isdigit() and 1 <= int(man_choice) <= total_items:
                    files_to_delete = [all_backups[int(man_choice) - 1]]
                    action_title = f"Suppression manuelle ciblée de '{files_to_delete[0].name}'"
                    break
                else:
                    ctx.console.print(_error("Choix invalide."))

        # --- SEGMENT 5 : GESTION DES RÈGLES DE PURGE AUTOMATIQUE ---
        elif main_choice == "5":
            ctx.console.print()
            ctx.console.print(_title("RÈGLES DE PURGE AUTOMATIQUE"))

            if not SCHEDULED_PURGES:
                ctx.console.print(_info("Aucune règle de purge automatique enregistrée."))
            else:
                p_table = Table(
                    title="Règles de Purge Actives",
                    show_header=True,
                    header_style=theme_registry.get_style("text.heading"),
                    border_style=theme_registry.get_style("border.default"),
                    box=box.ROUNDED,
                )
                p_table.add_column("#", style=theme_registry.get_style("text.info"), width=4)
                p_table.add_column("Type de Purge", style=theme_registry.get_style("text.info"))
                p_table.add_column("Valeur Cible", style=theme_registry.get_style("text.main"))
                p_table.add_column("Créée le", style=theme_registry.get_style("text.muted"))

                for idx, p_rule in enumerate(SCHEDULED_PURGES, start=1):
                    p_table.add_row(str(idx), p_rule["type"], p_rule["value"], p_rule["created_at"])

                ctx.console.print(p_table)
                ctx.console.print()

                cancel_p = ctx.console.input(_info("Désactiver / Supprimer une règle de purge ? (o/N) : ")).strip().lower()
                if cancel_p in ("o", "oui", "y", "yes"):
                    del_p = ctx.console.input(_info(f"Numéro de la règle à supprimer (1-{len(SCHEDULED_PURGES)}) : ")).strip()
                    if del_p.isdigit() and 1 <= int(del_p) <= len(SCHEDULED_PURGES):
                        removed_p = SCHEDULED_PURGES.pop(int(del_p) - 1)
                        with open(purge_auto_file, "w", encoding="utf-8") as f:
                            json.dump(SCHEDULED_PURGES, f, indent=2, ensure_ascii=False)
                        ctx.console.print(_success(f"Règle de purge '{removed_p['type']}' supprimée."))
                    else:
                        ctx.console.print(_error("Choix invalide."))
            return

        # --- 3. RECAPITULATIF ET CONFIRMATION D'EXÉCUTION ---
        if not files_to_delete:
            ctx.console.print()
            ctx.console.print(_warning("Aucun fichier ne correspond aux critères de suppression choisis."))
            return

        recap_size_bytes = sum(f.stat().st_size for f in files_to_delete)
        recap_size_mb = recap_size_bytes / (1024 * 1024)

        ctx.console.print()
        recap_table = Table(
            title="Récapitulatif de la Purge - Validation Requise",
            show_header=True,
            header_style=theme_registry.get_style("text.heading"),
            border_style=theme_registry.get_style("border.default"),
            box=box.ROUNDED,
        )
        recap_table.add_column("Propriété", style=theme_registry.get_style("text.info"), width=28)
        recap_table.add_column("Détail", style=theme_registry.get_style("text.main"))

        recap_table.add_row("Opération", action_title)
        recap_table.add_row("Nombre de fichiers ciblés", str(len(files_to_delete)))
        recap_table.add_row("Espace qui sera libéré", f"{recap_size_mb:.2f} MB ({recap_size_bytes / 1024:.1f} KB)")

        ctx.console.print(recap_table)
        ctx.console.print()
        ctx.console.print(_muted("Liste des fichiers ciblés :"))
        for fdel in files_to_delete[:10]:
            ctx.console.print(_info(f"  • {fdel.name}"))
        if len(files_to_delete) > 10:
            ctx.console.print(_muted(f"  ... et {len(files_to_delete) - 10} autre(s) fichier(s)."))

        ctx.console.print()
        confirm = ctx.console.input(_info(f"Confirmer la suppression DÉFINITIVE de {len(files_to_delete)} fichier(s) ? (o/N) : ")).strip().lower()

        if confirm not in ("o", "oui", "y", "yes"):
            ctx.console.print(_warning("Suppression annulée. Aucun fichier n'a été supprimé."))
            return

        # --- 4. EXÉCUTION DE LA SUPPRESSION ---
        persistence_port = ctx.container.get_persistence_port()
        all_backup_infos = persistence_port.list_backups(backup_dir)
        backups_by_path = {b.path: b for b in all_backup_infos}

        backups_to_delete = [
            backups_by_path[f] for f in files_to_delete if f in backups_by_path
        ]

        command = PurgeBackupsCommand(persistence_port=persistence_port)
        purge_result = command.execute(backups_to_delete)

        ctx.console.print()
        if purge_result.deleted_count > 0:
            ctx.console.print(_success(f"Purge terminée avec succès ! {purge_result.deleted_count} fichier(s) supprimé(s), {recap_size_mb:.2f} MB libérés."))
        if purge_result.error_count > 0:
            for err in purge_result.errors:
                ctx.console.print(_error(f"Erreur lors de la suppression de {err}"))
            ctx.console.print(_error(f"{purge_result.error_count} erreur(s) rencontrée(s) pendant la suppression."))

    _execute_action_flow(ctx, "5.6 Purge Backups", logic)

def action_5_7_advanced_cleanup(ctx: ActionContext) -> None:
    """5.7 — Nettoyage avancé (Par âge ou taille)."""
    import shutil
    from pathlib import Path
    from datetime import datetime, timedelta
    from rich import box
    from rich.table import Table

    def logic(out: List[Any]):
        ctx.console.print(_title("5.7 NETTOYAGE AVANCÉ DES FICHIERS"))
        ctx.console.print()

        # --- 1. SÉLECTION DU/DES DOSSIERS CIBLES ---
        ctx.console.print(_info("1. SÉLECTION DU DOSSIER CIBLE"))
        ctx.console.print(_info("  [1] ◉ Tous les logs ('var/logs/')"))
        ctx.console.print(_info("  [2] ◔ Cache temporaire ('var/cache/')"))
        ctx.console.print(_info("  [3] ◕ Fichiers d'exports ('var/exports/')"))
        ctx.console.print(_info("  [4] ◓ Archives de backups ('var/backups/')"))
        ctx.console.print(_info("  [5] 🗂️  Tout l'environnement runtime ('var/')"))
        ctx.console.print(_muted("  [0/q] ❌ Annuler"))

        target_choice = ctx.console.input(_info("\nChoix de la cible [1] : ")).strip().lower()

        if target_choice in ("0", "q"):
            ctx.console.print(_warning("Nettoyage annulé."))
            return

        target_map = {
            "1": [LOGS_DIR],
            "2": [CACHE_DIR],
            "3": [EXPORTS_DIR],
            "4": [BACKUPS_DIR],
            "5": [LOGS_DIR, CACHE_DIR, EXPORTS_DIR, BACKUPS_DIR],
        }

        selected_dirs = target_map.get(target_choice, [LOGS_DIR])

        # S'assurer de l'existence des dossiers
        for d in selected_dirs:
            d.mkdir(parents=True, exist_ok=True)

        if LOGS_DIR in selected_dirs:
            ctx.console.print(_muted(
                "ℹ️  app.log et audit.log sont exclus de ce nettoyage (fichiers actifs) — "
                "utilisez les menus 1.5 / 7.3 pour les gérer."
            ))

        # Collecte initiale de tous les fichiers — exclusion explicite des
        # fichiers de logs ACTIFS (app.log, audit.log), en écriture
        # continue par leurs FileHandler Python tant que l'application
        # tourne. Les supprimer pendant l'exécution ne libère l'espace
        # disque qu'à la fermeture du handle (inode supprimé mais
        # toujours référencé) — les prochaines entrées journalisées
        # disparaissent silencieusement jusqu'au redémarrage, sans
        # aucune indication de perte de données pour l'utilisateur.
        from omega_fire.infrastructure.config.paths import APP_LOG_PATH, AUDIT_LOG_PATH
        protected_log_files = {APP_LOG_PATH.resolve(), AUDIT_LOG_PATH.resolve()}

        all_candidate_files: list[Path] = []
        for d in selected_dirs:
            for f in d.rglob("*"):
                if f.is_file() and f.resolve() not in protected_log_files:
                    all_candidate_files.append(f)

        if not all_candidate_files:
            ctx.console.print(_warning("Aucun fichier trouvé dans les emplacements sélectionnés."))
            return

        # --- 2. CHOIX DES CRITÈRES DE FILTRAGE (SÉLECTION MULTIPLE) ---
        ctx.console.print()
        ctx.console.print(_title("2. CRITÈRES DE FILTRAGE MULTIPLES"))
        ctx.console.print(_info("  [1] ◴ Filtrer par âge (fichiers plus anciens que X jours)"))
        ctx.console.print(_info("  [2] ◷ Filtrer par taille minimale (fichiers plus grands que X MB)"))
        ctx.console.print(_info("  [3] ◵ Filtrer par extension (ex: .log, .tmp, .gz, .json)"))
        ctx.console.print(_info("  [4] ◶ Combiner Âge + Taille (ex: > 30 jours ET > 10 MB)"))
        ctx.console.print(_muted("  [0/q] ❌ Annuler"))

        crit_choice = ctx.console.input(_info("\nChoix de la stratégie de filtre [1] : ")).strip().lower()

        if crit_choice in ("0", "q"):
            ctx.console.print(_warning("Nettoyage annulé."))
            return

        min_age_days: int | None = None
        min_size_mb: float | None = None
        target_extension: str | None = None

        # Saisie pour l'âge
        if crit_choice in ("1", "4"):
            age_input = ctx.console.input(_info("Âge minimum des fichiers en jours (ex: 30) [30] : ")).strip()
            if age_input.lower() in ("0", "q"):
                ctx.console.print(_warning("Annulé."))
                return
            min_age_days = int(age_input) if age_input.isdigit() else 30

        # Saisie pour la taille
        if crit_choice in ("2", "4"):
            size_input = ctx.console.input(_info("Taille minimale en MB (ex: 5.0) [5.0] : ")).strip()
            if size_input.lower() in ("0", "q"):
                ctx.console.print(_warning("Annulé."))
                return
            try:
                min_size_mb = float(size_input) if size_input else 5.0
            except ValueError:
                min_size_mb = 5.0

        # Saisie pour l'extension
        if crit_choice == "3":
            ext_input = ctx.console.input(_info("Extension recherchée (ex: log, tmp, gz, json) [log] : ")).strip().lower()
            if ext_input in ("0", "q"):
                ctx.console.print(_warning("Annulé."))
                return
            target_extension = ext_input.replace(".", "") if ext_input else "log"

        # --- 3. APPLICATION DES FILTRES ---
        now = datetime.now()
        matching_files: list[Path] = []

        for ffile in all_candidate_files:
            try:
                stat = ffile.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                size_mb = stat.st_size / (1024 * 1024)

                # Verification âge
                if min_age_days is not None:
                    if now - mtime < timedelta(days=min_age_days):
                        continue

                # Verification taille
                if min_size_mb is not None:
                    if size_mb < min_size_mb:
                        continue

                # Verification extension
                if target_extension is not None:
                    if not ffile.name.lower().endswith(f".{target_extension}"):
                        continue

                matching_files.append(ffile)
            except Exception:
                continue

        if not matching_files:
            ctx.console.print()
            ctx.console.print(_warning("Aucun fichier ne correspond exactement à vos critères de filtrage."))
            return

        # --- 4. RÉCAPITULATIF ET CONFIRMATION ---
        total_size_bytes = sum(f.stat().st_size for f in matching_files)
        total_size_mb = total_size_bytes / (1024 * 1024)

        ctx.console.print()
        recap_table = Table(
            title="Récapitulatif du Nettoyage Avancé",
            show_header=True,
            header_style=theme_registry.get_style("text.heading"),
            border_style=theme_registry.get_style("border.default"),
            box=box.ROUNDED,
        )
        recap_table.add_column("Critères / Propriétés", style=theme_registry.get_style("text.info"), width=28)
        recap_table.add_column("Valeur retenue", style=theme_registry.get_style("text.main"))

        if min_age_days is not None:
            recap_table.add_row("Filtre Âge Minimum", f"> {min_age_days} jours")
        if min_size_mb is not None:
            recap_table.add_row("Filtre Taille Minimale", f"> {min_size_mb:.2f} MB")
        if target_extension is not None:
            recap_table.add_row("Filtre Extension", f".{target_extension}")

        recap_table.add_row("Nombre de fichiers ciblés", str(len(matching_files)))
        recap_table.add_row("Volume total à libérer", f"{total_size_mb:.2f} MB ({total_size_bytes / 1024:.1f} KB)")

        ctx.console.print(recap_table)
        ctx.console.print()

        ctx.console.print(_muted("Aperçu des premiers fichiers ciblés :"))
        for mf in matching_files[:8]:
            mtime_str = datetime.fromtimestamp(mf.stat().st_mtime).strftime("%d/%m/%Y")
            size_kb = mf.stat().st_size / 1024
            ctx.console.print(_info(f"  • {mf.relative_to(_PROJECT_ROOT)} ({size_kb:.1f} KB — {mtime_str})"))

        if len(matching_files) > 8:
            ctx.console.print(_muted(f"  ... et {len(matching_files) - 8} autre(s) fichier(s)."))

        ctx.console.print()
        confirm = ctx.console.input(_info(f"Confirmer le nettoyage DÉFINITIF de ces {len(matching_files)} fichier(s) ? (o/N) : ")).strip().lower()

        if confirm not in ("o", "oui", "y", "yes"):
            ctx.console.print(_warning("Opération de nettoyage annulée. Aucun fichier supprimé."))
            return

        # --- 5. EXÉCUTION DE LA SUPPRESSION ---
        deleted_count = 0
        error_count = 0

        for target_f in matching_files:
            try:
                target_f.unlink()
                deleted_count += 1
            except Exception as e:
                error_count += 1
                ctx.console.print(_error(f"Erreur lors de la suppression de '{target_f.name}' : {e}"))

        ctx.console.print()
        if deleted_count > 0:
            ctx.console.print(_success(f"Nettoyage avancé terminé ! {deleted_count} fichier(s) supprimé(s), {total_size_mb:.2f} MB libérés."))
        if error_count > 0:
            ctx.console.print(_error(f"{error_count} erreur(s) survenue(s) lors de la suppression."))

    _execute_action_flow(ctx, "5.7 Nettoyage Avancé", logic)

def action_5_8_log_stats(ctx: ActionContext) -> None:
    """Action déclenchée par le Menu 5.8 — Statistiques des logs."""
    show_log_stats_dashboard(ctx.console)
# ----------------------------------------------------------------------
# Menu 6 — Exports & rapports
# ----------------------------------------------------------------------
def action_6_1_export_blacklist(ctx: ActionContext) -> None:
    """6.1 — Exporter la blacklist complète (JSON, TXT, HTML)."""
    def logic(out: List[Any]):
        import os
        import json
        from datetime import datetime
        from rich import box
        from rich.table import Table
        from omega_fire.interfaces.cli.themes.registry import theme_registry

        prompt_mgr = PromptManager(ctx.console)

        ctx.console.print(_title("Exportation de la blacklist complète"))
        ctx.console.print()

        # -------------------------------------------------------------------------
        # ÉTAPE 1 : SELECTION DU FICHIER SOURCE (IPs)
        # -------------------------------------------------------------------------
        ctx.console.print(_muted("🖈 Epinglés :"))
        # Épingles persistées, même mécanisme que 5.2 (voir son commentaire) —
        # bug réel corrigé le 2026-09-04.
        from omega_fire.infrastructure.storage.files.json_store import JsonStore
        from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand

        pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )
        pinned_sources = pinned_command.list_paths()

        if pinned_sources:
            for idx, source in enumerate(pinned_sources, start=1):
                status = "" if os.path.exists(source) else " (non trouvé)"
                ctx.console.print(_info(f"  [{idx}]  {os.path.basename(source)}{status}"))
                ctx.console.print(_muted(f"      {source}"))
        else:
            ctx.console.print(_muted("  (Aucune épingle enregistrée)"))

        ctx.console.print()
        ctx.console.print(_info("  [m] 🖉 Saisir un chemin manuel"))
        ctx.console.print(_info("  [a] 🖈 Ajouter une nouvelle épingle"))
        if pinned_sources:
            ctx.console.print(_info("  [s] 🗑️ Supprimer une épingle"))
        ctx.console.print(_muted("  [0/q] ❌ Annuler"))

        try:
            choice = prompt_mgr.ask_text(_info("\nChoix de la source [1] : "), allow_cancel=True).strip().lower()
        except PromptCancelled:
            ctx.console.print(_warning("Opération annulée."))
            return

        if choice == "m":
            try:
                user_path = prompt_mgr.ask_text(_info("Chemin complet du fichier source : "), allow_cancel=True).strip()
            except PromptCancelled:
                ctx.console.print(_warning("Opération annulée."))
                return
            if not user_path:
                ctx.console.print(_warning("Opération annulée."))
                return
            if not os.path.isfile(user_path):
                ctx.console.print(_error(f"Fichier introuvable : {user_path}"))
                return
            selected_source = user_path

        elif choice == "a":
            new_pin = ctx.console.input(_info("Chemin complet du fichier à épingler (ou 'annuler') : ")).strip()
            if new_pin and not is_cancel_word(new_pin) and os.path.isfile(new_pin):
                add_result = pinned_command.add_path(new_pin)
                selected_source = new_pin
                if add_result.success:
                    ctx.console.print(_success(add_result.message))
                else:
                    ctx.console.print(_error(add_result.message))
            else:
                ctx.console.print(_error("Fichier introuvable ou invalide."))
                return

        elif choice == "s":
            if not pinned_sources:
                ctx.console.print(_error("Aucune épingle à supprimer."))
                return
            del_choice = ctx.console.input(_info(f"Numéro de l'épingle à supprimer (1-{len(pinned_sources)}) : ")).strip()
            if del_choice.isdigit() and 1 <= int(del_choice) <= len(pinned_sources):
                remove_result = pinned_command.remove_path(pinned_sources[int(del_choice) - 1])
                if remove_result.success:
                    ctx.console.print(_success(remove_result.message))
                else:
                    ctx.console.print(_error(remove_result.message))
            else:
                ctx.console.print(_error("Choix invalide."))
            return

        elif choice.isdigit() and 1 <= int(choice) <= len(pinned_sources):
            selected_source = pinned_sources[int(choice) - 1]
        else:
            selected_source = pinned_sources[0] if pinned_sources else str(DEFAULT_BLOCKLIST_FILE)

        if not os.path.isfile(selected_source):
            ctx.console.print(_error(f"Fichier introuvable : {selected_source}"))
            return

        # -------------------------------------------------------------------------
        # ÉTAPE 2 : LECTURE DU FICHIER SOURCE
        # -------------------------------------------------------------------------
        try:
            with open(selected_source, "r", encoding="utf-8") as f:
                ips_list = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except Exception as e:
            ctx.console.print(_error(f"Impossible de lire le fichier source : {e}"))
            return

        if not ips_list:
            ctx.console.print(_warning(f"Le fichier '{selected_source}' ne contient aucune IP valide à exporter."))
            return

        # -------------------------------------------------------------------------
        # ÉTAPE 3 : CHOIX DU FORMAT DE SORTIE
        # -------------------------------------------------------------------------
        ctx.console.print()
        ctx.console.print(_title("Format d'exportation"))
        ctx.console.print(_info("  [1] JSON (Brut structuré)"))
        ctx.console.print(_info("  [2] TXT  (Format texte brut - 1 IP par ligne, réinjectable)"))
        ctx.console.print(_info("  [3] HTML (Rapport visuel stylisé sur 3 colonnes)"))
        ctx.console.print()

        try:
            fmt_choice = prompt_mgr.ask_text(_info("Choix du format [1] : "), allow_cancel=True).strip() or "1"
        except PromptCancelled:
            ctx.console.print(_muted("Opération annulée."))
            return

        ext_map = {"1": "json", "2": "txt", "3": "html"}
        file_ext = ext_map.get(fmt_choice, "json")

        # -------------------------------------------------------------------------
        # ÉTAPE 4 : DÉFINITION DU CHEMIN DE DESTINATION
        # -------------------------------------------------------------------------
        target_dir = EXPORTS_DIR if file_ext == "html" else BLOCKLIST_DIR
        default_filename = f"export-blacklist.{file_ext}"
        default_filepath = str(target_dir / default_filename)

        ctx.console.print()
        ctx.console.print(_info(f"Chemin de sortie par défaut : {default_filepath}"))
        try:
            custom_path = prompt_mgr.ask_text(
                _info("Appuyez sur [Entrée] pour valider ou saisissez un chemin personnalisé (ou 'annuler') : "),
                allow_cancel=True,
            ).strip()
        except PromptCancelled:
            ctx.console.print(_muted("Opération annulée."))
            return

        final_path = custom_path if custom_path else default_filepath

        # Gestion des dossiers inexistants
        try:
            dest_folder = os.path.dirname(final_path)
            if dest_folder and not os.path.exists(dest_folder):
                os.makedirs(dest_folder, exist_ok=True)
        except Exception as e:
            ctx.console.print(_error(f"Impossible de créer le dossier de destination : {e}"))
            return

        # Gestion des conflits de fichiers existants
        if os.path.exists(final_path):
            ctx.console.print()
            ctx.console.print(_warning(f"Le fichier existe déjà : {final_path}"))
            ctx.console.print(_info("  [1] Renommer automatiquement (avec horodatage)"))
            ctx.console.print(_info("  [2] Écraser le fichier existant"))
            ctx.console.print(_muted("  [0/q] Annuler"))

            try:
                conflict_choice = prompt_mgr.ask_text(_info("\nChoix [1] : "), allow_cancel=True).strip().lower()
            except PromptCancelled:
                ctx.console.print(_muted("Exportation annulée."))
                return

            if conflict_choice == "1" or not conflict_choice:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_dir = os.path.dirname(final_path)
                file_name = os.path.basename(final_path)
                name, ext = os.path.splitext(file_name)
                final_path = os.path.join(base_dir, f"{name}_{timestamp}{ext}")

        # -------------------------------------------------------------------------
        # ÉTAPE 5 : GÉNÉRATION DU FICHIER SELON LE FORMAT
        # -------------------------------------------------------------------------
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Le choix de thème HTML est un prompt interactif — il doit se faire
        # avant l'animation du spinner, pas pendant (même principe que 6.4).
        theme_name = "omega-base"
        if file_ext == "html":
            try:
                theme_name = _prompt_html_theme(ctx, allow_cancel=True)
            except PromptCancelled:
                ctx.console.print(_muted("Opération annulée."))
                return

        try:
            with gauge_status(ctx.console, f"Génération de l'export [{file_ext.upper()}]..."):
                # 1. FORMAT JSON
                if file_ext == "json":
                    export_data = {
                        "source": "Omega-Fire",
                        "type": "Blacklist Export",
                        "source_file": selected_source,
                        "exported_at": now_str,
                        "total_ips": len(ips_list),
                        "ips": ips_list
                    }
                    with open(final_path, "w", encoding="utf-8") as f:
                        json.dump(export_data, f, indent=4, ensure_ascii=False)

                # 2. FORMAT TXT
                elif file_ext == "txt":
                    lines = [f"# Omega-Fire Blacklist Export", f"# Source : {selected_source}", f"# Généré le : {now_str}", f"# Total IPs : {len(ips_list)}", ""]
                    lines.extend(ips_list)
                    with open(final_path, "w", encoding="utf-8") as f:
                        f.write("\n".join(lines) + "\n")

                # 3. FORMAT HTML STYLISÉ (Rapport sur 3 colonnes)
                elif file_ext == "html":
                    if not ctx.container:
                        ctx.console.print(_error("Conteneur non disponible — export HTML impossible."))
                        return

                    col_size = (len(ips_list) + 2) // 3
                    col1 = ips_list[0:col_size]
                    col2 = ips_list[col_size:col_size*2]
                    col3 = ips_list[col_size*2:]
                    max_rows = max(len(col1), len(col2), len(col3))
                    ip_rows = [
                        (
                            col1[r] if r < len(col1) else "",
                            col2[r] if r < len(col2) else "",
                            col3[r] if r < len(col3) else "",
                        )
                        for r in range(max_rows)
                    ]

                    exporter = ctx.container.get_exporter_port("html")
                    exporter.export_data(
                        {
                            "page_title": "Exportation Blacklist - Omega-Fire",
                            "heading": "Rapport d'exportation Blacklist",
                            "source_label": "Source",
                            "source_value": "Blacklist Globale",
                            "generated_at": now_str,
                            "total_ips": len(ips_list),
                            "ip_rows": ip_rows,
                            "theme_name": theme_name,
                        },
                        final_path,
                        template_name="ip_export.html.j2",
                    )

            ctx.console.print()
            ctx.console.print(_success(f"✔ Exportation réussie : {len(ips_list)} IP(s) enregistrée(s) dans '{final_path}'."))

        except Exception as e:
            ctx.console.print(_error(f"Erreur lors de l'écriture du fichier d'export : {e}"))

    _execute_action_flow(ctx, "6.1 Exporter la blacklist", logic)

def action_6_2_export_rules(ctx: ActionContext) -> None:
    """6.2 — Exporter les règles (nftables / iptables)."""

    def logic(out: List[Any]):
        from datetime import datetime
        from omega_fire.application.queries.export_rules_summary import (
            ExportRulesSummaryQuery,
            ExportRulesSummaryRequest,
        )
        from omega_fire.infrastructure.config.paths import EXPORTS_DIR

        if not hasattr(ctx, "container") or not ctx.container or not hasattr(ctx.container, "rule_repository"):
            ctx.console.print(_error("Le conteneur ou le dépôt de règles n'est pas disponible."))
            return

        def print_choice(num: str, label: str) -> None:
            style_num = theme_registry.get_style("text.muted")
            style_label = theme_registry.get_style("text.main")
            t = Text()
            t.append("  [", style=style_num)
            t.append(num, style=style_num)
            t.append("] ", style=style_num)
            t.append(label, style=style_label)
            ctx.console.print(t)

        # ─── ÉTAPE 1 : Choix du contenu (périmètre nftables / iptables uniquement) ───
        ctx.console.print(_info("Contenu à exporter (fail2ban dispose de son propre export, menu 4.8) :"))
        print_choice("1", "Toutes les règles")
        print_choice("2", "Règles actives uniquement")
        print_choice("3", "Règles Omega-Fire uniquement (créées via 3.1)")
        print_choice("4", "Règles Système importées uniquement (détectées via 3.3)")
        print_choice("0", "Annuler")

        content_choice = ctx.console.input(_info("\nChoix [1-4] (Défaut: 1), ou '0' pour annuler : ")).strip() or "1"
        if is_cancel_word(content_choice):
            ctx.console.print(_muted("Export annulé."))
            return

        content_map = {
            "1": (ExportRulesSummaryRequest(origin_filter="all", active_only=False), "Toutes les règles"),
            "2": (ExportRulesSummaryRequest(origin_filter="all", active_only=True), "Règles actives uniquement"),
            "3": (ExportRulesSummaryRequest(origin_filter="managed", active_only=False), "Règles Omega-Fire uniquement"),
            "4": (ExportRulesSummaryRequest(origin_filter="imported", active_only=False), "Règles Système importées uniquement"),
        }
        request, filter_label = content_map.get(content_choice, content_map["1"])

        # ─── ÉTAPE 2 : Récupération et regroupement ───
        result = ExportRulesSummaryQuery(ctx.container.rule_repository).execute(request)
        if not result.success:
            ctx.console.print(_error(result.message))
            return
        if not result.full_list:
            ctx.console.print(_warning(result.message))
            return

        ctx.console.print(_info(f"\n{result.message}"))
        ctx.console.print()

        # ─── ÉTAPE 3 : Sélection du format d'exportation ───
        ctx.console.print(_info("Sélectionnez le format d'exportation :"))
        print_choice("1", "JSON  — données brutes structurées")
        print_choice("2", "HTML  — rapport visuel lisible [défaut]")
        print_choice("3", "TXT   — rapport texte brut")
        print_choice("0", "Annuler")

        format_choice = ctx.console.input(_info("\nVotre choix (1-3, défaut: 2), ou '0' pour annuler : ")).strip() or "2"
        if is_cancel_word(format_choice):
            ctx.console.print(_muted("Export annulé."))
            return
        format_key = {"1": "json", "2": "html", "3": "txt"}.get(format_choice, "html")
        extension = format_key

        # ─── ÉTAPE 4 : Confirmation du chemin ───
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"rules-nft-ipt_{timestamp}.{extension}"
        default_path = EXPORTS_DIR / default_filename

        ctx.console.print(_info(f"\nChemin par défaut : {default_path}"))
        path_input = ctx.console.input(
            _info("Appuyez sur Entrée pour valider, saisissez un autre chemin, ou 'annuler' : ")
        ).strip()
        if is_cancel_word(path_input):
            ctx.console.print(_muted("Export annulé."))
            return

        if path_input:
            output_path = Path(path_input)
            if output_path.is_dir():
                output_path = output_path / default_filename
        else:
            output_path = default_path

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # ─── ÉTAPE 5 : Construction des données et export ───
        # Le choix de thème HTML est un prompt interactif — il doit se faire
        # avant l'animation du spinner, pas pendant (même principe que 6.4).
        theme_name = "omega-base"
        if format_key == "html":
            try:
                theme_name = _prompt_html_theme(ctx, allow_cancel=True)
            except PromptCancelled:
                ctx.console.print(_muted("Opération annulée."))
                return

        try:
            with gauge_status(ctx.console, f"Génération de l'export [{format_key.upper()}]..."):
                if format_key == "html":
                    groups_data = []
                    for group in result.groups:
                        rep = group.representative
                        chain_val = rep.chain.value.upper() if hasattr(rep.chain, "value") else str(rep.chain).upper()
                        action_val = rep.action.value.upper() if hasattr(rep.action, "value") else str(rep.action).upper()
                        proto_val = rep.protocol.value.upper() if rep.protocol and hasattr(rep.protocol, "value") else "ALL"

                        origins = []
                        for r in group.rules:
                            label = "OMEGA" if r.origin == "managed" else "SYSTÈME"
                            if label not in origins:
                                origins.append(label)

                        groups_data.append({
                            "backend": rep.backend,
                            "origins": origins,
                            "chain": chain_val,
                            "action": action_val,
                            "protocol": proto_val,
                            "port": str(rep.port_start) if rep.port_start else "ANY",
                            "source": rep.source_cidr or "ANY",
                            "destination": rep.dest_cidr or "ANY",
                            "state": "ACTIF" if rep.enabled else "INACTIF",
                            "count": group.count,
                            "names": group.names,
                        })

                    html_data = {
                        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "filter_label": filter_label,
                        "total_rules": len(result.full_list),
                        "total_groups": len(result.groups),
                        "groups": groups_data,
                        "theme_name": theme_name,
                    }

                    exporter = ctx.container.get_exporter_port("html")
                    exporter.export_data(html_data, output_path, template_name="ruleset.html.j2")

                else:
                    rules_data = []
                    for r in result.full_list:
                        rules_data.append({
                            "id": r.rule_id,
                            "backend": r.backend,
                            "origin": r.origin,
                            "chain": r.chain.value if hasattr(r.chain, "value") else str(r.chain),
                            "action": r.action.value if hasattr(r.action, "value") else str(r.action),
                            "protocol": r.protocol.value if r.protocol and hasattr(r.protocol, "value") else None,
                            "port_start": r.port_start,
                            "port_end": r.port_end,
                            "source_cidr": r.source_cidr,
                            "dest_cidr": r.dest_cidr,
                            "comment": r.comment,
                            "enabled": r.enabled,
                            "external_ref": r.external_ref,
                            "interface": r.interface,
                        })

                    exporter = ctx.container.get_exporter_port(format_key)
                    exporter.export_data(rules_data, output_path)

        except Exception as e:
            ctx.console.print(_error(f"\nErreur lors de l'export : {e}"))
            return

        if hasattr(ctx.container, "app_logger") and ctx.container.app_logger:
            ctx.container.app_logger.info(
                f"Export des règles ({format_key}, {filter_label}) : {output_path}"
            )

        ctx.console.print()
        ctx.console.print(_success(f"Export terminé : {output_path}"))

    _execute_action_flow(ctx, "6.2 Exporter les règles", logic)

def action_6_3_export_audit(ctx: ActionContext) -> None:
    """6.3 — Rapport d'audit complet."""
    def logic(out: List[Any]):
        from datetime import datetime
        from pathlib import Path
        from rich import box
        from rich.table import Table
        from omega_fire.application.commands.export_audit_report import (
            ExportAuditReportCommand,
            ExportAuditReportRequest,
        )

        if not ctx.container:
            ctx.console.print(_error("Conteneur non disponible."))
            return

        ctx.console.print(_title("6.3 RAPPORT D'AUDIT COMPLET"))
        ctx.console.print()

        # --- 1. Épingle : dernier rapport généré ---
        audit_reports = sorted(
            [f for f in EXPORTS_DIR.glob("audit-rapport_*.*") if f.is_file()],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if audit_reports:
            last = audit_reports[0]
            last_date = datetime.fromtimestamp(last.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")
            ctx.console.print(_muted(f" Dernier rapport généré : {last.name} ({last_date})"))
            ctx.console.print()

        # --- 2. Choix du format ---
        ctx.console.print(_info("Format du rapport :"))
        ctx.console.print(_info("  [1] TXT  — rapport texte brut"))
        ctx.console.print(_info("  [2] HTML — rapport visuel lisible [défaut]"))
        ctx.console.print(_muted("  [0/q] ❌ Annuler"))
        choice = ctx.console.input(_info("\nChoix [1-2] (Défaut: 2) : ")).strip().lower()

        if choice in ("0", "q"):
            ctx.console.print(_warning("Opération annulée."))
            return

        fmt = "txt" if choice == "1" else "html"
        if fmt == "html":
            try:
                theme_name = _prompt_html_theme(ctx, allow_cancel=True)
            except PromptCancelled:
                ctx.console.print(_muted("Opération annulée."))
                return
        else:
            theme_name = "omega-base"

        # --- 3. Chemin de destination ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = EXPORTS_DIR / f"audit-rapport_{timestamp}.{fmt}"
        ctx.console.print()
        ctx.console.print(_info(f"Chemin par défaut : {default_path}"))
        ctx.console.print(_muted("  [0/q] ❌ Annuler"))
        user_path = ctx.console.input(_info("Appuyez sur Entrée pour valider, saisissez un autre chemin, ou annulez : ")).strip()

        if is_cancel_word(user_path):
            ctx.console.print(_warning("Opération annulée."))
            return

        final_path = user_path if user_path else str(default_path)

        ctx.console.print()

        # --- 4. Résolution des dépendances ---
        try:
            with gauge_status(ctx.console, f"Génération du rapport d'audit [{fmt.upper()}]..."):
                adapters = {
                    "nftables": ctx.container.get_firewall_port("nftables"),
                    "iptables": ctx.container.get_firewall_port("iptables"),
                    "ip6tables": ctx.container.get_firewall_port("ip6tables"),
                }
                try:
                    adapters["fail2ban"] = ctx.container.get_fail2ban_port()
                except Exception:
                    adapters["fail2ban"] = None

                command = ExportAuditReportCommand(
                    rule_repository=ctx.container.rule_repository,
                    ban_repository=ctx.container.ban_repository,
                    registry=ctx.capability_registry,
                    adapters=adapters,
                    audit_logger=ctx.container.audit_logger,
                    db_connection=ctx.container.db_connection,
                    html_exporter=ctx.container.html_exporter if fmt == "html" else None,
                )

                result = command.execute(ExportAuditReportRequest(
                    format=fmt,
                    destination=final_path,
                    theme_name=theme_name,
                ))

        except Exception as e:
            ctx.console.print(_error(f"ÉCHEC DE LA GÉNÉRATION : {e}"))
            return

        # --- 5. Affichage du résultat ---
        if not result.success:
            ctx.console.print(_error(f"ÉCHEC DE LA GÉNÉRATION : {result.message}"))
            return

        table = Table(
            title="Statut du Rapport d'Audit",
            show_header=True,
            header_style=theme_registry.get_style("text.heading"),
            border_style=theme_registry.get_style("border.default"),
            box=box.ROUNDED,
        )
        table.add_column("Propriété", style=theme_registry.get_style("text.info"), width=22)
        table.add_column("Détail", style=theme_registry.get_style("text.main"))

        table.add_row("Résultat", _success("RÉUSSI"))
        table.add_row("Format", fmt.upper())
        table.add_row("Fichier généré", str(result.file_path))

        ctx.console.print()
        ctx.console.print(table)
        ctx.console.print(_success(result.message))

    _execute_action_flow(ctx, "6.3 Rapport d'audit complet", logic)

def action_6_4_export_f2b_stats(ctx: ActionContext) -> None:
    """6.4 — Statistiques Fail2Ban."""
    def logic(out: List[Any]):
        from datetime import datetime
        from pathlib import Path
        from rich import box
        from rich.table import Table
        from omega_fire.infrastructure.backends.fail2ban.service_controller import (
            Fail2banServiceController,
        )
        from omega_fire.infrastructure.backends.fail2ban.history_reader import (
            Fail2banHistoryReader,
        )

        if not ctx.container:
            ctx.console.print(_error("Conteneur non disponible."))
            return

        ctx.console.print(_title("6.4 RAPPORT DÉTAILLÉ FAIL2BAN"))
        ctx.console.print()

        # --- 1. Épingle : dernier rapport généré ---
        f2b_reports = sorted(
            [f for f in EXPORTS_DIR.glob("f2b-rapport_*.*") if f.is_file()],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if f2b_reports:
            last = f2b_reports[0]
            last_date = datetime.fromtimestamp(last.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")
            ctx.console.print(_muted(f"📌 Dernier rapport généré : {last.name} ({last_date})"))
            ctx.console.print()

        # --- 2. Choix du format ---
        ctx.console.print(_info("Format du rapport :"))
        ctx.console.print(_info("  [1] TXT  — rapport texte brut"))
        ctx.console.print(_info("  [2] HTML — rapport visuel lisible [défaut]"))
        ctx.console.print(_muted("  [0/q] ❌ Annuler"))
        choice = ctx.console.input(_info("\nChoix [1-2] (Défaut: 2) : ")).strip().lower()

        if choice in ("0", "q"):
            ctx.console.print(_warning("Opération annulée."))
            return

        fmt = "txt" if choice == "1" else "html"
        if fmt == "html":
            try:
                theme_name = _prompt_html_theme(ctx, allow_cancel=True)
            except PromptCancelled:
                ctx.console.print(_muted("Opération annulée."))
                return
        else:
            theme_name = "omega-base"

        # --- 3. Chemin de destination ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = EXPORTS_DIR / f"f2b-rapport_{timestamp}.{fmt}"
        ctx.console.print()
        ctx.console.print(_info(f"Chemin par défaut : {default_path}"))
        ctx.console.print(_muted("  [0/q] ❌ Annuler"))
        user_path = ctx.console.input(_info("Appuyez sur Entrée pour valider, saisissez un autre chemin, ou annulez : ")).strip()

        if is_cancel_word(user_path):
            ctx.console.print(_warning("Opération annulée."))
            return

        final_path = user_path if user_path else str(default_path)

        ctx.console.print()

        # --- 4. Résolution des dépendances ---
        try:
            with gauge_status(ctx.console, f"Génération du rapport [{fmt.upper()}]..."):
                fail2ban_adapter = ctx.container.get_fail2ban_port()
                service_controller = Fail2banServiceController()
                history_reader = Fail2banHistoryReader()

                command = ExportF2bReportCommand(
                    fail2ban_adapter=fail2ban_adapter,
                    service_controller=service_controller,
                    history_reader=history_reader,
                    html_exporter=ctx.container.html_exporter if fmt == "html" else None,
                )

                result = command.execute(ExportF2bReportRequest(
                    format=fmt,
                    destination=final_path,
                    theme_name=theme_name,
                ))

        except Exception as e:
            ctx.console.print(_error(f"ÉCHEC DE LA GÉNÉRATION : {e}"))
            return

        # --- 5. Affichage du résultat ---
        if not result.success:
            ctx.console.print(_error(f"ÉCHEC DE LA GÉNÉRATION : {result.message}"))
            return

        table = Table(
            title="Statut du Rapport Fail2ban",
            show_header=True,
            header_style=theme_registry.get_style("text.heading"),
            border_style=theme_registry.get_style("border.default"),
            box=box.ROUNDED,
        )
        table.add_column("Propriété", style=theme_registry.get_style("text.info"), width=22)
        table.add_column("Détail", style=theme_registry.get_style("text.main"))

        table.add_row("Résultat", _success("RÉUSSI"))
        table.add_row("Format", fmt.upper())
        table.add_row("Fichier généré", str(result.file_path))

        ctx.console.print()
        ctx.console.print(table)
        ctx.console.print(_success(result.message))

    _execute_action_flow(ctx, "6.4 Rapport détaillé Fail2ban", logic)
# ----------------------------------------------------------------------
# Menu 7 — Système & persistance
# ----------------------------------------------------------------------
def action_7_1_backup_state(ctx: ActionContext) -> None:
    """7.1 — Sauvegarder l'état complet."""
    def logic(out: List[Any]):
        from rich import box
        from rich.table import Table

        if not ctx.container:
            ctx.console.print(_error("Conteneur non disponible."))
            return
        ctx.console.print(_title("7.1 SAUVEGARDER L'ÉTAT COMPLET"))
        ctx.console.print()
        ctx.console.print(_info("Capture l'état actuel : règles firewall, IPs bannies (nftables/iptables/fail2ban)."))
        ctx.console.print()
        description = ctx.console.input(_info("Description (optionnelle, ou 'annuler') : ")).strip()
        if is_cancel_word(description):
            ctx.console.print(_muted("Sauvegarde annulée."))
            return

        # Confirmation avant exécution — aucun changement destructif n'est
        # en jeu ici (7.1 ne fait qu'ajouter une archive), mais le
        # principe reste : rien ne se déclenche sans un dernier accord
        # explicite de l'utilisateur.
        ctx.console.print()
        ctx.console.print(_info(f"Description : {description or '(aucune)'}"))
        confirm = ctx.console.input(_info("Confirmez-vous la sauvegarde ? [O/n] : ")).strip().lower()
        if confirm and confirm not in ("o", "oui", "y", "yes"):
            ctx.console.print(_info("Sauvegarde annulée."))
            return

        try:
            persistence_port = ctx.container.get_persistence_port()
            adapters = {
                "nftables": ctx.container.get_firewall_port("nftables"),
                "iptables": ctx.container.get_firewall_port("iptables"),
                "ip6tables": ctx.container.get_firewall_port("ip6tables"),
            }
            try:
                adapters["fail2ban"] = ctx.container.get_fail2ban_port()
            except Exception:
                adapters["fail2ban"] = None
            command = BackupStateCommand(persistence_port=persistence_port, adapters=adapters)
            result = command.execute(BackupStateRequest(description=description))
        except Exception as e:
            ctx.console.print(_error(f"ÉCHEC DE LA SAUVEGARDE : {e}"))
            return
        if not result.success:
            ctx.console.print(_error(f"ÉCHEC DE LA SAUVEGARDE : {result.message}"))
            return
        table = Table(
            title="Statut de la Sauvegarde",
            show_header=True,
            header_style=theme_registry.get_style("text.heading"),
            border_style=theme_registry.get_style("border.default"),
            box=box.ROUNDED,
        )
        table.add_column("Propriété", style=theme_registry.get_style("text.info"), width=22)
        table.add_column("Détail", style=theme_registry.get_style("text.main"))
        table.add_row("Résultat", _success("RÉUSSI"))
        table.add_row("Identifiant", result.snapshot_id or "N/A")
        table.add_row("Règles capturées", str(result.rules_count))
        table.add_row("IPs bannies capturées", str(result.blacklist_count))
        table.add_row("Jails fail2ban capturées", str(result.jails_count))
        ctx.console.print()
        ctx.console.print(table)
        ctx.console.print(_success(result.message))
    _execute_action_flow(ctx, "7.1 Sauvegarder l'état", logic)

def action_7_2_restore_state(ctx: ActionContext) -> None:
    """7.2 — Restaurer un état."""
    def logic(out: List[Any]):
        from rich.box import ROUNDED
        from rich.table import Table
        from rich.text import Text
        from omega_fire.application.commands.restore_state import RestoreStateCommand, RestoreStateRequest

        # QUIT = sort de 7.2 entièrement (retour menu principal).
        # CANCEL = annule seulement l'étape/le sous-menu en cours, reste dans 7.2.
        if not ctx.container:
            ctx.console.print(_error("Conteneur non disponible."))
            return

        try:
            persistence_port = ctx.container.get_persistence_port()
        except Exception as e:
            ctx.console.print(_error(f"Persistance indisponible : {e}"))
            return

        style_border = theme_registry.get_style("border.default")
        style_heading = theme_registry.get_style("text.heading")
        style_muted = theme_registry.get_style("text.muted")
        style_main = theme_registry.get_style("text.main")
        style_success = theme_registry.get_style("action.success")
        style_warning = theme_registry.get_style("action.warning")

        PAGE_SIZE = 8

        def _pause() -> None:
            pause_prompt(ctx.console)

        def _origin_badge(origin: str) -> Text:
            if origin == "auto_preset":
                return Text("AUTO-PROFIL", style=style_warning)
            elif origin == "manual":
                return Text("MANUEL", style=style_success)
            return Text((origin or "?").upper(), style=style_muted)

        def _do_restore(snapshot) -> None:
            ctx.console.print()
            ctx.console.print(_warning("⚠️  ATTENTION :"))
            ctx.console.print(_warning("  • Les règles firewall actuellement gérées par Omega-Fire seront"))
            ctx.console.print(_warning("    RETIRÉES puis REMPLACÉES par celles du snapshot."))
            ctx.console.print(_info("  • Les IPs bannies du snapshot seront AJOUTÉES (rien n'est retiré)."))
            ctx.console.print(_info("  • Les jails fail2ban ne sont PAS restaurées automatiquement (info seulement)."))
            ctx.console.print(_muted("  • Les règles/IPs d'autres outils (UFW, etc.) ne sont jamais touchées."))
            ctx.console.print()

            confirm = ctx.console.input(
                _warning(f"Confirmer la restauration de '{snapshot.id}' ? (o/N) : ")
            ).strip().lower()
            if confirm not in ("o", "oui", "y", "yes"):
                ctx.console.print(_warning("Restauration annulée."))
                return

            ctx.console.print()
            ctx.console.print(_muted("Restauration en cours..."))

            try:
                adapters = {
                    "nftables": ctx.container.get_firewall_port("nftables"),
                    "iptables": ctx.container.get_firewall_port("iptables"),
                    "ip6tables": ctx.container.get_firewall_port("ip6tables"),
                }
                try:
                    adapters["fail2ban"] = ctx.container.get_fail2ban_port()
                except Exception:
                    adapters["fail2ban"] = None

                command = RestoreStateCommand(
                    persistence_port=persistence_port,
                    adapters=adapters,
                    rule_repository=ctx.container.rule_repository,
                )
                result = command.execute(RestoreStateRequest(snapshot_id=snapshot.id))
            except Exception as e:
                ctx.console.print(_error(f"ÉCHEC DE LA RESTAURATION : {e}"))
                return

            if not result.success:
                ctx.console.print(_error(f"ÉCHEC DE LA RESTAURATION : {result.message}"))
                return

            table = Table(
                title="Rapport de Restauration",
                show_header=True,
                header_style=style_heading,
                border_style=style_border,
                box=ROUNDED,
            )
            table.add_column("Propriété", style=style_main, width=26)
            table.add_column("Détail", style=style_main)

            table.add_row("Résultat", _success("RÉUSSI"))
            table.add_row("Snapshot restauré", snapshot.id)
            table.add_row("Règles retirées (anciennes)", str(result.rules_removed))
            table.add_row("Règles appliquées (snapshot)", str(result.rules_applied))
            table.add_row("IPs ajoutées", str(result.ips_added))
            table.add_row("IPs déjà présentes (ignorées)", str(result.ips_already_present))
            table.add_row("Jails dans le snapshot (info)", str(result.jails_in_snapshot))

            ctx.console.print()
            ctx.console.print(table)

            if result.errors:
                ctx.console.print()
                ctx.console.print(_warning(f"{len(result.errors)} erreur(s) rencontrée(s) :"))
                for err in result.errors[:10]:
                    ctx.console.print(_error(f"  • {err}"))
                if len(result.errors) > 10:
                    ctx.console.print(_muted(f"  ... et {len(result.errors) - 10} autre(s)."))

            ctx.console.print()
            ctx.console.print(_success(result.message))

        def _do_edit_description(snapshot) -> None:
            ctx.console.print()
            ctx.console.print(_info(f"Description actuelle : {snapshot.description or '(aucune)'}"))
            new_desc = ctx.console.input(_info("Nouvelle description (ou 'annuler') : ")).strip()
            if not new_desc or is_step_cancel_word(new_desc) or is_quit_word(new_desc):
                ctx.console.print(_muted("Modification annulée."))
                return
            try:
                updated = persistence_port.update_snapshot_description(snapshot.id, new_desc)
            except Exception as e:
                ctx.console.print(_error(f"Erreur lors de la modification : {e}"))
                return
            if updated:
                ctx.console.print(_success("Description mise à jour."))
            else:
                ctx.console.print(_error("Snapshot introuvable (a-t-il été supprimé entre-temps ?)."))

        def _do_delete_single(snapshot) -> None:
            confirm = ctx.console.input(
                _warning(f"Confirmez-vous la suppression DÉFINITIVE de '{snapshot.id}' ? [o/N] : ")
            ).strip().lower()
            if confirm not in ("o", "oui", "y", "yes"):
                ctx.console.print(_info("Suppression annulée."))
                return
            try:
                persistence_port.delete_snapshot(snapshot.id)
                ctx.console.print(_success(f"Snapshot '{snapshot.id}' supprimé."))
            except Exception as e:
                ctx.console.print(_error(f"Erreur lors de la suppression : {e}"))

        def _snapshot_submenu(snapshot) -> bool:
            """Retourne True si l'utilisateur veut quitter 7.2 entièrement."""
            ctx.console.print()
            ctx.console.print(_title(f"Snapshot : {snapshot.id}"))
            ctx.console.print(_info(f"Description : {snapshot.description or '(aucune)'}"))
            ctx.console.print(_info("  [1]   Restaurer cet état"))
            ctx.console.print(_info("  [2] ✏️  Modifier la description"))
            ctx.console.print(_info("  [3] 🗑️  Supprimer ce snapshot"))
            ctx.console.print(_info("  [0] ↩️  Retour à la liste"))
            ctx.console.print(_muted("  [q] ⏹  Quitter 7.2"))

            choice = ctx.console.input(_info("\nVotre choix : ")).strip()

            if is_quit_word(choice):
                return True
            if not choice or is_step_cancel_word(choice):
                return False
            elif choice == "1":
                _do_restore(snapshot)
                _pause()
            elif choice == "2":
                _do_edit_description(snapshot)
                _pause()
            elif choice == "3":
                _do_delete_single(snapshot)
                _pause()
            else:
                ctx.console.print(_error("Choix invalide."))
                _pause()

            return False

        def _delete_multiple(snapshots: list) -> None:
            raw = ctx.console.input(
                _info("\nNuméros à supprimer, séparés par une virgule (ex: 3,7,12) ou 'annuler' : ")
            ).strip()
            if not raw or is_step_cancel_word(raw) or is_quit_word(raw):
                ctx.console.print(_muted("Suppression annulée."))
                return

            raw_parts = [p.strip() for p in raw.split(",") if p.strip()]
            targets = []
            invalid = []
            for part in raw_parts:
                if part.isdigit() and 1 <= int(part) <= len(snapshots):
                    targets.append(snapshots[int(part) - 1])
                else:
                    invalid.append(part)

            if invalid:
                ctx.console.print(_error(f"Numéro(s) invalide(s) ignoré(s) : {', '.join(invalid)}"))

            if not targets:
                ctx.console.print(_error("Aucun numéro valide fourni. Annulation."))
                return

            ctx.console.print()
            ctx.console.print(_warning(f"Snapshots à supprimer définitivement ({len(targets)}) :"))
            for snap in targets:
                ctx.console.print(_warning(f"  • {snap.id} — {snap.description or '(aucune description)'}"))

            confirm = ctx.console.input(_warning("\nConfirmer la suppression ? [o/N] : ")).strip().lower()
            if confirm not in ("o", "oui", "y", "yes"):
                ctx.console.print(_info("Suppression annulée."))
                return

            success_count = 0
            error_count = 0
            for snap in targets:
                try:
                    persistence_port.delete_snapshot(snap.id)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    ctx.console.print(_error(f"  ❌ {snap.id} : {e}"))

            ctx.console.print()
            ctx.console.print(_success(f"{success_count} snapshot(s) supprimé(s)."))
            if error_count:
                ctx.console.print(_error(f"{error_count} échec(s)."))

        # ─── Boucle principale ───
        page = 0
        while True:
            try:
                snapshots = persistence_port.list_snapshots()
            except Exception as e:
                ctx.console.print(_error(f"Impossible de lister les snapshots : {e}"))
                return

            if not snapshots:
                ctx.console.print(_info("Aucun snapshot disponible. Utilisez d'abord le menu 7.1."))
                return

            total_pages = (len(snapshots) + PAGE_SIZE - 1) // PAGE_SIZE
            page = max(0, min(page, total_pages - 1))
            start_idx = page * PAGE_SIZE
            end_idx = start_idx + PAGE_SIZE
            page_snapshots = snapshots[start_idx:end_idx]

            ctx.console.print(_title(f"7.2 RESTAURER UN ÉTAT (Page {page + 1}/{total_pages})"))
            ctx.console.print()

            table = Table(box=ROUNDED, border_style=style_border, header_style=style_heading, expand=True)
            table.add_column("N°", style=style_muted, justify="center", width=4)
            table.add_column("Date", style=style_main, width=12)
            table.add_column("Origine", justify="center", width=12)
            table.add_column("Description", style=style_main)
            table.add_column("Règles", style=style_muted, justify="center", width=7)
            table.add_column("IPs", style=style_muted, justify="center", width=6)
            table.add_column("Jails", style=style_muted, justify="center", width=6)

            for offset, snap in enumerate(page_snapshots):
                global_idx = start_idx + offset + 1
                table.add_row(
                    str(global_idx),
                    snap.created_at.strftime("%d/%m %H:%M"),
                    _origin_badge(snap.origin),
                    snap.description or "(aucune)",
                    str(snap.rules_count),
                    str(snap.blacklist_count),
                    str(snap.jails_count),
                )

            ctx.console.print(table)
            ctx.console.print()

            nav_opts = []
            if page < total_pages - 1:
                nav_opts.append("[N] Page suivante")
            if page > 0:
                nav_opts.append("[P] Page précédente")
            if nav_opts:
                ctx.console.print(_info("  " + "  |  ".join(nav_opts)))

            ctx.console.print(_info(f"  [1-{len(snapshots)}] Sélectionner un snapshot"))
            ctx.console.print(_info("  [D] 🗑️  Supprimer plusieurs snapshots"))
            ctx.console.print(_muted("  [0/q] ↩️  Retour au menu"))

            choice = ctx.console.input(_info("\nVotre choix : ")).strip()

            if not choice or is_quit_word(choice) or is_step_cancel_word(choice):
                return

            if choice.upper() == "N" and page < total_pages - 1:
                page += 1
                continue
            elif choice.upper() == "P" and page > 0:
                page -= 1
                continue
            elif choice.upper() == "D":
                _delete_multiple(snapshots)
                _pause()
                continue
            elif choice.isdigit() and 1 <= int(choice) <= len(snapshots):
                selected_snapshot = snapshots[int(choice) - 1]
                want_quit = _snapshot_submenu(selected_snapshot)
                if want_quit:
                    return
                continue
            else:
                ctx.console.print(_error("Choix invalide."))
                _pause()
                continue

    _execute_action_flow(ctx, "7.2 Restaurer un état", logic)

def action_7_3_action_history(ctx: ActionContext) -> None:
    """7.3 — Historique des actions (audit)."""
    def logic(out: List[Any]):
        from datetime import datetime, timedelta
        from rich.box import ROUNDED
        from rich.table import Table
        from rich.text import Text
        from omega_fire.application.queries.read_audit_history import (
            ReadAuditHistoryQuery,
            ReadAuditHistoryRequest,
        )

        PAGE_SIZE = 12

        if not ctx.container:
            ctx.console.print(_error("Conteneur non disponible."))
            return

        try:
            audit_port = ctx.container.get_audit_port()
        except Exception as e:
            ctx.console.print(_error(f"Registre d'audit indisponible : {e}"))
            return

        style_border = theme_registry.get_style("border.default")
        style_heading = theme_registry.get_style("text.heading")
        style_muted = theme_registry.get_style("text.muted")
        style_main = theme_registry.get_style("text.main")
        style_success = theme_registry.get_style("action.success")
        style_error = theme_registry.get_style("action.error")

        def _pause() -> None:
            pause_prompt(ctx.console)

        def _fetch(keyword: str) -> list:
            result = ReadAuditHistoryQuery(audit_port).execute(
                ReadAuditHistoryRequest(limit=500, keyword=keyword)
            )
            if not result.success:
                ctx.console.print(_error(result.message))
                return []
            return result.entries

        def _result_badge(success: bool) -> Text:
            return Text("OK", style=style_success) if success else Text("ÉCHEC", style=style_error)

        def _details_cell(entry) -> str:
            parts = []
            if entry.target and entry.target != "N/A":
                parts.append(f"cible: {entry.target}")
            if entry.error_message:
                parts.append(f"erreur: {entry.error_message}")
            return " | ".join(parts) if parts else "-"

        def _do_purge_menu() -> None:
            ctx.console.print()
            ctx.console.print(_title("Gestion du journal d'audit"))
            ctx.console.print(_info("  [1] ◴ Supprimer les entrées de + de 30 jours"))
            ctx.console.print(_info("  [2] ◷ Supprimer les entrées de + de 120 jours"))
            ctx.console.print(_info("  [3] ◵ Supprimer les entrées antérieures à une date précise"))
            ctx.console.print(_info("  [4] ◶ Supprimer les N entrées les plus anciennes"))
            ctx.console.print(_muted("  [0] Annuler"))

            choice = ctx.console.input(_info("\nVotre choix : ")).strip()
            if not choice or is_step_cancel_word(choice) or is_quit_word(choice):
                ctx.console.print(_muted("Gestion annulée."))
                return

            older_than = None
            removal_label = ""

            if choice == "1":
                older_than = datetime.now() - timedelta(days=30)
                removal_label = "les entrées de plus de 30 jours"
            elif choice == "2":
                older_than = datetime.now() - timedelta(days=120)
                removal_label = "les entrées de plus de 120 jours"
            elif choice == "3":
                raw_date = ctx.console.input(
                    _info("Date limite (format JJ/MM/AAAA, ou 'annuler') : ")
                ).strip()
                if not raw_date or is_step_cancel_word(raw_date) or is_quit_word(raw_date):
                    ctx.console.print(_muted("Gestion annulée."))
                    return
                try:
                    older_than = datetime.strptime(raw_date, "%d/%m/%Y")
                except ValueError:
                    ctx.console.print(_error("Format de date invalide (attendu : JJ/MM/AAAA)."))
                    return
                removal_label = f"les entrées antérieures au {raw_date}"
            elif choice == "4":
                raw_count = ctx.console.input(
                    _info("Nombre d'entrées les plus anciennes à supprimer (ou 'annuler') : ")
                ).strip()
                if not raw_count or is_step_cancel_word(raw_count) or is_quit_word(raw_count):
                    ctx.console.print(_muted("Gestion annulée."))
                    return
                if not raw_count.isdigit() or int(raw_count) <= 0:
                    ctx.console.print(_error("Nombre invalide."))
                    return
                count = int(raw_count)
            else:
                ctx.console.print(_error("Choix invalide."))
                return

            ctx.console.print()
            if choice == "4":
                ctx.console.print(_warning(f"Vous allez supprimer les {count} entrées d'audit les plus anciennes."))
            else:
                ctx.console.print(_warning(f"Vous allez supprimer {removal_label}."))

            confirm = ctx.console.input(_warning("Confirmer la suppression ? [o/N] : ")).strip().lower()
            if confirm not in ("o", "oui", "y", "yes"):
                ctx.console.print(_info("Suppression annulée."))
                return

            try:
                if choice == "4":
                    removed = audit_port.delete_oldest(count)
                else:
                    removed = audit_port.clear(older_than=older_than)
            except Exception as e:
                ctx.console.print(_error(f"Erreur lors de la suppression : {e}"))
                return

            ctx.console.print(_success(f"{removed} entrée(s) supprimée(s)."))

        # ─── Boucle principale ───
        keyword = ""
        page = 0

        while True:
            entries = _fetch(keyword)

            if not entries:
                ctx.console.print(_info(
                    "Aucune entrée d'audit trouvée." + (f" (filtre : '{keyword}')" if keyword else "")
                ))
                ctx.console.print()
                ctx.console.print(_info("  [F] 🔍 Changer le filtre"))
                ctx.console.print(_info("  [G] 🗑️  Gérer / Purger le journal"))
                ctx.console.print(_muted("  [0/q] ↩️  Retour au menu"))
                choice = ctx.console.input(_info("\nVotre choix : ")).strip()
                if choice.upper() == "F":
                    new_kw = ctx.console.input(_info("Nouveau filtre (Entrée = aucun, 'annuler' = inchangé) : ")).strip()
                    if not is_step_cancel_word(new_kw) and not is_quit_word(new_kw):
                        keyword = new_kw
                    page = 0
                    continue
                elif choice.upper() == "G":
                    _do_purge_menu()
                    _pause()
                    page = 0
                    continue
                else:
                    return

            total_pages = (len(entries) + PAGE_SIZE - 1) // PAGE_SIZE
            page = max(0, min(page, total_pages - 1))
            start_idx = page * PAGE_SIZE
            end_idx = start_idx + PAGE_SIZE
            page_entries = entries[start_idx:end_idx]

            filter_label = f" — Filtre : '{keyword}'" if keyword else ""
            ctx.console.print(_title(f"7.3 HISTORIQUE DES ACTIONS (Page {page + 1}/{total_pages}){filter_label}"))
            ctx.console.print()

            table = Table(box=ROUNDED, border_style=style_border, header_style=style_heading, expand=True)
            table.add_column("Heure", style=style_muted, width=17)
            table.add_column("Action", style=style_main)
            table.add_column("Acteur", style=style_muted, width=12)
            table.add_column("Résultat", justify="center", width=9)
            table.add_column("Détails", style=style_muted)

            for entry in page_entries:
                table.add_row(
                    entry.timestamp.strftime("%d/%m %H:%M:%S"),
                    entry.action,
                    entry.actor,
                    _result_badge(entry.success),
                    _details_cell(entry),
                )

            ctx.console.print(table)
            ctx.console.print()
            ctx.console.print(_muted(f"{len(entries)} entrée(s) au total (limite de lecture : 500)."))
            ctx.console.print()

            nav_opts = []
            if page < total_pages - 1:
                nav_opts.append("[N] Page suivante")
            if page > 0:
                nav_opts.append("[P] Page précédente")
            if nav_opts:
                ctx.console.print(_info("  " + "  |  ".join(nav_opts)))

            ctx.console.print(_info("  [F] 🔍 Filtrer par mot-clé"))
            ctx.console.print(_info("  [G] 🗑️  Gérer / Purger le journal"))
            ctx.console.print(_muted("  [0/q] ↩️  Retour au menu"))

            choice = ctx.console.input(_info("\nVotre choix : ")).strip()

            if not choice or is_quit_word(choice) or is_step_cancel_word(choice):
                return
            elif choice.upper() == "N" and page < total_pages - 1:
                page += 1
            elif choice.upper() == "P" and page > 0:
                page -= 1
            elif choice.upper() == "F":
                new_kw = ctx.console.input(_info("Nouveau filtre (Entrée = aucun, 'annuler' = inchangé) : ")).strip()
                if not is_step_cancel_word(new_kw) and not is_quit_word(new_kw):
                    keyword = new_kw
                    page = 0
            elif choice.upper() == "G":
                _do_purge_menu()
                _pause()
                page = 0
            else:
                ctx.console.print(_error("Choix invalide."))
                _pause()

    _execute_action_flow(ctx, "7.3 Historique des actions", logic)

def action_7_4_reload_config(ctx: ActionContext) -> None:
    """7.4 — Recharger la configuration.

    Réutilise exactement le même mécanisme que 1.3 (SystemScanner.scan()
    via ctx.container.scanner) — même re-scan complet des sondes système
    et du fichier config/omega-fire.conf, mais avec un affichage minimal
    plutôt que le détail diagnostic complet de 1.3.
    """
    def logic(out: List[Any]):
        if not ctx.container:
            ctx.console.print(_error("Conteneur non disponible."))
            return

        try:
            scanner = ctx.container.scanner if hasattr(ctx.container, "scanner") else None
            if scanner is None:
                ctx.console.print(_error("Impossible de récupérer la sonde système depuis le conteneur."))
                return

            with gauge_status(ctx.console, "Re-scan en cours..."):
                scan_results = scanner.scan()
            scan_errors = scan_results.get("errors", [])

            if scan_errors:
                ctx.console.print(_warning(f"Configuration rechargée avec {len(scan_errors)} avertissement(s)."))
            else:
                ctx.console.print(_success("Configuration rechargée."))

        except Exception as e:
            ctx.console.print(_error(f"Échec du rechargement : {e}"))

    _execute_action_flow(ctx, "7.4 Recharger config", logic)
# ----------------------------------------------------------------------
# Menu 8 — Monitoring & statistiques
# ----------------------------------------------------------------------
def action_8_1_live_dashboard(ctx: ActionContext) -> None:
    """8.1 — Tableau de bord en temps réel (Live Dashboard)."""
    from omega_fire.interfaces.cli.renderers.dashboard import render_general_state

    stats_provider = None
    if ctx.container:
        try:
            from omega_fire.application.queries.dashboard_snapshot import DashboardSnapshotProvider
            from omega_fire.infrastructure.logging.stats.log_aggregator import LogAggregator

            try:
                monitoring_port = ctx.container.get_monitoring_port()
            except Exception:
                monitoring_port = None

            try:
                audit_port = ctx.container.get_audit_port()
            except Exception:
                audit_port = None

            try:
                fail2ban_port = ctx.container.get_fail2ban_port()
            except Exception:
                fail2ban_port = None

            firewall_ports = {}
            for backend in ("nftables", "iptables", "ip6tables"):
                try:
                    firewall_ports[backend] = ctx.container.get_firewall_port(backend)
                except Exception:
                    firewall_ports[backend] = None

            rule_repository = getattr(ctx.container, "rule_repository", None)
            ban_repository = getattr(ctx.container, "ban_repository", None)

            stats_provider = DashboardSnapshotProvider(
                monitoring_port=monitoring_port,
                audit_port=audit_port,
                rule_repository=rule_repository,
                log_aggregator=LogAggregator(),
                ban_repository=ban_repository,
                fail2ban_port=fail2ban_port,
                firewall_ports=firewall_ports,
                capability_registry=ctx.capability_registry,
            )
        except Exception:
            pass

    ctx.console.clear()
    render_general_state(
        capability_registry=ctx.capability_registry,
        console=ctx.console,
        wait_for_key=True,
        fw_stats_provider=stats_provider,
    )

def action_8_2_conntrack_status(ctx: ActionContext) -> None:
    """8.2 — État des connexions (Conntrack)."""
    def logic(out: List[Any]):
        from omega_fire.application.queries.conntrack_status import get_conntrack_status
        from omega_fire.interfaces.cli.renderers.conntrack_view import (
            render_conntrack_summary,
            render_conntrack_table,
        )

        def _get_monitoring_port():
            if not ctx.container:
                return None
            try:
                return ctx.container.get_monitoring_port()
            except Exception:
                return None

        monitoring_port = _get_monitoring_port()
        if monitoring_port is None:
            ctx.console.print(_error("Port de monitoring non disponible."))
            return

        # Collecte initiale non filtrée, pour connaître les protocoles/
        # états réellement présents avant de proposer les filtres.
        state = {
            "protocol_filter": "",
            "state_filter": "",
            "limit": 100,
        }

        def fetch():
            with gauge_status(ctx.console, "Scan des connexions..."):
                return get_conntrack_status(
                    monitoring_port=monitoring_port,
                    protocol_filter=state["protocol_filter"],
                    state_filter=state["state_filter"],
                    limit=state["limit"],
                )

        result = fetch()

        def build_screen():
            ctx.console.print()
            ctx.console.print(_title("8.2 État des connexions (Conntrack)"))
            if state["protocol_filter"] or state["state_filter"]:
                filters_desc = []
                if state["protocol_filter"]:
                    filters_desc.append(f"protocole={state['protocol_filter']}")
                if state["state_filter"]:
                    filters_desc.append(f"état={state['state_filter']}")
                ctx.console.print(_info(f"Filtres actifs : {', '.join(filters_desc)}"))
            ctx.console.print()
            ctx.console.print(render_conntrack_summary(result))
            ctx.console.print()
            ctx.console.print(render_conntrack_table(result))
            ctx.console.print()

            footer_text = Text(no_wrap=True)
            footer_text.append("[r]", style=theme_registry.get_style("footer.key"))
            footer_text.append("afraîchir  ", style=theme_registry.get_style("footer.label"))
            footer_text.append("|  ", style=theme_registry.get_style("footer.separator"))
            footer_text.append("[f]", style=theme_registry.get_style("footer.key"))
            footer_text.append("iltrer  ", style=theme_registry.get_style("footer.label"))
            footer_text.append("|  ", style=theme_registry.get_style("footer.separator"))
            footer_text.append("[t]", style=theme_registry.get_style("footer.key"))
            footer_text.append("hème  ", style=theme_registry.get_style("footer.label"))
            footer_text.append("|  ", style=theme_registry.get_style("footer.separator"))
            footer_text.append("[e]", style=theme_registry.get_style("footer.key"))
            footer_text.append("xporter HTML  ", style=theme_registry.get_style("footer.label"))
            footer_text.append("|  ", style=theme_registry.get_style("footer.separator"))
            footer_text.append("[Entrée]", style=theme_registry.get_style("footer.key"))
            footer_text.append(" Retour au menu", style=theme_registry.get_style("footer.label"))

            ctx.console.print(Panel(
                footer_text,
                border_style=theme_registry.get_style("border.default"),
                box=box.ROUNDED,
                padding=(0, 2),
            ))

        def do_export():
            try:
                from omega_fire.infrastructure.exporters.html_exporter import HtmlExporter
                from omega_fire.infrastructure.config.paths import EXPORTS_DIR, TEMPLATES_DIR

                # Prompt interactif — avant l'animation du spinner, pas pendant.
                theme_name = _prompt_html_theme(ctx, allow_cancel=True)

                with gauge_status(ctx.console, "Génération de l'export [HTML]..."):
                    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = EXPORTS_DIR / f"conntrack-rapport_{timestamp}.html"

                    filters_desc = []
                    if state["protocol_filter"]:
                        filters_desc.append(f"protocole={state['protocol_filter']}")
                    if state["state_filter"]:
                        filters_desc.append(f"état={state['state_filter']}")

                    data = {
                        "page_title": "Export Conntrack - Omega-Fire",
                        "heading": "Rapport des connexions Conntrack",
                        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "filters_label": ", ".join(filters_desc),
                        "total_count": result.total_count,
                        "by_protocol": result.by_protocol,
                        "by_state": result.by_state,
                        "entries": result.entries,
                        "theme_name": theme_name,
                    }

                    exporter = HtmlExporter(templates_dir=TEMPLATES_DIR)
                    exporter.export_data(data, output_path, template_name="conntrack_export.html.j2")

                ctx.console.print()
                ctx.console.print(_success(f"Rapport exporté : {output_path}"))
            except PromptCancelled:
                ctx.console.print()
                ctx.console.print(_muted("Export annulé."))
            except Exception as e:
                ctx.console.print()
                ctx.console.print(_error(f"Échec de l'export : {e}"))

        def do_filter():
            nonlocal result

            ctx.console.print()
            ctx.console.print(_title("Filtrer les connexions"))

            if result.by_protocol:
                ctx.console.print(_info("Protocoles disponibles :"))
                protocols = list(result.by_protocol.keys())
                for idx, proto in enumerate(protocols, start=1):
                    ctx.console.print(_info(f"  [{idx}] {proto} ({result.by_protocol[proto]})"))
                ctx.console.print(_info("  [Entrée] Tous"))
                ctx.console.print(_muted("  [0] Annuler le filtrage"))

                choice = ctx.console.input(_info("\nVotre choix : ")).strip()
                if is_step_cancel_word(choice) or is_quit_word(choice):
                    return
                elif choice.isdigit() and 1 <= int(choice) <= len(protocols):
                    state["protocol_filter"] = protocols[int(choice) - 1]
                else:
                    state["protocol_filter"] = ""
            else:
                ctx.console.print(_muted("Aucun protocole détecté à filtrer."))

            if result.by_state:
                ctx.console.print()
                ctx.console.print(_info("États disponibles :"))
                states = list(result.by_state.keys())
                for idx, st in enumerate(states, start=1):
                    ctx.console.print(_info(f"  [{idx}] {st} ({result.by_state[st]})"))
                ctx.console.print(_info("  [Entrée] Tous"))
                ctx.console.print(_muted("  [0] Annuler le filtrage"))

                choice = ctx.console.input(_info("\nVotre choix : ")).strip()
                if is_step_cancel_word(choice) or is_quit_word(choice):
                    return
                elif choice.isdigit() and 1 <= int(choice) <= len(states):
                    state["state_filter"] = states[int(choice) - 1]
                else:
                    state["state_filter"] = ""
            else:
                ctx.console.print(_muted("Aucun état détecté à filtrer."))

            limit_str = ctx.console.input(
                _info(f"\nNombre max de lignes (actuel: {state['limit']}, 'annuler' = inchangé) : ")
            ).strip()
            if limit_str and not is_step_cancel_word(limit_str) and not is_quit_word(limit_str):
                try:
                    state["limit"] = int(limit_str)
                except ValueError:
                    ctx.console.print(_error("Nombre invalide, valeur précédente conservée."))

            result = fetch()

        build_screen()

        while True:
            choice = ctx.console.input(
                _info("\nVotre choix ([r]afraîchir / [f]iltrer / [t]hème / [e]xporter / [Entrée] retour) : ")
            ).strip().lower()

            if not choice:
                return
            elif choice == "r":
                result = fetch()
                build_screen()
            elif choice == "f":
                do_filter()
                build_screen()
            elif choice == "e":
                do_export()
            elif choice == "t":
                themes_list = []
                try:
                    if hasattr(theme_registry, "get_available_themes"):
                        themes_list = list(theme_registry.get_available_themes())
                    elif hasattr(theme_registry, "_themes"):
                        themes_list = list(theme_registry._themes.keys())
                except Exception:
                    pass

                if themes_list:
                    try:
                        current = theme_registry.get_active().name
                        next_idx = (themes_list.index(current) + 1) % len(themes_list) if current in themes_list else 0
                        theme_registry.set_active(themes_list[next_idx], silent=True)
                    except Exception:
                        pass

                build_screen()
            else:
                ctx.console.print(_error("Choix invalide."))

    _execute_action_flow(ctx, "8.2 Connexions Conntrack", logic, pause_at_end=False)
#=======================================================================
def _build_kpi_table(summary) -> "Table":
    """Build the 4 KPI cards as a single-row Table, for use in static
    (non-Live) screens — unlike render_kpi_cards() (kpi_cards.py),
    which returns a Layout that only respects height constraints
    inside a Live/screen=True context (menu 5.8's use case). A bare
    console.print(layout) outside Live leaves Rich free to stretch
    unconstrained child Panels to fill most of the terminal height,
    which is exactly the oversized-cards bug this function avoids —
    a Table's row height is bound to its actual content instead.
    """
    

    style_border = theme_registry.get_style("border.default")
    style_info = theme_registry.get_style("text.info")
    style_danger = theme_registry.get_style("text.danger")
    style_warning = theme_registry.get_style("text.warning")
    style_main = theme_registry.get_style("text.main")
    style_muted = theme_registry.get_style("text.muted")

    table = Table(box=box.ROUNDED, border_style=style_border, expand=True, show_header=False)
    table.add_column("events", ratio=1)
    table.add_column("bans", ratio=1)
    table.add_column("jail", ratio=1)
    table.add_column("peak", ratio=1)

    events_cell = Text()
    events_cell.append(f"{summary.total_events:,}\n", style=style_info)
    events_cell.append(f"Logs scannés ({summary.data_source})", style=style_muted)

    bans_cell = Text()
    bans_cell.append(f"{summary.total_bans:,}\n", style=style_danger)
    bans_cell.append("Adresses IP bloquées", style=style_muted)

    jail_cell = Text()
    jail_cell.append(f"{summary.top_jail_name}\n", style=style_warning)
    jail_cell.append("Service le plus ciblé", style=style_muted)

    peak_cell = Text()
    peak_cell.append(f"{summary.peak_hour}\n", style=style_main)
    peak_cell.append(f"Pic ({summary.peak_count} évts)", style=style_muted)

    table.add_row(events_cell, bans_cell, jail_cell, peak_cell)

    return table

def _build_top_tables_columns(result) -> "Columns":
    """Rebuild the Top IPs / Top Jails tables side-by-side for static
    screens, independently of stat_tables.py::render_stat_tables()
    (which returns a Layout — same unbounded-height issue as
    kpi_cards.py, already worked around by _build_kpi_table()). Uses
    Columns (not Layout) to keep the side-by-side arrangement while
    letting each Table's height follow its actual content.
    """
    from rich.columns import Columns

    style_border = theme_registry.get_style("border.default")
    style_heading = theme_registry.get_style("text.heading")
    style_main = theme_registry.get_style("text.main")
    style_muted = theme_registry.get_style("text.muted")
    style_danger = theme_registry.get_style("text.danger")
    style_warning = theme_registry.get_style("text.warning")
    style_success = theme_registry.get_style("status.available")

    # --- Top IPs ---
    ip_table = Table(box=box.ROUNDED, border_style=style_border, header_style=style_heading, expand=True)
    ip_table.add_column("#", style=style_muted, justify="right", width=3)
    ip_table.add_column("Adresse IP", style=style_main)
    ip_table.add_column("Bans", style=style_danger, justify="right")
    ip_table.add_column("Dernier Ban", style=style_muted, justify="right")

    if not result.top_ips:
        ip_table.add_row("-", "Aucune donnée", "0", "--:--")
    else:
        for idx, ip_stat in enumerate(result.top_ips[:8], 1):
            ip_table.add_row(str(idx), ip_stat["ip"], str(ip_stat["total_bans"]), ip_stat["last_ban"][11:19])

    ip_panel = Panel(
        ip_table, title="Top Adresses IP Ciblées", title_align="left",
        border_style=style_border, expand=True,
    )

    # --- Top Jails ---
    jail_table = Table(box=box.ROUNDED, border_style=style_border, header_style=style_heading, expand=True)
    jail_table.add_column("Jail / Service", style=style_main)
    jail_table.add_column("Statut", justify="center", width=10)
    jail_table.add_column("Bans", style=style_warning, justify="right")
    jail_table.add_column("Part", justify="left")

    if not result.top_jails:
        jail_table.add_row("Aucune donnée", "-", "0", "")
    else:
        for jail in result.top_jails[:8]:
            status_text = Text("● Actif", style=style_success) if jail["is_active"] else Text("○ Archivé", style=style_muted)
            bar_len = int(jail["percentage"] / 10)
            bar = Text()
            bar.append("█" * bar_len, style=style_main)
            bar.append("░" * (10 - bar_len), style=style_muted)
            bar.append(f" {jail['percentage']}%", style=style_muted)
            jail_table.add_row(jail["name"], status_text, str(jail["total_bans"]), bar)

    jail_panel = Panel(
        jail_table, title="Activité par Service (Jail)", title_align="left",
        border_style=style_border, expand=True,
    )

    from omega_fire.interfaces.cli.renderers.styles import get_terminal_width
    half_width = (get_terminal_width() - 6) // 2
    ip_panel.width = half_width
    jail_panel.width = half_width

    return Columns([ip_panel, jail_panel], equal=True, expand=False)

def _build_management_evolution_columns(ctx, result) -> "Columns":
    """Place the Gestion and Évolution des Règles panels side-by-side,
    same rationale as _build_top_tables_columns() — Columns instead of
    stacking, bounded height instead of unconstrained Layout.
    """
    from rich.columns import Columns
    from omega_fire.interfaces.cli.renderers.stats.management_panel import render_management_panel
    from omega_fire.interfaces.cli.renderers.stats.rules_evolution_panel import render_rules_evolution_panel

    management_panel = render_management_panel(
        rule_changes=result.management.get("rule_changes", 0),
        backups=result.management.get("backups", 0),
        restores=result.management.get("restores", 0),
        total_actions=result.management.get("total_actions", 0),
        success_rate=result.management.get("success_rate", 0.0),
        recent_entries=result.management.get("recent_entries", []),
    )
    evolution_panel = render_rules_evolution_panel(result.rules_evolution)

    from omega_fire.interfaces.cli.renderers.styles import get_terminal_width
    half_width = (get_terminal_width() - 6) // 2
    management_panel.width = half_width
    evolution_panel.width = half_width

    return Columns([management_panel, evolution_panel], equal=True, expand=False)
    
def _render_stats_report_screen(
    ctx: ActionContext,
    period_code: str,
    period_label: str,
    period_suffix: str,
    title: str,
) -> None:
    """Shared screen logic for menus 8.3 (7 days) and 8.4 (30 days) —
    both call this with only period_code/period_label/period_suffix/
    title differing, avoiding near-total duplication between the two
    actions.

    Static report screen (not Live-refreshed like menus 5.8/8.1):
    the report is built once, displayed, then reacts to key presses
    ([t] theme swap + full redraw, [e] HTML export, Enter to return)
    without a background refresh thread.
    """
    from datetime import datetime
    from rich.box import ROUNDED
    from rich.panel import Panel
    from rich.text import Text
    from omega_fire.application.queries.build_stats_report import (
        BuildStatsReportQuery,
        BuildStatsReportRequest,
    )
    from omega_fire.core.stats.models import LogStatsSummary, IpStat, JailStat
    from omega_fire.interfaces.cli.renderers.stats.ascii_charts import render_hourly_chart
    from omega_fire.interfaces.cli.renderers.stats.daily_trend_chart import render_daily_trend_chart

    if not ctx.container:
        ctx.console.print(_error("Conteneur non disponible."))
        return

    try:
        audit_port = ctx.container.get_audit_port()
    except Exception:
        audit_port = None

    try:
        persistence_port = ctx.container.get_persistence_port()
    except Exception:
        persistence_port = None

    with gauge_status(ctx.console, f"Construction du rapport [{period_label}]..."):
        result = BuildStatsReportQuery(
            audit_port=audit_port,
            persistence_port=persistence_port,
        ).execute(BuildStatsReportRequest(period_code=period_code, period_label=period_label))

    if not result.success:
        ctx.console.print(_error(result.message))
        return

    style_border = theme_registry.get_style("border.default")
    style_heading = theme_registry.get_style("text.heading")
    style_muted = theme_registry.get_style("text.muted")

    # Objet minimal compatible avec les renderers déjà existants de 5.8
    # (kpi_cards.py/ascii_charts.py/stat_tables.py, tous conçus pour
    # recevoir un LogStatsSummary complet) — reconstruit à partir des
    # données déjà dépaquetées par BuildStatsReportQuery, pour réutiliser
    # ces trois renderers SANS aucune modification.
    summary = LogStatsSummary(
        period_label=period_label,
        start_date=datetime.now(),
        end_date=datetime.now(),
        total_events=result.kpi.get("total_events", 0),
        total_bans=result.kpi.get("total_bans", 0),
        peak_hour=result.kpi.get("peak_hour", "--:--"),
        peak_count=result.kpi.get("peak_count", 0),
        top_jail_name=result.kpi.get("top_jail_name", "Aucun"),
        top_jails=[
            JailStat(name=j["name"], total_bans=j["total_bans"], is_active=j["is_active"], percentage=j["percentage"])
            for j in result.top_jails
        ],
        top_ips=[
            IpStat(ip=i["ip"], total_bans=i["total_bans"], last_ban=datetime.fromisoformat(i["last_ban"]))
            for i in result.top_ips
        ],
        hourly_series=result.hourly_series,
        data_source=result.kpi.get("data_source", "Inconnue"),
    )

    def build_screen():
        theme = theme_registry.get_active()
        use_emoji = getattr(theme, "prefers_emojis", True)

        header_text = Text(no_wrap=True)
        if use_emoji:
            header_text.append("📊 ", style=style_heading)
        header_text.append(title, style=style_heading)
        header_text.append("  │  ", style=style_muted)
        header_text.append(f"Source: {summary.data_source}", style=style_muted)
        header_text.append("  │  ", style=style_muted)
        header_text.append(f"Theme: {theme.display_name}", style=style_muted)

        ctx.console.print()
        ctx.console.print(Panel(header_text, border_style=style_border, box=ROUNDED, padding=(0, 2)))
        ctx.console.print()

        ctx.console.print(_build_kpi_table(summary))
        ctx.console.print()
        ctx.console.print(render_hourly_chart(summary, height=4))
        ctx.console.print()
        ctx.console.print(render_daily_trend_chart(result.daily_trend, title="Tendance Journalière"))
        ctx.console.print()
        ctx.console.print(_build_top_tables_columns(result))
        ctx.console.print()
        ctx.console.print(_build_management_evolution_columns(ctx, result))
        ctx.console.print()
        footer_text = Text(no_wrap=True)
        footer_text.append("[r]", style=theme_registry.get_style("footer.key"))
        footer_text.append("afraîchir  ", style=theme_registry.get_style("footer.label"))
        footer_text.append("|  ", style=theme_registry.get_style("footer.separator"))
        footer_text.append("[t]", style=theme_registry.get_style("footer.key"))
        footer_text.append("hème  ", style=theme_registry.get_style("footer.label"))
        footer_text.append("|  ", style=theme_registry.get_style("footer.separator"))
        footer_text.append("[e]", style=theme_registry.get_style("footer.key"))
        footer_text.append("xporter HTML  ", style=theme_registry.get_style("footer.label"))
        footer_text.append("|  ", style=theme_registry.get_style("footer.separator"))
        footer_text.append("[Entrée]", style=theme_registry.get_style("footer.key"))
        footer_text.append(" Retour au menu", style=theme_registry.get_style("footer.label"))

        ctx.console.print(Panel(footer_text, border_style=style_border, box=ROUNDED, padding=(0, 2)))

    def do_export():
        try:
            from omega_fire.infrastructure.exporters.html_exporter import HtmlExporter
            from omega_fire.infrastructure.config.paths import EXPORTS_DIR, TEMPLATES_DIR
            from omega_fire.domain.reports.serializers import report_to_serializable

            # Prompt interactif — avant l'animation du spinner, pas pendant.
            theme_name = _prompt_html_theme(ctx, allow_cancel=True)

            with gauge_status(ctx.console, "Génération de l'export [HTML]..."):
                EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = EXPORTS_DIR / f"stats_report_{period_suffix}_{timestamp}.html"

                data = report_to_serializable(result.report)
                data["theme_name"] = theme_name

                exporter = HtmlExporter(templates_dir=TEMPLATES_DIR)
                exporter.export_data(data, output_path, template_name="stats_report.html.j2")

            ctx.console.print()
            ctx.console.print(_success(f"Rapport exporté : {output_path}"))
        except PromptCancelled:
            ctx.console.print()
            ctx.console.print(_muted("Export annulé."))
        except Exception as e:
            ctx.console.print()
            ctx.console.print(_error(f"Échec de l'export : {e}"))

    build_screen()

    while True:
        choice = ctx.console.input(_info("\nVotre choix ([r]afraîchir / [t]hème / [e]xporter / [Entrée] retour) : ")).strip().lower()

        if not choice:
            return
        elif choice == "r":
            build_screen()
        elif choice == "t":
            themes_list = []
            try:
                if hasattr(theme_registry, "get_available_themes"):
                    themes_list = list(theme_registry.get_available_themes())
                elif hasattr(theme_registry, "_themes"):
                    themes_list = list(theme_registry._themes.keys())
            except Exception:
                pass

            if themes_list:
                try:
                    current = theme_registry.get_active().name
                    next_idx = (themes_list.index(current) + 1) % len(themes_list) if current in themes_list else 0
                    theme_registry.set_active(themes_list[next_idx], silent=True)
                except Exception:
                    pass

            build_screen()
        elif choice == "e":
            do_export()
        else:
            ctx.console.print(_error("Choix invalide."))
def action_8_3_stats_7_days(ctx: ActionContext) -> None:
    """8.3 — Rapports statistiques (7 jours)."""
    def logic(out: List[Any]):
        _render_stats_report_screen(
            ctx,
            period_code="7d",
            period_label="7 jours",
            period_suffix="7j",
            title="RAPPORT STATISTIQUE — 7 JOURS",
        )
    _execute_action_flow(ctx, "8.3 Rapports statistiques (7 jours)", logic, pause_at_end=False)
def action_8_4_stats_30_days(ctx: ActionContext) -> None:
    """8.4 — Rapports statistiques (30 jours)."""
    def logic(out: List[Any]):
        _render_stats_report_screen(
            ctx,
            period_code="30d",
            period_label="30 jours",
            period_suffix="30j",
            title="RAPPORT STATISTIQUE — 30 JOURS",
        )
    _execute_action_flow(ctx, "8.4 Rapports statistiques (30 jours)", logic, pause_at_end=False)


# Épingles pour l'analyse lnav — mêmes serveurs web que DEFAULT_LIVE_TAIL_PINS
# (application/commands/manage_live_tail_pins.py) mais liste propre à 8.6 :
# access ET error log par backend, puisque lnav sait fusionner plusieurs
# fichiers en une seule vue (ce que 5.1 ne fait pas).
DEFAULT_LNAV_PINS: dict[str, str] = {
    "Nginx Access Log": "/var/log/nginx/access.log",
    "Nginx Error Log": "/var/log/nginx/error.log",
    "Apache Access Log": "/var/log/apache2/access.log",
    "Apache Error Log": "/var/log/apache2/error.log",
    "Lighttpd Access Log": "/var/log/lighttpd/access.log",
    "Lighttpd Error Log": "/var/log/lighttpd/error.log",
    "Caddy Access Log": "/var/log/caddy/access.log",
}


def action_8_6_lnav_analysis(ctx: ActionContext) -> None:
    """8.6 — Visualiser les logs serveurs avec lnav."""

    def logic(out: List[Any]):
        from rich.box import ROUNDED
        from pathlib import Path

        from omega_fire.infrastructure.storage.files.json_store import JsonStore
        from omega_fire.application.commands.manage_live_tail_pins import ManageLiveTailPinsCommand
        from omega_fire.infrastructure.config.paths import RUNTIME_DIR

        prompt_mgr = PromptManager(ctx.console)

        # ManageLiveTailPinsCommand n'a rien de spécifique au live tail (5.1) —
        # juste un CRUD générique pins+historique paramétré par ses defaults et
        # ses chemins de stockage. On l'instancie ici avec une liste et un
        # stockage propres à lnav, pour ne jamais mélanger les deux historiques.
        pins_command = ManageLiveTailPinsCommand(
            JsonStore(RUNTIME_DIR),
            defaults=DEFAULT_LNAV_PINS,
            custom_relative_path="lnav_custom_pins.json",
            disabled_relative_path="lnav_disabled_pins.json",
            history_relative_path="lnav_history.json",
        )

        active_pinned = pins_command.list_active_pinned()
        history = pins_command.list_history()

        style_border = theme_registry.get_style("border.default")
        style_heading = theme_registry.get_style("text.heading")
        style_main = theme_registry.get_style("text.main")
        style_muted = theme_registry.get_style("text.muted")

        ctx.console.print(_info("Sources de journaux disponibles — sélection multiple possible, lnav fusionne les fichiers choisis :"))
        ctx.console.print()

        source_table = Table(
            box=ROUNDED,
            border_style=style_border,
            header_style=style_heading,
            expand=True,
        )
        source_table.add_column("Choix", style=style_muted, justify="center", width=7)
        source_table.add_column("Type / Nom", style=style_heading, width=24)
        source_table.add_column("Chemin / Cible", style=style_main)

        display_items = {}
        idx = 1

        for name, path in active_pinned.items():
            key = str(idx)
            display_items[key] = {"type": "pinned", "name": name, "path": path}
            source_table.add_row(f"[{key}]", f"🖥 {name}", path)
            idx += 1

        for h_path in history[:5]:
            key = str(idx)
            display_items[key] = {"type": "history", "name": "Historique récent", "path": h_path}
            source_table.add_row(f"[{key}]", "🕒 Récent", h_path)
            idx += 1

        ctx.console.print(source_table)
        ctx.console.print(_info("  [M]   Saisie manuelle (un ou plusieurs chemins séparés par des virgules)"), highlight=False)
        ctx.console.print(_info("  [G]   Gestion des entrées (Créer / Supprimer / Purger)"), highlight=False)
        ctx.console.print()

        # Sélection multiple par virgules : même convention que le reste de
        # l'appli (3.2 suppression de règles, 4.2 ban/unban, 7.2 restauration —
        # toutes en `split(",")`, jamais de syntaxe de plage type "1-3").
        choice = ctx.console.input(
            _info("Sélectionnez une ou plusieurs sources (numéros séparés par des virgules, ou M/G, Entrée pour annuler) : ")
        ).strip()

        if not choice:
            ctx.console.print(_warning("Opération annulée."))
            return

        choice_upper = choice.upper()

        # ─── SOUS-MENU [G] : GESTION UNIFIÉE (identique à 5.1) ───
        if choice_upper == "G":
            ctx.console.print()
            ctx.console.print(_info("=== Gestion des Épingles & Historique (lnav) ==="))
            ctx.console.print(_info("  [1] 🖈 Ajouter une nouvelle épingle"), highlight=False)
            ctx.console.print(_info("  [2] ✖ Supprimer un élément du tableau (Épingle ou Historique)"), highlight=False)
            ctx.console.print(_info("  [3] 🕱 Purger tout le cache (Épingles & Historique)"), highlight=False)
            ctx.console.print(_info("  [0] ↩️  Annuler"), highlight=False)

            try:
                g_choice = prompt_mgr.ask_text(_info("\nChoix [1/2/3/0] : "), allow_cancel=True).strip()
            except PromptCancelled:
                g_choice = None

            if not g_choice:
                ctx.console.print(_muted("Opération annulée."))
                return

            if g_choice == "1":
                try:
                    name = prompt_mgr.ask_text(_info("Nom de l'épingle (ou 'annuler') : "), allow_cancel=True).strip()
                except PromptCancelled:
                    name = None
                if not name:
                    ctx.console.print(_muted("Ajout annulé."))
                    return
                try:
                    path = prompt_mgr.ask_text(_info("Chemin du fichier (ou 'annuler') : "), allow_cancel=True).strip()
                except PromptCancelled:
                    path = None
                if not path:
                    ctx.console.print(_muted("Ajout annulé."))
                    return

                add_result = pins_command.add_pinned(name, path)
                if add_result.success:
                    ctx.console.print(_success(add_result.message))
                else:
                    ctx.console.print(_error(add_result.message))

            elif g_choice == "2":
                if not display_items:
                    ctx.console.print(_warning("Le tableau est vide."))
                    return

                ctx.console.print(_info("\nÉléments actuellement présents dans le tableau :"))
                for num_key, item in display_items.items():
                    badge = "🖥" if item["type"] == "pinned" else "🕒"
                    ctx.console.print(_info(f"  [{num_key}] {badge} {item['name']} -> {item['path']}"), highlight=False)

                try:
                    del_num = prompt_mgr.ask_text(
                        _info("\nNuméro de l'élément à supprimer du tableau (ou 'annuler') : "),
                        allow_cancel=True,
                    ).strip()
                except PromptCancelled:
                    del_num = None
                if not del_num:
                    ctx.console.print(_muted("Suppression annulée."))
                    return

                if del_num in display_items:
                    target_item = display_items[del_num]

                    if target_item["type"] == "pinned":
                        remove_result = pins_command.remove_pinned(target_item["name"])
                    else:
                        remove_result = pins_command.remove_history_entry(target_item["path"])

                    if remove_result.success:
                        ctx.console.print(_success(f"L'entrée [{del_num}] ({target_item['path']}) a été supprimée !"))
                    else:
                        ctx.console.print(_error(remove_result.message))
                else:
                    ctx.console.print(_error("Numéro invalide."))

            elif g_choice == "3":
                pins_command.purge_all()
                ctx.console.print(_success("Historique et épingles lnav purgés avec succès !"))

            else:
                ctx.console.print(_error("Choix invalide."))

            return

        # ─── Résolution de la ou des sources ───
        resolved_paths: list[str] = []

        if choice_upper == "M":
            try:
                raw_manual = prompt_mgr.ask_text(
                    _info("\nEntrez un ou plusieurs chemins/URL HTTP, séparés par des virgules (ou 'annuler') : "),
                    allow_cancel=True,
                ).strip()
            except PromptCancelled:
                raw_manual = None
            if raw_manual:
                resolved_paths = [p.strip() for p in raw_manual.split(",") if p.strip()]
        else:
            raw_items = [item.strip() for item in choice.split(",") if item.strip()]
            invalid_entries = []
            for item in raw_items:
                if item in display_items:
                    resolved_paths.append(display_items[item]["path"])
                else:
                    invalid_entries.append(item)
            if invalid_entries:
                ctx.console.print(_warning(f"Numéro(s) ignoré(s), invalide(s) : {', '.join(invalid_entries)}"))

        if not resolved_paths:
            ctx.console.print(_warning("Aucune source valide sélectionnée. Opération annulée."))
            return

        # ─── Validation d'existence ───
        # lnav accepte aussi les chemins distants (http/https) tels quels
        # (confirmé : "logfileN The log files, directories, or remote
        # paths to view." dans `lnav --help`, et testé en conditions
        # réelles — lnav télécharge et parse correctement une URL HTTP).
        # Seuls les chemins locaux passent par la vérification d'existence.
        valid_paths: list[str] = []
        missing_paths: list[str] = []
        for p in resolved_paths:
            if p.startswith(("http://", "https://")) or Path(p).is_file():
                valid_paths.append(p)
            else:
                missing_paths.append(p)

        if missing_paths:
            ctx.console.print(_error(f"Fichier(s) introuvable(s), ignoré(s) : {', '.join(missing_paths)}"))

        if not valid_paths:
            ctx.console.print(_warning("Aucun fichier valide au final. Opération annulée."))
            return

        # ─── Mise à jour de l'historique (une entrée par nouveau chemin) ───
        known_paths = pins_command.list_all_known_paths()
        for p in valid_paths:
            if p not in known_paths:
                pins_command.record_history(p)

        # ─── Récapitulatif puis lancement ───
        ctx.console.print()
        ctx.console.print(_success(f"{len(valid_paths)} fichier(s) retenu(s) pour l'analyse lnav (fusion automatique) :"))
        for p in valid_paths:
            ctx.console.print(_info(f"  • {p}"), highlight=False)
        ctx.console.print()

        from omega_fire.interfaces.cli.renderers.lnav_live import render_lnav_live

        pause_prompt(ctx.console, "\nAppuyez sur [Entrée] pour lancer lnav (Ctrl-Q pour quitter une fois dedans)...")

        try:
            render_lnav_live([Path(p) for p in valid_paths], ctx.console)
        except FileNotFoundError:
            ctx.console.print(_error(
                "L'exécutable 'lnav' est introuvable (non installé ou absent du PATH). "
                "Sur Arch/EndeavourOS : sudo pacman -S lnav"
            ))

    _execute_action_flow(ctx, "8.6 Visualiser les logs serveurs (lnav)", logic)


# ----------------------------------------------------------------------
# Action Registry Class
# ----------------------------------------------------------------------
class ActionRegistry:
    """Registry of all available menu actions."""
    
    def __init__(self, capability_registry: Any):
        self.capability_registry = capability_registry
        self._actions: dict[str, Callable[[ActionContext], None]] = {
            "0": action_quit,
            "1.1": action_1_1_show_registry,
            "1.2": action_1_2_capability_detail,
            "1.3": action_1_3_rescan,
            "1.4": action_1_4_recent_diagnostics,
            "1.5": action_1_5_app_log,
            "1.6": action_1_6_search_diagnostics,
            "1.7": action_1_7_export_state,
            "2.1": action_2_1_ban_ip,
            "2.2": action_2_2_ban_list,
            "2.3": action_2_3_unban_ip,
            "2.4": action_2_4_unban_list,
            "2.5": action_2_5_list_banned,
            "2.6": action_2_6_sync_backends,
            "2.7": action_2_7_import_file,
            "2.8": action_2_8_export_file,
            "2.9": action_2_9_flush_backends,
            "3.1": action_3_1_create_advanced_rule,
            "3.2": action_3_2_delete_rule,
            "3.3": action_3_3_list_rules,
            "3.4": action_3_4_apply_preset,
            "4.1": action_4_1_jails_status,
            "4.2": action_4_2_jail_ban_unban,
            "4.3": action_4_3_jail_transfer,
            "4.4": action_4_4_create_jail,
            "4.5": action_4_5_delete_jail,
            "4.6": action_4_6_clear_jail,
            "4.7": action_4_7_purge_all_jails,
            "4.8": action_4_8_export_jail,
            "4.9": action_4_9_verify_config,
            "4.10": action_4_10_manage_fail2ban_service,
            "5.1": action_5_1_live_tail,
            "5.2": action_5_2_top_ips,
            "5.3": action_5_3_remove_ip_logs,
            "5.4": action_5_4_rotate_logs,
            "5.5": action_5_5_restore_backup,
            "5.6": action_5_6_purge_backups,
            "5.7": action_5_7_advanced_cleanup,
            "5.8": action_5_8_log_stats,
            "6.1": action_6_1_export_blacklist,
            "6.2": action_6_2_export_rules,
            "6.3": action_6_3_export_audit,
            "6.4": action_6_4_export_f2b_stats,
            "7.1": action_7_1_backup_state,
            "7.2": action_7_2_restore_state,
            "7.3": action_7_3_action_history,
            "7.4": action_7_4_reload_config,
            "8.1": action_8_1_live_dashboard,
            "8.2": action_8_2_conntrack_status,
            "8.3": action_8_3_stats_7_days,
            "8.4": action_8_4_stats_30_days,
            "8.6": action_8_6_lnav_analysis,
        }
    
    def get_action(self, menu_id: str) -> Optional[Callable[[ActionContext], None]]:
        """Get the action callable for a menu ID."""
        return self._actions.get(menu_id)
