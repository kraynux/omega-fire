# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Application settings.

Defines the application settings as a dataclass, loaded from environment
variables and configuration files. This is the single source of truth
for all configuration values used by the application.

This module performs file I/O to load configuration and is therefore
in infrastructure/.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from omega_fire.infrastructure.config.env import EnvLoader
from omega_fire.infrastructure.config.paths import AppPaths
from configparser import ConfigParser  # ← config manuel


@dataclass
class DatabaseSettings:
    """Database configuration settings."""
    path: Path
    timeout: float = 10.0
    journal_mode: str = "WAL"
    foreign_keys: bool = True


@dataclass
class LoggingSettings:
    """Logging configuration settings."""
    level: str = "INFO"
    app_log_path: Path = field(default_factory=lambda: Path("var/logs/omega-fire.log"))
    audit_log_path: Path = field(default_factory=lambda: Path("var/logs/audit.log"))
    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class BackendSettings:
    """Backend configuration settings."""
    default_backend: str = "nftables"
    nftables_table: str = "filter"
    nftables_family: str = "inet"
    nftables_blacklist_set: str = "blacklist"
    iptables_chain: str = "INPUT"
    command_timeout: float = 10.0


@dataclass
class ExportSettings:
    """Export configuration settings."""
    exports_dir: Path = field(default_factory=lambda: Path("var/exports"))
    default_format: str = "json"
    pretty_json: bool = True
    json_indent: int = 2


@dataclass
class BackupSettings:
    """Backup configuration settings."""
    backups_dir: Path = field(default_factory=lambda: Path("var/backups"))
    max_backups: int = 10
    compress: bool = True

@dataclass
class UserResourcesSettings:
    """User-defined resources that extend automatic detection.
    
    Allows users to declare custom resources that the scanner cannot detect:
    - Extra log paths (custom web servers, applications)
    - Custom web server process names
    - Extra monitoring ports
    - Custom backend declarations
    """
    extra_log_paths: list[str] = field(default_factory=list)
    custom_web_servers: list[str] = field(default_factory=list)
    extra_monitoring_ports: list[int] = field(default_factory=list)
    custom_backends: list[str] = field(default_factory=list)
    config_file_path: Optional[Path] = None
    
    def is_empty(self) -> bool:
        """Check if no user resources are declared."""
        return (
            not self.extra_log_paths
            and not self.custom_web_servers
            and not self.extra_monitoring_ports
            and not self.custom_backends
        )

@dataclass
class UserResourcesSettings:
    """User-defined resources that extend automatic detection.
    
    Allows users to declare custom resources that the scanner cannot detect:
    - Extra log paths (custom web servers, applications)
    - Custom web server process names
    - Extra monitoring ports
    - Custom backend declarations
    """
    extra_log_paths: list[str] = field(default_factory=list)
    custom_web_servers: list[str] = field(default_factory=list)
    extra_monitoring_ports: list[int] = field(default_factory=list)
    custom_backends: list[str] = field(default_factory=list)
    config_file_path: Optional[Path] = None
    
    def is_empty(self) -> bool:
        """Check if no user resources are declared."""
        return (
            not self.extra_log_paths
            and not self.custom_web_servers
            and not self.extra_monitoring_ports
            and not self.custom_backends
        )

@dataclass
class AppSettings:
    """Main application settings.
    
    Aggregates all sub-settings into a single configuration object.
    """
    app_name: str = "omega-fire"
    version: str = "1.0.0"
    debug: bool = False
    paths: AppPaths = field(default_factory=AppPaths)
    database: DatabaseSettings = field(default_factory=lambda: DatabaseSettings(Path("var/db/omega.db")))
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    backend: BackendSettings = field(default_factory=BackendSettings)
    export: ExportSettings = field(default_factory=ExportSettings)
    backup: BackupSettings = field(default_factory=BackupSettings)
    user_resources: UserResourcesSettings = field(default_factory=UserResourcesSettings)  # ← config utilisateur manuel

