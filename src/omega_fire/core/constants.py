# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Core constants for the application.
Defines global constants used throughout the application.
Centralizes configuration values and system limits.
Conforms to Omega-Fire architecture charter:
- No business logic (only constants)
- Provides global constants for the entire application
"""
# Application metadata
APP_NAME = "Omega-Fire"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Linux Firewall Manager"
# Terminal requirements
MIN_TERMINAL_WIDTH = 80
MIN_TERMINAL_HEIGHT = 24
OPTIMAL_TERMINAL_WIDTH = 120
OPTIMAL_TERMINAL_HEIGHT = 40
# System limits
MAX_AUDIT_EVENTS = 10000
MAX_BAN_ENTRIES = 100000
MAX_RULE_ENTRIES = 10000
MAX_LOG_LINES = 1000000
# Timeouts (in seconds)
DEFAULT_COMMAND_TIMEOUT = 10
DEFAULT_SCAN_TIMEOUT = 30
DEFAULT_LOG_READ_TIMEOUT = 5
# File paths (relative to project root)
VAR_DIR = "var"
DB_DIR = "var/db"
CACHE_DIR = "var/cache"
EXPORTS_DIR = "var/exports"
BACKUPS_DIR = "var/backups"
LOGS_DIR = "var/logs"
# Database
DB_FILENAME = "omega.db"
DB_PATH = f"{DB_DIR}/{DB_FILENAME}"
# Log files
APP_LOG_FILENAME = "omega-fire.log"
AUDIT_LOG_FILENAME = "audit.log"
APP_LOG_PATH = f"{LOGS_DIR}/{APP_LOG_FILENAME}"
AUDIT_LOG_PATH = f"{LOGS_DIR}/{AUDIT_LOG_FILENAME}"
# Default values
DEFAULT_THEME = "omega-base"
FALLBACK_THEME = "omega-mono"
DEFAULT_LOG_LINES = 30
DEFAULT_TOP_N = 10
# Backend identifiers
BACKEND_NFTABLES = "nftables"
BACKEND_IPTABLES = "iptables"
BACKEND_FAIL2BAN = "fail2ban"
BACKEND_CONNTRACK = "conntrack"
# Service identifiers
SERVICE_MANAGER = "service_manager"
SERVICE_FAIL2BAN = "fail2ban_service"
# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_INTERRUPTED = 130
# <-- INFO DEV ---------------------------------------------------------
# Role :
# - Definit les constantes globales utilisees dans toute l'application
# - Centralise les valeurs de configuration et les limites systeme
#
# Pourquoi dans core/ (charte) :
# - C'est un module transverse utilise par toute l'application
# - Pas de logique metier
# - Fournit les constantes globales pour l'ensemble de l'application
#
# Ce qu'il ne contient PAS :
# - Pas de logique metier
# - Pas de rendu
# - Pas de navigation
# - Pas de dependance vers domain/, application/, infrastructure/, interfaces/
#
# Points cles :
# - Metadonnees application : APP_NAME, APP_VERSION, APP_DESCRIPTION
# - Exigences terminal : MIN_TERMINAL_WIDTH/HEIGHT, OPTIMAL_TERMINAL_WIDTH/HEIGHT
# - Limites systeme : MAX_AUDIT_EVENTS, MAX_BAN_ENTRIES, etc.
# - Timeouts : DEFAULT_COMMAND_TIMEOUT, DEFAULT_SCAN_TIMEOUT, etc.
# - Chemins fichiers : VAR_DIR, DB_DIR, LOGS_DIR, etc.
# - Base de donnees : DB_FILENAME, DB_PATH
# - Fichiers logs : APP_LOG_FILENAME, AUDIT_LOG_FILENAME, etc.
# - Valeurs par defaut : DEFAULT_THEME, FALLBACK_THEME, etc.
# - Identifiants backend : BACKEND_NFTABLES, BACKEND_IPTABLES, etc.
# - Identifiants service : SERVICE_MANAGER, SERVICE_FAIL2BAN
# - Codes sortie : EXIT_SUCCESS, EXIT_ERROR, EXIT_INTERRUPTED
#---------------------------------------------------------------------->
