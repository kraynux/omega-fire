# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Known services reference list.

Defines the fixed list of well-known system services/processes that
Omega-Fire actively looks for via process detection (pgrep), beyond
the core firewall backends (nftables, iptables, fail2ban, conntrack).

This is the single source of truth for "what services does Omega-Fire
know how to look for" — both the scanner (which populates the
capability registry) and the dashboard renderer (which displays the
results) read from this same list, avoiding duplication and drift
between what is scanned and what is displayed.
"""

KNOWN_SERVICES: dict[str, list[str]] = {
    "system_services": [
        "sshd", "tailscaled", "smbd", "nmbd", "docker", "dockerd",
        "containerd", "cupsd", "cronie", "ntpd", "chronyd",
    ],
    "servers": [
        # Web / reverse proxy
        "lighttpd", "nginx", "apache2", "httpd", "caddy", "haproxy",
        "traefik", "openresty", "php-fpm",
        # Base de données
        "mysqld", "mariadbd", "postgres", "redis-server", "mongod",
        # Mail
        "postfix", "exim", "dovecot", "sendmail",
        # DNS
        "bind9", "named", "unbound", "dnsmasq", "pdns_server",
        # Fichiers / partage
        "nfsd", "vsftpd", "proftpd", "pure-ftpd", "sftpgo",
        # VPN
        "openvpn", "wireguard", "strongswan",
        # Monitoring
        "grafana-server", "prometheus", "netdata",
    ],
    "bureau_distant": [
        "x0vncserver", "vncserver", "tigervncserver", "tightvncserver",
        "x11vnc", "vino-server", "krfb", "wayvnc", "turbovnc",
        "rustdesk", "teamviewerd", "anydesk", "nxserver",
        "x2goserver", "xrdp", "remmina",
    ],
    "security_network": [
        # Note : ufw et firewalld n'ont généralement pas de process
        # permanent détectable via pgrep — ufw applique ses règles au
        # démarrage puis s'efface (visibles indirectement dans les
        # chaînes nftables ufw-* si actif), firewalld peut fonctionner
        # de façon similaire selon la configuration. Détection process
        # conservée ici par cohérence de structure, mais peut ne rien
        # trouver même si l'outil est actif — limitation connue.
        "opensnitch", "firewalld", "ufw", "crowdsec", "webmin",
        "csf", "shorewall", "bunkerweb",
    ],
}


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Liste fixe des services/process connus qu'Omega-Fire recherche via
#   détection de process (pgrep), en complément des backends firewall.
# - Source unique de vérité, partagée entre infrastructure/probe/scanner.py
#   (qui peuple le registre) et interfaces/cli/renderers/dashboard.py
#   (qui affiche les résultats) — évite la duplication et la dérive
#   entre ce qui est scanné et ce qui est affiché.
#
# Pourquoi dans infrastructure/probe/ (charte) :
# - Donnée statique directement liée au mécanisme de scan technique
#   (pgrep), colocalisée avec lui plutôt que dans core/.
#
# Comment il sera utilisé :
# - infrastructure/probe/scanner.py::_scan_known_services() itère
#   dessus pour peupler le registre de capacités.
# - interfaces/cli/renderers/dashboard.py importe KNOWN_SERVICES au
#   lieu de définir sa propre REFERENCE_CAPABILITIES locale.
#----------------------------------------------------------------------
