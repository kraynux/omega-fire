# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban filter content generation.

Pure domain logic for generating fail2ban filter (failregex) content.
This module defines WHAT a generated filter's content looks like, not
HOW/WHEN it gets written to disk (infrastructure's job, see
Fail2banAdapter.write_filter()) or WHEN one should be generated at all
(application/interfaces' job).
"""


def generate_default_http_filter(jail_name: str) -> str:
    """Generate a generic HTTP-log failure filter (400/401/403/404/500).

    Matches common access/error log formats (nginx, apache, caddy,
    lighttpd) capturing the client IP as <HOST> on HTTP requests that
    ended in a client/server error status.

    Relocated verbatim from
    interfaces/cli/actions.py::action_4_4_create_jail — same regex,
    same behavior, not a rewrite. That location generated this content
    directly in interfaces/, a charter violation (business logic +
    disk write in the interface layer).

    Not a smart per-service filter: every jail using this default gets
    the exact same generic regex regardless of the actual log format
    being monitored — a known, pre-existing limitation carried forward
    unchanged (e.g. a syslog file has no HTTP status lines at all, so a
    filter generated this way for it will simply never match anything).

    Args:
        jail_name: Name of the jail this filter is generated for (used
            only in the comment header, not in the regex itself).

    Returns:
        Filter file content (fail2ban ini format, [Definition] section).
    """
    return (
        f"# Filtre généré automatiquement par Omega-Fire pour {jail_name}\n"
        "[Definition]\n"
        "failregex = ^<HOST> - - \\[[^\\]]+\\] \"(?:GET|POST|HEAD|CONNECT|PUT|DELETE) .* HTTP/.*\" (?:400|401|403|404|500)\n"
        "            ^<HOST> - - \\[[^\\]]+\\] \".*\" (?:400|401|403|404|500)\n"
        "            ^\\s*<HOST> \\S+ \\S+ \\[[^\\]]+\\] \".*\" (?:400|401|403|404|500)\n"
        "ignoreregex =\n"
    )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Génère le CONTENU d'un filtre fail2ban (regex failregex/ignoreregex)
#   à partir d'un nom de jail. Pure fonction, aucun effet de bord.
# Pourquoi dans domain/ (charte) :
# - Décider de la regex de détection d'échec est une règle métier, pas
#   une décision d'affichage ni d'infrastructure — c'est exactement ce
#   que le référentiel (§5) identifiait comme mal placé dans
#   interfaces/cli/actions.py::action_4_4_create_jail.
# - Aucune dépendance externe (pas d'I/O, pas de subprocess).
# Ce qu'il ne contient PAS :
# ❌ Pas d'écriture sur disque (infrastructure/backends/fail2ban/adapter.py
#   ::write_filter() s'en charge)
# ❌ Pas de décision sur QUAND générer un filtre (application/interfaces)
# ❌ Pas de variation par type de log (limitation connue, conservée telle
#   quelle — un seul gabarit générique HTTP pour l'instant)
# Points clés :
# - generate_default_http_filter() : seule fonction pour l'instant,
#   contenu identique à ce qui était en dur dans actions.py (relocalisé,
#   pas réécrit)
# Comment il sera utilisé :
# - interfaces/cli/actions.py::action_4_4_create_jail appelle cette
#   fonction puis passe le résultat à
#   infrastructure/backends/fail2ban/adapter.py::Fail2banAdapter.write_filter()
#---------------------------------------------------------------------->
