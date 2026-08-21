# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Manage blocklist file use case.

Orchestrates file-level management of the blocklist directory
(var/blocklist/): listing, creating, renaming, deleting files, and
editing their content line by line (adding/removing an IP). Every
save is validated via domain/ip_blacklist/validation.py first —
Option B (cleanup, never blocking): invalid lines are silently
dropped from what's written to disk, but always reported back to the
caller so the user is informed, never surprised.

Conforms to Omega-Fire architecture charter:
- No direct file I/O (delegates entirely to TextStore, received
  already resolved by the caller)
- No subprocess calls
- Uses domain/ip_blacklist/validation.py for line format rules — never
  reimplements or duplicates that logic here
- Never decides whether to ban the resulting IPs — that decision and
  its execution belong to menu 2's ban pipeline
  (BanIpToAllBackendsCommand), called separately by
  interfaces/cli/actions.py once the file is ready
"""
from dataclasses import dataclass, field

from pathlib import Path

from omega_fire.domain.ip_blacklist.validation import (
    ParsedLine,
    LineKind,
    classify_line,
    parse_blocklist_content,
    extract_valid_ips,
    extract_rejected_lines,
    rebuild_clean_content,
)
from omega_fire.infrastructure.storage.files.text_store import TextStore, TextStoreError


@dataclass
class BlocklistFileInfo:
    """Metadata about a single blocklist file, for listing."""
    name: str
    path: str


@dataclass
class BlocklistFileContent:
    """Result of loading and parsing a blocklist file's content."""
    success: bool
    name: str
    parsed_lines: list[ParsedLine] = field(default_factory=list)
    valid_ips: list[str] = field(default_factory=list)
    rejected_lines: list[ParsedLine] = field(default_factory=list)
    message: str = ""


@dataclass
class BlocklistFileSaveResult:
    """Result of saving (creating, editing) a blocklist file."""
    success: bool
    name: str
    valid_ips: list[str] = field(default_factory=list)
    rejected_lines: list[ParsedLine] = field(default_factory=list)
    message: str = ""


