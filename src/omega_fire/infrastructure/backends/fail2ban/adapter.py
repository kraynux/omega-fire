# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban backend adapter.

Implements the concrete fail2ban operations: list jails, get status,
ban/unban IPs in jails. Uses subprocess to execute fail2ban-client commands.

This is the only module that directly calls fail2ban-client via subprocess.
"""
import os
import re
import sqlite3
import subprocess
import time
from typing import Optional, Any
from omega_fire.infrastructure.backends.fail2ban.parser import Fail2banParser
from omega_fire.infrastructure.backends.fail2ban.exceptions import (
    Fail2banCommandError,
    JailNotFoundError,
    Fail2banPermissionError,
)
from omega_fire.infrastructure.backends.fail2ban.service_controller import Fail2banServiceController
from omega_fire.infrastructure.backends.fail2ban.history_reader import DEFAULT_F2B_DB_PATH
from omega_fire.ports.fail2ban import JailInfo, JailStatus
from omega_fire.shared.networking import IPAddress
from omega_fire.domain.fail2ban.exceptions import (
    JailNotFoundError as DomainJailNotFoundError,
    JailAlreadyExistsError as DomainJailAlreadyExistsError,
    IPAlreadyBannedError,
    IPNotFoundError,
)


class Fail2banAdapter:
    """Concrete adapter for fail2ban operations.

    Executes fail2ban-client commands via subprocess and transforms results
    into domain models using parser.
    """

    def __init__(
        self,
        timeout: float = 10.0,
        service_manager: Optional[Any] = None,
        service_controller: Optional[Fail2banServiceController] = None,
    ):
        """Initialize the fail2ban adapter.
        Args:
            timeout: Maximum time for command execution (seconds)
            service_manager: Optional ServiceManager instance, used by
                future features (menu 6.4) to check the fail2ban
                service's running state via systemd/openrc/runit,
                independently of whether fail2ban-client responds.
                Not yet used by this adapter's current methods.
            service_controller: Optional Fail2banServiceController, used
                by stop_service()/restart_service()/enable_service()
                (Fail2banPort contract). Self-constructed if omitted —
                construction is cheap, service-manager detection is lazy
                on first actual use.
        """
        self._parser = Fail2banParser()
        self._timeout = timeout
        self._service_manager = service_manager
        self._service_controller = service_controller or Fail2banServiceController()

    def _run_command(self, cmd: list[str]) -> str:
        """Execute a fail2ban-client command and return stdout.

        Args:
            cmd: Command as list of arguments

        Returns:
            Command stdout as string

        Raises:
            Fail2banCommandError: If the command fails
            Fail2banPermissionError: If permission is denied
        """
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
                    raise Fail2banPermissionError(operation=" ".join(cmd[:3]))
                raise Fail2banCommandError(
                    command=" ".join(cmd),
                    returncode=result.returncode,
                    stderr=stderr,
                )

            return result.stdout

        except subprocess.TimeoutExpired:
            raise Fail2banCommandError(
                command=" ".join(cmd),
                returncode=-1,
                stderr=f"Command timed out after {self._timeout}s",
            )
        except FileNotFoundError:
            raise Fail2banCommandError(
                command=" ".join(cmd),
                returncode=-1,
                stderr="fail2ban-client binary not found",
            )

    def _run_raw(self, cmd: list[str]) -> subprocess.CompletedProcess:
        """Execute a fail2ban-client command without raising on non-zero exit.

        Unlike _run_command, a failing return code here is a normal,
        expected outcome (e.g. config validation reporting errors), not
        an infrastructure failure — the caller inspects the result itself.

        Args:
            cmd: Command as list of arguments

        Returns:
            The completed subprocess.CompletedProcess (stdout/stderr/returncode)

        Raises:
            Fail2banCommandError: If the command times out or the binary is missing
        """
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise Fail2banCommandError(
                command=" ".join(cmd),
                returncode=-1,
                stderr=f"Command timed out after {self._timeout}s",
            )
        except FileNotFoundError:
            raise Fail2banCommandError(
                command=" ".join(cmd),
                returncode=-1,
                stderr="fail2ban-client binary not found",
            )

    def _translate_not_found(self, jail_name: str, error: Fail2banCommandError) -> None:
        """Re-raise a command failure as a domain JailNotFoundError if the
        stderr indicates the jail doesn't exist; otherwise re-raise as-is.

        Always raises — either the translated error or the original one.

        Args:
            jail_name: Name of the jail the failing command targeted
            error: The Fail2banCommandError caught from _run_command

        Raises:
            DomainJailNotFoundError: If stderr indicates a missing jail
            Fail2banCommandError: The original error otherwise
        """
        stderr = (error.stderr or "").lower()
        if "not found" in stderr or "no jail" in stderr:
            raise DomainJailNotFoundError(jail_name) from error
        # Format réel observé sur ce fail2ban-client pour un jail absent :
        # "NOK: ('nom-jail',)" — ne contient ni "not found" ni "no jail",
        # confirmé par test réel (référentiel §18/§45). Le nom du jail est
        # exigé en plus du préfixe "nok" pour ne traduire que les échecs
        # NOK qui référencent bien CE jail, pas tout échec NOK générique.
        if stderr.strip().startswith("nok") and jail_name.lower() in stderr:
            raise DomainJailNotFoundError(jail_name) from error
        raise error

    def _to_ip_list(self, raw_ips: list[str]) -> list[IPAddress]:
        """Convert raw IP strings to validated IPAddress value objects.

        Args:
            raw_ips: Raw IP address strings (e.g. from parser output)

        Returns:
            List of IPAddress objects; malformed entries are skipped.
        """
        result = []
        for raw in raw_ips:
            try:
                result.append(IPAddress(raw))
            except ValueError:
                continue
        return result

    def _get_config_best_effort(self, jail_name: str, param: str, default: str) -> str:
        """Fetch a jail configuration parameter, falling back to a default.

        Used to enrich JailInfo with optional fields (filter, log path,
        maxretry, bantime, findtime) where a lookup failure shouldn't
        abort the whole listing.

        Args:
            jail_name: Name of the jail
            param: Parameter name (e.g. "maxretry", "bantime")
            default: Value to return if the lookup fails

        Returns:
            The parameter value, or default on any failure.
        """
        try:
            return self.get_jail_config(jail_name, param)
        except Exception:
            return default

    _DURATION_MULTIPLIERS = {
        "": 1,
        "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
        "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
        "h": 3600, "hour": 3600, "hours": 3600,
        "d": 86400, "day": 86400, "days": 86400,
        "w": 604800, "week": 604800, "weeks": 604800,
        "mo": 2592000, "month": 2592000, "months": 2592000,
        "y": 31536000, "year": 31536000, "years": 31536000,
    }

    def _parse_duration_to_seconds(self, value: str) -> Optional[str]:
        """Convert a fail2ban human-readable duration ("24h", "1h",
        "15m", "1w", or a combination like "1h30m") to seconds, as a
        string — matching the form `fail2ban-client get <jail> bantime`
        already returns, so downstream code expecting a plain digit
        string doesn't need to know the on-disk value could be anything
        else.

        Real finding, not theoretical: this project's own jail.d/*.conf
        files on the dev machine use "24h"/"1h" for bantime, not raw
        seconds — a naive regex reading the file verbatim would let
        "24h" through unchanged, and JailInfo.ban_time's
        `int(x) if x.isdigit() else 0` conversion would then silently
        collapse it to 0 instead of raising or falling back.

        Covers fail2ban's common suffixes (s/sec(s)/second(s),
        m/min(s)/minute(s), h/hour(s), d/day(s), w/week(s), and
        mo/month(s), y/year(s) as calendar-approximate 30/365-day
        units) and sums multiple tokens (e.g. "1h30m"). Not a full
        reimplementation of fail2ban's own Utils.str2seconds — no
        locale variants beyond these, and the -1/-2 sentinels are the
        caller's concern (already digits, returned as-is here).

        Args:
            value: Raw string as written in the config file.

        Returns:
            Seconds as a string, or None if the value can't be parsed
            at all — the caller must then omit the field rather than
            guess.
        """
        value = value.strip()
        if value.lstrip("-").isdigit():
            return value  # already raw seconds (or a sentinel like -1/-2)

        tokens = re.findall(r"(\d+)\s*([a-zA-Z]*)", value)
        if not tokens:
            return None

        total = 0
        for number, unit in tokens:
            multiplier = self._DURATION_MULTIPLIERS.get(unit.lower())
            if multiplier is None:
                return None
            total += int(number) * multiplier
        return str(total)

    def _extract_section_block(self, content: str, name: str) -> Optional[str]:
        """Return the raw text of the `[name]` section within a
        fail2ban-style ini file — from its `[name]` header to the next
        `[...]` header (any section, including `[DEFAULT]`) or EOF.

        Needed because a single jail.d file can define several jails as
        separate `[section]` blocks (e.g. this project's own
        honeypot.conf on the machine that surfaced this — referentiel
        §82.4), not just the one-file-per-jail convention
        create_jail()/delete_jail() use. `[DEFAULT]` is deliberately
        never matched as a stand-in for `name` — inheriting DEFAULT
        values is left to the fail2ban-client fallback
        (_get_config_best_effort()), same as before.

        Args:
            content: Full text of one config file.
            name: Jail name to find the section for.

        Returns:
            The section's body text (excluding the `[name]` header
            line itself), or None if this file has no `[name]` section.
        """
        section_re = re.compile(rf'^\[{re.escape(name)}\][ \t]*$', re.MULTILINE)
        match = section_re.search(content)
        if not match:
            return None
        start = match.end()
        next_section = re.search(r'^\[.+?\][ \t]*$', content[start:], re.MULTILINE)
        end = start + next_section.start() if next_section else len(content)
        return content[start:end]

    def _read_params_from_block(self, block: str) -> dict[str, str]:
        """Extract logpath/maxretry/bantime/findtime from a section's
        raw text — same regex + duration-normalization rules used
        before this method was factored out of
        _get_static_config_from_disk(), so it can run against a block
        already isolated by _extract_section_block() instead of only
        against a whole single-jail file's full content.

        Returns:
            Dict with whichever of the 4 fields were found in this
            block, "bantime"/"findtime" normalized to seconds (omitted
            if unparseable — never guessed).
        """
        result: dict[str, str] = {}
        for param in ("logpath", "maxretry", "bantime", "findtime"):
            match = re.search(rf'^\s*{param}\s*=\s*(.+)$', block, re.MULTILINE)
            if not match:
                continue
            raw_value = match.group(1).strip()
            if param in ("bantime", "findtime"):
                parsed = self._parse_duration_to_seconds(raw_value)
                if parsed is None:
                    continue  # unparseable — omit, caller falls back per-field
                result[param] = parsed
            else:
                result[param] = raw_value
        return result

    def _get_static_config_from_disk(
        self,
        name: str,
        jail_d_dir: str = "/etc/fail2ban/jail.d",
        jail_conf_path: Optional[str] = None,
        jail_local_path: Optional[str] = None,
    ) -> dict:
        """Read logpath/maxretry/bantime/findtime for a jail directly
        from disk, instead of up to 4 `fail2ban-client get` subprocess
        round-trips (~400ms each, confirmed by direct timing).

        Scans fail2ban's real config-loading order — jail.conf, then
        jail.d/*.conf (alphabetical), then jail.local, then
        jail.d/*.local (alphabetical) — looking for a `[name]` section
        in each file (via _extract_section_block()) and merging
        whichever fields are found, later files overriding earlier
        ones per-field. Replaces the previous jail.d/<name>.conf-only
        lookup, which missed:
        - Jails sharing one file as multiple `[section]` blocks (real
          case found in production: referentiel §82.4 — 11 of 19 jails
          on one deployment had no exactly-matching file, some grouped
          under a differently-named file like honeypot.conf).
        - Jails defined directly in jail.local/jail.conf, never
          touching jail.d at all (e.g. this project's own sshd,
          recidive — standard fail2ban default jails).

        Still best-effort, not authoritative: `[DEFAULT]` section
        values are never inherited here (same limitation as before —
        _get_config_best_effort() covers anything unresolved via
        fail2ban-client itself, which does apply DEFAULT correctly).

        Args:
            name: Jail name
            jail_d_dir: Directory jail.d/*.conf|*.local live in
                (overridable for testing without touching the real
                /etc/fail2ban)
            jail_conf_path: Path to jail.conf (defaults to jail_d_dir's
                parent + "jail.conf"; overridable for testing)
            jail_local_path: Path to jail.local (defaults to
                jail_d_dir's parent + "jail.local"; overridable for
                testing)

        Returns:
            Dict with whichever of "logpath"/"maxretry"/"bantime"/
            "findtime" keys were found across all scanned files. Empty
            dict if the jail's section wasn't found anywhere — the
            caller must fall back to fail2ban-client get per missing
            field in that case, never treat {} as "jail has no
            configuration".
        """
        base_dir = os.path.dirname(os.path.normpath(jail_d_dir))
        if jail_conf_path is None:
            jail_conf_path = os.path.join(base_dir, "jail.conf")
        if jail_local_path is None:
            jail_local_path = os.path.join(base_dir, "jail.local")

        candidate_files = [jail_conf_path]
        if os.path.isdir(jail_d_dir):
            candidate_files += sorted(
                os.path.join(jail_d_dir, fname)
                for fname in os.listdir(jail_d_dir)
                if fname.endswith(".conf")
            )
        candidate_files.append(jail_local_path)
        if os.path.isdir(jail_d_dir):
            candidate_files += sorted(
                os.path.join(jail_d_dir, fname)
                for fname in os.listdir(jail_d_dir)
                if fname.endswith(".local")
            )

        result: dict[str, str] = {}
        for path in candidate_files:
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue
            block = self._extract_section_block(content, name)
            if block is None:
                continue
            result.update(self._read_params_from_block(block))

        return result

    def _get_current_bans_from_db(
        self, db_path: Any = DEFAULT_F2B_DB_PATH
    ) -> Optional[dict[str, list[str]]]:
        """Bulk-read currently-banned IPs for ALL jails in one SQLite query.

        Replaces N x `fail2ban-client status <jail>` (~400ms each,
        confirmed by direct timing against the real binary — process
        startup + socket connection, not command-specific) with a single
        read of fail2ban's own database. At 4 jails this alone doesn't
        matter much; at the 10-200 jails a security-conscious deployment
        can reach, N sequential ~400ms round-trips (4-80s) is the actual
        bottleneck this method removes.

        Uses fail2ban's own definition of "currently banned", copied from
        the real installed source (fail2ban 1.1.0,
        Fail2BanDb._getCurrentBans() in server/database.py) — the exact
        query the daemon itself runs to restore state on restart: a ban
        is current if `timeofban + bantime > now`, OR `bantime <= -1`
        (permanent ban, no expiry). `bantime == -2` (legacy pre-v3-schema
        sentinel meaning "unknown duration, use the jail's current
        default") is excluded rather than guessed at, to avoid a false
        "currently banned" positive on an indeterminate duration — a
        marginal case, unlikely on a fresh v4-schema database.

        A natural ban expiry does NOT delete the `bips` row immediately
        (fail2ban purges it lazily, by default 24h x 3 after expiry) —
        the time filter above, not row absence, is what keeps expired
        bans out of the result.

        Blind spot shared with the old fail2ban-client approach, not a
        regression: an IP unbanned via raw iptables/nft outside fail2ban
        is invisible to both (neither fail2ban-client status nor its own
        database knows about it).

        Args:
            db_path: Path to fail2ban's SQLite database. Overridable for
                testing without touching the real file.

        Returns:
            {jail_name: [ip, ...]} for every jail with at least one
            currently-banned IP (jails with zero bans are simply absent
            as a key — callers must not treat that as "unavailable").
            None if the database file is missing, unreadable, or the
            query otherwise fails — callers must fall back to the
            per-jail mechanism in that case, never treat None as "zero
            bans everywhere" (that's what an empty-but-non-None dict
            with no matching keys means instead).
        """
        if not os.path.exists(db_path):
            return None
        try:
            uri = f"file:{db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=2.0)
            try:
                now = time.time()
                cursor = conn.execute(
                    "SELECT jail, ip FROM bips "
                    "WHERE (timeofban + bantime > ? OR bantime <= -1) AND bantime != -2",
                    (now,),
                )
                result: dict[str, list[str]] = {}
                for jail_name, ip in cursor.fetchall():
                    result.setdefault(jail_name, []).append(ip)
                return result
            finally:
                conn.close()
        except Exception:
            return None

    def _build_jail_info(self, name: str) -> JailInfo:
        """Build a port-conformant JailInfo for a single jail.

        Composes get_jail_status() (counts/banned IPs) with individual
        get_jail_config() lookups for the descriptive fields the status
        command doesn't expose. Costs 1 + 3 subprocess calls per jail —
        acceptable for occasional menu use, not a tight loop. Each
        fail2ban-client invocation costs a flat ~400ms regardless of the
        command issued (confirmed by direct timing against the real
        binary — process startup + socket connection, not specific to
        any subcommand) — every call skipped here is ~400ms saved,
        multiplied by the number of jails.

        Permanent limitation, confirmed against the real binary: "filter"
        is never queried — `fail2ban-client get <jail> filter` is not a
        supported action on this fail2ban version ("Invalid command (no
        get action or not yet implemented)"), and there is no other
        read-only command exposing the configured filter name at
        runtime. Querying it would cost a real subprocess round-trip
        (~400ms) for a call that is *guaranteed* to fail every time — not
        worth attempting. JailInfo.filter is left at its default "" for
        this reason; this isn't a bug to fix later, it's a ceiling of
        what fail2ban-client exposes (same category as
        JailStatus.failed_ips always being []).

        find_time is queried the same way as max_retry/ban_time
        (2026-08-16 : menu 6.4's report gained a real reader of
        JailInfo.find_time, invalidating the previous "zero real
        callers" premise for leaving it at a hardcoded 0 — see
        _build_jail_info_fast() for the no-subprocess fast path).

        Args:
            name: Name of the jail

        Raises:
            DomainJailNotFoundError: If the jail doesn't exist
        """
        try:
            raw = self.get_jail_status(name)
        except JailNotFoundError as e:
            raise DomainJailNotFoundError(name) from e

        log_path = self._get_config_best_effort(name, "logpath", default="")
        max_retry = self._get_config_best_effort(name, "maxretry", default="0")
        ban_time = self._get_config_best_effort(name, "bantime", default="0")
        find_time = self._get_config_best_effort(name, "findtime", default="0")

        return JailInfo(
            name=name,
            active=True,
            banned_count=raw.get("currently_banned", 0),
            banned_ips=self._to_ip_list(raw.get("banned_ips", [])),
            filter="",  # never queried — see docstring above
            log_path=log_path,
            max_retry=int(max_retry) if str(max_retry).isdigit() else 0,
            ban_time=int(ban_time) if str(ban_time).isdigit() else 0,
            find_time=int(find_time) if str(find_time).isdigit() else 0,
        )

    def _build_jail_info_fast(
        self, name: str, banned_ips: list[str], disk_config: dict
    ) -> JailInfo:
        """Build a JailInfo without any per-jail fail2ban-client call, for
        the nominal fast path of list_jails_info() (DB available).

        banned_ips comes from a single bulk SQLite query already done by
        the caller (_get_current_bans_from_db), not a subprocess call.
        disk_config comes from _get_static_config_from_disk() — a field
        missing from it (file partially written, or an unparseable
        bantime) triggers a single targeted fail2ban-client get call for
        that one field only, never a full per-jail fallback.

        Args:
            name: Jail name
            banned_ips: Currently-banned IPs for this jail (raw strings),
                already time-filtered by the caller.
            disk_config: Whatever _get_static_config_from_disk(name)
                returned — may be missing any of its 3 keys.

        Returns:
            JailInfo (filter="" is the one permanent gap left — see
            _build_jail_info docstring; find_time is now populated,
            same disk-first/subprocess-fallback path as max_retry/
            ban_time).
        """
        log_path = (
            disk_config["logpath"] if "logpath" in disk_config
            else self._get_config_best_effort(name, "logpath", default="")
        )
        max_retry_raw = (
            disk_config["maxretry"] if "maxretry" in disk_config
            else self._get_config_best_effort(name, "maxretry", default="0")
        )
        ban_time_raw = (
            disk_config["bantime"] if "bantime" in disk_config
            else self._get_config_best_effort(name, "bantime", default="0")
        )
        find_time_raw = (
            disk_config["findtime"] if "findtime" in disk_config
            else self._get_config_best_effort(name, "findtime", default="0")
        )

        return JailInfo(
            name=name,
            active=True,
            banned_count=len(banned_ips),
            banned_ips=self._to_ip_list(banned_ips),
            filter="",  # never queried — see _build_jail_info docstring
            log_path=log_path,
            max_retry=int(max_retry_raw) if str(max_retry_raw).isdigit() else 0,
            ban_time=int(ban_time_raw) if str(ban_time_raw).isdigit() else 0,
            find_time=int(find_time_raw) if str(find_time_raw).isdigit() else 0,
        )

    def list_jails(self) -> list[str]:
        """List all fail2ban jails.

        Returns:
            List of jail names
        """
        output = self._run_command(["fail2ban-client", "status"])
        return self._parser.parse_jail_list(output)

    def list_jails_info(self) -> list[JailInfo]:
        """List all fail2ban jails, port-conformant (Fail2banPort.list_jails).

        Coexists with list_jails() (list[str]) — does not replace it; the
        existing callers of list_jails() are unaffected.

        Scaling fix (see /home/kraynux/.claude/plans/cryptic-tickling-wolf.md):
        the nominal path costs 1 `fail2ban-client status` (list_jails(),
        already minimal) + 1 SQLite query (all jails at once) + disk
        reads (jail.d/*.conf) — no per-jail fail2ban-client call at all,
        versus the previous 1 + 4N subprocess calls (~400ms each). Falls
        back to the untouched, fully subprocess-based _build_jail_info()
        for ALL jails if fail2ban's database is unavailable (deployment
        without persistent storage, permissions, missing file) — never a
        silent error, just the old (slower) behavior in that case.
        Per-jail, per-field fallback (via _build_jail_info_fast) handles
        the narrower case of a jail.d file existing but missing/
        unparseable individual fields.

        Returns:
            List of JailInfo, one per configured jail.
        """
        names = self.list_jails()
        bans_by_jail = self._get_current_bans_from_db()
        if bans_by_jail is None:
            return [self._build_jail_info(name) for name in names]

        return [
            self._build_jail_info_fast(
                name, bans_by_jail.get(name, []), self._get_static_config_from_disk(name)
            )
            for name in names
        ]

    def get_jail_status(self, jail_name: str) -> dict:
        """Get the status of a specific jail.

        Args:
            jail_name: Name of the jail

        Returns:
            Dictionary with jail status

        Raises:
            JailNotFoundError: If the jail does not exist
        """
        try:
            output = self._run_command(["fail2ban-client", "status", jail_name])
            return self._parser.parse_jail_status(output, jail_name)
        except Fail2banCommandError as e:
            if "not found" in e.stderr.lower() or "no jail" in e.stderr.lower():
                raise JailNotFoundError(jail_name) from e
            raise

    def get_jail_status_info(self, jail_name: str) -> JailStatus:
        """Get the status of a jail, port-conformant (Fail2banPort.get_jail_status).

        Coexists with get_jail_status() (dict) — does not replace it; the
        existing callers of get_jail_status() are unaffected.

        Permanent limitation: `failed_ips` is always [] — fail2ban-client
        only exposes failure *counts* ("Currently failed", "Total failed"),
        never the per-IP list of addresses currently failing but not yet
        banned (that data lives in fail2ban's internal FailManager, not in
        any documented fail2ban-client output). Not a TODO, a ceiling of
        what the CLI exposes.

        Args:
            jail_name: Name of the jail

        Returns:
            JailStatus with counts and banned IPs (failed_ips always []).

        Raises:
            DomainJailNotFoundError: If the jail does not exist
        """
        try:
            raw = self.get_jail_status(jail_name)
        except JailNotFoundError as e:
            raise DomainJailNotFoundError(jail_name) from e

        return JailStatus(
            name=jail_name,
            currently_failed=raw.get("currently_failed", 0),
            total_failed=raw.get("total_failed", 0),
            failed_ips=[],
            banned_ips=self._to_ip_list(raw.get("banned_ips", [])),
        )

    def ban_ip_in_jail(self, jail_name: str, ip: str) -> bool:
        """Ban an IP in a specific jail.

        Args:
            jail_name: Name of the jail
            ip: IP address to ban

        Returns:
            True if the ban was successful
        """
        self._run_command(["fail2ban-client", "set", jail_name, "banip", ip])
        return True

    def unban_ip_in_jail(self, jail_name: str, ip: str) -> bool:
        """Unban an IP from a specific jail.

        Args:
            jail_name: Name of the jail
            ip: IP address to unban

        Returns:
            True if the unban was successful
        """
        self._run_command(["fail2ban-client", "set", jail_name, "unbanip", ip])
        return True

    def ban_ip(self, jail_name: str, ip: IPAddress) -> None:
        """Ban an IP in a specific jail, port-conformant (Fail2banPort.ban_ip).

        Coexists with ban_ip_in_jail() (bool return) — does not replace
        it; the existing callers of ban_ip_in_jail() are unaffected.

        Args:
            jail_name: Name of the jail
            ip: IP address to ban

        Raises:
            DomainJailNotFoundError: If the jail doesn't exist
            IPAlreadyBannedError: If the IP is already banned in the jail
        """
        try:
            output = self._run_command(["fail2ban-client", "set", jail_name, "banip", str(ip)])
        except Fail2banCommandError as e:
            self._translate_not_found(jail_name, e)
            raise
        if self._parser.parse_set_ip_result(output) == 0:
            raise IPAlreadyBannedError(str(ip), jail_name)

    def unban_ip(self, jail_name: str, ip: IPAddress) -> None:
        """Unban an IP from a specific jail, port-conformant (Fail2banPort.unban_ip).

        Coexists with unban_ip_in_jail() (bool return) — does not replace
        it; the existing callers of unban_ip_in_jail() are unaffected.

        Args:
            jail_name: Name of the jail
            ip: IP address to unban

        Raises:
            DomainJailNotFoundError: If the jail doesn't exist
            IPNotFoundError: If the IP is not currently banned in the jail
        """
        try:
            output = self._run_command(["fail2ban-client", "set", jail_name, "unbanip", str(ip)])
        except Fail2banCommandError as e:
            self._translate_not_found(jail_name, e)
            raise
        if self._parser.parse_set_ip_result(output) == 0:
            raise IPNotFoundError(str(ip), jail_name)

    def get_banned_ips(self, jail_name: str) -> list[str]:
        """Get the list of banned IPs in a jail.

        Args:
            jail_name: Name of the jail

        Returns:
            List of banned IP addresses
        """
        output = self._run_command(["fail2ban-client", "status", jail_name])
        return self._parser.parse_ban_list(output)

    def get_jail_config(self, jail_name: str, param: str) -> str:
        """Get a configuration parameter of a jail.

        Args:
            jail_name: Name of the jail
            param: Parameter name (e.g., "maxretry", "bantime"). "logpath"
                is special-cased: unlike other params, fail2ban-client
                formats it as a human-readable block ("No file is
                currently monitored" / "Current monitored log file(s):
                \\n`- /path") rather than a raw value — confirmed no
                existing caller passes "logpath" here today, so parsing
                it properly is safe (see parser.parse_logpath).

        Returns:
            Parameter value as string
        """
        output = self._run_command(["fail2ban-client", "get", jail_name, param])
        if param == "logpath":
            return self._parser.parse_logpath(output)
        return self._parser.parse_get_command(output)

    def flush_jail(self, jail_name: str) -> int:
        """Flush all bans from a jail (Fail2banPort contract).

        Updated in place (previously returned bool) — grep-confirmed zero
        live callers of the previous bool-returning form before this change.

        Uses `set <jail> unbanip <ip> [<ip> ...]` with the jail's current
        banned IPs passed explicitly. Two things were confirmed wrong by
        smoke-testing against the real binary before landing on this:
        `set <jail> flushban` (what the pre-existing bool-returning
        version used) doesn't exist on this fail2ban version, and its
        replacement `unbanip --all` silently unbans nothing (returns "0")
        despite exiting 0 — passing the explicit IP list is what actually
        works. The count returned comes from fail2ban-client's own output
        (parse_set_ip_result), not a pre-flush guess.

        Args:
            jail_name: Name of the jail

        Returns:
            Number of IPs actually unbanned by the flush.

        Raises:
            DomainJailNotFoundError: If the jail doesn't exist
        """
        try:
            banned_ips = self.get_banned_ips(jail_name)
        except Fail2banCommandError as e:
            self._translate_not_found(jail_name, e)
            raise
        if not banned_ips:
            return 0
        output = self._run_command(["fail2ban-client", "set", jail_name, "unbanip", *banned_ips])
        result = self._parser.parse_set_ip_result(output)
        return result if result >= 0 else len(banned_ips)

    def flush_all_jails(self) -> int:
        """Flush all bans from every jail (Fail2banPort contract).

        Best-effort: an error on one jail doesn't block flushing the rest.

        Returns:
            Total number of IPs unbanned across all jails.
        """
        total = 0
        for name in self.list_jails():
            try:
                total += self.flush_jail(name)
            except (Fail2banCommandError, DomainJailNotFoundError, Fail2banPermissionError):
                continue
        return total

    def write_filter(
        self,
        filter_name: str,
        content: str,
        filter_d_dir: str = "/etc/fail2ban/filter.d",
    ) -> bool:
        """Write a fail2ban filter file, only if it doesn't already exist.

        Infrastructure-only concern: writes whatever content it's
        given verbatim — generating that content is a domain/ concern
        (see domain/fail2ban/filters.py), not this adapter's. Mirrors
        create_jail()'s own "don't clobber existing config" behavior —
        never overwrites a filter a user (or fail2ban itself, for a
        stock filter name) may already have in place.

        Args:
            filter_name: Name of the filter (written as {filter_name}.conf)
            content: Full filter file content to write verbatim
            filter_d_dir: Directory to write into (overridable for
                testing without touching the real /etc/fail2ban)

        Returns:
            True if the file was written, False if it already existed
            (left untouched in that case).

        Raises:
            Fail2banPermissionError: If writing requires elevated privileges
            Fail2banCommandError: If the write fails for another reason
        """
        filter_path = os.path.join(filter_d_dir, f"{filter_name}.conf")
        if os.path.exists(filter_path):
            return False
        try:
            os.makedirs(filter_d_dir, exist_ok=True)
            with open(filter_path, "w", encoding="utf-8") as f:
                f.write(content)
        except PermissionError as e:
            raise Fail2banPermissionError(operation=f"write_filter:{filter_name}") from e
        except OSError as e:
            raise Fail2banCommandError(command=f"write {filter_path}", returncode=-1, stderr=str(e))
        return True

    def create_jail(
        self,
        name: str,
        filter_name: str,
        log_path: str,
        *,
        max_retry: int | str = 5,
        ban_time: int | str = 3600,
        find_time: int | str = 600,
        port: str | None = None,
        jail_d_dir: str = "/etc/fail2ban/jail.d",
    ) -> JailInfo:
        """Create a new fail2ban jail (Fail2banPort contract).

        Writes jail.d/{name}.conf referencing an existing filter_name.
        Does NOT generate filter content — the port's own signature takes
        filter_name as a reference to an already-existing filter, never
        content, so authoring filter regex is out of scope here (a
        domain/ concern for a later phase, not this adapter). If
        filter_name doesn't resolve to a real file under filter.d/,
        `fail2ban-client reload` below fails with a clear stderr message
        instead of silently succeeding with a broken jail.

        Args:
            name: Name of the jail to create
            filter_name: Name of an existing filter under filter.d/ (e.g. "sshd")
            log_path: Path to the log file to monitor
            max_retry: Max attempts before ban
            ban_time: Ban duration in seconds, or fail2ban's own
                human-readable duration syntax (e.g. "1h", "24h") — both
                forms are written verbatim into jail.d; fail2ban parses
                either natively on load, no conversion needed here. The
                returned JailInfo always reflects the real post-creation
                state via _build_jail_info(), not these raw parameters.
            find_time: Detection window in seconds, or human-readable
                duration syntax (e.g. "10m") — same note as ban_time.
            port: Port(s) targeted by the ban action (e.g. "80,443", "ssh")
                — written into the jail.d file if given; omitted entirely
                if None, matching the pre-existing behavior (referentiel
                §33 — this parameter was added specifically so callers
                that do need it, like action_4_4_create_jail, don't have
                to write jail.d themselves anymore).
            jail_d_dir: Directory to write the jail config into (overridable
                for testing without touching the real /etc/fail2ban)

        Returns:
            JailInfo for the newly created jail.

        Raises:
            DomainJailAlreadyExistsError: If a jail with this name already exists
            Fail2banPermissionError: If writing the config requires elevated privileges
            Fail2banCommandError: If the config can't be written, or reload fails
        """
        jail_conf_path = os.path.join(jail_d_dir, f"{name}.conf")
        if os.path.exists(jail_conf_path) or name in self.list_jails():
            raise DomainJailAlreadyExistsError(name)

        port_line = f"port = {port}\n" if port else ""
        content = (
            f"# Généré par Omega-Fire\n"
            f"[{name}]\n"
            f"enabled = true\n"
            f"{port_line}"
            f"filter = {filter_name}\n"
            f"logpath = {log_path}\n"
            f"maxretry = {max_retry}\n"
            f"findtime = {find_time}\n"
            f"bantime = {ban_time}\n"
        )
        try:
            os.makedirs(jail_d_dir, exist_ok=True)
            log_dir = os.path.dirname(log_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            if not os.path.exists(log_path):
                open(log_path, "a", encoding="utf-8").close()
            with open(jail_conf_path, "w", encoding="utf-8") as f:
                f.write(content)
        except PermissionError as e:
            raise Fail2banPermissionError(operation=f"create_jail:{name}") from e
        except OSError as e:
            raise Fail2banCommandError(command=f"write {jail_conf_path}", returncode=-1, stderr=str(e))

        reload_result = self._run_raw(["fail2ban-client", "reload"])
        if reload_result.returncode != 0:
            self._run_raw(["fail2ban-client", "start", name])

        return self._build_jail_info(name)

    def list_configured_jail_files(self, jail_d_dir: str = "/etc/fail2ban/jail.d") -> dict[str, str]:
        """List jail config files present on disk (Fail2banPort contract).

        Moved here from action_4_5_delete_jail (interfaces/cli/actions.py),
        qui faisait ce même scan `os.listdir()` directement — violation de
        la charte hexagonale (référentiel §80). Logique inchangée, seule
        la couche d'exécution change.

        Args:
            jail_d_dir: Directory the jail configs live in (overridable for testing)

        Returns:
            Mapping {jail_name: absolute path to its .conf/.local file}.
        """
        jail_files: dict[str, str] = {}
        if not os.path.exists(jail_d_dir):
            return jail_files
        for fname in os.listdir(jail_d_dir):
            if fname.endswith(".conf") or fname.endswith(".local"):
                j_name = fname.rsplit(".", 1)[0]
                jail_files[j_name] = os.path.join(jail_d_dir, fname)
        return jail_files

    def delete_jail(
        self,
        jail_name: str,
        jail_d_dir: str = "/etc/fail2ban/jail.d",
        filter_d_dir: str = "/etc/fail2ban/filter.d",
    ) -> None:
        """Delete a fail2ban jail (Fail2banPort contract).

        Looks for both `{jail_name}.conf` and `{jail_name}.local` under
        jail_d_dir — both are valid fail2ban config file extensions, and
        action_4_5_delete_jail's own pre-existing discovery (before it
        delegated here, referentiel §33/§35) already scanned for both.
        Widened in place rather than added alongside: zero real callers
        of this method existed before action_4_5_delete_jail's own
        migration (grep-confirmed), so there was no existing behavior to
        preserve.

        Args:
            jail_name: Name of the jail to delete
            jail_d_dir: Directory the jail config lives in (overridable for testing)
            filter_d_dir: Directory jail-named filters would live in, if any
                (overridable for testing)

        Raises:
            DomainJailNotFoundError: If the jail exists neither on disk nor in the daemon
        """
        jail_conf_paths = [
            os.path.join(jail_d_dir, f"{jail_name}.conf"),
            os.path.join(jail_d_dir, f"{jail_name}.local"),
        ]
        existing_conf_paths = [p for p in jail_conf_paths if os.path.exists(p)]
        exists_in_daemon = jail_name in self.list_jails()
        if not existing_conf_paths and not exists_in_daemon:
            raise DomainJailNotFoundError(jail_name)

        self._run_raw(["fail2ban-client", "stop", jail_name])  # best-effort

        for path in existing_conf_paths:
            os.remove(path)

        filter_conf_path = os.path.join(filter_d_dir, f"{jail_name}.conf")
        if os.path.exists(filter_conf_path):
            os.remove(filter_conf_path)

        self._run_raw(["fail2ban-client", "reload"])  # best-effort

    def reload_jail(self, jail_name: str) -> bool:
        """Reload a jail configuration.

        Args:
            jail_name: Name of the jail

        Returns:
            True if the reload was successful
        """
        self._run_command(["fail2ban-client", "reload", jail_name])
        return True

    def is_available(self) -> bool:
        """Check if fail2ban-client is available on the system.

        Returns:
            True if fail2ban-client is installed and functional
        """
        try:
            self._run_command(["fail2ban-client", "ping"])
            return True
        except (Fail2banCommandError, Fail2banPermissionError):
            return False

    def verify_config(self) -> tuple[bool, list[str]]:
        """Verify the fail2ban configuration validity (Fail2banPort contract).

        Uses `fail2ban-client -t`, which tests the on-disk configuration
        without requiring an already-running daemon and without applying
        any change. Read-only.

        Returns:
            Tuple (is_valid, errors) — is_valid is True if the config test
            passed; errors is the list of non-empty output lines reported
            by fail2ban-client on failure (empty list if valid).
        """
        result = self._run_raw(["fail2ban-client", "-t"])
        if result.returncode == 0:
            return True, []
        raw_output = (result.stderr or result.stdout or "").strip()
        errors = [line.strip() for line in raw_output.splitlines() if line.strip()]
        if not errors:
            errors = [f"fail2ban-client -t a échoué sans détail (code de retour {result.returncode})"]
        return False, errors

    def stop_service(self) -> None:
        """Stop the fail2ban service (Fail2banPort contract).

        Delegates to the composed Fail2banServiceController (systemd/
        openrc/runit, auto-detected). Exceptions from the controller
        (Fail2banServiceError) propagate as-is — already the established
        exception for "fail2ban service operation failed" everywhere
        else in this codebase, no re-wrapping.

        Raises:
            Fail2banServiceError: If the stop operation fails
        """
        self._service_controller.stop()

    def restart_service(self) -> None:
        """Restart the fail2ban service (Fail2banPort contract).

        Raises:
            Fail2banServiceError: If the restart operation fails
        """
        self._service_controller.restart()

    def enable_service(self) -> None:
        """Enable the fail2ban service at boot (Fail2banPort contract).

        Raises:
            Fail2banServiceError: If the enable operation fails
        """
        self._service_controller.enable()

    def start_service(self) -> None:
        """Start the fail2ban service (Fail2banPort contract).

        Delegates to the composed Fail2banServiceController (systemd/
        openrc/runit, auto-detected). Exceptions from the controller
        (Fail2banServiceError) propagate as-is.

        Raises:
            Fail2banServiceError: If the start operation fails
        """
        self._service_controller.start()

    def disable_service(self) -> None:
        """Disable the fail2ban service at boot (Fail2banPort contract).

        Raises:
            Fail2banServiceError: If the disable operation fails
        """
        self._service_controller.disable()

    def is_service_active(self) -> bool:
        """Check whether the fail2ban service is currently active
        (Fail2banPort contract). Never raises — returns False if the
        service manager can't be detected (same fail-safe as the
        underlying Fail2banServiceController.is_active())."""
        return self._service_controller.is_active()

    def is_service_enabled(self) -> bool:
        """Check whether the fail2ban service is enabled at boot
        (Fail2banPort contract). Never raises — returns False if the
        service manager can't be detected."""
        return self._service_controller.is_enabled()


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Implémente les opérations concrètes fail2ban via subprocess
# - Point d'entrée unique pour toutes les interactions avec fail2ban-client
# - Retourne des objets du domaine (Jail, BanEntry) ou des dicts structurés
# Pourquoi dans infrastructure/ (charte) :
# - C'est le SEUL module autorisé à appeler fail2ban-client via subprocess
# - Implémente les contrats que l'application/ utilisera via les ports
# - L'application/ ne doit JAMAIS importer ce module directement
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de validation de jail, pas de politiques de transfert)
# ❌ Pas de dépendance vers application/ ou interfaces/
# ❌ Pas de décision de grisage ou d'autorisation
# Points clés :
# - Fail2banAdapter : classe principale avec timeout configurable
# - _run_command() : exécute une commande fail2ban-client via subprocess.run()
#   - Gère les timeouts, permissions, binaires manquants
#   - Lève Fail2banCommandError ou Fail2banPermissionError
# - list_jails() : retourne la liste des noms de jails
# - get_jail_status() : retourne un dict avec compteurs et IPs bannies
# - ban_ip_in_jail() / unban_ip_in_jail() : ban/unban dans un jail spécifique
# - get_banned_ips() : retourne la liste des IPs bannies d'un jail
# - get_jail_config() : retourne la valeur d'un paramètre de configuration
# - flush_jail() / reload_jail() : vide ou recharge un jail
# - is_available() : vérifie que fail2ban-client est installé
# - create_jail() / delete_jail() : écrivent/suppriment jail.d/{name}.conf
# - write_filter() : écrit un filtre filter.d/{name}.conf déjà généré par
#   domain/fail2ban/filters.py (n'écrase jamais un filtre existant)
# - list_jails_info() : chemin rapide sans fail2ban-client par jail
#   (_get_current_bans_from_db() + _get_static_config_from_disk()),
#   repli sur l'ancien mécanisme par-jail si la base est indisponible
# - Composition : utilise Fail2banParser pour le parsing
# Comment il sera utilisé (aperçu) :
# - ports/fail2ban.py définira le contrat que cet adapter implémente
# - app/bootstrap.py instanciera cet adapter et l'injectera via les ports
# - application/commands/ utilisera le port (pas cet adapter directement)
# - Les tests mockeront subprocess.run pour simuler différents états
#---------------------------------------------------------------------->
