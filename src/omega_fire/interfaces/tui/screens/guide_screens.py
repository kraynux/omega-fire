# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Guide d'aide (version 3.5, « comme omega-serv ») : menu du guide (toutes les fiches,
dans l'ordre des menus), fiche detaillee avec ses liens « Voir aussi », FAQ, export HTML
de tout le guide avec la FAQ (theme au choix), ou de la FAQ seule. Ouvert par le bouton « 10. AIDE » de l'accueil et depuis
l'aide generique ; la touche `a` reste l'aide de l'ecran courant."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Footer, Header, Select, Static

from omega_fire.interfaces.tui.export_language import export_translation
from omega_fire.interfaces.tui.screens._base import OmegaScreen, format_help_entry
from omega_fire.interfaces.tui.screens.export_blacklist_screen import _HTML_THEMES
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.interfaces.tui.support.guide import GuidePage, guide_pages, page_by_id
from omega_fire.interfaces.tui.support.guide_faq import FaqEntry, faq_entries
from omega_fire.shared.i18n import _, translating_as

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "10 Guide d'aide"
GUIDE_EXPORT_PREFIX = "guide-aide_"


def page_body(page: GuidePage) -> str:
    """Texte (markup Rich) d'une fiche — meme rendu que la touche `a`."""
    if page.entry is not None:
        return format_help_entry(page.entry)
    if page.lines:
        return "\n".join(f"{key:<14} {description}" for key, description in page.lines)
    return page.text or _("Pas encore de fiche détaillée pour cette action.")


class GuideMenuScreen(OmegaScreen):
    CSS = """
    GuideMenuScreen #guide-table {
        height: 1fr;
    }

    GuideMenuScreen #guide-export {
        width: 100%;
        height: auto;
        align: left middle;
    }

    GuideMenuScreen #guide-theme {
        width: 1fr;
        max-width: 64;
    }

    GuideMenuScreen #guide-actions {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 0;
    }
    """

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._pages = guide_pages()

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static(_("GUIDE D'AIDE"), classes="omega-title")
            yield Static(
                _("Toutes les fiches d'aide d'Omega-Fire, dans l'ordre des menus. Entrée : ouvrir la "
                  "fiche. Depuis n'importe quel écran, la touche `a` ouvre la fiche de cet écran."),
                classes="omega-hint",
            )
            with Horizontal(id="guide-export", classes="omega-actions"):
                yield Select([(label, name) for name, label in _HTML_THEMES.items()], value="omega-base",
                             id="guide-theme", allow_blank=False)
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Exporter le guide en HTML"), id="export-html")
            yield DataTable(id="guide-table")
        with Horizontal(classes="omega-actions", id="guide-actions"):
            with Container(classes="omega-btn-frame"):
                yield Button(_("Ouvrir"), id="open", variant="primary")
            # FAQ dans la barre du bas : sur la ligne du theme, elle sortait de l'ecran une
            # fois traduite (russe, allemand) a 100 colonnes.
            with Container(classes="omega-btn-frame"):
                yield Button(_("FAQ"), id="faq")
            with Container(classes="omega-btn-frame"):
                yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#guide-table", DataTable)
        table.cursor_type = "row"
        table.add_columns(_("Section"), _("Fiche"))
        previous = None
        for index, page in enumerate(self._pages):
            # Le nom de section n'est ecrit qu'une fois par groupe : lecture en arborescence.
            section = page.section if page.section != previous else ""
            previous = page.section
            table.add_row(section, page.title, key=str(index))
        table.focus()

    def _open_highlighted(self) -> None:
        table = self.query_one("#guide-table", DataTable)
        row = table.cursor_row
        if row is not None and 0 <= row < len(self._pages):
            self.app.push_screen(GuideDetailScreen(self._pages[row], pages=self._pages))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._open_highlighted()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
        elif event.button.id == "open":
            self._open_highlighted()
        elif event.button.id == "export-html":
            export_guide_html(self, self._container, str(self.query_one("#guide-theme", Select).value))
        elif event.button.id == "faq":
            self.app.push_screen(FaqScreen(container=self._container,
                                           theme_name=str(self.query_one("#guide-theme", Select).value)))