def load_settings(
    env_file: Optional[Path] = None,
    base_dir: Optional[Path] = None,
) -> AppSettings:
    """Load application settings from environment and paths.
    
    Args:
        env_file: Optional path to .env file
        base_dir: Optional base directory (default: current working directory)
    
    Returns:
        AppSettings instance
    """
    # Load environment variables
    env = EnvLoader(env_file)
    env.load()
    
    # Initialize paths
    paths = AppPaths(base_dir)
    paths.ensure_dirs()
    
    # Load user resources from config file (NEW)
    user_resources = _load_user_resources(env, paths)
    
    # Build settings from environment
    settings = AppSettings(
        app_name=env.get("APP_NAME", "omega-fire"),
        version=env.get("APP_VERSION", "1.0.0"),
        debug=env.get_bool("DEBUG", False),
        paths=paths,
        database=DatabaseSettings(
            path=paths.db_path,
            timeout=env.get_float("DB_TIMEOUT", 10.0),
            journal_mode=env.get("DB_JOURNAL_MODE", "WAL"),
            foreign_keys=env.get_bool("DB_FOREIGN_KEYS", True),
        ),
        logging=LoggingSettings(
            level=env.get("LOG_LEVEL", "INFO"),
            app_log_path=paths.app_log_path,
            audit_log_path=paths.audit_log_path,
            max_bytes=env.get_int("LOG_MAX_BYTES", 10 * 1024 * 1024),
            backup_count=env.get_int("LOG_BACKUP_COUNT", 5),
        ),
        backend=BackendSettings(
            default_backend=env.get("DEFAULT_BACKEND", "nftables"),
            nftables_table=env.get("NFTABLES_TABLE", "filter"),
            nftables_family=env.get("NFTABLES_FAMILY", "inet"),
            nftables_blacklist_set=env.get("NFTABLES_BLACKLIST_SET", "blacklist"),
            iptables_chain=env.get("IPTABLES_CHAIN", "INPUT"),
            command_timeout=env.get_float("COMMAND_TIMEOUT", 10.0),
        ),
        export=ExportSettings(
            exports_dir=paths.exports_dir,
            default_format=env.get("DEFAULT_EXPORT_FORMAT", "json"),
            pretty_json=env.get_bool("PRETTY_JSON", True),
            json_indent=env.get_int("JSON_INDENT", 2),
        ),
        backup=BackupSettings(
            backups_dir=paths.backups_dir,
            max_backups=env.get_int("MAX_BACKUPS", 10),
            compress=env.get_bool("COMPRESS_BACKUPS", True),
        ),
        user_resources=user_resources,  # ← NOUVEAU
    )
    
    return settings

def _load_user_resources(env: EnvLoader, paths: AppPaths) -> UserResourcesSettings:
    """Load user-defined resources from environment or config file.
    
    Supports two sources:
    1. Environment variables (EXTRA_LOG_PATHS, CUSTOM_WEB_SERVERS, etc.)
    2. Config file (omega-fire.conf) if present
    
    Args:
        env: Environment loader instance.
        paths: Application paths instance.
    
    Returns:
        UserResourcesSettings with parsed values.
    """
    # Try to load from config file first
    config_file = _find_user_config_file(paths)
    
    if config_file and config_file.exists():
        try:
            return _parse_user_config_file(config_file)
        except Exception:
            pass  # Fall back to environment variables
    
    # Load from environment variables
    extra_log_paths = _parse_list(env.get("EXTRA_LOG_PATHS", ""))
    custom_web_servers = _parse_list(env.get("CUSTOM_WEB_SERVERS", ""))
    extra_monitoring_ports = _parse_int_list(env.get("EXTRA_MONITORING_PORTS", ""))
    custom_backends = _parse_list(env.get("CUSTOM_BACKENDS", ""))
    
    return UserResourcesSettings(
        extra_log_paths=extra_log_paths,
        custom_web_servers=custom_web_servers,
        extra_monitoring_ports=extra_monitoring_ports,
        custom_backends=custom_backends,
        config_file_path=config_file,
    )


def _find_user_config_file(paths: AppPaths) -> Optional[Path]:
    """Find the user config file in standard locations.
    
    Search order:
    1. /etc/omega-fire/omega-fire.conf
    2. ~/.omega-fire/omega-fire.conf
    3. ~/.omega-fire.conf
    4. ./omega-fire.conf (current directory)
    
    Args:
        paths: Application paths instance.
    
    Returns:
        Path to config file if found, None otherwise.
    """
    search_paths = [
        Path("/etc/omega-fire/omega-fire.conf"),
        Path.home() / ".omega-fire" / "omega-fire.conf",
        Path.home() / ".omega-fire.conf",
        paths.config_dir / "omega-fire.conf",
        paths.base_dir / "omega-fire.conf",
    ]
    
    for path in search_paths:
        if path.exists():
            return path
    
    return None


def _parse_user_config_file(config_file: Path) -> UserResourcesSettings:
    """Parse a user config file (INI format).
    
    Expected format:
    [logs]
    extra_paths = /var/log/myapp/access.log, /opt/custom/error.log
    
    [web_servers]
    custom = my-server, another-server
    
    [monitoring]
    extra_ports = 8080, 9090, 3000
    
    [backends]
    custom = my-custom-backend
    
    Args:
        config_file: Path to the config file.
    
    Returns:
        UserResourcesSettings with parsed values.
    """
    from configparser import ConfigParser
    
    parser = ConfigParser()
    parser.read(config_file, encoding='utf-8')
    
    extra_log_paths = []
    if parser.has_section("logs"):
        extra_log_paths = _parse_list(parser.get("logs", "extra_paths", fallback=""))
    
    custom_web_servers = []
    if parser.has_section("web_servers"):
        custom_web_servers = _parse_list(parser.get("web_servers", "custom", fallback=""))
    
    extra_monitoring_ports = []
    if parser.has_section("monitoring"):
        extra_monitoring_ports = _parse_int_list(parser.get("monitoring", "extra_ports", fallback=""))
    
    custom_backends = []
    if parser.has_section("backends"):
        custom_backends = _parse_list(parser.get("backends", "custom", fallback=""))
    
    return UserResourcesSettings(
        extra_log_paths=extra_log_paths,
        custom_web_servers=custom_web_servers,
        extra_monitoring_ports=extra_monitoring_ports,
        custom_backends=custom_backends,
        config_file_path=config_file,
    )


