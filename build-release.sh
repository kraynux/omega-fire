#!/usr/bin/env bash
# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# ==============================================================================
# Construit l'archive distribuable omega-fire-<version>.tar.gz : copie le
# projet (sans artefacts dev/runtime), vendore omega-lib (dependance
# obligatoire non publiee sur PyPI, voir install.sh), archive le tout.
# Meme mecanisme qu'omega-stress/omega-check (Phase 6 de la feuille de
# route de migration TUI). Outil de maintenance, jamais lui-meme inclus
# dans l'archive generee.
# ==============================================================================

set -e

# Forcer un environnement UTF-8 pour l'affichage des icônes (voir la même
# protection dans install.sh / omega-fire.sh).
if [ -z "${LC_ALL:-}" ] && [ -z "${LANG:-}" ] || [ "${LANG:-}" = "C" ] || [ "${LANG:-}" = "POSIX" ]; then
    if locale -a 2>/dev/null | grep -qi '^C\.utf8$'; then
        export LC_ALL=C.UTF-8
        export LANG=C.UTF-8
    elif locale -a 2>/dev/null | grep -qi '^en_US\.utf8$'; then
        export LC_ALL=en_US.UTF-8
        export LANG=en_US.UTF-8
    fi
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}ℹ️  $1${NC}"; }
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; }

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OMEGA_LIB_SRC="${OMEGA_LIB_SRC:-$HOME/DEV/LIB/omega-lib}"

if [ ! -d "$OMEGA_LIB_SRC" ]; then
    err "omega-lib introuvable : $OMEGA_LIB_SRC (definissez OMEGA_LIB_SRC si le chemin differe)."
    exit 1
fi

# pyproject.toml est vide (omega-fire n'utilise pas cet outillage, voir
# DECISIONS_ARCHITECTURE.md) — la version vit dans OMEGA_FIRE_VERSION
# (application/queries/dashboard_snapshot.py), seule source de verite
# actuelle pour ce numero.
VERSION="$(grep -m1 '^OMEGA_FIRE_VERSION' "$PROJECT_ROOT/src/omega_fire/application/queries/dashboard_snapshot.py" | sed -E 's/OMEGA_FIRE_VERSION = "(.*)"/\1/')"
ARCHIVE_NAME="omega-fire-${VERSION}.tar.gz"

STAGING_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGING_DIR"' EXIT
DEST="$STAGING_DIR/omega-fire"
mkdir -p "$DEST"

info "Copie du projet omega-fire..."
rsync -a \
    --exclude='.venv/' --exclude='venv/' \
    --exclude='__pycache__/' --exclude='*.pyc' \
    --exclude='.pytest_cache/' --exclude='.mypy_cache/' --exclude='.ruff_cache/' \
    --exclude='.import_linter_cache/' --exclude='*.egg-info/' \
    --exclude='.git/' --exclude='.claude/' \
    --exclude='var/blocklist/*' --exclude='var/cache/*' --exclude='var/backups/*' \
    --exclude='var/runtime/*' --exclude='var/exports/*' --exclude='var/db/*' \
    --exclude='var/logs/*' --exclude='var/screenshots/*' --exclude='var/settings.json' \
    --exclude='var/*.log' --exclude='var/*.jsonl' \
    --exclude='*~' --exclude='*.bak' --exclude='*.swp' \
    --exclude='.coverage' --exclude='htmlcov/' \
    --exclude='build-release.sh' --exclude='omega-fire-*.tar.gz' --exclude='omega-fire.tar.gz' \
    "$PROJECT_ROOT/" "$DEST/"

info "Vendoring d'omega-lib (dependance obligatoire, non publiee sur PyPI)..."
mkdir -p "$DEST/vendor/omega-lib"
rsync -a \
    --exclude='.venv/' --exclude='__pycache__/' --exclude='*.pyc' \
    --exclude='.pytest_cache/' --exclude='.mypy_cache/' --exclude='.ruff_cache/' \
    --exclude='*.egg-info/' --exclude='.git/' --exclude='tests/' \
    "$OMEGA_LIB_SRC/" "$DEST/vendor/omega-lib/"

info "Archivage..."
tar -C "$STAGING_DIR" -czf "$PROJECT_ROOT/$ARCHIVE_NAME" omega-fire

ok "Archive generee : $ARCHIVE_NAME"
echo "sha256sum $ARCHIVE_NAME :"
sha256sum "$PROJECT_ROOT/$ARCHIVE_NAME"
