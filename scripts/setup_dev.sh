#!/usr/bin/env bash
# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Configure l'environnement de developpement pour omega-fire.
# Suppose que ~/DEV/LIB/omega-lib existe deja (meme convention que
# omega-check/omega-stress). Installe omega-lib EN PREMIER, avant
# requirements.txt, pour que pip la trouve deja satisfaite dans le venv
# et ne tente jamais de la chercher sur PyPI (elle n'y est pas publiee).
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -e ../../LIB/omega-lib
pip install --quiet -r requirements.txt

echo "Environnement pret (.venv actif)."
