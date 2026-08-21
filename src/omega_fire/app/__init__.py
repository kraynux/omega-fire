# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Marque le package src/omega_fire/app comme module importable
# - Sert de point d'entrée symbolique pour la couche app
# - N'embarque aucune logique métier, seulement la définition du package
#
# Pourquoi dans app/ (charte) :
# - C'est une couche de composition et de câblage applicatif
# - Le fichier doit rester léger pour éviter les import circulaires
# - Il permet d'exposer le package sans coupler les sous-modules entre eux
#
# Ce qu'il ne contient PAS :
# - ❌ Pas de logique métier
# - ❌ Pas de dépendance directe vers infrastructure/
# - ❌ Pas de construction de menu
# - ❌ Pas d'appel système
# - ❌ Pas d'initialisation lourde au moment de l'import
#
# Ce qu'il contient :
# - Un marqueur de package Python
# - Éventuellement des exports publics strictement nécessaires
# - Rien d'autre par défaut
#
# Points clés :
# - __init__.py peut rester vide sans problème technique
# - Il sert à signaler explicitement que le dossier est un package
# - Il évite les ambiguïtés d'import et aide les outils de développement
# - Il ne doit pas déclencher de traitement au chargement
#
# Comment il sera utilisé (aperçu) :
# - Les imports de la couche app passeront par ce package
# - Les modules app/* seront consommés sans exposition forcée ici
# - Les tests vérifieront que le package est importable sans effet de bord
#----------------------------------------------------------------------> 
