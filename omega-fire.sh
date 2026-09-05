#!/usr/bin/env bash
# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# ==============================================================================
# Script d'amorçage sécurisé - OMEGA-FIRE CLI
# Exige les privilèges root pour interagir avec nftables, fail2ban & le réseau.
# ==============================================================================

set -e

# Forcer un environnement UTF-8 : sans ça, sudo (qui réinitialise
# l'environnement par défaut) ou une session distante mal configurée
# peuvent faire retomber LANG/LC_ALL sur une locale C/POSIX, ce qui casse
# l'affichage des icônes (Python/Rich les remplacent alors par "??").
if [ -z "${LC_ALL:-}" ] && [ -z "${LANG:-}" ] || [ "${LANG:-}" = "C" ] || [ "${LANG:-}" = "POSIX" ]; then
    if locale -a 2>/dev/null | grep -qi '^C\.utf8$'; then
        export LC_ALL=C.UTF-8
        export LANG=C.UTF-8
    elif locale -a 2>/dev/null | grep -qi '^en_US\.utf8$'; then
        export LC_ALL=en_US.UTF-8
        export LANG=en_US.UTF-8
    fi
fi

# Couleurs pour le terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
LIGHT_BLUE='\033[1;34m'    
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
LIGHT_WHITE='\033[0;37m' 
CYAN='\033[0;36m'
LIGHT_CYAN='\033[1;36m'	
NC='\033[0m'
echo -e "${LIGHT_WHITE}${NC}"
echo -e "${LIGHT_WHITE}DÉMARRAGE DE L'APPLICATION${NC}"
echo -e "${LIGHT_WHITE}${NC}"
echo -e "${WHITE}	░▒▓█████████████████▓▒░${NC}"
echo -e "${WHITE}	░ Ω M E G A - F I R E ░${NC}"
echo -e "${WHITE}	░▒▓█████████████████▓▒░${NC}" 
echo -e "${LIGHT_WHITE}${NC}"
echo -e "${LIGHT_WHITE}Vérification des privileges en cours${NC}"
echo -e "${LIGHT_WHITE}${NC}"
# 1. Vérification / Élévation des privilèges root (sudo)
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}[SECURITY] Omega-Fire requiert les privilèges d'administration.${NC}"
    echo -e "${YELLOW}           (Accès requis pour nftables, fail2ban-client, etc.)${NC}\n"
    
    # Demande de mot de passe sudo (--preserve-env pour ne pas perdre la
    # locale UTF-8 forcée ci-dessus : sudo réinitialise l'environnement
    # par défaut, ce qui provoquerait le même souci d'affichage sous root)
    exec sudo --preserve-env=LANG,LC_ALL "$0" "$@"
    exit $?
fi

# 1b. Umask permissif pour le groupe : l'appli tourne toujours en root
# (ci-dessus), donc tout fichier qu'elle crée sous var/ (logs, exports,
# état runtime) est root:root par défaut. Combiné au bit setgid posé sur
# var/ à l'installation (groupe dédié "omega-fire", cf. installation.txt),
# cet umask garantit que ces fichiers restent lisibles ET modifiables par
# l'utilisateur normal sans sudo — sans lui, le setgid seul ne suffit pas :
# umask par défaut (022) donnerait rw-r--r--, groupe en lecture seule.
umask 002

# 2. Détection du répertoire racine du projet
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 3. Détection de l'interpréteur Python (.venv ou venv ou système)
if [ -d ".venv" ]; then
    VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
elif [ -d "venv" ]; then
    VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"
else
    VENV_PYTHON="$(which python3)"
fi

if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}❌ Erreur : Aucun interpréteur Python trouvé.${NC}"
    exit 1
fi

# 4. Confirmation d'authentification
echo -e "${GREEN}✔ Authentification réussie (Root). Lancement du système...${NC}\n"

# 5. Exécution du point d'entrée officiel (module omega_fire)
export PYTHONPATH="$SCRIPT_DIR/src"
exec "$VENV_PYTHON" -m omega_fire "$@"
