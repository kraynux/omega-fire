# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Audit logger.

Provides a specialized logger for audit events. Writes to a separate
audit log file with a structured format suitable for security auditing
and compliance.

This module performs file I/O to write audit logs and is therefore
in infrastructure/.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List

from omega_fire.ports.audit import AuditPort, AuditEntry, AuditLevel
from omega_fire.infrastructure.config.paths import AUDIT_LOG_PATH, LOGS_DIR

class AuditLogger(AuditPort):
    """Specialized logger for audit events.

    Writes structured audit events to a separate log file.
    Each event includes timestamp, event type, actor, action,
    and result.
    """

    def __init__(self, name: str = "omega_fire.audit", log_dir: Optional[Path] = None):
        """Initialize the audit logger.

        Args:
            name: Logger name (default: omega_fire.audit)
            log_dir: Optional directory path for log files
        """
        self._logger = logging.getLogger(name)
        self.log_dir = log_dir or LOGS_DIR
        self.log_file = AUDIT_LOG_PATH

        # Configuration de l'écriture automatique sur disque
        self._setup_file_handler()

    def _setup_file_handler(self) -> None:
        """Initialise le dossier et le FileHandler pour l'écriture sur le disque."""
        self._logger.setLevel(logging.INFO)
        # Empêche les événements d'audit de remonter dans app.log
        self._logger.propagate = False
        # Vérifie si le FileHandler est déjà présent pour éviter les doublons d'écriture
        has_file_handler = any(isinstance(h, logging.FileHandler) for h in self._logger.handlers)

        if not has_file_handler:
            try:
                # 1. Création automatique du dossier de destination (ex: var/logs)
                self.log_dir.mkdir(parents=True, exist_ok=True)

                # 2. Création du handler d'écriture sur le fichier audit.log
                file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
                
                # Format brut : on écrit uniquement le JSON sur chaque ligne
                formatter = logging.Formatter("%(message)s")
                file_handler.setFormatter(formatter)

                self._logger.addHandler(file_handler)
            except Exception:
                # Fallback silencieux en cas de problème de permission
                pass

    # ------------------------------------------------------------------
    # Implémentation des méthodes du contrat AuditPort
    # ------------------------------------------------------------------

    def log(
        self,
        action: str,
        actor: str,
        target: str,
        *,
        level: AuditLevel = AuditLevel.INFO,
        details: Optional[dict] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """Enregistre un événement d'audit conforme au contrat AuditPort."""
        result = "success" if success else "failure"
        evt_details = details or {}
        if error_message:
            evt_details["error"] = error_message
        evt_details["target"] = target

        self.log_event(
            event_type=level.value,
            actor=actor,
            action=action,
            result=result,
            details=evt_details,
        )

    def get_recent(self, limit: int = 50) -> List[AuditEntry]:
        """Récupère les N plus récentes entrées d'audit pour l'affichage UI."""
        entries: List[AuditEntry] = []

        # Si aucun handler fichier n'est configuré ou que le fichier n'existe pas
        if not self.log_file.exists():
            return entries

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in reversed(lines[-limit:]):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    dt = datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat()))
                    level = AuditLevel.INFO
                    success = data.get("result") == "success"

                    entries.append(
                        AuditEntry(
                            timestamp=dt,
                            level=level,
                            action=data.get("action", "unknown"),
                            actor=data.get("actor", "system"),
                            target=data.get("details", {}).get("target", "N/A"),
                            details=data.get("details"),
                            success=success,
                            error_message=data.get("details", {}).get("error"),
                        )
                    )
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass

        return entries

    def get_all_since(self, since: Optional[datetime] = None) -> List[AuditEntry]:
        """Récupère toutes les entrées d'audit depuis une date donnée.

        Contrairement à get_recent()/search(), ne s'arrête pas à une
        limite fixe de nombre de lignes — nécessaire pour les rapports
        d'audit qui couvrent une période longue (menu 6.3), où le
        nombre d'événements pertinents peut largement dépasser 50.

        Args:
            since: date à partir de laquelle inclure les entrées. Si
                None, retourne tout le fichier depuis le début.

        Returns:
            Liste de AuditEntry, dans l'ordre chronologique (plus
            ancien en premier), contrairement à get_recent() qui
            retourne du plus récent au plus ancien.
        """
        entries: List[AuditEntry] = []

        if not self.log_file.exists():
            return entries

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        dt = datetime.fromisoformat(
                            data.get("timestamp", datetime.now().isoformat())
                        )

                        if since is not None and dt < since:
                            continue

                        success = data.get("result") == "success"

                        entries.append(
                            AuditEntry(
                                timestamp=dt,
                                level=AuditLevel.INFO,
                                action=data.get("action", "unknown"),
                                actor=data.get("actor", "system"),
                                target=data.get("details", {}).get("target", "N/A"),
                                details=data.get("details"),
                                success=success,
                                error_message=data.get("details", {}).get("error"),
                            )
                        )
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

        return entries

    def search(
        self,
        *,
        action: Optional[str] = None,
        actor: Optional[str] = None,
        target: Optional[str] = None,
        level: Optional[AuditLevel] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Recherche des entrées d'audit."""
        recent = self.get_recent(limit=limit)
        filtered = []
        for e in recent:
            if action and action.lower() not in e.action.lower():
                continue
            if actor and actor.lower() not in e.actor.lower():
                continue
            if target and target.lower() not in e.target.lower():
                continue
            filtered.append(e)
        return filtered

    def clear(self, older_than: Optional[datetime] = None) -> int:
        """Purge les entrées d'audit.

        If older_than is provided, only entries strictly BEFORE that
        date are removed — entries from older_than onward are kept and
        rewritten to the file. If older_than is None, the file is
        wiped entirely (previous behavior, still correct for that
        specific case).

        Returns:
            Number of entries actually removed.
        """
        if not self.log_file.exists():
            return 0

        if older_than is None:
            try:
                self.log_file.write_text("")
                return 1
            except Exception:
                return 0

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return 0

        kept_lines = []
        removed_count = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
                dt = datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat()))
            except (json.JSONDecodeError, ValueError):
                # Ligne corrompue/illisible : conservée par précaution
                # plutôt que supprimée silencieusement sans certitude
                # sur sa date réelle.
                kept_lines.append(line)
                continue

            if dt < older_than:
                removed_count += 1
            else:
                kept_lines.append(line)

        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.writelines(kept_lines)
        except Exception:
            return 0

        return removed_count

    def delete_oldest(self, count: int) -> int:
        """Supprime les N entrées les plus anciennes, conserve le reste.

        Parses every line to get accurate chronological ordering
        (append order in the file already matches write order, but
        parsing timestamps explicitly avoids any assumption about file
        ordering being preserved through prior edits).

        Returns:
            Number of entries actually removed.
        """
        if count <= 0 or not self.log_file.exists():
            return 0

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return 0

        parsed: list[tuple[datetime, str]] = []
        unparseable: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
                dt = datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat()))
                parsed.append((dt, line))
            except (json.JSONDecodeError, ValueError):
                # Conservée par précaution, jamais comptée parmi les
                # "plus anciennes" faute de date fiable.
                unparseable.append(line)

        parsed.sort(key=lambda item: item[0])

        to_remove = min(count, len(parsed))
        kept_lines = [line for _, line in parsed[to_remove:]] + unparseable

        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.writelines(kept_lines)
        except Exception:
            return 0

        return to_remove

    # ------------------------------------------------------------------
    # Méthodes spécialisées
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Méthodes spécialisées
    # ------------------------------------------------------------------

    def log_event(
        self,
        event_type: str,
        actor: str,
        action: str,
        result: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log an audit event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "actor": actor,
            "action": action,
            "result": result,
            "details": details or {},
        }

        self._logger.info(json.dumps(event, ensure_ascii=False))
        for handler in self._logger.handlers:
            handler.flush()
            
    def log_ban(
        self,
        ip: str,
        backend: str,
        actor: str = "user",
        result: str = "success",
        comment: str = "",
    ) -> None:
        self.log_event(
            event_type="ban",
            actor=actor,
            action=f"ban_ip:{ip}",
            result=result,
            details={"backend": backend, "comment": comment},
        )

    def log_unban(
        self,
        ip: str,
        backend: str,
        actor: str = "user",
        result: str = "success",
    ) -> None:
        self.log_event(
            event_type="unban",
            actor=actor,
            action=f"unban_ip:{ip}",
            result=result,
            details={"backend": backend},
        )

    def log_rule_change(
        self,
        action: str,
        backend: str,
        actor: str = "user",
        result: str = "success",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.log_event(
            event_type="rule_change",
            actor=actor,
            action=f"rule_{action}",
            result=result,
            details={"backend": backend, **(details or {})},
        )

    def log_sync(
        self,
        source: str,
        destination: str,
        actor: str = "user",
        result: str = "success",
        count: int = 0,
    ) -> None:
        self.log_event(
            event_type="sync",
            actor=actor,
            action=f"sync:{source}->{destination}",
            result=result,
            details={"count": count},
        )

    def log_export(
        self,
        format: str,
        path: str,
        actor: str = "user",
        result: str = "success",
    ) -> None:
        self.log_event(
            event_type="export",
            actor=actor,
            action=f"export:{format}",
            result=result,
            details={"path": path},
        )

    def log_backup(
        self,
        path: str,
        actor: str = "user",
        result: str = "success",
    ) -> None:
        self.log_event(
            event_type="backup",
            actor=actor,
            action="backup:create",
            result=result,
            details={"path": path},
        )

    def log_restore(
        self,
        path: str,
        actor: str = "user",
        result: str = "success",
    ) -> None:
        self.log_event(
            event_type="restore",
            actor=actor,
            action="backup:restore",
            result=result,
            details={"path": path},
        )

    def get_logger(self) -> logging.Logger:
        return self._logger


def get_audit_logger() -> AuditLogger:
    return AuditLogger()


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Fournit un logger spécialisé pour les événements d'audit
# - Adaptateur concrètement connecté au port AuditPort.
# - Écrit dans un fichier séparé avec un format structuré JSON
# - Logue les événements sous forme JSON structurée via logging Python standard.
# - Implémente get_recent() pour permettre la lecture du journal par application/ queries.
# - Méthodes de convenance pour les événements courants (ban, unban, sync, etc.)
# - Conserve toutes les méthodes spécialisées (log_ban, log_unban, etc.).
# Pourquoi dans infrastructure/logging/ (charte) :
# - C'est de l'infrastructure technique (logging d'audit)
# - Le domaine ne doit pas connaître le système de logging
# - L'application/ utilise AuditLogger via injection
# - Accès aux fichiers I/O et au logger natif Python.
# - Respecte le contrat AuditPort sans que le cœur connaisse le fichier réel.
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# ❌ Pas de décision de quoi logger (c'est le rôle des composants)
# Points clés :
# - AuditLogger : classe principale avec log_event() générique
# - Méthodes spécialisées : log_ban(), log_unban(), log_rule_change(),
#   log_sync(), log_export(), log_backup(), log_restore()
# - Format JSON structuré : timestamp, event_type, actor, action, result, details
# - Chaque événement est sérialisé en JSON pour faciliter l'analyse
# - get_logger() : retourne le logger Python sous-jacent
# - Fonction de convenance : get_audit_logger()
# - get_all_since() : lit TOUT le fichier (pas de limite fixe comme
#   get_recent()), filtré optionnellement par date — utilisé par le
#   rapport d'audit (menu 6.3) qui doit couvrir une période longue.
# - clear(older_than=...) : CORRIGÉ — honore désormais réellement le
#   paramètre older_than (ne réécrit que les entrées postérieures),
#   au lieu de vider tout le fichier inconditionnellement comme avant.
# - delete_oldest(count) : nouvelle méthode, purge par VOLUME (les N
#   plus anciennes) plutôt que par ÂGE — complète clear() pour le
#   menu 7.3.
# Comment il sera utilisé (aperçu) :
# - application/pipeline/hooks/audit_hook.py l'utilisera pour logger les événements
# - Tous les cas d'usage importants loggeront leurs actions via AuditLogger
# - Les tests mockeront AuditLogger pour vérifier les appels
#---------------------------------------------------------------------->