def _parse_list(value: str) -> list[str]:
    """Parse a comma-separated list of strings.
    
    Args:
        value: Comma-separated string.
    
    Returns:
        List of stripped, non-empty strings.
    """
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_int_list(value: str) -> list[int]:
    """Parse a comma-separated list of integers.
    
    Args:
        value: Comma-separated string of integers.
    
    Returns:
        List of valid integers (invalid ones are skipped).
    """
    if not value:
        return []
    result = []
    for item in value.split(","):
        item = item.strip()
        if item:
            try:
                result.append(int(item))
            except ValueError:
                pass  # Skip invalid integers
    return result



def get_default_settings() -> AppSettings:
    """Get default settings without loading from environment.
    
    Returns:
        AppSettings with default values
    """
    return AppSettings()


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les settings de l'application sous forme de dataclasses
# - Charge les valeurs depuis les variables d'environnement ET un fichier de config
# - Centralise toute la configuration en un seul objet AppSettings
# - Supporte la déclaration de ressources utilisateur (logs, serveurs, ports)
#
# Pourquoi dans infrastructure/config/ (charte) :
# - C'est de la configuration technique (fichiers, chemins, timeouts)
# - Le domaine ne doit pas connaître les settings
# - L'application/ reçoit les settings via injection
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# ❌ Pas d'écriture de fichiers de configuration
#
# Points clés :
# - AppSettings : dataclass principale qui agrège tous les sous-settings
# - Sous-settings : DatabaseSettings, LoggingSettings, BackendSettings,
#   ExportSettings, BackupSettings, UserResourcesSettings
# - UserResourcesSettings : permet de déclarer des ressources personnalisées
#   (logs, serveurs web, ports de monitoring, backends)
# - load_settings() : charge depuis .env + paths + fichier config, crée les répertoires
# - _load_user_resources() : charge les ressources utilisateur depuis config ou env
# - _find_user_config_file() : cherche omega-fire.conf dans les emplacements standard
# - _parse_user_config_file() : parse le fichier INI
# - _parse_list() et _parse_int_list() : helpers de parsing
#
# Variables d'environnement supportées :
# - APP_NAME, APP_VERSION, DEBUG
# - DB_TIMEOUT, DB_JOURNAL_MODE, DB_FOREIGN_KEYS
# - LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT
# - DEFAULT_BACKEND, NFTABLES_TABLE, NFTABLES_FAMILY, etc.
# - DEFAULT_EXPORT_FORMAT, PRETTY_JSON, JSON_INDENT
# - MAX_BACKUPS, COMPRESS_BACKUPS
# - EXTRA_LOG_PATHS, CUSTOM_WEB_SERVERS, EXTRA_MONITORING_PORTS, CUSTOM_BACKENDS
#
# Fichier de configuration utilisateur (omega-fire.conf) :
# [logs]
# extra_paths = /var/log/myapp/access.log, /opt/custom/error.log
#
# [web_servers]
# custom = my-server, another-server
#
# [monitoring]
# extra_ports = 8080, 9090, 3000
#
# [backends]
# custom = my-custom-backend
#
# Emplacements recherchés pour omega-fire.conf (dans cet ordre, le
# premier trouvé gagne) :
# 1. /etc/omega-fire/omega-fire.conf
# 2. ~/.omega-fire/omega-fire.conf
# 3. ~/.omega-fire.conf
# 4. <projet>/config/omega-fire.conf (emplacement recommandé — garde
#    toute la configuration à l'intérieur du projet, cohérent avec
#    var/ pour les données runtime, sans jamais toucher au système ou
#    au $HOME de l'utilisateur)
# 5. <projet>/omega-fire.conf (racine, rétrocompatibilité)
#
# Comment il sera utilisé (aperçu) :
# - app/bootstrap.py chargera les settings au démarrage
# - Tous les composants recevront AppSettings via injection
# - Le scanner utilisera user_resources pour détecter les ressources personnalisées
# - Les tests utiliseront get_default_settings() ou mockeront les valeurs
#---------------------------------------------------------------------->