def export_guide_html(screen: OmegaScreen, container: DependencyContainer, theme_name: str,
                      *, faq_only: bool = False) -> None:
    """Guide complet (fiches + FAQ) ou FAQ seule, dans le dossier d'exports (visible en 6.6),
    dans la « Langue des exports » des Reglages comme les autres exports (retour utilisateur
    2026-10-28 : guide et FAQ sortaient toujours dans la langue de l'interface)."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = "faq" if faq_only else "guide"
    path = container.exports_dir / f"{GUIDE_EXPORT_PREFIX}{name}_{timestamp}.html"
    export_state = export_translation(screen, container)

    def write() -> None:
        with translating_as(export_state):
            # Fiches, titres et FAQ reconstruits ICI, sous la langue des exports.
            context = guide_html_context([] if faq_only else guide_pages(), theme_name,
                                         datetime.now().strftime("%Y-%m-%d %H:%M:%S"), faq=faq_entries(),
                                         faq_only=faq_only)
            container.get_exporter_port("html").export_data(context, path, template_name="guide.html.j2")

    def done(_result: None) -> None:
        message = _("FAQ exportée : {path} (visible en 6.6).") if faq_only else \
            _("Guide exporté : {path} (visible en 6.6).")
        screen.app.notify(message.format(path=path), timeout=8)
        log_action_result(container, _ACTION_TITLE, status="success")

    def failed(error: Exception) -> None:
        screen.app.notify(_("Erreur lors de l'écriture du fichier d'export : {e}").format(e=error),
                          severity="error")
        log_action_result(container, _ACTION_TITLE, status="failure", error=str(error))

    screen.run_blocking(write, done, busy_message=_("Export du guide en cours..."), on_error=failed)


def guide_html_context(pages: list[GuidePage], theme_name: str, generated_at: str,
                       faq: tuple[FaqEntry, ...] = (), faq_only: bool = False) -> dict:
    """Donnees du modele guide.html.j2 : sections dans l'ordre, fiches avec leurs rubriques,
    puis la FAQ groupee par categorie (ordre de redaction)."""
    sections: list[dict] = []
    for page in pages:
        if not sections or sections[-1]["title"] != page.section:
            sections.append({"title": page.section, "pages": []})
        entry = page.entry
        sections[-1]["pages"].append({
            "anchor": "p-" + page.page_id.replace(".", "-"),
            "title": page.title,
            "summary": _(entry.summary) if entry else page.text,
            "usage": [_(text) for text in entry.usage] if entry else [],
            "consequences": [_(text) for text in entry.consequences] if entry else [],
            "warnings": [_(text) for text in entry.warnings] if entry else [],
            "mechanism": _(entry.mechanism) if entry and entry.mechanism else "",
            "see_also": [("p-" + ref.replace(".", "-"), ref) for ref in (entry.see_also if entry else [])],
            "lines": list(page.lines),
        })
    faq_groups: list[dict] = []
    for index, item in enumerate(faq):
        if not faq_groups or faq_groups[-1]["title"] != item.category:
            faq_groups.append({"title": item.category, "entries": []})
        faq_groups[-1]["entries"].append({"anchor": f"faq-{index + 1}", "question": item.question,
                                          "answer": item.answer})
    return {
        "page_title": _("FAQ - Omega-Fire") if faq_only else _("Guide d'aide - Omega-Fire"),
        "heading": _("FAQ Omega-Fire") if faq_only else _("Guide d'aide Omega-Fire"),
        "faq_title": _("FAQ"),
        "faq_groups": faq_groups,
        "generated_at": generated_at,
        "theme_name": theme_name,
        "sections": sections,
        "labels": {
            "contents": _("Sommaire"), "usage": _("Comment l'utiliser"),
            "consequences": _("Conséquences"), "warnings": _("À savoir"), "see_also": _("Voir aussi"),
        },
    }


class GuideDetailScreen(OmegaScreen):
    """Une fiche du guide ; « Voir aussi » ouvre les fiches liees."""

    CSS = """
    GuideDetailScreen #guide-detail-actions {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 0;
    }
    """

    def __init__(self, page: GuidePage, *, pages: list[GuidePage] | None = None) -> None:
        super().__init__()
        self._page = page
        self._pages = pages or guide_pages()

    def compose(self) -> ComposeResult:
        page = self._page
        yield Header()
        with VerticalScroll(classes="omega-panel"):
            yield Static(page.title.upper(), classes="omega-title")
            yield Static(page.section, classes="omega-hint")
            yield Static("")
            yield Static(page_body(page))
        links = [ref for ref in (page.entry.see_also if page.entry else []) if page_by_id(ref, self._pages)]
        with Horizontal(classes="omega-actions", id="guide-detail-actions"):
            for ref in links:
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Voir {ref}").format(ref=ref), id=f"see-{ref.replace('.', '-')}")
            with Container(classes="omega-btn-frame"):
                yield Button(_("Retour"), id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "back":
            self.dismiss()
        elif button_id.startswith("see-"):
            target = page_by_id(button_id.removeprefix("see-").replace("-", "."), self._pages)
            if target is not None:
                self.app.push_screen(GuideDetailScreen(target, pages=self._pages))


class FaqScreen(OmegaScreen):
    """FAQ du guide : questions groupees par categorie, export HTML de la FAQ seule."""

    CSS = """
    FaqScreen #faq-actions {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 0;
    }
    """

    def __init__(self, *, container: DependencyContainer, theme_name: str = "omega-base") -> None:
        super().__init__()
        self._container = container
        self._theme_name = theme_name

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-panel"):
            yield Static(_("FAQ"), classes="omega-title")
            category = None
            for item in faq_entries():
                if item.category != category:
                    category = item.category
                    yield Static("")
                    yield Static(category.upper(), classes="omega-subtitle")
                yield Static("")
                yield Static(_("[b]Q. {question}[/b]").format(question=item.question))
                yield Static(_("R. {answer}").format(answer=item.answer))
        with Horizontal(classes="omega-actions", id="faq-actions"):
            with Container(classes="omega-btn-frame"):
                yield Button(_("Exporter la FAQ en HTML"), id="export-faq")
            with Container(classes="omega-btn-frame"):
                yield Button(_("Retour"), id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
        elif event.button.id == "export-faq":
            export_guide_html(self, self._container, self._theme_name, faq_only=True)
