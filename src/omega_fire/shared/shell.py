# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Wrapper générique pour exécuter des commandes shell."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from omega_fire.shared.exceptions import ShellCommandError


@dataclass(frozen=True, slots=True)
class ShellResult:
    """Résultat d'une commande shell.

    Attributs:
        return_code: code de retour du processus (0 = succès).
        stdout: sortie standard capturée (texte).
        stderr: sortie d'erreur capturée (texte).
        command: commande exécutée (liste ou chaîne).
    """

    return_code: int
    stdout: str
    stderr: str
    command: str | list[str]

    @property
    def success(self) -> bool:
        """True si le code de retour est 0."""
        return self.return_code == 0

    def raise_if_failed(self, context: str = "") -> None:
        """Lève ShellCommandError si la commande a échoué.

        Args:
            context: contexte optionnel pour le message d'erreur.
        """
        if not self.success:
            msg = f"Commande échouée (rc={self.return_code})"
            if context:
                msg = f"{context}: {msg}"
            raise ShellCommandError(
                msg,
                command=self.command,
                return_code=self.return_code,
                stdout=self.stdout,
                stderr=self.stderr,
            )


def run_shell(
    command: str | list[str],
    *,
    check: bool = False,
    timeout: float | None = None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> ShellResult:
    """Exécute une commande shell et retourne le résultat.

    Args:
        command: commande à exécuter (chaîne ou liste).
        check: si True, lève ShellCommandError si rc != 0.
        timeout: timeout en secondes (None = pas de timeout).
        cwd: répertoire de travail (None = courant).
        env: variables d'environnement (None = hérite).
        input_text: texte à envoyer sur stdin (optionnel).

    Returns:
        ShellResult avec return_code, stdout, stderr, command.

    Raises:
        ShellCommandError: si check=True et rc != 0, ou si timeout dépassé.
    """
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
            input=input_text,
            check=False,  # On gère nous-mêmes les erreurs
        )
        result = ShellResult(
            return_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            command=command,
        )
        if check:
            result.raise_if_failed()
        return result

    except subprocess.TimeoutExpired as exc:
        raise ShellCommandError(
            f"Timeout dépassé ({timeout}s)",
            command=command,
            return_code=None,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
        ) from exc
    except FileNotFoundError as exc:
        raise ShellCommandError(
            f"Commande introuvable: {command!r}",
            command=command,
            return_code=None,
        ) from exc
    except OSError as exc:
        raise ShellCommandError(
            f"Erreur OS lors de l'exécution: {exc}",
            command=command,
            return_code=None,
        ) from exc

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Fournit un wrapper générique pour exécuter des commandes shell via subprocess.
# - Retourne un ShellResult (dataclass frozen) avec return_code, stdout, stderr.
# - Gère les erreurs : timeout, commande introuvable, OSError.
#
# Pourquoi dans shared/ (charte) :
# - C'est un utilitaire technique transversal, non métier
# - Utilisé par infrastructure/backends/ (nftables, iptables, fail2ban)
# - Utilisé par infrastructure/probe/ (détection système)
# - Aucun lien avec une règle firewall, fail2ban, logs, blacklist
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de logique métier (ex: parsing spécifique nftables)
# ❌ Pas de décision d'exécution (c'est le rôle de application/pipeline/)
# ❌ Pas de gestion de capacités (c'est le rôle de core/capability_registry.py)
#
# Points clés :
# - ShellResult : dataclass frozen avec return_code, stdout, stderr, command
# - ShellResult.success : propriété True si rc == 0
# - ShellResult.raise_if_failed() : lève ShellCommandError si échec
# - run_shell() : exécute une commande avec options (check, timeout, cwd, env)
# - run_shell() capture stdout/stderr en texte (pas bytes)
# - run_shell() gère TimeoutExpired, FileNotFoundError, OSError
# - Si check=True, lève automatiquement ShellCommandError si rc != 0
#
# Comment il sera utilisé (aperçu) :
# - infrastructure/backends/nftables/adapter.py appellera run_shell(["nft", "list"])
# - infrastructure/backends/fail2ban/adapter.py appellera run_shell(["fail2ban-client", "status"])
# - infrastructure/probe/command_probe.py utilisera run_shell() pour tester binaires
# - infrastructure/probe/service_probe.py utilisera run_shell() pour tester services
# - infrastructure/ encapsulera les ShellCommandError en BackendError (charte)
#---------------------------------------------------------------------->        
