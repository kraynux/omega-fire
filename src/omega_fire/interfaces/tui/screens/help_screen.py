# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran Aide : reference statique des raccourcis et sections de
l'application. Adapte du patron screens/help_screen.py d'omega-check
(D-008) — memes raccourcis (deja identiques a ceux d'omega-fire, voir
interfaces/cli/keybindings.py), contenu propre a omega-fire pour les
sections de menu."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Button, Footer, Header, Static

from omega_fire.interfaces.tui.screens._base import OmegaScreen

_SHORTCUTS = (
    ("Haut / Bas", "Naviguer entre les elements d'un ecran"),
    ("Tab / Maj+Tab", "Naviguer entre les champs d'un formulaire"),
    ("Echap", "Retour a l'ecran precedent (confirmation de sortie sur l'accueil)"),
    ("t", "Theme suivant (applique immediatement, sans confirmation)"),
    ("r", "Rafraichir la detection du terminal"),
    ("a", "Cette aide"),
    ("q", "Quitter (avec confirmation)"),
)

_SECTIONS = (
    ("1. Etat des capacites & diagnostics", "Registre des composants systeme detectes, diagnostics, journal applicatif."),
    ("2. Gestion des IPs", "Bannissement/debannissement unifie (nftables/iptables/fail2ban), import/export."),
    ("3. Gestion des regles", "Regles de filtrage avancees, politiques pre-definies par backend."),
    ("4. Gestion Fail2ban", "Jails, transferts d'IPs, service Fail2ban."),
    ("5. Gestion des logs", "Analyse des logs, rotation, restauration, nettoyage."),
    ("6. Exports & rapports", "Exports de la blacklist, des regles, rapports d'audit."),
    ("7. Systeme & persistance", "Sauvegarde/restauration d'etat complet, historique des actions."),
    ("8. Monitoring & statistiques", "Tableau de bord temps reel, conntrack, statistiques."),
)


class HelpScreen(OmegaScreen):
    """Reference generique, accessible depuis n'importe quel ecran (touche
    `a`) — precedee du contenu contextuel de l'ecran courant quand celui-ci
    en fournit un (voir OmegaScreen.help_content(), redefini par
    SectionScreen/HomeScreen : retour utilisateur reel, l'aide doit
    refleter le menu en cours, pas seulement une reference statique)."""

    def __init__(self, *, context: tuple[str, str] | None = None) -> None:
        super().__init__()
        # ATTENTION : `_context` (sans prefixe distinct) collide avec
        # MessagePump._context, une methode PRIVEE de Textual utilisee
        # par _process_messages() ("with self._context():") — l'ecraser
        # ici cassait silencieusement tout traitement de message sur cet
        # ecran (gel total au premier `a`, bug reel decouvert en testant
        # cette fonctionnalite). D'ou le nom `_help_context`, jamais
        # `_context` seul, sur un Widget/Screen Textual.
        self._help_context = context

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-panel"):
            yield Static("AIDE", classes="omega-title")
            if self._help_context is not None:
                context_title, context_body = self._help_context
                yield Static(context_title, classes="omega-subtitle")
                yield Static(context_body)
                yield Static("")
            yield Static("Raccourcis clavier", classes="omega-subtitle")
            for key, description in _SHORTCUTS:
                yield Static(f"{key:<14} {description}")
            yield Static("")
            yield Static("Sections", classes="omega-subtitle")
            for title, description in _SECTIONS:
                yield Static(f"[b]{title}[/b]\n{description}\n")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button("Retour", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
