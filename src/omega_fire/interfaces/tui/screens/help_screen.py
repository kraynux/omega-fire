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
from omega_fire.interfaces.tui.screens.contact_support import contact_support_screen
from omega_fire.shared.i18n import _

_SHORTCUTS = (
    (_("Haut / Bas"), _("Naviguer entre les éléments d'un écran")),
    (_("Tab / Maj+Tab"), _("Naviguer entre les champs d'un formulaire")),
    (_("Échap"), _("Retour à l'écran précédent (confirmation de sortie sur l'accueil)")),
    ("t", _("Thème suivant (appliqué immédiatement, sans confirmation)")),
    ("r", _("Rafraîchir la détection du terminal")),
    ("a", _("Cette aide")),
    ("q", _("Quitter (avec confirmation)")),
)

_SECTIONS = (
    (_("1. Capacités & diagnostics"), _("Registre des composants système détectés, diagnostics, journal applicatif.")),
    (_("2. Gestion des IPs"), _("Bannissement/débannissement unifié (nftables/iptables/fail2ban), import/export.")),
    (_("3. Gestion des règles"), _("Règles de filtrage avancées, politiques pré-définies par backend.")),
    (_("4. Gestion Fail2ban"), _("Jails, transferts d'IPs, service Fail2ban.")),
    (_("5. Gestion des logs"), _("Analyse des logs, rotation, restauration, nettoyage.")),
    (_("6. Exports & rapports"), _("Exports de la blacklist, des règles, rapports d'audit.")),
    (_("7. Système & persistance"), _("Sauvegarde/restauration d'état complet, historique des actions.")),
    (_("8. Monitoring & statistiques"), _("Tableau de bord temps réel, conntrack, statistiques.")),
)


class HelpScreen(OmegaScreen):
    """Reference generique, accessible depuis n'importe quel ecran (touche
    `a`) — precedee du contenu contextuel de l'ecran courant quand celui-ci
    en fournit un (voir OmegaScreen.help_content(), redefini par
    SectionScreen/HomeScreen : retour utilisateur reel, l'aide doit
    refleter le menu en cours, pas seulement une reference statique)."""

    def __init__(self, *, context: tuple[str, str] | None = None, container: object | None = None) -> None:
        super().__init__()
        # Contact et support (omega-lib, D-016, 2026-11-09) : services prepares par le conteneur ;
        # absents (bouton masque) si l'aide est ouverte sans conteneur.
        self._contact_support = getattr(container, "contact_support", None)
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
            yield Static(_("AIDE"), classes="omega-title")
            if self._help_context is not None:
                context_title, context_body = self._help_context
                yield Static(context_title, classes="omega-subtitle")
                yield Static(context_body)
                yield Static("")
            yield Static(_("Raccourcis clavier"), classes="omega-subtitle")
            for key, description in _SHORTCUTS:
                yield Static(_("{key:<14} {description}").format(key=key, description=description))
            yield Static("")
            yield Static(_("Sections"), classes="omega-subtitle")
            for title, description in _SECTIONS:
                yield Static(_("[b]{title}[/b]\n{description}\n").format(title=title, description=description))
            with Horizontal(classes="omega-actions"):
                if hasattr(self.app, "action_open_guide"):
                    with Container(classes="omega-btn-frame"):
                        yield Button(_("Guide d'aide complet"), id="guide", variant="primary")
                if self._contact_support is not None:
                    with Container(classes="omega-btn-frame"):
                        yield Button(_("Contact et support"), id="contact-support")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
        elif event.button.id == "contact-support" and self._contact_support is not None:
            self.app.push_screen(contact_support_screen(self._contact_support))
        elif event.button.id == "guide":
            self.dismiss()
            self.app.action_open_guide()
