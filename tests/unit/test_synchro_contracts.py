# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrats d'interconnexion, etape 2 du 2026-11-10 (omega-lib D-017) : jeton et fiche d'omega-fire.
Jamais le vrai var/ : la racine du projet est remplacee par un dossier temporaire."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import patch

from omega_lib.synchro.codec import sheet_from_dict, sheet_to_dict, token_from_dict
from omega_lib.synchro.models import CapabilityState

from omega_fire.app import synchro_runner
from omega_fire.application.queries.synchro_contracts import BinaryProbe, FireProbes, build_fire_sheet

NOW = datetime(2026, 11, 10, 14, 6, tzinfo=timezone.utc)
PRESENT = BinaryProbe(True, True)
PRESENT_UNCHECKED = BinaryProbe(True, False)
MISSING = BinaryProbe(False, False)


def _probes(**overrides):
    values = {"nft": PRESENT, "iptables": MISSING, "fail2ban_client": PRESENT, "fail2ban_service_state": "active",
              "jail_d_present": True, "as_root": True}
    values.update(overrides)
    return FireProbes(**values)


def test_root_sheet_is_complete_and_valid():
    sheet = build_fire_sheet(_probes(), "3.6", "0123456789abcdef0123456789abcdef", NOW)
    assert not sheet.partial
    assert sheet.capabilities["nftables"] is CapabilityState.ACTIVE
    assert sheet.capabilities["iptables"] is CapabilityState.ABSENT
    assert sheet.capabilities["fail2ban"] is CapabilityState.ACTIVE
    parsed = sheet_from_dict(json.loads(json.dumps(sheet_to_dict(sheet))))
    assert parsed.ok, parsed.detail
    assert parsed.value.extra["backends"]["iptables"] == "absent"


def test_user_sheet_is_partial_with_unknown_backends():
    sheet = build_fire_sheet(_probes(nft=PRESENT_UNCHECKED, as_root=False, fail2ban_service_state="error"),
                             "3.6", "", NOW)
    assert sheet.partial
    assert sheet.capabilities["nftables"] is CapabilityState.UNKNOWN
    assert sheet.capabilities["fail2ban"] is CapabilityState.UNKNOWN


def test_fail2ban_stopped_or_missing():
    assert build_fire_sheet(_probes(fail2ban_service_state="inactive"), "3.6", "", NOW).capabilities[
        "fail2ban"] is CapabilityState.DISABLED
    assert build_fire_sheet(_probes(fail2ban_client=MISSING), "3.6", "", NOW).capabilities[
        "fail2ban"] is CapabilityState.ABSENT


def test_token_command_writes_in_project_var_only(tmp_path, capsys):
    with patch.object(synchro_runner, "_project_root", return_value=tmp_path):
        assert synchro_runner.run_synchro(["jeton"]) == 0
    token = token_from_dict(json.loads((tmp_path / "var" / "omega-jeton.json").read_text(encoding="utf-8"))).value
    assert token is not None and token.tool == "omega-fire" and token.version
    assert json.loads(capsys.readouterr().out)["installation_id"] == token.installation_id


def test_sheet_command_reads_token_id(tmp_path, capsys):
    with patch.object(synchro_runner, "_project_root", return_value=tmp_path), \
            patch.object(synchro_runner, "_probes", return_value=_probes(as_root=False)):
        synchro_runner.run_synchro(["jeton"])
        capsys.readouterr()
        assert synchro_runner.run_synchro(["fiche", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["installation_id"]) == 32 and payload["partial"] is True


def test_unknown_subcommand_shows_usage(capsys):
    assert synchro_runner.run_synchro(["autre"]) == 2
    assert "usage" in capsys.readouterr().err