class ManageBlocklistFileCommand:
    """Use case: manage blocklist files (list, create, rename, delete,
    load, edit) as a distinct concern from actually applying their
    content to a firewall backend.
    """

    def __init__(self, text_store: TextStore):
        """Initialize the command.

        Args:
            text_store: Already-configured TextStore rooted at the
                blocklist directory (var/blocklist/).
        """
        self._store = text_store

    def list_files(self, pattern: str = "*.txt") -> list[BlocklistFileInfo]:
        """List every blocklist file matching the given pattern."""
        return [
            BlocklistFileInfo(name=p.name, path=str(p))
            for p in self._store.list_files(pattern)
        ]

    def create_file(self, name: str) -> BlocklistFileSaveResult:
        """Create a new, empty blocklist file with a header comment.

        Fails explicitly if a file with this name already exists —
        TextStore.save() would silently overwrite otherwise.
        """
        if self._store.exists(name):
            return BlocklistFileSaveResult(
                success=False,
                name=name,
                message=f"Un fichier nommé '{name}' existe déjà.",
            )

        try:
            self._store.save(name, "# Omega-Fire Blocklist\n")
        except TextStoreError as e:
            return BlocklistFileSaveResult(success=False, name=name, message=str(e))

        return BlocklistFileSaveResult(success=True, name=name, message=f"Fichier '{name}' créé.")

    def rename_file(self, name: str, new_name: str) -> BlocklistFileSaveResult:
        """Rename a blocklist file."""
        try:
            self._store.rename(name, new_name)
        except TextStoreError as e:
            return BlocklistFileSaveResult(success=False, name=name, message=str(e))

        return BlocklistFileSaveResult(
            success=True, name=new_name, message=f"Fichier renommé en '{new_name}'."
        )
    def import_from_path(self, source_path: str, dest_name: str) -> BlocklistFileSaveResult:
        """Import a file from an arbitrary absolute path OUTSIDE
        var/blocklist/, copying (never moving) its content into the
        managed directory under dest_name. The source file is never
        modified or deleted.

        Uses a temporary TextStore anchored on the source file's parent
        directory to perform the read — keeps all I/O inside TextStore
        (infrastructure/), rather than reading the file directly here.

        Content is validated the same way as save_content() (Option B:
        cleanup, never blocking) once copied — an externally-sourced
        file is never trusted to already be well-formed.
        """
        source = Path(source_path)

        if not source.exists() or not source.is_file():
            return BlocklistFileSaveResult(
                success=False, name=dest_name, message=f"Fichier source introuvable : {source_path}"
            )

        if self._store.exists(dest_name):
            return BlocklistFileSaveResult(
                success=False,
                name=dest_name,
                message=f"Un fichier nommé '{dest_name}' existe déjà dans var/blocklist/.",
            )

        try:
            external_store = TextStore(source.parent)
            raw_content = external_store.load(source.name)
        except TextStoreError as e:
            return BlocklistFileSaveResult(success=False, name=dest_name, message=str(e))

        return self.save_content(dest_name, raw_content)

    def delete_file(self, name: str) -> BlocklistFileSaveResult:
        """Delete a blocklist file."""
        deleted = self._store.delete(name)
        if deleted:
            return BlocklistFileSaveResult(success=True, name=name, message=f"Fichier '{name}' supprimé.")
        return BlocklistFileSaveResult(success=False, name=name, message=f"Fichier '{name}' introuvable.")

    def load_file(self, name: str) -> BlocklistFileContent:
        """Load and parse a blocklist file's content.

        Never raises for malformed pre-existing content: rejected
        lines are reported, never hidden — a load never modifies the
        file, only a subsequent save_content()/add_ip()/remove_ip() does.
        """
        try:
            raw_content = self._store.load(name)
        except TextStoreError as e:
            return BlocklistFileContent(success=False, name=name, message=str(e))

        parsed = parse_blocklist_content(raw_content)
        return BlocklistFileContent(
            success=True,
            name=name,
            parsed_lines=parsed,
            valid_ips=extract_valid_ips(parsed),
            rejected_lines=extract_rejected_lines(parsed),
        )

    def save_content(self, name: str, raw_content: str) -> BlocklistFileSaveResult:
        """Validate and save arbitrary raw content to a blocklist file.

        Option B (cleanup, never blocking): invalid lines are silently
        dropped from what's written to disk, but always reported in
        the result so the caller can inform the user — never a silent
        surprise.
        """
        parsed = parse_blocklist_content(raw_content)
        rejected = extract_rejected_lines(parsed)
        clean_content = rebuild_clean_content(parsed)

        try:
            self._store.save(name, clean_content)
        except TextStoreError as e:
            return BlocklistFileSaveResult(
                success=False, name=name, rejected_lines=rejected, message=str(e)
            )

        return BlocklistFileSaveResult(
            success=True,
            name=name,
            valid_ips=extract_valid_ips(parsed),
            rejected_lines=rejected,
            message=f"Fichier '{name}' enregistré.",
        )

    def add_ip(self, name: str, ip_or_cidr: str, comment: str = "") -> BlocklistFileSaveResult:
        """Add a single IP/CIDR line to a blocklist file, skipping it if
        already present. Validates the new line BEFORE appending —
        never writes a malformed entry, unlike save_content() which
        cleans up after the fact.
        """
        candidate_line = f"{ip_or_cidr} # {comment}".strip() if comment else ip_or_cidr
        classified = classify_line(candidate_line)

        if classified.kind != LineKind.IP:
            return BlocklistFileSaveResult(
                success=False,
                name=name,
                message=classified.reason or f"'{ip_or_cidr}' n'est pas une IP ou un réseau CIDR valide.",
            )

        loaded = self.load_file(name)
        if not loaded.success:
            return BlocklistFileSaveResult(success=False, name=name, message=loaded.message)

        if classified.ip in loaded.valid_ips:
            return BlocklistFileSaveResult(
                success=True,
                name=name,
                valid_ips=loaded.valid_ips,
                rejected_lines=loaded.rejected_lines,
                message=f"'{classified.ip}' est déjà présent dans '{name}'.",
            )

        existing_raw = self._store.load(name)
        separator = "" if (not existing_raw or existing_raw.endswith("\n")) else "\n"
        new_content = existing_raw + separator + candidate_line + "\n"

        return self.save_content(name, new_content)

    def remove_ip(self, name: str, ip_or_cidr: str) -> BlocklistFileSaveResult:
        """Remove every line matching the given IP/CIDR from a blocklist
        file. Comment and blank lines are always preserved."""
        loaded = self.load_file(name)
        if not loaded.success:
            return BlocklistFileSaveResult(success=False, name=name, message=loaded.message)

        if ip_or_cidr not in loaded.valid_ips:
            return BlocklistFileSaveResult(
                success=True,
                name=name,
                valid_ips=loaded.valid_ips,
                rejected_lines=loaded.rejected_lines,
                message=f"'{ip_or_cidr}' n'était pas présent dans '{name}'.",
            )

        remaining = [
            line.raw for line in loaded.parsed_lines
            if not (line.kind == LineKind.IP and line.ip == ip_or_cidr)
        ]
        new_content = "\n".join(remaining) + ("\n" if remaining else "")

        return self.save_content(name, new_content)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Gère le CYCLE DE VIE des fichiers blocklist (var/blocklist/) : liste,
