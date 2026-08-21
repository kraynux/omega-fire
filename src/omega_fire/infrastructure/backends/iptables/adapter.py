# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Iptables backend adapter.

Implements the concrete iptables operations: ban, unban, list rules,
list bans, flush, preset application, ruleset snapshot/restore. Uses
subprocess to execute iptables commands.
"""
import ipaddress
import re
import shlex
import subprocess
from typing import Optional, Union
from omega_fire.domain.rules.models import FirewallRule, RuleChain
from omega_fire.domain.rules.presets import FirewallPreset, PresetRule, list_presets
from omega_fire.domain.rules.exceptions import PolicyNotFoundError
from omega_fire.domain.ip_blacklist.models import BanEntry
from omega_fire.domain.ip_blacklist.exceptions import (
    IPAlreadyBannedError,
    IPFamilyMismatchError,
    IPNotFoundError,
)
from omega_fire.shared.networking import IPAddress
from omega_fire.ports.firewall import FirewallStats
from omega_fire.infrastructure.backends.iptables.parser import IptParser
from omega_fire.infrastructure.backends.iptables.serializer import IptSerializer
from omega_fire.infrastructure.backends.iptables.mapper import IptMapper
from omega_fire.infrastructure.backends.iptables.exceptions import (
    IptCommandError,
    IptPermissionError,
)


class IptablesAdapter:
    """Concrete adapter for iptables operations."""

    def __init__(self, timeout: float = 10.0):
        self._parser = IptParser()
        self._serializer = IptSerializer()
        self._mapper = IptMapper()
        self._timeout = timeout

    def _run_command(self, cmd: list[str]) -> str:
        """Execute an iptables command and return stdout."""
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
                    raise IptPermissionError(operation=" ".join(cmd[:3]))
                raise IptCommandError(
                    command=" ".join(cmd),
                    returncode=result.returncode,
                    stderr=stderr,
                )

            return result.stdout

        except subprocess.TimeoutExpired:
            raise IptCommandError(
                command=" ".join(cmd),
                returncode=-1,
                stderr=f"Command timed out after {self._timeout}s",
            )
        except FileNotFoundError:
            raise IptCommandError(
                command=" ".join(cmd),
                returncode=-1,
                stderr="iptables binary not found",
            )

    def _run_command_with_input(self, cmd: list[str], input_text: str) -> str:
        """Execute a command feeding it stdin content (used by load_ruleset)."""
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
                    raise IptPermissionError(operation=" ".join(cmd[:3]))
                raise IptCommandError(
                    command=" ".join(cmd),
                    returncode=result.returncode,
                    stderr=stderr,
                )

            return result.stdout

        except subprocess.TimeoutExpired:
            raise IptCommandError(
                command=" ".join(cmd),
                returncode=-1,
                stderr=f"Command timed out after {self._timeout}s",
            )
        except FileNotFoundError:
            raise IptCommandError(
                command=" ".join(cmd),
                returncode=-1,
                stderr=f"{cmd[0]} binary not found",
            )

    def ban_ip(self, ip: Union[str, list[str]], chain: str = "INPUT", comment: str = "") -> bool:
        """Ban one or multiple IP addresses using iptables."""
        ip_list = []
        if isinstance(ip, list):
            ip_list = [i.strip() for i in ip if i.strip()]
        elif isinstance(ip, str):
            ip_list = [i.strip() for i in re.split(r"[,\s]+", ip) if i.strip()]

        if not ip_list:
            return False

        success = True
        for single_ip in ip_list:
            # iptables ne peut représenter que de l'IPv4 (contrairement à
            # nftables) — une IPv6 glissée ici (ex. jail fail2ban mixte)
            # doit échouer proprement plutôt que produire une commande
            # incompatible (plan IPv6 iptables, référentiel §53, Phase B).
            try:
                if ipaddress.ip_address(single_ip).version != 4:
                    success = False
                    continue
            except ValueError:
                success = False
                continue

            try:
                cmd = self._serializer.build_ban_command(ip=single_ip, chain=chain, comment=comment)
                self._run_command(cmd)
            except IptCommandError:
                success = False

        return success

    def unban_ip(self, ip: Union[str, list[str]], chain: str = "INPUT") -> bool:
        """Unban one or multiple IP addresses using iptables."""
        ip_list = []
        if isinstance(ip, list):
            ip_list = [i.strip() for i in ip if i.strip()]
        elif isinstance(ip, str):
            ip_list = [i.strip() for i in re.split(r"[,\s]+", ip) if i.strip()]

        if not ip_list:
            return False

        overall_success = True

        for single_ip in ip_list:
            try:
                if ipaddress.ip_address(single_ip).version != 4:
                    overall_success = False
                    continue
            except ValueError:
                overall_success = False
                continue

            try:
                cmd = self._serializer.build_unban_command(ip=single_ip, chain=chain)
                self._run_command(cmd)
                continue
            except IptCommandError:
                pass

            try:
                list_cmd = ["iptables", "-L", chain, "-n", "--line-numbers"]
                output = self._run_command(list_cmd)

                matching_lines = []
                for line in output.splitlines():
                    parts = line.split()
                    if len(parts) >= 5 and parts[1] == "DROP" and (parts[4] == single_ip or parts[4].startswith(f"{single_ip}/")):
                        if parts[0].isdigit():
                            matching_lines.append(int(parts[0]))

                if not matching_lines:
                    overall_success = False
                    continue

                matching_lines.sort(reverse=True)
                for line_num in matching_lines:
                    del_cmd = self._serializer.build_delete_rule_command(chain, line_num)
                    self._run_command(del_cmd)

            except Exception:
                overall_success = False

        return overall_success

    def is_ip_banned(self, ip: IPAddress) -> bool:
        """Check if an IP is currently banned (FirewallPort contract).

        Composes list_bans() at its default scope (chain=INPUT) — the
        same default ban_ip() itself uses.

        Args:
            ip: IP address to check

        Returns:
            True if a DROP rule for this IP exists on the chain.

        Raises:
            IPFamilyMismatchError: If ip is not IPv4 — this adapter only
                ever represents the iptables (v4) backend (référentiel §53).
        """
        if ip.version != 4:
            raise IPFamilyMismatchError(str(ip), expected_version=4, backend="iptables")
        ip_str = str(ip)
        return any(b.ip.split("/")[0] == ip_str for b in self.list_bans())

    def ban_single_ip(self, ip: IPAddress, *, reason: str = "") -> None:
        """Ban a single IP (FirewallPort.ban_ip contract).

        Coexists with ban_ip() (batch, bool return) — does not replace it;
        BanIpCommand and its existing callers are unaffected.

        Args:
            ip: IP address to ban
            reason: Ban reason, stored as the iptables rule comment

        Raises:
            IPAlreadyBannedError: If the IP is already banned on iptables
        """
        ip_str = str(ip)
        if self.is_ip_banned(ip):
            raise IPAlreadyBannedError(ip_str, "iptables")
        cmd = self._serializer.build_ban_command(ip=ip_str, chain="INPUT", comment=reason)
        self._run_command(cmd)

    def unban_single_ip(self, ip: IPAddress) -> None:
        """Unban a single IP (FirewallPort.unban_ip contract).

        Coexists with unban_ip() (batch, bool return) — does not replace
        it; UnbanIpCommand and its existing callers are unaffected.

        Tries direct '-D' deletion first; falls back to line-number-based
        deletion on failure — confirmed by real testing that this is not
        an edge case: build_unban_command() never reconstructs the '-m
        comment --comment ...' clause build_ban_command() adds whenever a
        reason is given, so a direct '-D' with a plain "-s ip -j DROP"
        spec never matches a commented rule ("Bad rule" from iptables).
        This mirrors the same fallback unban_ip() (the batch method)
        already has, for the identical reason.

        Args:
            ip: IP address to unban

        Raises:
            IPNotFoundError: If the IP is not currently banned on iptables
        """
        ip_str = str(ip)
        if not self.is_ip_banned(ip):
            raise IPNotFoundError(ip_str)

        try:
            cmd = self._serializer.build_unban_command(ip=ip_str, chain="INPUT")
            self._run_command(cmd)
            return
        except IptCommandError:
            pass

        list_cmd = ["iptables", "-L", "INPUT", "-n", "--line-numbers"]
        output = self._run_command(list_cmd)

        matching_lines = []
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[1] == "DROP" and (parts[4] == ip_str or parts[4].startswith(f"{ip_str}/")):
                if parts[0].isdigit():
                    matching_lines.append(int(parts[0]))

        if not matching_lines:
            raise IPNotFoundError(ip_str)

        matching_lines.sort(reverse=True)
        for line_num in matching_lines:
            del_cmd = self._serializer.build_delete_rule_command("INPUT", line_num)
            self._run_command(del_cmd)

    def list_rules(self, chain: str = "") -> list[FirewallRule]:
        """List all firewall rules from iptables."""
        cmd = self._serializer.build_list_command(chain)
        output = self._run_command(cmd)
        parsed = self._parser.parse_rules_save(output)
        return self._mapper.map_rules(parsed)

    def list_bans(self, chain: str = "INPUT") -> list[BanEntry]:
        """List all banned IPs from iptables."""
        cmd = self._serializer.build_list_command(chain)
        output = self._run_command(cmd)
        ips = self._parser.parse_ban_list(output)
        return self._mapper.map_bans(ips)

    def get_stats(self) -> FirewallStats:
        """Get aggregate firewall statistics (FirewallPort contract).

        Uses IptParser.parse_rules_verbose() (already present, previously
        unused by any adapter method) against 'iptables -L -n -v' —
        list_rules() itself uses '-S' (iptables-save format), which has
        no counters at all. Unlike NftablesAdapter.get_stats(), no
        'counter keyword' caveat here: iptables tracks per-rule packet/
        byte counters unconditionally, no opt-in syntax required.

        Returns:
            FirewallStats with counters aggregated from the live ruleset.
        """
        try:
            output = self._run_command(self._serializer.build_list_verbose_command())
        except IptCommandError:
            return FirewallStats(0, 0, 0, 0, 0)

        parsed = self._parser.parse_rules_verbose(output)

        return FirewallStats(
            total_rules=len(parsed),
            total_packets=sum(p.get("packets", 0) for p in parsed),
            total_bytes=sum(p.get("bytes", 0) for p in parsed),
            dropped_packets=sum(p.get("packets", 0) for p in parsed if p.get("action") == "drop"),
            accepted_packets=sum(p.get("packets", 0) for p in parsed if p.get("action") == "accept"),
        )

    def add_rule(
        self,
        chain: str,
        action: str,
        protocol: Optional[str] = None,
        port: Optional[str] = None,
        source: Optional[str] = None,
        destination: Optional[str] = None,
        comment: str = "",
    ) -> bool:
        """Add a firewall rule to iptables."""
        cmd = self._serializer.build_add_rule_command(
            chain=chain, action=action, protocol=protocol,
            port=port, source=source, destination=destination, comment=comment,
        )
        self._run_command(cmd)
        return True

    def delete_rule(self, chain: str, rule_num: int) -> bool:
        """Delete a firewall rule by number."""
        cmd = self._serializer.build_delete_rule_command(chain, rule_num)
        self._run_command(cmd)
        return True

    def delete_rule_by_content(self, raw_line: str) -> bool:
        """Delete a rule using its exact iptables-save specification.

        iptables supports deleting a rule by its full specification
        ("-A ..." replaced with "-D ...") rather than only by numeric
        line index, which is unstable.

        Args:
            raw_line: The raw rule specification as produced by
                'iptables -S', e.g. "-A INPUT -p tcp --dport 22 -j DROP".

        Returns:
            True if the deletion command succeeded.

        Raises:
            IptCommandError: If raw_line is not a valid "-A ..." specification,
                or if the underlying iptables command fails.
        """
        if not raw_line or not raw_line.strip().startswith("-A "):
            raise IptCommandError(
                command=raw_line or "",
                returncode=-1,
                stderr="Invalid rule specification for deletion (expected '-A ...' format)",
            )

        # shlex.split (et non .split() naïf) : respecte les guillemets,
        # indispensable pour les commentaires contenant des espaces.
        args = shlex.split(raw_line.strip())
        args[0] = "-D"
        cmd = ["iptables"] + args

        self._run_command(cmd)
        return True

    def flush_chain(self, chain: str) -> bool:
        """Flush all rules from a chain."""
        cmd = self._serializer.build_flush_chain_command(chain)
        self._run_command(cmd)
        return True

    def flush_all(self) -> bool:
        """Flush all rules from all chains."""
        cmd = self._serializer.build_flush_all_command()
        self._run_command(cmd)
        return True

    def flush(self) -> int:
        """Flush all rules from the backend (FirewallPort contract).

        Mirrors flush_all() (all built-in chains of the filter table) —
        no multi-tool-table ambiguity here unlike NftablesAdapter.flush():
        this adapter only ever touches the standard 'filter' table, never
        a custom table another tool might own.

        Returns:
            Number of rules that were in scope immediately before flushing.
        """
        try:
            rules = self.list_rules()
        except IptCommandError:
            rules = []
        count = len(rules)
        self.flush_all()
        return count

    def is_available(self) -> bool:
        """Check if iptables is available on the system."""
        try:
            self._run_command(["iptables", "--version"])
            return True
        except (IptCommandError, IptPermissionError):
            return False

    # ------------------------------------------------------------------
    # Preset application / ruleset snapshot & restore (menu 3.4)
    # ------------------------------------------------------------------

    def dump_ruleset(self) -> str:
        """Return the full current ruleset as text, for snapshotting.

        Returns:
            Raw output of 'iptables-save', suitable for later
            re-injection via load_ruleset().
        """
        return self._run_command(["iptables-save"])

    def load_ruleset(self, content: str) -> bool:
        """Wipe the current ruleset and reload it from a previous dump.

        iptables-restore replaces (rather than merges into) the tables
        present in the given content by default, but the filter table is
        explicitly flushed first as well for symmetry with the nftables
        adapter and to guarantee no cumulation regardless of content shape.

        Args:
            content: Ruleset text as previously produced by dump_ruleset()

        Returns:
            True if the reload succeeded.
        """
        try:
            self._run_command(["iptables", "-F"])
            self._run_command(["iptables", "-X"])
        except IptCommandError:
            pass

        if content.strip():
            self._run_command_with_input(["iptables-restore"], content)
        return True

    def apply_preset(self, preset: FirewallPreset) -> bool:
        """Apply a domain-level FirewallPreset to iptables.

        Always flushes the filter table first (a preset is a complete
        base policy, not an addition to whatever was active before).

        Args:
            preset: The preset to translate and apply

        Returns:
            True if the preset was fully applied.
        """
        self._run_command(["iptables", "-F"])
        self._run_command(["iptables", "-X"])

        for chain_policy in preset.chain_policies:
            chain_name = chain_policy.chain.value.upper()
            policy_word = chain_policy.default_action.value.upper()
            if policy_word not in ("ACCEPT", "DROP"):
                # Les chaînes intégrées iptables n'acceptent que ACCEPT/DROP
                # comme politique par défaut (pas REJECT/LOG).
                policy_word = "DROP"
            self._run_command(["iptables", "-P", chain_name, policy_word])

        for rule in preset.rules:
            for cmd in self._build_preset_rule_commands(rule):
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
        introduces no new iptables translation logic. Resolution happens
        before any mutation: an unknown policy_name raises without
        touching the live ruleset at all.

        Args:
            policy_name: Preset key ("1"-"9") or exact name (case-insensitive)

        Returns:
            Number of individual iptables rules issued (post
            port-explosion — see _build_preset_rule_commands()), not
            len(preset.rules).

        Raises:
            PolicyNotFoundError: If policy_name matches no known preset
        """
        preset = self._resolve_policy(policy_name)
        if preset is None:
            raise PolicyNotFoundError(
                policy_name, "aucun profil FirewallPreset ne correspond (domain/rules/presets.py)"
            )
        self.apply_preset(preset)
        return sum(len(self._build_preset_rule_commands(r)) for r in preset.rules)

    def set_chain_policy(self, chain_name: str, policy: str = "ACCEPT") -> bool:
        """Set (or reset) the default policy of a base chain.

        Args:
            chain_name: Base chain name, case-insensitive (input,
                output, forward)
            policy: Target policy ("ACCEPT" or "DROP")

        Returns:
            True if the policy was applied.
        """
        self._run_command(["iptables", "-P", chain_name.upper(), policy.upper()])
        return True

    def _build_preset_rule_commands(self, rule: PresetRule) -> list[list[str]]:
        """Translate a domain PresetRule into one or more iptables append commands.

        A PresetRule with multiple ports (e.g. ports=[22, 80, 443]) is
        exploded into one independent iptables rule per port (--dport)
        rather than a single rule using '-m multiport --dports 22,80,443'.
        This mirrors the nftables adapter and keeps every applied port
        individually manageable afterwards (menu 3.2 delete, menu 7.2
        restore) — a multiport rule can only be deleted or restored as a
        whole, never adjusted port by port.
        """
        chain_name = rule.chain.value.upper()
        ports_to_apply: list[Optional[int]] = list(rule.ports) if rule.ports else [None]

        commands: list[list[str]] = []

        for single_port in ports_to_apply:
            cmd = ["iptables", "-A", chain_name]

            if rule.loopback_only:
                iface_flag = "-i" if rule.chain == RuleChain.INPUT else "-o"
                cmd.extend([iface_flag, "lo"])

            if rule.match_established:
                cmd.extend(["-m", "state", "--state", "ESTABLISHED,RELATED"])

            if rule.protocol and single_port is None:
                cmd.extend(["-p", rule.protocol.value])
            elif rule.protocol and single_port is not None:
                cmd.extend(["-p", rule.protocol.value, "--dport", str(single_port)])

            if rule.source_cidr:
                cmd.extend(["-s", rule.source_cidr])

            if rule.dest_cidr:
                cmd.extend(["-d", rule.dest_cidr])

            cmd.extend(["-j", rule.action.value.upper()])
            commands.append(cmd)

        return commands


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Implémente les opérations concrètes iptables via subprocess
# - Miroir de nftables/adapter.py mais pour iptables
# - Point d'entrée unique pour toutes les interactions avec iptables
# - Applique les profils prédéfinis (menu 3.4) et gère snapshot/restore
#   du ruleset complet
# Pourquoi dans infrastructure/ (charte) :
# - SEUL module autorisé à appeler iptables via subprocess
# - Implémente les contrats que l'application/ utilisera via les ports
# - L'application/ ne doit JAMAIS importer ce module directement
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier, pas de dépendance vers application/ ou interfaces/
#    (les politiques elles-mêmes viennent de domain/rules/presets.py)
# Points clés :
# - IptablesAdapter : ban_ip, unban_ip, list_rules, list_bans, add_rule,
#   delete_rule, delete_rule_by_content, flush_chain, flush_all, is_available
# - dump_ruleset() : 'iptables-save' -> texte, pour snapshot (menu 3.4)
# - load_ruleset(content) : flush (-F -X) + 'iptables-restore' -> restauration
#   depuis un snapshot, jamais de cumul (menu 3.4, option [R])
# - apply_preset(preset) : flush + traduit un FirewallPreset (domain/rules/
#   presets.py) en politiques de chaîne + règles iptables (menu 3.4)
# - _build_preset_rule_commands() : traduit une PresetRule (loopback_only,
#   match_established, protocole, ports multiples via -m multiport,
#   source/destination) en arguments iptables
# - delete_rule_by_content() : suppression par spécification complète
#   ("-A ..." → "-D ..."), stable car indépendante de la position de la
#   règle dans la chaîne (utilisée par 3.2 pour les règles managed)
# Comment il sera utilisé (aperçu) :
# - ports/firewall.py définira le contrat que cet adapter implémente
# - app/bootstrap.py instanciera cet adapter et l'injectera via les ports
# - application/commands/apply_preset.py utilise apply_preset()/dump_ruleset() (menu 3.4)
# - application/commands/restore_preset_state.py utilise load_ruleset() (menu 3.4)
#---------------------------------------------------------------------->
