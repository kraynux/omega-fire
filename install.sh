#!/usr/bin/env bash
# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# ==============================================================================
# Script d'installation - OMEGA-FIRE CLI
# À lancer depuis le dossier extrait de l'archive : cd omega-fire && ./install.sh
# Résilient : peut être relancé sans erreur si une étape a déjà été faite.
# Une seule distro détectée automatiquement (pas de script séparé par distro) —
# seuls deux points varient réellement (module venv sur Debian/Ubuntu, Nerd
# Font), tout le reste (venv, pip, permissions, alias) est identique partout.
# ==============================================================================

set -e

# Forcer un environnement UTF-8 : une session distante mal configurée peut
# faire retomber LANG/LC_ALL sur une locale C/POSIX, ce qui casse l'affichage
# des icônes ci-dessous (remplacées par "??").
if [ -z "${LC_ALL:-}" ] && [ -z "${LANG:-}" ] || [ "${LANG:-}" = "C" ] || [ "${LANG:-}" = "POSIX" ]; then
    if locale -a 2>/dev/null | grep -qi '^C\.utf8$'; then
        export LC_ALL=C.UTF-8
        export LANG=C.UTF-8
    elif locale -a 2>/dev/null | grep -qi '^en_US\.utf8$'; then
        export LC_ALL=en_US.UTF-8
        export LANG=en_US.UTF-8
    fi
fi

# Couleurs (mêmes conventions que omega-fire.sh)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}ℹ️  $1${NC}"; }
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; }
tip()  { echo -e "${WHITE}💡 $1${NC}"; }

echo -e "${WHITE}	░▒▓████████████████████████████████▓▒░${NC}"
echo -e "${WHITE}	░ Ω M E G A - F I R E — INSTALLATION ░${NC}"
echo -e "${WHITE}	░▒▓████████████████████████████████▓▒░${NC}"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# -------------------------------------------------------------------------
# 1. Détection de la distribution — seulement pour les 2 points qui varient
#    réellement d'une distro à l'autre (module venv, suggestion Nerd Font).
#    ID seul ne suffit pas : les dérivées (Manjaro/EndeavourOS -> arch,
#    Mint/Pop!_OS -> debian/ubuntu, CentOS/RHEL -> fedora) ont un ID propre
#    mais un ID_LIKE qui les rattache à la famille — les deux sont vérifiés.
# -------------------------------------------------------------------------
DISTRO_ID="unknown"
DISTRO_LIKE=""
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO_ID="${ID:-unknown}"
    DISTRO_LIKE="${ID_LIKE:-}"
fi

DISTRO_MATCH="${DISTRO_ID} ${DISTRO_LIKE}"
case "$DISTRO_MATCH" in
    *arch*)             DISTRO_FAMILY="arch" ;;
    *fedora*|*rhel*)     DISTRO_FAMILY="fedora" ;;
    *debian*|*ubuntu*)   DISTRO_FAMILY="debian" ;;
    *)                   DISTRO_FAMILY="unknown" ;;
esac
info "Distribution détectée : ${DISTRO_ID} (famille : ${DISTRO_FAMILY})"

# -------------------------------------------------------------------------
# 2. Environnement virtuel Python
# -------------------------------------------------------------------------
if [ -d ".venv" ]; then
    info ".venv existe déjà, création ignorée."
else
    if ! python3 -m venv .venv 2>/tmp/omega-fire-venv-err.log; then
        err "Échec de la création de l'environnement virtuel."
        if [ "$DISTRO_FAMILY" = "debian" ]; then
            warn "Sur Debian/Ubuntu (et dérivées), le module venv n'est pas toujours inclus avec python3 de base."
            tip "Installez-le puis relancez ce script : sudo apt install python3-venv"
        else
            cat /tmp/omega-fire-venv-err.log >&2
        fi
        rm -f /tmp/omega-fire-venv-err.log
        exit 1
    fi
    rm -f /tmp/omega-fire-venv-err.log
    ok "Environnement virtuel créé (.venv)."
fi

