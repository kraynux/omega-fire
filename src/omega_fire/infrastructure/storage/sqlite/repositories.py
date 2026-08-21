# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""SQLite repositories.

Implements the persistence contracts defined in ports/ using SQLite.
Repositories handle CRUD operations for domain entities: bans, rules,
audit logs, snapshots.

This module performs real file I/O and is therefore in infrastructure/.
"""
import sqlite3
from datetime import datetime
from typing import Optional
from omega_fire.domain.ip_blacklist.models import BanEntry, BanStatus, BanSource
from omega_fire.domain.rules.models import FirewallRule, RuleAction, RuleChain, RuleProtocol, RuleFamily
from omega_fire.infrastructure.storage.sqlite.connection import DatabaseConnection
from omega_fire.infrastructure.storage.sqlite.exceptions import (
    RepositoryError,
    EntityNotFoundError,
)


class BanRepository:
    """Repository for BanEntry domain objects."""
    
    def __init__(self, db: DatabaseConnection):
        self._db = db
    
    def save(self, ban: BanEntry) -> int:
        try:
            cursor = self._db.execute(
                """
                INSERT INTO bans (ip, backend, status, source, comment, banned_at, expires_at, jail_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ban.ip,
                    ban.backend,
                    ban.status.value,
                    ban.source.value,
                    ban.comment,
                    ban.banned_at.isoformat(),
                    ban.expires_at.isoformat() if ban.expires_at else None,
                    ban.jail_name,
                ),
            )
            self._db.get_connection().commit()
            return cursor.lastrowid
        except Exception as e:
            raise RepositoryError(
                repository="BanRepository",
                operation="save",
                reason=str(e),
            ) from e

    def mark_removed_by_ip(self, ip: str, backend: str, removed_by: str = "user") -> bool:
        """Mark the currently-active ban row for (ip, backend) as removed.

        Keyed by (ip, backend, status=active) rather than by row id — the
        domain BanEntry returned by find_all()/find_by_ip() carries no id
        (save() is the only place an id is ever exposed, as its return
        value), so this mirrors the existing delete_by_ip() pattern
        instead of requiring one.

        Returns:
            True if a row was updated, False if no active ban matched
            (e.g. it was never recorded in the first place — not an
            error, the caller already knows the real unban succeeded).
        """
        try:
            cursor = self._db.execute(
                """
                UPDATE bans
                SET status = ?, removed_at = ?, removed_by = ?, updated_at = datetime('now')
                WHERE ip = ? AND backend = ? AND status = ?
                """,
                (
                    BanStatus.REMOVED.value,
                    datetime.now().isoformat(),
                    removed_by,
                    ip,
                    backend,
                    BanStatus.ACTIVE.value,
                ),
            )
            self._db.get_connection().commit()
            return cursor.rowcount > 0
        except Exception as e:
            raise RepositoryError(
                repository="BanRepository",
                operation="mark_removed_by_ip",
                reason=str(e),
            ) from e
    
    def find_by_id(self, ban_id: int) -> Optional[BanEntry]:
        try:
            cursor = self._db.execute(
                "SELECT * FROM bans WHERE id = ?",
                (ban_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_ban(row)
        except Exception as e:
            raise RepositoryError(
                repository="BanRepository",
                operation="find_by_id",
                reason=str(e),
            ) from e
    
    def find_by_ip(self, ip: str) -> list[BanEntry]:
        try:
            cursor = self._db.execute(
                "SELECT * FROM bans WHERE ip = ? ORDER BY banned_at DESC",
                (ip,),
            )
            return [self._row_to_ban(row) for row in cursor.fetchall()]
        except Exception as e:
            raise RepositoryError(
                repository="BanRepository",
                operation="find_by_ip",
                reason=str(e),
            ) from e
    
    def find_all(self, backend: Optional[str] = None, status: Optional[str] = None) -> list[BanEntry]:
        try:
            query = "SELECT * FROM bans WHERE 1=1"
            params = []
            
            if backend:
                query += " AND backend = ?"
                params.append(backend)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY banned_at DESC"
            
            cursor = self._db.execute(query, tuple(params))
            return [self._row_to_ban(row) for row in cursor.fetchall()]
        except Exception as e:
            raise RepositoryError(
                repository="BanRepository",
                operation="find_all",
                reason=str(e),
            ) from e
    
    def delete(self, ban_id: int) -> bool:
        try:
            cursor = self._db.execute(
                "DELETE FROM bans WHERE id = ?",
                (ban_id,),
            )
            self._db.get_connection().commit()
            return cursor.rowcount > 0
        except Exception as e:
            raise RepositoryError(
                repository="BanRepository",
                operation="delete",
                reason=str(e),
            ) from e
    
    def delete_by_ip(self, ip: str, backend: Optional[str] = None) -> int:
        try:
            query = "DELETE FROM bans WHERE ip = ?"
            params = [ip]
            
            if backend:
                query += " AND backend = ?"
                params.append(backend)
            
            cursor = self._db.execute(query, tuple(params))
            self._db.get_connection().commit()
            return cursor.rowcount
        except Exception as e:
            raise RepositoryError(
                repository="BanRepository",
                operation="delete_by_ip",
                reason=str(e),
            ) from e
    
    def _row_to_ban(self, row) -> BanEntry:
        return BanEntry(
            ip=row["ip"],
            backend=row["backend"],
            status=BanStatus(row["status"]),
            source=BanSource(row["source"]),
            comment=row["comment"],
            banned_at=datetime.fromisoformat(row["banned_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            removed_at=datetime.fromisoformat(row["removed_at"]) if row["removed_at"] else None,
            removed_by=row["removed_by"],
            jail_name=row["jail_name"],
        )


class RuleRepository:
    """Repository for FirewallRule domain objects."""
    
    def __init__(self, db: DatabaseConnection):
        self._db = db
    
    def save(self, rule: FirewallRule) -> int:
        try:
            cursor = self._db.execute(
                """
                INSERT INTO rules (backend, family, table_name, chain, action, protocol,
                                   port_start, port_end, source_cidr, dest_cidr, comment,
                                   priority, enabled, rule_id, external_ref, origin, interface,
                                   created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rule.backend,
                    rule.family.value,
                    rule.table_name,
                    rule.chain.value,
                    rule.action.value,
                    rule.protocol.value if rule.protocol else None,
                    rule.port_start,
                    rule.port_end,
                    rule.source_cidr,
                    rule.dest_cidr,
                    rule.comment,
                    rule.priority,
                    1 if rule.enabled else 0,
                    rule.rule_id,
                    rule.external_ref,
                    rule.origin,
                    rule.interface,
                    datetime.now().isoformat(),
                ),
            )
            self._db.get_connection().commit()
            return cursor.lastrowid
        except Exception as e:
            raise RepositoryError(
                repository="RuleRepository",
                operation="save",
                reason=str(e),
            ) from e
    
    def find_all(self, backend: Optional[str] = None) -> list[FirewallRule]:
        try:
            #  LE CORRECTIF : Forcer la connexion si elle est fermée
            if not getattr(self._db, "_connection", None):
                self._db.connect()

            query = "SELECT * FROM rules WHERE 1=1"
            params = []
            
            if backend:
                query += " AND backend = ?"
                params.append(backend)
            
            query += " ORDER BY priority DESC, id DESC"
            
            cursor = self._db.execute(query, tuple(params))
            return [self._row_to_rule(row) for row in cursor.fetchall()]
        except Exception as e:
            raise RepositoryError(
                repository="RuleRepository",
                operation="find_all",
                reason=str(e),
            ) from e
    
    def find_by_id(self, rule_id: int) -> Optional[FirewallRule]:
        """Find a single rule by its SQLite ID.
        
        Used before deletion (menu 3.2) to know the rule's backend and
        external_ref, needed to remove it from the live kernel before
        removing it from the database.
        
        Args:
            rule_id: Rule ID (SQLite primary key)
        
        Returns:
            FirewallRule if found, None otherwise
        
        Raises:
            RepositoryError: If query fails
        """
        try:
            if not getattr(self._db, "_connection", None):
                self._db.connect()

            cursor = self._db.execute(
                "SELECT * FROM rules WHERE id = ?",
                (rule_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_rule(row)
        except Exception as e:
            raise RepositoryError(
                repository="RuleRepository",
                operation="find_by_id",
                reason=str(e),
            ) from e
    
    def exists_similar(
        self,
        backend: str,
        chain: str,
        action: str,
        protocol: str,
        port_start: Optional[int],
        source_cidr: Optional[str],
    ) -> Optional[int]:
        """Detect a duplicate rule WITHIN the same backend only.

        Scoped to backend: the same logical rule created independently
        on nftables AND iptables (e.g. via menu 3.1 applying to all
        detected backends by default) must never be flagged as a
        duplicate of itself — that is the intended, desired outcome,
        not a collision. Only a true repeat within the SAME backend is
        a duplicate worth blocking.

        Protocol comparison uses IFNULL(protocol, 'ALL') on both sides:
        a rule with no protocol filter (protocol=NULL in DB, "ALL" as
        passed by create_rule.py) must match another rule with no
        protocol filter — a bare '=' comparison would silently never
        match NULL against the string "ALL" in SQL.
        """
        try:
            if not getattr(self._db, "_connection", None):
                self._db.connect()

            cursor = self._db.execute(
                """
                SELECT id FROM rules
                WHERE backend = ? AND chain = ? AND action = ?
                  AND IFNULL(protocol, 'ALL') = IFNULL(?, 'ALL')
                  AND IFNULL(port_start, 0) = IFNULL(?, 0)
                  AND IFNULL(source_cidr, '') = IFNULL(?, '')
                """,
                (backend, chain, action, protocol, port_start, source_cidr),
            )
            row = cursor.fetchone()
            return row["id"] if row else None
        except Exception as e:
            raise RepositoryError(
                repository="RuleRepository",
                operation="exists_similar",
                reason=str(e),
            ) from e

    def find_equivalent_rules(
        self,
        exclude_backend: str,
        chain: str,
        action: str,
        protocol: str,
        port_start: Optional[int],
        source_cidr: Optional[str],
    ) -> list[FirewallRule]:
        """Find rules representing the SAME logical intent on OTHER
        backends (never the excluded one).

        Used symmetrically by:
        - Menu 3.1 (create): check whether an equivalent rule already
          exists on another backend before creating a new one there.
        - Menu 3.2 (delete): find sibling rules on other backends so the
          user can be informed and choose to remove them together,
          rather than unknowingly leaving one backend still enforcing a
          rule the other no longer has.

        Same matching criteria as exists_similar() (chain, action,
        protocol, port_start, source_cidr — protocol comparison treats
        NULL and "ALL" as equivalent via IFNULL, so a rule with no
        protocol filter is correctly matched against another with no
        protocol filter), but returns full rule objects across every
        OTHER backend rather than a single ID within one backend.
        """
        try:
            if not getattr(self._db, "_connection", None):
                self._db.connect()

            cursor = self._db.execute(
                """
                SELECT * FROM rules
                WHERE backend != ? AND chain = ? AND action = ?
                  AND IFNULL(protocol, 'ALL') = IFNULL(?, 'ALL')
                  AND IFNULL(port_start, 0) = IFNULL(?, 0)
                  AND IFNULL(source_cidr, '') = IFNULL(?, '')
                """,
                (exclude_backend, chain, action, protocol, port_start, source_cidr),
            )
            return [self._row_to_rule(row) for row in cursor.fetchall()]
        except Exception as e:
            raise RepositoryError(
                repository="RuleRepository",
                operation="find_equivalent_rules",
                reason=str(e),
            ) from e
    
    def update_enabled(self, rule_id: int, enabled: bool) -> bool:
        try:
            cursor = self._db.execute(
                "UPDATE rules SET enabled = ? WHERE id = ?",
                (1 if enabled else 0, rule_id),
            )
            self._db.get_connection().commit()
            return cursor.rowcount > 0
        except Exception as e:
            raise RepositoryError(
                repository="RuleRepository",
                operation="update_enabled",
                reason=str(e),
            ) from e
    
    def update_external_ref(self, rule_id: int, external_ref: Optional[str]) -> bool:
        """Update the external_ref (technical backend identifier) of a rule.
        
        Used after a rule has been successfully applied to the live
        backend (menu 3.1), once its handle / raw specification has been
        retrieved from the backend adapter, so it can later be removed
        from the kernel by menu 3.2.
        
        Args:
            rule_id: Rule ID (SQLite primary key)
            external_ref: New technical identifier, or None to clear it
        
        Returns:
            True if a row was updated, False if not found
        
        Raises:
            RepositoryError: If update fails
        """
        try:
            cursor = self._db.execute(
                "UPDATE rules SET external_ref = ? WHERE id = ?",
                (external_ref, rule_id),
            )
            self._db.get_connection().commit()
            return cursor.rowcount > 0
        except Exception as e:
            raise RepositoryError(
                repository="RuleRepository",
                operation="update_external_ref",
                reason=str(e),
            ) from e
    
    def find_by_external_ref(self, backend: str, external_ref: str) -> Optional[FirewallRule]:
        try:
            if not getattr(self._db, "_connection", None):
                self._db.connect()

            cursor = self._db.execute(
                "SELECT * FROM rules WHERE backend = ? AND external_ref = ?",
                (backend, external_ref),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_rule(row)
        except Exception as e:
            raise RepositoryError(
                repository="RuleRepository",
                operation="find_by_external_ref",
                reason=str(e),
            ) from e
    
    def count_managed(self, backend: str) -> int:
        """Count currently active 'managed' rules for a backend.

        Used by the dashboard (menu 8.1) to detect whether an active
        preset profile has been manually modified since its
        application: compared against rules_count_at_apply stored in
        active_preset_{backend}.json at the moment ApplyPresetCommand
        succeeded. A mismatch in either direction (more OR fewer rules
        now) reveals a manual create (3.1) or delete (3.2) since.

        Only counts origin="managed" — rules imported from other tools
        (origin="imported") are never part of a preset and would
        otherwise pollute this comparison.
        """
        try:
            if not getattr(self._db, "_connection", None):
                self._db.connect()

            cursor = self._db.execute(
                "SELECT COUNT(*) as cnt FROM rules WHERE backend = ? AND origin = 'managed'",
                (backend,),
            )
            row = cursor.fetchone()
            return row["cnt"] if row else 0
        except Exception as e:
            raise RepositoryError(
                repository="RuleRepository",
                operation="count_managed",
                reason=str(e),
            ) from e

    def delete(self, rule_id: int) -> bool:
        try:
            cursor = self._db.execute(
                "DELETE FROM rules WHERE id = ?",
                (rule_id,),
            )
            self._db.get_connection().commit()
            return cursor.rowcount > 0
        except Exception as e:
            raise RepositoryError(
                repository="RuleRepository",
                operation="delete",
                reason=str(e),
            ) from e
    
    def _row_to_rule(self, row: sqlite3.Row) -> FirewallRule:
        raw_chain = row["chain"]
        try:
            chain_val = RuleChain(raw_chain.lower() if isinstance(raw_chain, str) else raw_chain)
        except (ValueError, KeyError, AttributeError):
            try:
                chain_val = RuleChain.INPUT
            except Exception:
                chain_val = raw_chain

        raw_action = row["action"]
        try:
            action_val = RuleAction(raw_action.lower() if isinstance(raw_action, str) else raw_action)
        except (ValueError, KeyError, AttributeError):
            action_val = RuleAction.ACCEPT if hasattr(RuleAction, "ACCEPT") else raw_action

        raw_proto = row["protocol"]
        proto_val = None
        if raw_proto:
            try:
                proto_val = RuleProtocol(raw_proto.lower() if isinstance(raw_proto, str) else raw_proto)
            except (ValueError, KeyError, AttributeError):
                proto_val = None

        raw_family = row["family"] if "family" in row.keys() and row["family"] else "ip"
        try:
            family_val = RuleFamily(raw_family.lower() if isinstance(raw_family, str) else raw_family)
        except (ValueError, KeyError, AttributeError):
            family_val = RuleFamily.IP

        

        return FirewallRule(
            rule_id=row["id"],
            backend=row["backend"],
            family=family_val,
            table_name=row["table_name"] if "table_name" in row.keys() and row["table_name"] else "filter",
            chain=chain_val,
            action=action_val,
            protocol=proto_val,
            port_start=row["port_start"],
            source_cidr=row["source_cidr"],
            dest_cidr=row["dest_cidr"],
            comment=row["comment"],
            enabled=bool(row["enabled"]),
            external_ref=row["external_ref"] if "external_ref" in row.keys() else None,
            origin=row["origin"] if "origin" in row.keys() and row["origin"] else "imported",
            interface=row["interface"] if "interface" in row.keys() else None,
        )
        
class AuditRepository:
    """Repository for audit log entries."""
    
    def __init__(self, db: DatabaseConnection):
        self._db = db
    
    def save(self, event_type: str, command_name: str, step_name: str,
             success: bool, error_message: Optional[str] = None,
             details: Optional[dict] = None) -> int:
        try:
            import json
            cursor = self._db.execute(
                """
                INSERT INTO audit_logs (event_type, timestamp, command_name, step_name,
                                        success, error_message, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    datetime.now().isoformat(),
                    command_name,
                    step_name,
                    1 if success else 0,
                    error_message,
                    json.dumps(details) if details else None,
                ),
            )
            self._db.get_connection().commit()
            return cursor.lastrowid
        except Exception as e:
            raise RepositoryError(
                repository="AuditRepository",
                operation="save",
                reason=str(e),
            ) from e
    
    def find_recent(self, limit: int = 100) -> list[dict]:
        try:
            cursor = self._db.execute(
                "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            raise RepositoryError(
                repository="AuditRepository",
                operation="find_recent",
                reason=str(e),
            ) from e


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Implémente les contrats de persistance définis dans ports/
# - Gère les opérations CRUD pour les entités du domaine : bans, rules, audit logs
# - Convertit les objets du domaine en lignes DB et vice-versa
# Pourquoi dans infrastructure/ (charte) :
# - C'est une implémentation technique qui fait des I/O réels (SQL)
# - Le domaine ne doit pas connaître SQLite (règle de dépendance)
# - L'application/ utilise ces repositories via ports/, pas directement
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas de dépendance vers application/ ou interfaces/
# ❌ Pas de validation métier (c'est le rôle du domaine)
# Points clés :
# - BanRepository : CRUD pour BanEntry
#   - save() : insère un ban
#   - find_by_id() / find_by_ip() / find_all() : requêtes
#   - delete() / delete_by_ip() : suppressions
#   - _row_to_ban() : conversion row → BanEntry
# - RuleRepository : CRUD pour FirewallRule
#   - save() : insère une règle (incl. external_ref, origin, interface)
#   - find_all() : requête avec filtre optionnel
#   - find_by_id() : recherche par ID SQLite (utilisé avant suppression, 3.2)
#   - exists_similar() : détecte un doublon avant création, SCOPÉ À UN
#     SEUL BACKEND (menu 3.1) — comparaison protocole tolérante à NULL
#     via IFNULL(protocol, 'ALL')
#   - find_equivalent_rules() : trouve les règles de même intention SUR
#     LES AUTRES BACKENDS (menu 3.1 vérification, menu 3.2 information
#     avant suppression croisée) — mêmes critères qu'exists_similar()
#   - find_by_external_ref() : recherche par identifiant technique backend
#     (utilisé par la synchro pour éviter les doublons)
#   - update_enabled() : bascule enabled True/False sans supprimer la ligne
#     (utilisé par la synchro quand une règle disparaît du backend live)
#   - update_external_ref() : enregistre l'identifiant technique obtenu après
#     application d'une règle managed au backend (menu 3.1)
#   - delete() : suppression
#   - _row_to_rule() : conversion row → FirewallRule (incl. external_ref, origin, interface)
# - AuditRepository : insertion et requête d'événements d'audit
#   - save() : insère un événement
#   - find_recent() : retourne les N derniers événements
# - Gestion des enums : conversion string ↔ enum (BanStatus, RuleAction, etc.)
# - Gestion des dates : conversion datetime ↔ ISO string
# - Gestion du JSON : sérialisation/désérialisation du champ details
# - Transactions : commit automatique après chaque opération
# Comment il sera utilisé (aperçu) :
# - ports/blacklist.py définira le contrat que BanRepository implémente
# - ports/rules.py définira le contrat que RuleRepository implémente
# - app/bootstrap.py instanciera ces repositories et les injectera
# - application/commands/ utilisera les ports (pas ces repositories directement)
#---------------------------------------------------------------------->
