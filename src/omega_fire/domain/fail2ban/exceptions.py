# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban domain exceptions.

Pure domain exceptions for the fail2ban subdomain.
These express business rule violations, not technical failures
of the fail2ban-client binary. They are caught by application/
and translated into Results or user-facing messages.
"""
from omega_fire.shared.i18n import _


class Fail2banError(Exception):
    """Base exception for fail2ban domain.
    
    All domain-specific exceptions for fail2ban inherit from this.
    """
    pass


class JailNotFoundError(Fail2banError):
    """Raised when attempting to operate on a non-existent jail.
    
    Business rule: a jail must exist before it can be queried,
    banned from, or unbanned.
    """
    def __init__(self, jail_name: str):
        self.jail_name = jail_name
        super().__init__(_("Jail « {jail_name} » introuvable").format(jail_name=jail_name))


class JailNotDeletableError(Fail2banError):
    """Le jail ne peut pas etre supprime sans toucher a d'autres reglages (point 7, version
    3.5) : defini dans jail.conf / jail.local, ou dans un fichier jail.d partage avec
    d'autres jails. `blocked` : constante BLOCKED_* de domain/fail2ban/definitions.py."""
    def __init__(self, jail_name: str, blocked: str, files: tuple[str, ...] = ()):
        self.jail_name = jail_name
        self.blocked = blocked
        self.files = files
        super().__init__(_("Le jail « {jail_name} » ne peut pas être supprimé ici ({files})").format(
            jail_name=jail_name, files=", ".join(files)))


class InvalidJailConfigError(Fail2banError):
    """Raised when a jail configuration is invalid.
    
    Examples: invalid maxretry value, invalid bantime,
    invalid findtime, missing required field, invalid log path.
    """
    def __init__(self, jail_name: str, reason: str):
        self.jail_name = jail_name
        self.reason = reason
        super().__init__(_("Configuration invalide pour le jail « {jail_name} » : {reason}").format(jail_name=jail_name, reason=reason))


class JailAlreadyExistsError(Fail2banError):
    """Raised when attempting to create a jail that already exists.
    
    Business rule: a jail name must be unique.
    """
    def __init__(self, jail_name: str):
        self.jail_name = jail_name
        super().__init__(_("Le jail « {jail_name} » existe déjà").format(jail_name=jail_name))


class JailDisabledError(Fail2banError):
    """Raised when attempting to ban/unban on a disabled jail.
    
    Business rule: operations on a jail require it to be enabled.
    """
    def __init__(self, jail_name: str):
        self.jail_name = jail_name
        super().__init__(_("Le jail « {jail_name} » est désactivé").format(jail_name=jail_name))


class InvalidIPForJailError(Fail2banError):
    """Raised when an IP is invalid for a specific jail context.

    Examples: IPv6 IP on an IPv4-only jail, IP already banned in jail.
    """
    def __init__(self, ip: str, jail_name: str, reason: str):
        self.ip = ip
        self.jail_name = jail_name
        self.reason = reason
        super().__init__(_("IP {ip} invalide pour le jail « {jail_name} » : {reason}").format(ip=ip, jail_name=jail_name, reason=reason))


class IPAlreadyBannedError(Fail2banError):
    """Raised when attempting to ban an IP already banned in a jail.

    Business rule: banning an already-banned IP in the same jail is a
    no-op at the fail2ban level; the port surfaces it as an error so
    callers can distinguish it from a genuine ban.
    """
    def __init__(self, ip: str, jail_name: str):
        self.ip = ip
        self.jail_name = jail_name
        super().__init__(_("L'IP {ip} est déjà bannie dans le jail « {jail_name} »").format(ip=ip, jail_name=jail_name))


class IPNotFoundError(Fail2banError):
    """Raised when attempting to unban an IP not currently banned in a jail.

    Business rule: unbanning an IP that isn't banned in the jail is a
    no-op at the fail2ban level; the port surfaces it as an error so
    callers can distinguish it from a genuine unban.
    """
    def __init__(self, ip: str, jail_name: str):
        self.ip = ip
        self.jail_name = jail_name
        super().__init__(_("IP {ip} introuvable dans le jail « {jail_name} »").format(ip=ip, jail_name=jail_name))


class TransferError(Fail2banError):
    """Raised when transferring IPs from jail to blacklist fails.
    
    Examples: blacklist backend unavailable, invalid IP in jail,
    transfer conflict.
    """
    def __init__(self, jail_name: str, reason: str):
        self.jail_name = jail_name
        self.reason = reason
        super().__init__(_("Erreur de transfert depuis le jail « {jail_name} » : {reason}").format(jail_name=jail_name, reason=reason))


class InvalidParameterError(Fail2banError):
    """Raised when a fail2ban parameter is out of valid range.
    
    Examples: maxretry < 1, bantime < 0, findtime < 0.
    """
    def __init__(self, parameter: str, value, reason: str):
        self.parameter = parameter
        self.value = value
        self.reason = reason
        super().__init__(
            _("Paramètre « {parameter} » invalide (valeur={value}) : {reason}").format(parameter=parameter, value=value, reason=reason)
        )
# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions métier spécifiques au sous-domaine fail2ban. Ces exceptions expriment des violations de règles métier (jail inexistant, configuration invalide, transfert impossible), pas des pannes techniques du client fail2ban.
# Pourquoi dans domain/ (charte) :
# - C'est une erreur métier : violation d'un invariant du domaine fail2ban
# - Aucune dépendance externe (hérite juste de Exception)
# -Testable sans aucun backend réel
# -Sera capturée par application/ pour être traduite en Result ou message utilisateur
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis infrastructure/ (pas d'erreur technique du client fail2ban)
# ❌ Pas d'import depuis interfaces/ (pas de message utilisateur)
# ❌ Pas d'import depuis application/ (pas de logique de cas d'usage)
# Points clés :
# - Hiérarchie claire : toutes les exceptions héritent de Fail2banError
# - 9 exceptions ciblées :
#   - JailNotFoundError : jail inexistant
#   - InvalidJailConfigError : configuration invalide
#   - JailAlreadyExistsError : jail déjà existant
#   - JailDisabledError : jail désactivé
#   - InvalidIPForJailError : IP invalide pour un jail
#   - TransferError : échec de transfert jail → blacklist
#   - InvalidParameterError : paramètre hors limites
#   - IPAlreadyBannedError : ban_ip() sur une IP déjà bannie dans le jail (Fail2banPort.ban_ip)
#   - IPNotFoundError : unban_ip() sur une IP non bannie dans le jail (Fail2banPort.unban_ip)
# - Contexte riche : chaque exception stocke les données pertinentes (jail_name, ip, parameter)
# - Aucune dépendance : ne sait rien de fail2ban-client, SQLite ou Rich
# Comment elles seront utilisées (aperçu) :
# - domain/fail2ban/service.py les lèvera quand une règle métier est violée
# - application/commands/jail_ban.py les capturera et les traduira en Result.fail()
# - interfaces/cli/actions.py affichera le message à l'utilisateur
#---------------------------------------------------------------------->
