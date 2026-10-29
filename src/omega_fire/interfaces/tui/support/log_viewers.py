# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ouverture d'un lecteur de logs sur des chemins donnes (5.2 Favoris, 5.3 Voir les logs),
a appeler depuis un gestionnaire de clic (lnav y est lance directement).
Le garde-fou (2 logs ou plus -> lnav seul) est verifie ici aussi : jamais une troncature."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from omega_fire.domain.logs.viewer_type import ViewerType, allowed_viewers
from omega_fire.shared.i18n import _


def open_viewer(app: Any, container: Any, viewer: ViewerType, paths: list[str]) -> bool:
    if not paths:
        app.notify(_("Sélectionnez au moins un log."), severity="warning")
        return False
    if viewer not in allowed_viewers(len(paths)):
        app.notify(_("{count} logs sélectionnés : seul lnav peut les ouvrir ensemble.").format(count=len(paths)),
                   severity="warning")
        return False
    if viewer is ViewerType.SIMPLE:
        from omega_fire.interfaces.tui.screens.live_tail_screen import LiveTailScreen
        app.push_screen(LiveTailScreen(container=container, source=paths[0]))
    elif viewer is ViewerType.CLASSIC:
        from omega_fire.interfaces.tui.screens.log_classic_viewer_screen import LogClassicViewerScreen
        app.push_screen(LogClassicViewerScreen(container=container, path=paths[0]))
    else:
        # Lance depuis le clic lui-meme (comme 8.6), jamais a l'ouverture d'un ecran : sinon
        # l'interface se bloquait (retour utilisateur 2026-10-28).
        from omega_fire.interfaces.tui.screens.lnav_screen import run_lnav
        existing = [p for p in paths if Path(p).is_file()]
        missing = [p for p in paths if p not in existing]
        if missing:
            app.notify(_("Fichier(s) introuvable(s), ignoré(s) : {value}").format(value=", ".join(missing)),
                       severity="warning")
        if not existing:
            return False
        try:
            run_lnav(app, existing)
        except FileNotFoundError:
            app.notify(_("L'exécutable 'lnav' est introuvable (non installé ou absent du PATH). "
                         "Sur Arch/EndeavourOS : sudo pacman -S lnav"), severity="error")
            return False
        except Exception as e:
            app.notify(_("Échec du lancement de lnav : {e}").format(e=e), severity="error")
            return False
    return True


def viewer_label(viewer: ViewerType) -> str:
    return {ViewerType.SIMPLE: _("Simple"), ViewerType.CLASSIC: _("Classique"), ViewerType.LNAV: "lnav"}[viewer]
