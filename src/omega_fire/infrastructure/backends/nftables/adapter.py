# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Nftables backend adapter.

Implements the concrete nftables operations: ban, unban, list rules,
list bans, flush, preset application, ruleset snapshot/restore. Uses
subprocess to execute nft commands and the parser/serializer/mapper
for data transformation.

This is the only module that directly calls nft via subprocess.
"""
import subprocess
import re
from typing import Optional, Union, List
from omega_fire.domain.rules.models import FirewallRule, RuleChain
from omega_fire.domain.rules.presets import FirewallPreset, PresetRule, list_presets
from omega_fire.domain.rules.exceptions import PolicyNotFoundError
from omega_fire.domain.ip_blacklist.models import BanEntry, BanStatus, BanSource
from omega_fire.domain.ip_blacklist.exceptions import IPAlreadyBannedError, IPNotFoundError
from omega_fire.shared.networking import IPAddress
from omega_fire.shared.parsing import IPV4_PATTERN, IPV6_PATTERN
from omega_fire.ports.firewall import FirewallStats
from omega_fire.infrastructure.backends.nftables.parser import NftParser
from omega_fire.infrastructure.backends.nftables.serializer import NftSerializer, addr_family_keyword
from omega_fire.infrastructure.backends.nftables.mapper import NftMapper
from omega_fire.infrastructure.backends.nftables.exceptions import (
    NftCommandError,
    NftPermissionError,
)


class NftablesAdapter:
    """Concrete adapter for nftables operations.

    Executes nft commands via subprocess and transforms results
    into domain models using parser, serializer, and mapper.
    """

    def __init__(self, timeout: float = 10.0):
        """Initialize the nftables adapter.

        Args:
            timeout: Maximum time for command execution (seconds)
        """
        self._parser = NftParser()
        self._serializer = NftSerializer()
        self._mapper = NftMapper()
        self._timeout = timeout

    def _run_command(self, cmd: list[str]) -> str:
        """Execute an nft command and return stdout."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )

            if result.returncode != 0:
                stderr = result.stderr.strip()
                if "Permission denied" in stderr or "Operation not permitted" in stderr:
                    raise NftPermissionError(operation=" ".join(cmd[:3]))
                raise NftCommandError(
                    command=" ".join(cmd),
                    returncode=result.returncode,
                    stderr=stderr,
                )

            return result.stdout

        except subprocess.TimeoutExpired:
            raise NftCommandError(
                command=" ".join(cmd),
                returncode=-1,
                stderr=f"Command timed out after {self._timeout}s",
            )
        except FileNotFoundError:
            raise NftCommandError(
                command=" ".join(cmd),
                returncode=-1,
                stderr="nft binary not found",
            )

    def _run_command_with_input(self, cmd: list[str], input_text: str) -> str:
        """Execute an nft command feeding it stdin content (used by load_ruleset)."""
        try:
            result = subprocess.run(
                cmd,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )

            if result.returncode != 0:
                stderr = result.stderr.strip()
                if "Permission denied" in stderr or "Operation not permitted" in stderr:
                    raise NftPermissionError(operation=" ".join(cmd[:3]))
                raise NftCommandError(
                    command=" ".join(cmd),
                    returncode=result.returncode,
                    stderr=stderr,
                )

            return result.stdout

        except subprocess.TimeoutExpired:
            raise NftCommandError(
                command=" ".join(cmd),
                returncode=-1,
                stderr=f"Command timed out after {self._timeout}s",
            )
        except FileNotFoundError:
            raise NftCommandError(
                command=" ".join(cmd),
                returncode=-1,
                stderr="nft binary not found",
            )

    # IP v4 continue d'utiliser le set "blackhole" déjà en production, tel
    # quel (jamais renommé) ; le v6 obtient son propre set à côté —
    # référentiel §50, plan IPv6 Phase B.
    _BLACKHOLE_SET_BY_VERSION = {4: "blackhole", 6: "blackhole_v6"}

    def _blackhole_set_name(self, ip_version: int) -> str:
        """Nom du set blackhole à utiliser pour la version d'IP donnée."""
        return self._BLACKHOLE_SET_BY_VERSION.get(ip_version, "blackhole")

    def _ensure_blackhole_set(
        self,
        family: str = "inet",
        table: str = "filter",
        set_name: str = "blackhole",
        set_type: str = "ipv4_addr",
    ) -> None:
        """Garantit l'existence de la table, du set et de la règle de
        filtrage blackhole.

        set_type détermine à la fois le type du set nft et le mot-clé
        d'expression de la règle de filtrage ("ip saddr" pour ipv4_addr,
        "ip6 saddr" pour ipv6_addr) — défaut inchangé (ipv4_addr/"ip"),
        ban_ip()/unban_ip() (batch, ligne ~167) qui n'appellent pas ce
        paramètre gardent exactement leur comportement d'avant.
        """
        saddr_kw = "ip6" if set_type == "ipv6_addr" else "ip"
        init_cmds = [
            ["nft", "add", "table", family, table],
            ["nft", "add", "set", family, table, set_name, f"{{ type {set_type}; flags timeout; }}"],
            ["nft", "add", "chain", family, table, "input", "{ type filter hook input priority 0; policy accept; }"],
            ["nft", "add", "rule", family, table, "input", saddr_kw, "saddr", f"@{set_name}", "drop"],
        ]
        for cmd in init_cmds:
            try:
                self._run_command(cmd)
            except NftCommandError as e:
                if "File exists" in str(e) or "already exists" in str(e):
                    continue

    def _ensure_chain(self, family: str, table: str, chain: str) -> None:
        """Garantit l'existence d'une chaîne de base avant d'y ajouter une règle.

        Couvre n'importe laquelle des trois chaînes de base proposées par
        le menu 3.1 (input, forward, output) — sans quoi une règle
        demandée par l'utilisateur sur forward/output échoue
        systématiquement, la chaîne n'existant pas encore sur le système.
        """
        init_cmds = [
            ["nft", "add", "table", family, table],
            [
                "nft", "add", "chain", family, table, chain,
                f"{{ type filter hook {chain} priority 0; policy accept; }}",
            ],
        ]
        for cmd in init_cmds:
            try:
                self._run_command(cmd)
            except NftCommandError as e:
                if "File exists" in str(e) or "already exists" in str(e):
                    continue

    def ban_ip(
        self,
        ip: Union[str, List[str]],
        table: str = "filter",
        family: str = "inet",
        set_name: str = "blackhole",
        comment: str = "",
    ) -> bool:
        """Ban one or multiple IP addresses using nftables."""
        self._ensure_blackhole_set(family=family, table=table, set_name=set_name)

        ip_list = []
        if isinstance(ip, list):
            ip_list = [i.strip() for i in ip if i.strip()]
        elif isinstance(ip, str):
            ip_list = [i.strip() for i in re.split(r"[,\s]+", ip) if i.strip()]

        if not ip_list:
            return False

        success = True
        for single_ip in ip_list:
            try:
                cmd = self._serializer.build_ban_command(
                    ip=single_ip, table=table, family=family, set_name=set_name, comment=comment
                )
                self._run_command(cmd)
            except NftCommandError as e:
                if "File exists" in str(e) or "already exists" in str(e):
                    continue
                success = False

        return success

    def unban_ip(
        self,
        ip: Union[str, List[str]],
        table: str = "filter",
        family: str = "inet",
        set_name: str = "blackhole",
    ) -> bool:
        """Unban one or multiple IP addresses using nftables."""
        ip_list = []
        if isinstance(ip, list):
            ip_list = [i.strip() for i in ip if i.strip()]
        elif isinstance(ip, str):
            ip_list = [i.strip() for i in re.split(r"[,\s]+", ip) if i.strip()]

        if not ip_list:
            return False

        success = True
        for single_ip in ip_list:
            try:
                cmd = self._serializer.build_unban_command(
                    ip=single_ip, table=table, family=family, set_name=set_name
                )
                self._run_command(cmd)
            except NftCommandError as e:
                if "No such file or directory" in str(e) or "does not exist" in str(e):
                    continue
                success = False

        return success

    def ban_single_ip(self, ip: IPAddress, *, reason: str = "") -> None:
        """Ban a single IP (FirewallPort.ban_ip contract).

        Coexists with ban_ip() (batch, bool return) — does not replace it;
        BanIpCommand and its existing callers are unaffected.

        Args:
            ip: IP address to ban
            reason: Ban reason, stored as the nft set element comment

        Raises:
            IPAlreadyBannedError: If the IP is already banned on nftables
        """
        ip_str = str(ip)
        set_name = self._blackhole_set_name(ip.version)
        if self.is_ip_banned(ip):
            raise IPAlreadyBannedError(ip_str, "nftables")
        set_type = "ipv6_addr" if ip.version == 6 else "ipv4_addr"
        self._ensure_blackhole_set(set_name=set_name, set_type=set_type)
        cmd = self._serializer.build_ban_command(
            ip=ip_str, table="filter", family="inet", set_name=set_name, comment=reason
        )
        self._run_command(cmd)

    def unban_single_ip(self, ip: IPAddress) -> None:
        """Unban a single IP (FirewallPort.unban_ip contract).

        Coexists with unban_ip() (batch, bool return) — does not replace
        it; UnbanIpCommand and its existing callers are unaffected.

        Args:
            ip: IP address to unban

        Raises:
            IPNotFoundError: If the IP is not currently banned on nftables
        """
        ip_str = str(ip)
        if not self.is_ip_banned(ip):
            raise IPNotFoundError(ip_str)
        cmd = self._serializer.build_unban_command(
            ip=ip_str, table="filter", family="inet", set_name=self._blackhole_set_name(ip.version)
        )
        self._run_command(cmd)

    def list_rules(self) -> list[FirewallRule]:
        """List all firewall rules from nftables, across ALL tables and families.

        Does not assume any specific table name or family: real systems can
        have rules spread across multiple tables created by different tools
        (UFW typically uses family 'ip', Omega-Fire's own managed rules use
        'inet', other tools may use yet other names/families, known or not
        in advance). Querying the full ruleset with -a (handles included)
        and letting the parser discover tables/chains dynamically is the
        only approach that works across arbitrary, unknown user configurations.

        One specific, deliberate exclusion: family "ip" / table "filter" is
        never included here. This exact combination is nft's own hardcoded
        convention for the iptables-nft compatibility layer — the table nft
        itself labels "managed by iptables-nft, do not touch!" in its
        output. Any rule living there — whether posted by Omega-Fire's own
        IptablesAdapter, by UFW, or by a manual iptables command — is
        already fully and correctly represented by
        IptablesAdapter.list_rules() (backend="iptables", via 'iptables -S',
        which reads this exact same kernel table through the compat layer).
        Including it here too would report the identical live rule twice
        under two different backend labels — confirmed in real testing as
        the source of duplicate rows in RuleRepository (32 nftables-tagged
        rows for 16 real rules) after applying a profile on nftables while
        an iptables profile was also active.
        """
        cmd = ["nft", "-a", "list", "ruleset"]
        try:
            output = self._run_command(cmd)
        except NftCommandError:
            return []
        parsed = self._parser.parse_ruleset(output)

        # Exclusion de la table de compatibilité iptables-nft (ip/filter) —
        # voir docstring ci-dessus : déjà représentée intégralement par
        # IptablesAdapter.list_rules(), jamais par ce backend.
        parsed = [
            p for p in parsed
            if not (p.get("family") == "ip" and p.get("table") == "filter")
        ]

        return self._mapper.map_rules(parsed)

    # Motif combiné IPv4|IPv6 + commentaire nft optionnel — composé sur les
    # fragments partagés et déjà corrigés de shared/parsing.py (référentiel
    # §49) plutôt que de dupliquer la regex IPv6 une 2e fois ici.
    _BAN_ELEMENT_PATTERN = re.compile(
        rf'((?:{IPV4_PATTERN})|(?:{IPV6_PATTERN}))(?:\s+comment\s+"([^"]+)")?'
    )

    def list_bans(
        self,
        table: str = "filter",
        family: str = "inet",
        set_name: Optional[str] = None,
    ) -> list[BanEntry]:
        """List all banned IPs from nftables with their comments.

        set_name=None (défaut) interroge et fusionne les deux sets
        blackhole connus (IPv4 "blackhole" et IPv6 "blackhole_v6") —
        les 13+ appelants réels existants, tous sans argument explicite,
        obtiennent la visibilité IPv6 sans modification de leur côté
        (référentiel §50, plan IPv6 Phase B). Passer un set_name explicite
        cible un seul set (utilisé par is_ip_banned() pour une recherche
        ciblée sur la famille de l'IP demandée).

        Si le set IPv6 n'existe pas encore (aucun bannissement IPv6 n'a
        jamais eu lieu), la requête échoue silencieusement pour ce seul
        set (NftCommandError attrapée, ignorée) — comportement strictement
        identique à avant ce correctif pour tout système n'ayant jamais
        banni d'IPv6.
        """
        set_names = [set_name] if set_name is not None else list(self._BLACKHOLE_SET_BY_VERSION.values())

        seen_ips: dict[str, str] = {}
        for name in set_names:
            cmd = self._serializer.build_list_set_command(family, table, name)
            try:
                output = self._run_command(cmd)
            except NftCommandError:
                continue

            matches = self._BAN_ELEMENT_PATTERN.findall(output)
            for ip_addr, comment_text in matches:
                comment_final = comment_text if comment_text else "Règle active nftables"
                seen_ips[ip_addr] = comment_final

        return [
            BanEntry(
                ip=ip_addr,
                backend="nftables",
                status=BanStatus.ACTIVE,
                source=BanSource.MANUAL,
                comment=comment_final,
            )
            for ip_addr, comment_final in seen_ips.items()
        ]

    def get_stats(self) -> FirewallStats:
        """Get aggregate firewall statistics (FirewallPort contract).

        System-wide scope (all tables/families) — same exclusion as
        list_rules() for family="ip"/table="filter" (already fully
        reported by IptablesAdapter, would double-count otherwise).
        Read-only, so unlike flush() there's no destructive-scope
        argument for narrowing this to inet/filter only; doing so would
        make total_rules diverge confusingly from len(list_rules()).

        Reads the parser's raw dicts directly rather than composing
        list_rules() — domain.rules.models.FirewallRule (what list_rules()
        maps to) has no packets/bytes fields, and NftMapper silently drops
        the parser's counter values when building it. This method is
        therefore independent of list_rules()/the mapper entirely.

        Known limitation, not yet corrected by this method: nft only
        tracks packets/bytes for rules carrying an explicit 'counter'
        statement. Omega-Fire's own rule-building code (ban_ip, add_rule,
        _build_preset_rule_commands) never adds one, so Omega-Fire-managed
        rules may report 0 packets/bytes here even while actively
        matching traffic — a real constraint of the underlying tool, not
        a bug in this aggregation.

        Returns:
            FirewallStats with counters aggregated from the live ruleset.
        """
        try:
            output = self._run_command(["nft", "-a", "list", "ruleset"])
        except NftCommandError:
            return FirewallStats(0, 0, 0, 0, 0)

        parsed = [
            p for p in self._parser.parse_ruleset(output)
            if not (p.get("family") == "ip" and p.get("table") == "filter")
        ]

        return FirewallStats(
            total_rules=len(parsed),
            total_packets=sum(p.get("packets", 0) for p in parsed),
            total_bytes=sum(p.get("bytes", 0) for p in parsed),
            dropped_packets=sum(p.get("packets", 0) for p in parsed if p.get("action") == "drop"),
            accepted_packets=sum(p.get("packets", 0) for p in parsed if p.get("action") == "accept"),
        )

    def is_ip_banned(self, ip: IPAddress) -> bool:
        """Check if an IP is currently banned (FirewallPort contract).

        Passe un set_name explicite à list_bans() (dérivé de ip.version,
        référentiel §50) plutôt que d'utiliser sa portée fusionnée par
        défaut : cible directement le seul set pertinent pour la famille
        de l'IP demandée, sans requête inutile sur l'autre.

        Args:
            ip: IP address to check

        Returns:
            True if the IP is present in the relevant blackhole set.
        """
        ip_str = str(ip)
        set_name = self._blackhole_set_name(ip.version)
        return any(b.ip.split("/")[0] == ip_str for b in self.list_bans(set_name=set_name))

    def add_rule(
        self,
        family: str,
        table: str,
        chain: str,
        action: str,
        protocol: Optional[str] = None,
        port: Optional[str] = None,
        source: Optional[str] = None,
        destination: Optional[str] = None,
        comment: str = "",
    ) -> bool:
        """Add a firewall rule to nftables.

        Ensures the target chain exists (input, forward or output) before
        attempting to add the rule — see _ensure_chain().
        """
        self._ensure_chain(family=family, table=table, chain=chain)

        cmd = self._serializer.build_add_rule_command(
            family=family,
            table=table,
            chain=chain,
            action=action,
            protocol=protocol,
            port=port,
            source=source,
            destination=destination,
            comment=comment,
        )
        self._run_command(cmd)
        return True

    def delete_rule(
        self,
        family: str,
        table: str,
        chain: str,
        handle: int,
    ) -> bool:
        """Delete a firewall rule by handle."""
        cmd = self._serializer.build_delete_rule_command(family, table, chain, handle)
        self._run_command(cmd)
        return True

    def flush_chain(self, family: str, table: str, chain: str) -> bool:
        """Flush all rules from a chain."""
        cmd = self._serializer.build_flush_chain_command(family, table, chain)
        self._run_command(cmd)
        return True

    def flush_table(self, family: str, table: str) -> bool:
        """Flush all rules from a table."""
        cmd = self._serializer.build_flush_table_command(family, table)
        self._run_command(cmd)
        return True

    def flush(self) -> int:
        """Flush all rules from the backend (FirewallPort contract).

        Scoped to family="inet"/table="filter" ONLY — mirrors
        apply_preset()'s own documented reasoning: a global 'nft flush
        ruleset' destroys silently any table belonging to another tool
        on the same system (confirmed in real testing: applying an
        nftables profile globally wiped active iptables rules). Never
        touches other tables/families (notably 'ip'/'filter', owned by
        iptables-nft).

        Returns:
            Number of rules that were in scope immediately before flushing
            (0 if the table didn't exist yet — nothing to flush).
        """
        family, table = "inet", "filter"
        try:
            output = self._run_command(["nft", "-a", "list", "table", family, table])
        except NftCommandError as e:
            if "No such file or directory" in str(e) or "does not exist" in str(e):
                return 0
            raise
        count = len(self._parser.parse_ruleset(output))
        self.flush_table(family, table)
        return count

    def is_available(self) -> bool:
        """Check if nftables is available on the system."""
        try:
            self._run_command(["nft", "--version"])
            return True
        except (NftCommandError, NftPermissionError):
            return False

    # ------------------------------------------------------------------
    # Preset application / ruleset snapshot & restore (menu 3.4)
    # ------------------------------------------------------------------

    def dump_ruleset(self) -> str:
        """Return the current state of inet/filter as text, for snapshotting.

        Scoped to inet/filter ONLY — the one table this adapter (and
        apply_preset()/flush()) ever manages — NOT the full 'nft list
        ruleset' (all tables/families). A prior version dumped everything,
        which could include 'table ip filter' (iptables-nft's own compat
        view of live iptables state, including fail2ban's chains). That
        table uses xtables-compat expressions (e.g. 'xt match "conntrack"')
        that load_ruleset()'s 'nft -f -' loader cannot recreate — confirmed
        by a real incident where a full-ruleset snapshot/restore cycle
        wiped iptables/fail2ban protection with no way back. Scoping the
        dump at the source is what makes load_ruleset() safe to use.

        Returns:
            Raw output of 'nft list table inet filter', suitable for
            later re-injection via load_ruleset(). "" if the table
            doesn't exist yet (no preset ever applied through Omega-Fire).
        """
        try:
            return self._run_command(["nft", "list", "table", "inet", "filter"])
        except NftCommandError as e:
            if "No such file or directory" in str(e) or "does not exist" in str(e):
                return ""
            raise

    def _strip_ip_filter_table(self, content: str) -> str:
        """Remove any 'table ip filter { ... }' block from nft ruleset text.

        Defensive, on top of dump_ruleset() now being scoped at the
        source: a snapshot file written to disk by a version of this
        adapter predating that fix (see RUNTIME_DIR in
        application/commands/apply_preset.py) could still contain a full
        dump including this table. Reinjecting it would reproduce the
        exact same incident this method exists to prevent — table ip
        filter is nft's compat view of iptables-nft state (owned by
        IptablesAdapter, never something this adapter should touch),
        and its xtables-compat expressions cannot be reloaded via
        'nft -f -' regardless of how the flush itself was scoped.

        Args:
            content: Ruleset text, possibly containing table ip filter

        Returns:
            content with any table ip filter block (and its preceding
            "# Warning: ..." comment line, if present) removed.
        """
        lines = content.split("\n")
        result: list[str] = []
        in_ip_filter = False
        depth = 0

        for line in lines:
            stripped = line.strip()
            if not in_ip_filter and re.match(r"table\s+ip\s+filter\s*\{", stripped):
                in_ip_filter = True
                depth = line.count("{") - line.count("}")
                if result and result[-1].strip().startswith("# Warning"):
                    result.pop()
                continue
            if in_ip_filter:
                depth += line.count("{") - line.count("}")
                if depth <= 0:
                    in_ip_filter = False
                continue
            result.append(line)

        return "\n".join(result)

    def load_ruleset(self, content: str) -> bool:
        """Wipe and reload inet/filter from a previous dump_ruleset().

        Scoped to inet/filter ONLY — mirrors flush()'s own scoping.
        Never a global 'nft flush ruleset': that destroyed 'table ip
        filter' (iptables-nft's own compat table) in a real incident,
        with no way to recreate it afterward (see dump_ruleset()
        docstring). Also strips any table ip filter block that might
        still be present in content (e.g. from a snapshot file written
        before this fix) before reinjecting, as a second line of defense.

        Args:
            content: Ruleset text as previously produced by dump_ruleset()

        Returns:
            True if the reload succeeded.
        """
        try:
            self._run_command(["nft", "flush", "table", "inet", "filter"])
        except NftCommandError as e:
            if not ("No such file or directory" in str(e) or "does not exist" in str(e)):
                raise

        content = self._strip_ip_filter_table(content)
        if content.strip():
            self._run_command_with_input(["nft", "-f", "-"], content)
        return True

    def apply_preset(self, preset: FirewallPreset) -> bool:
        """Apply a domain-level FirewallPreset to nftables.

        Always flushes the entire ruleset first (a preset is a complete
        base policy, not an addition to whatever was active before).

        Uses family "inet" / table "filter" — the same space already
        used by every other Omega-Fire mechanism (3.1 rules, 2.1 bans).
        Previously used family "ip", which collides with the table
        iptables-nft manages for itself on systems where iptables is
        the iptables-nft compatibility layer (confirmed via 'nft list
        ruleset' showing "table ip filter is managed by iptables-nft,
        do not touch!") — restoring/removing rules in that table risked
        interfering with structures Omega-Fire does not own.

        Args:
            preset: The preset to translate and apply

        Returns:
            True if the preset was fully applied.
        """
        family = "inet"
        table = "filter"

        # Flush scopé à la SEULE table qu'Omega-Fire possède (inet
        # filter), jamais 'nft flush ruleset' (portée globale, toutes
        # tables/familles). Un flush global détruit silencieusement
        # toute table appartenant à un autre outil sur le même système
        # — notamment 'ip filter', gérée par iptables-nft dès qu'une
        # règle iptables a été posée (confirmé en test réel : appliquer
        # un profil nftables effaçait entièrement les règles iptables
        # actives, sans qu'Omega-Fire n'ait jamais eu l'intention d'y
        # toucher).
        try:
            self._run_command(["nft", "flush", "table", family, table])
        except NftCommandError as e:
            # Table pas encore créée (première utilisation) : rien à
            # vider, on continue normalement vers sa création.
            if not ("No such file or directory" in str(e) or "does not exist" in str(e)):
                raise

        try:
            self._run_command(["nft", "add", "table", family, table])
        except NftCommandError as e:
            if not ("File exists" in str(e) or "already exists" in str(e)):
                raise

        for chain_policy in preset.chain_policies:
            chain_name = chain_policy.chain.value
            policy_word = chain_policy.default_action.value
            cmd = [
                "nft", "add", "chain", family, table, chain_name,
                f"{{ type filter hook {chain_name} priority 0; policy {policy_word}; }}",
            ]
            # Une chaîne de base (input/output/forward) peut déjà exister
            # dans cette table — notamment posée par _ensure_chain() si
            # le menu 3.1 a déjà été utilisé. Une redéclaration avec le
            # même type/hook/priority mais une policy différente est
            # acceptée par nft et met à jour la policy (vérifié : add
            # chain sur chaîne existante, même hook, policy différente
            # -> policy effectivement changée, aucune erreur). Seule une
            # déclaration structurellement différente (type/hook
            # different) échoue avec "already exists ... different
            # declaration" — dans ce cas de figure improbable ici, on
            # n'interrompt pas l'application du reste du profil.
            try:
                self._run_command(cmd)
            except NftCommandError as e:
                if not ("already exists" in str(e)):
                    raise

        for rule in preset.rules:
            for cmd in self._build_preset_rule_commands(family, table, rule):
                self._run_command(cmd)

        return True

    def _resolve_policy(self, policy_name: str) -> Optional[FirewallPreset]:
        """Resolve a policy_name against domain.rules.presets.PRESETS.

        Matches by exact key ("1"-"9") or exact name, case-insensitive.
        Never consulted core/policies.py's separate Policy/PolicyName
        system — confirmed to have zero real callers anywhere in src/,
        an independent orphaned duplication, since removed (referentiel
        §39, 2026-08-17).
        """
        normalized = policy_name.strip().lower()
        for preset in list_presets():
            if preset.key == policy_name or preset.name.lower() == normalized:
                return preset
        return None

    def apply_policy(self, policy_name: str) -> int:
        """Apply a predefined policy by name (FirewallPort contract).

        Resolves against the live preset system already backing menu 3.4
        (domain.rules.presets.PRESETS), then delegates to apply_preset() —
        introduces no new nft translation logic. Resolution happens before
        any mutation: an unknown policy_name raises without touching the
        live ruleset at all.

        Args:
            policy_name: Preset key ("1"-"9") or exact name (case-insensitive)

        Returns:
            Number of individual nft rules issued (post port-explosion —
            see _build_preset_rule_commands()), not len(preset.rules).

        Raises:
            PolicyNotFoundError: If policy_name matches no known preset
        """
        preset = self._resolve_policy(policy_name)
        if preset is None:
            raise PolicyNotFoundError(
                policy_name, "aucun profil FirewallPreset ne correspond (domain/rules/presets.py)"
            )
        self.apply_preset(preset)
        return sum(len(self._build_preset_rule_commands("inet", "filter", r)) for r in preset.rules)

    def set_chain_policy(
        self,
        chain_name: str,
        policy: str = "accept",
        family: str = "inet",
        table: str = "filter",
    ) -> bool:
        """Set (or reset) the default policy of a base chain.

        Uses the same mechanism as apply_preset(): declaring a chain
        with the same type/hook/priority but a different policy updates
        the policy in place without affecting existing rules (verified
        manually: no error, no rule loss). If the chain doesn't exist
        yet, it is created with this policy. Creates the table first
        if needed, mirroring apply_preset()'s own table handling.

        Args:
            chain_name: Base chain name (input, output, forward)
            policy: Target policy ("accept" or "drop")
            family: Address family (default: "inet", Omega-Fire's own
                space — never "ip", which nftables-nft manages for
                itself on iptables-nft systems)
            table: Table name (default: "filter")

        Returns:
            True if the policy was applied.
        """
        try:
            self._run_command(["nft", "add", "table", family, table])
        except NftCommandError as e:
            if not ("File exists" in str(e) or "already exists" in str(e)):
                raise

        cmd = [
            "nft", "add", "chain", family, table, chain_name,
            f"{{ type filter hook {chain_name} priority 0; policy {policy}; }}",
        ]
        try:
            self._run_command(cmd)
        except NftCommandError as e:
            if not ("already exists" in str(e)):
                raise
        return True

    def _build_preset_rule_commands(self, family: str, table: str, rule: PresetRule) -> list[list[str]]:
        """Translate a domain PresetRule into one or more nft add-rule commands.

        A PresetRule with multiple ports (e.g. ports=[22, 80, 443]) is
        exploded into one independent nft rule per port rather than a
        single rule with a grouped port set ('dport { 22, 80, 443 }').
        This keeps every applied port individually manageable afterwards
        (menu 3.2 delete, menu 7.2 restore) — a grouped rule can only be
        deleted or restored as a whole, never adjusted port by port.
        """
        chain_name = rule.chain.value

        # Un port à la fois : la liste du profil si elle existe, sinon
        # [None] pour ne construire qu'une seule commande (cas sans
        # port, ex. loopback_only, match_established, ICMP).
        ports_to_apply: list[Optional[int]] = list(rule.ports) if rule.ports else [None]

        commands: list[list[str]] = []

        for single_port in ports_to_apply:
            cmd = ["nft", "add", "rule", family, table, chain_name]

            if rule.loopback_only:
                iface_kw = "iifname" if rule.chain == RuleChain.INPUT else "oifname"
                cmd.extend([iface_kw, "lo"])

            if rule.match_established:
                cmd.extend(["ct", "state", "established,related"])

            if rule.protocol and single_port is None:
                # "ip protocol" (IPv4-only) aligné sur "meta l4proto" —
                # même forme dual-stack-safe déjà utilisée par
                # NftSerializer.build_add_rule_command() pour ce même cas
                # (protocole seul, sans port) ; les deux chemins étaient
                # incohérents avant ce correctif (référentiel §50).
                cmd.extend(["meta", "l4proto", rule.protocol.value])
            elif rule.protocol and single_port is not None:
                cmd.extend([rule.protocol.value, "dport", str(single_port)])

            if rule.source_cidr:
                cmd.extend([addr_family_keyword(rule.source_cidr), "saddr", rule.source_cidr])

            if rule.dest_cidr:
                cmd.extend([addr_family_keyword(rule.dest_cidr), "daddr", rule.dest_cidr])

            cmd.append(rule.action.value)
            commands.append(cmd)

        return commands

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Implémente les opérations concrètes nftables via subprocess
# - Point d'entrée unique pour toutes les interactions avec nft
# - Coordonne parser, serializer et mapper pour la transformation des données
# - Retourne des objets du domaine (FirewallRule, BanEntry)
# - Applique les profils prédéfinis (menu 3.4) et gère snapshot/restore
#   du ruleset complet
# Pourquoi dans infrastructure/ (charte) :
# - C'est le SEUL module autorisé à appeler nft via subprocess
# - Implémente les contrats que l'application/ utilisera via les ports
# - L'application/ ne doit JAMAIS importer ce module directement
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de validation de règles, pas de politiques —
#    les politiques elles-mêmes viennent de domain/rules/presets.py)
# ❌ Pas de dépendance vers application/ ou interfaces/
# ❌ Pas de décision de grisage ou d'autorisation
# Points clés :
# - NftablesAdapter : classe principale avec timeout configurable
# - _run_command() / _run_command_with_input() : exécution nft (stdout
#   simple ou avec contenu stdin, pour load_ruleset)
# - _ensure_blackhole_set() : garantit table/set/chaîne input pour le ban
# - _ensure_chain() : garantit l'existence d'une chaîne de base (input,
#   forward, output) avant l'ajout d'une règle utilisateur (menu 3.1)
# - ban_ip() / unban_ip() : ajoute/supprime une IP du set blacklist
# - list_rules() / list_bans() : lecture de l'état live
# - add_rule() / delete_rule() : gestion individuelle d'une règle (menu 3.1/3.2)
# - dump_ruleset() : 'nft list ruleset' -> texte, pour snapshot (menu 3.4)
# - load_ruleset(content) : flush + 'nft -f -' -> restauration depuis un
#   snapshot, jamais de cumul (menu 3.4, option [R])
# - apply_preset(preset) : flush + traduit un FirewallPreset (domain/rules/
#   presets.py) en table/chaînes/règles nft (menu 3.4)
# - _build_preset_rule_commands() : traduit une PresetRule (loopback_only,
#   match_established, protocole, ports multiples, source/destination) en
#   arguments nft
# - is_available() : vérifie que nft est installé
# Comment il sera utilisé (aperçu) :
# - ports/firewall.py définira le contrat que cet adapter implémente
# - app/bootstrap.py instanciera cet adapter et l'injectera via les ports
# - application/commands/create_rule.py utilise add_rule() (menu 3.1)
# - application/commands/apply_preset.py utilise apply_preset()/dump_ruleset() (menu 3.4)
#---------------------------------------------------------------------->
