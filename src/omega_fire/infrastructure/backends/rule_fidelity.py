# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Une regle lue dans le noyau peut-elle etre recreee a l'identique ?

Le parseur ne garde que chaine, action, protocole, port, adresses et commentaire.
Une regle qui a d'autres criteres (ct state, interface, type ICMP, limit, jump vers
une chaine UFW...) ou qui vit dans la chaine d'un autre outil (ufw-*, ts-*...) ne
peut pas etre recreee fidelement : la reappliquer en change le sens (constate le
2026-10-28 : `ct state established accept` restaure en « tout accepter » par 7.2).

Controle volontairement strict (liste blanche) : tout element non reconnu rend la
regle non restaurable. Les regles creees par Omega-Fire (3.1, 3.4) passent, puisque
les serializers n'emettent que ces elements."""
from __future__ import annotations

import re
import shlex

BASE_CHAINS = ("input", "output", "forward")

_PORT_NFT = re.compile(r"^\d+(-\d+)?$")
_PORT_IPT = re.compile(r"^\d+(:\d+)?$")
_ADDR = re.compile(r"^[0-9a-fA-F:.]+(/\d+)?$")
_PROTOCOLS = {"tcp", "udp", "icmp", "icmpv6", "ipv6-icmp"}

_NFT_HANDLE = re.compile(r"\s*#\s*handle\s+\d+\s*$")
_NFT_COMMENT = re.compile(r'\s+comment\s+"[^"]*"')
_NFT_COUNTER = re.compile(r"\bcounter(\s+packets\s+\d+\s+bytes\s+\d+)?")
_NFT_VERDICTS = {"accept", "drop", "reject", "log"}


def nft_rule_restorable(family: str, table: str, chain: str, raw: str) -> bool:
    if (family, table) != ("inet", "filter") or chain not in BASE_CHAINS:
        return False
    text = _NFT_HANDLE.sub("", raw or "")
    if len(_NFT_COMMENT.findall(text)) > 1:
        return False
    text = _NFT_COUNTER.sub(" ", _NFT_COMMENT.sub(" ", text))
    tokens = text.split()
    if not tokens or tokens[-1] not in _NFT_VERDICTS:
        return False
    i, body = 0, tokens[:-1]
    while i < len(body):
        t = body[i:i + 3]
        if len(t) == 3 and t[0] in ("tcp", "udp") and t[1] == "dport" and _PORT_NFT.match(t[2]):
            i += 3
        elif len(t) == 3 and t[:2] == ["meta", "l4proto"] and t[2] in _PROTOCOLS:
            i += 3
        elif len(t) == 3 and t[0] in ("ip", "ip6") and t[1] in ("saddr", "daddr") and _ADDR.match(t[2]):
            i += 3
        else:
            return False
    return True


_IPT_VERDICTS = {"ACCEPT", "DROP", "REJECT", "LOG"}
_IPT_DEFAULT_REJECT = {"icmp-port-unreachable", "icmp6-port-unreachable"}


def iptables_rule_restorable(raw: str) -> bool:
    try:
        tokens = shlex.split(raw or "")
    except ValueError:
        return False
    if len(tokens) < 2 or tokens[0] != "-A" or tokens[1].lower() not in BASE_CHAINS \
            or tokens[1] != tokens[1].upper():
        return False
    i, verdict = 2, None
    while i < len(tokens):
        opt = tokens[i]
        value = tokens[i + 1] if i + 1 < len(tokens) else None
        if value is None:
            return False
        if opt == "-p" and value in _PROTOCOLS:
            pass
        elif opt == "-m" and value in ("tcp", "udp", "comment"):
            pass
        elif opt == "--dport" and _PORT_IPT.match(value):
            pass
        elif opt in ("-s", "-d") and _ADDR.match(value):
            pass
        elif opt == "--comment":
            pass
        elif opt == "-j" and value in _IPT_VERDICTS and verdict is None:
            verdict = value
        elif opt == "--reject-with" and verdict == "REJECT" and value in _IPT_DEFAULT_REJECT:
            pass
        else:
            return False
        i += 2
    return verdict is not None


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Dit si une règle live peut être recréée telle quelle par 7.2.
#   Appelé par les mappers (champ FirewallRule.restorable), enregistré
#   dans le snapshot (7.1), relu par restore_state (7.2).
# Pourquoi dans infrastructure/backends/ :
# - Dépend de la syntaxe nft / iptables -S.
#----------------------------------------------------------------------