#   création, renommage, suppression, chargement, édition ligne par ligne
#   (ajout/retrait d'IP) — DISTINCT de l'action de bannir réellement le
#   contenu d'un fichier sur un backend (menu 2's ban pipeline).
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration : délègue toute l'I/O à TextStore (infrastructure/),
#   toute la validation de format à domain/ip_blacklist/validation.py.
# - Aucun subprocess, aucun accès fichier direct dans ce fichier lui-même.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/storage/files/ concret autre que
#    TextStore (reçu déjà résolu par l'appelant)
# ❌ Pas d'appel à un adapter backend (nftables/iptables/fail2ban) — ne
#    bannit JAMAIS rien lui-même
# ❌ Pas de rendu UI
# ❌ Pas de logique de validation de ligne dupliquée (déléguée entièrement
#    à domain/ip_blacklist/validation.py)
#
# Points clés :
# - BlocklistFileInfo : métadonnées légères pour le listage
# - BlocklistFileContent : résultat d'un chargement (lignes classifiées,
#   IPs valides, lignes rejetées) — un chargement ne modifie jamais le fichier
# - BlocklistFileSaveResult : résultat de toute opération d'écriture
#   (create/rename/save_content/add_ip/remove_ip)
# - save_content() : POINT UNIQUE d'écriture pour du contenu arbitraire —
#   Option B actée (nettoyage automatique, jamais bloquant, toujours
#   rapporté via rejected_lines)
# - add_ip()/remove_ip() : rechargent, modifient, délèguent à
#   save_content() — aucun chemin d'écriture ne contourne la validation
# - create_file()/rename_file() : gardes explicites contre l'écrasement
#   silencieux (vérification exists() avant écriture)
# - import_from_path() : importe un fichier depuis un chemin absolu
#   ARBITRAIRE (hors var/blocklist/), copie jamais déplacement — la
#   source n'est jamais modifiée. Utilise un TextStore temporaire
#   ancré sur le dossier source pour rester cohérent avec le principe
#   "toute I/O passe par TextStore".
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_2_7_import_file(ctx) (Phase 6, à venir)
#   ↓ instancie TextStore(BLOCKLIST_DIR), résout ManageBlocklistFileCommand
#   ↓ une fois le fichier prêt, IPs valides extraites : appel séparé à
#     BanIpToAllBackendsCommand (menu 2's pipeline, jamais mélangé ici)
#---------------------------------------------------------------------->
