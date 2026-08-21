# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""IP blacklist domain exceptions.

Pure domain exceptions. These express business rule violations,
not technical failures. They are caught by application/ and
translated into Results or user-facing messages.
"""


class IPBlacklistError(Exception):
    """Base exception for IP blacklist domain.
    
    All domain-specific exceptions inherit from this.
    """
    pass


class IPAlreadyBannedError(IPBlacklistError):
    """Raised when attempting to ban an IP that is already banned.
    
    This is a business rule violation: the invariant is that
    an IP cannot be banned twice on the same backend.
    """
    def __init__(self, ip: str, backend: str):
        self.ip = ip
        self.backend = backend
        super().__init__(f"IP {ip} is already banned on {backend}")


class IPNotFoundError(IPBlacklistError):
    """Raised when attempting to unban or query an IP that is not banned.
    
    This is a business rule violation: you cannot unban an IP
    that doesn't exist in the blacklist.
    """
    def __init__(self, ip: str):
        self.ip = ip
        super().__init__(f"IP {ip} not found in blacklist")


class InvalidIPError(IPBlacklistError):
    """Raised when an IP address format is invalid.

    This is a validation error at the domain level: the IP
    doesn't conform to IPv4 or IPv6 standards.
    """
    def __init__(self, ip: str):
        self.ip = ip
        super().__init__(f"Invalid IP address format: {ip}")


class IPFamilyMismatchError(IPBlacklistError):
    """Raised when an IP's version does not match what this backend
    instance can represent.

    Distinct from InvalidIPError: the address format itself is valid,
    but the wrong family for this backend (e.g. an IPv6 address passed
    to the iptables adapter, or an IPv4 address passed to ip6tables —
    plan IPv6 iptables, référentiel §53, Phase B). iptables and
    ip6tables are two separate binaries with no dual-stack mechanism at
    the tool level (unlike nftables), so each adapter instance can only
    ever represent one family.
    """
    def __init__(self, ip: str, expected_version: int, backend: str):
        self.ip = ip
        self.expected_version = expected_version
        self.backend = backend
        super().__init__(
            f"IP {ip} is not IPv{expected_version} — incompatible with backend '{backend}'"
        )

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions métier spécifiques au sous-domaine blacklist d'IPs. Ces exceptions expriment des règles métier violées (IP déjà bannie, IP introuvable, IP invalide), pas des pannes techniques.
# Pourquoi dans domain/ (charte) : 
# - C'est une erreur métier : violation d'un invariant du domaine
# - Aucune dépendance externe (hérite juste de Exception)
# - Testable sans aucun backend réel
# - Sera capturée par application/ pour être traduite en Result ou message utilisateur
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas d'erreur technique)
# ❌ Pas d'import depuis interfaces/ (pas de message utilisateur)
# ❌ Pas d'import depuis application/ (pas de logique de cas d'usage)
# Points clés à retenir :
# - Hiérarchie claire : toutes les exceptions héritent de IPBlacklistError → permet de capturer globalement si besoin
# - Contexte riche : chaque exception stocke les données pertinentes (ip, backend) → utile pour l'audit et les messages
# - Messages explicites : le message d'erreur est compréhensible sans contexte additionnel
# - Aucune dépendance : ces exceptions ne savent rien de nftables, iptables, fail2ban, SQLite ou Rich
# Comment elles seront utilisées (aperçu) :
# - domain/ip_blacklist/service.py les lèvera quand une règle métier est violée
# - application/commands/ban_ip.py les capturera et les traduira en Result.fail()
# - interfaces/cli/actions.py affichera le message à l'utilisateur
#---------------------------------------------------------------------->
