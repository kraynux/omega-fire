#!/usr/bin/env bash
# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# ==============================================================================
# Copie l'etat vivant (config/omega-fire.conf, blocklist, base de donnees,
# exports, sauvegardes, captures) d'une ANCIENNE installation omega-fire
# vers CETTE installation-ci.
#
# Jamais invoque interactivement par l'utilisateur en temps normal : appele
# AUTOMATIQUEMENT par install.sh quand il detecte une extraction fraiche
# (var/db/ vide ici - aucune base de donnees reelle encore accumulee) a
# cote d'une ancienne installation sans ambiguite (voir install.sh, meme
# raison qu'omega-serv/migrate-state.sh, meme incident reel 2026-09-29 -
# "le but d'une mise a jour... c'est de recuperer les parametres et
# contenu presents"). --yes systematique dans ce cas, le seul
# "consentement" necessaire est celui d'avoir lance ./install.sh
# lui-meme. Reste utilisable a la main (sans --yes, demande alors une
# confirmation ecrite) pour une recuperation manuelle ciblee.
#
# sudo requis (contrairement a omega-serv, omega-fire tourne ENTIEREMENT
# en sudo - var/db, var/logs, var/runtime appartiennent a root:root, voir
# install.sh §5) : ce script ne tente aucune elevation lui-meme, il
# echoue simplement (permission refusee, message clair) si lance sans
# les droits necessaires - jamais un `sudo -v` cache ici, coherent avec
# le reste du projet (README, alias `fire="sudo ..."`).
#
# Usage : sudo ./migrate-state.sh <ancien-dossier-omega-fire> [--yes]
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${CYAN}ℹ️  $1${NC}"; }
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OLD_DIR=""
ASSUME_YES="false"
for arg in "$@"; do
    case "$arg" in
        --yes|-y) ASSUME_YES="true" ;;
        *) OLD_DIR="$arg" ;;
    esac
done

if [ -z "$OLD_DIR" ]; then
    err "Usage : $0 <ancien-dossier-omega-fire> [--yes]"
    echo "Exemple : $0 ~/omega-fire.old-20260929"
    exit 1
fi

OLD_DIR="$(cd "$OLD_DIR" 2>/dev/null && pwd || true)"
if [ -z "$OLD_DIR" ] || [ ! -d "$OLD_DIR" ]; then
    err "Dossier introuvable : ${1}"
    exit 1
fi

if [ "$OLD_DIR" = "$SCRIPT_DIR" ]; then
    err "L'ancien dossier ne peut pas etre le meme que celui-ci ($SCRIPT_DIR)."
    exit 1
fi

if [ "$ASSUME_YES" != "true" ]; then
    echo ""
    warn "Cette action va ECRASER dans :"
    echo "    $SCRIPT_DIR"
    warn "les fichiers d'etat (config, base de donnees, blocklist, exports...) copies depuis :"
    echo "    $OLD_DIR"
    echo ""
    read -r -p "Tapez CONFIRMER pour continuer : " confirmation
    if [ "$confirmation" != "CONFIRMER" ]; then
        err "Annule."
        exit 1
    fi
fi

info "Recuperation de l'etat depuis $OLD_DIR..."

_copy() {
    local rel="$1"
    if [ -e "$OLD_DIR/$rel" ]; then
        mkdir -p "$(dirname "$SCRIPT_DIR/$rel")"
        rsync -a "$OLD_DIR/$rel" "$SCRIPT_DIR/$rel"
        ok "Recupere : $rel"
    fi
}

_copy_dir_contents() {
    local rel="$1"
    if [ -d "$OLD_DIR/$rel" ]; then
        mkdir -p "$SCRIPT_DIR/$rel"
        rsync -a "$OLD_DIR/$rel/" "$SCRIPT_DIR/$rel/"
        ok "Recupere : $rel/"
    fi
}

# Meme liste que build-release.sh (section "exclude"), a l'exception de
# var/cache/*, var/logs/*, var/runtime/*, var/*.log, var/*.jsonl : etat
# transitoire, jamais reporte d'une installation a l'autre, se regenere
# tout seul.
_copy "config/omega-fire.conf"
_copy_dir_contents "var/blocklist"
_copy_dir_contents "var/db"
_copy_dir_contents "var/backups"
_copy_dir_contents "var/exports"
_copy_dir_contents "var/screenshots"
_copy "var/settings.json"

if command -v getent >/dev/null 2>&1 && getent group omega-fire >/dev/null 2>&1; then
    chgrp -R omega-fire "$SCRIPT_DIR/var" 2>/dev/null || true
    chmod -R g+rwX "$SCRIPT_DIR/var" 2>/dev/null || true
fi

ok "Etat recupere depuis l'ancienne installation."
