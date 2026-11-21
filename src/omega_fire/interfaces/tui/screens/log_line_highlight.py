# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Couleurs de la colonne « Message » du viewer Simple (retour utilisateur omega-serv 2026-11-20, porte dans omega-fire le 2026-11-21) : une nuance par information
(date, adresse, requete, code, User-Agent...) pour lire une ligne d'un coup d'oeil.

Uniquement les variables du theme courant (`text-primary`, `text-accent`...) : aucun theme a retoucher, et les
couleurs suivent le theme choisi. La ligne reste du texte brut (Text, jamais du balisage Rich : elle vient du
client) ; seules des plages en sont colorees."""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from rich.style import Style
from rich.text import Text

from omega_fire.domain.log_stats.parser import (
    APACHE_TIMESTAMP,
    COMBINED_LOG_PATTERN,
    ISO_TIMESTAMP,
    SERVICE_TAG_PATTERN,
    SYSLOG_TIMESTAMP,
    extract_all_ips,
)

_QUOTED_RE = re.compile(r'"(?:[^"\\]|\\.)*"')
_TIMESTAMP_RES = tuple(re.compile(pattern) for pattern in (ISO_TIMESTAMP, APACHE_TIMESTAMP, SYSLOG_TIMESTAMP))
_LEVEL_RE = re.compile(r"\b(error|err|critical|crit|fatal|alert|emerg|emergency|warning|warn)\b", re.IGNORECASE)
_PROTOCOL_RE = re.compile(r"\s(HTTP/\d(?:\.\d)?)$")


_BOLD = Style(bold=True)
_ITALIC = Style(italic=True)


def _bold(color: str) -> Style:
    return Style.parse(color) + _BOLD


def _italic(color: str) -> Style:
    return Style.parse(color) + _ITALIC


@dataclass(frozen=True)
class LinePalette:
    date: str
    ip: str
    method: Style
    service: Style
    agent: Style
    good: str
    redirect: str
    warn: str
    bad: str
    muted: str = "dim"

    def status(self, code: int) -> Style:
        if code < 300:
            return _bold(self.good)
        if code < 400:
            return _bold(self.redirect)
        return _bold(self.warn) if code < 500 else _bold(self.bad)


def palette_from_theme(variables: Mapping[str, str]) -> LinePalette:
    def pick(name: str, fallback: str) -> str:
        return variables.get(name) or fallback

    return LinePalette(
        date=pick("text-secondary", "cyan"), ip=pick("text-accent", "magenta"),
        method=_bold(pick('text-primary', 'blue')), service=_bold(pick('text-primary', 'blue')),
        agent=_italic(pick('text-primary', 'blue')), good=pick("text-success", "green"),
        redirect=pick("text-primary", "cyan"), warn=pick("text-warning", "yellow"), bad=pick("text-error", "red"),
    )


def highlight_log_line(line: str, palette: LinePalette) -> Text:
    text = Text(line, no_wrap=True)
    combined = COMBINED_LOG_PATTERN.search(line)
    if combined is not None:
        _highlight_combined(text, line, combined, palette)
        return text
    for regex in _TIMESTAMP_RES:
        found = regex.search(line)
        if found is not None:
            text.stylize(palette.date, found.start(), found.end())
            break
    tag = SERVICE_TAG_PATTERN.search(line)
    if tag is not None:
        text.stylize(palette.service, tag.start(1), tag.end())
    _stylize_ips(text, line, palette.ip)
    for level in _LEVEL_RE.finditer(line):
        word = level.group(1).lower()
        text.stylize(_bold(palette.warn if word.startswith('warn') else palette.bad), level.start(), level.end())
    return text


def _highlight_combined(text: Text, line: str, match: re.Match[str], palette: LinePalette) -> None:
    text.stylize(_bold(palette.ip), match.start("ip"), match.end("ip"))
    text.stylize(palette.date, match.start("time") - 1, match.end("time") + 1)
    text.stylize(palette.method, match.start("method"), match.end("method"))
    request_end = line.find('"', match.end("path"))
    if request_end > 0:
        protocol = _PROTOCOL_RE.search(line, match.end("path"), request_end)
        if protocol is not None:
            text.stylize(palette.muted, protocol.start(1), protocol.end(1))
    text.stylize(palette.status(int(match.group("status"))), match.start("status"), match.end("status"))
    text.stylize(palette.muted, match.start("size"), match.end("size"))
    # Apres la taille (Combined) : "referent" "User-Agent", puis ce que le format ajoute (identifiant de requete).
    quoted = list(_QUOTED_RE.finditer(line, match.end()))
    for index, part in enumerate(quoted[:2]):
        style = palette.agent if index == 1 else palette.muted
        text.stylize(style, part.start(), part.end())
    rest = quoted[1].end() if len(quoted) > 1 else (quoted[0].end() if quoted else match.end())
    if rest < len(line):
        text.stylize(palette.muted, rest, len(line))


def _stylize_ips(text: Text, line: str, style: str) -> None:
    start = 0
    for ip in extract_all_ips(line):
        position = line.find(ip, start)
        if position < 0:
            position = line.find(ip)
        if position >= 0:
            text.stylize(_bold(style), position, position + len(ip))
            start = position + len(ip)