# -------------------------------------------------------------------------
# 3. Dépendances — omega-lib n'est pas publiée sur PyPI : l'archive
#    distribuable la vendore dans vendor/omega-lib/ (voir build-release.sh)
#    — installée ICI, avant requirements.txt, pour que pip la trouve déjà
#    satisfaite dans le venv et ne tente jamais de la chercher sur PyPI.
#    Absente en clone de développement (omega-lib vient alors du monorepo
#    local ~/DEV/LIB/omega-lib, déjà installée à part via
#    scripts/setup_dev.sh) : étape silencieusement ignorée si
#    vendor/omega-lib/ n'existe pas — même mécanisme qu'omega-stress/
#    omega-check.
# -------------------------------------------------------------------------
source .venv/bin/activate
pip install -q --upgrade pip
if [ -d "$SCRIPT_DIR/vendor/omega-lib" ]; then
    pip install -q -e "$SCRIPT_DIR/vendor/omega-lib"
    ok "Dépendance vendorée omega-lib installée."
fi
pip install -q -r requirements.txt
ok "Dépendances installées."

# -------------------------------------------------------------------------
# 4. Scripts exécutables
# -------------------------------------------------------------------------
chmod +x omega-fire.sh
chmod +x "$SCRIPT_DIR/install.sh"

# -------------------------------------------------------------------------
# 5. Permissions var/ — groupe dédié + setgid, pour que root (l'appli
#    tourne toujours en sudo) ET l'utilisateur normal puissent lire/écrire
#    les fichiers créés sous var/ (logs, exports, état runtime), sans
#    jamais ouvrir les droits à tout le système.
# -------------------------------------------------------------------------
mkdir -p var

if getent group omega-fire >/dev/null 2>&1; then
    info "Groupe omega-fire déjà présent."
else
    sudo groupadd omega-fire
    ok "Groupe omega-fire créé."
fi

if groups "$USER" 2>/dev/null | grep -qw omega-fire; then
    info "$USER déjà membre du groupe omega-fire."
else
    sudo usermod -aG omega-fire "$USER"
    ok "$USER ajouté au groupe omega-fire."
fi

sudo chgrp -R omega-fire var
sudo chmod -R 2775 var
ok "Permissions var/ prêtes."
tip "L'appli (toujours lancée en sudo) fonctionne dès maintenant, aucune reconnexion requise."
tip "Optionnel : pour accéder aux fichiers de var/ SANS sudo, le groupe omega-fire doit être actif dans votre session — automatique à la prochaine connexion, ou immédiat avec 'newgrp omega-fire'."

# -------------------------------------------------------------------------
# 6. Alias (optionnel) — bash et zsh, quel que soit celui réellement utilisé
# -------------------------------------------------------------------------
ALIAS_LINE="alias fire=\"sudo ${SCRIPT_DIR}/omega-fire.sh\""

for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    rc_name="$(basename "$rc")"
    if grep -qxF "$ALIAS_LINE" "$rc" 2>/dev/null; then
        info "Alias déjà présent dans $rc_name."
    elif echo "$ALIAS_LINE" >> "$rc" 2>/dev/null; then
        ok "Alias ajouté à $rc_name."
    else
        warn "Impossible d'ajouter l'alias à $rc_name."
    fi
done

# -------------------------------------------------------------------------
# 7. Nerd Font — information seulement, jamais installée automatiquement
#    (police système, pas une dépendance applicative).
# -------------------------------------------------------------------------
echo ""
tip "Pour un affichage correct des icônes du dashboard, une Nerd Font est requise :"
case "$DISTRO_FAMILY" in
    arch)
        echo "    sudo pacman -S ttf-nerd-fonts-symbols"
        ;;
    fedora)
        echo "    sudo dnf copr enable che/nerd-fonts && sudo dnf install nerd-fonts-jetbrains-mono"
        ;;
    *)
        echo "    Pas de paquet officiel sur cette distribution — installation manuelle :"
        echo "    mkdir -p ~/.local/share/fonts"
        echo "    curl -fLo /tmp/NerdFontsSymbolsOnly.zip https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip"
        echo "    unzip -o /tmp/NerdFontsSymbolsOnly.zip -d ~/.local/share/fonts && fc-cache -fv"
        ;;
esac

echo ""
ok "Installation terminée."
tip "Lancez Omega-Fire avec : ${SCRIPT_DIR}/omega-fire.sh (ou 'fire' dans un nouveau terminal si l'alias vient d'être ajouté)."
