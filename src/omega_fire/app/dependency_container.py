# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Dependency injection container for Omega-Fire.

Assembles and wires all components at application startup.
This is the ONLY place where infrastructure/ implementations are connected
to application/ via ports/ contracts.

Conforms to Omega-Fire architecture charter:
- Pure wiring logic, NO business rules
- NO logic about WHEN to call what
- NO direct system calls (only via adapters)
- Lazy initialization to avoid loading everything at startup
- Single source of truth for dependency graph
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from omega_fire.core.capability_registry import CapabilityRegistry
    from omega_fire.infrastructure.probe.scanner import CapabilityScanner
    from omega_fire.plugins.manager import PluginManager
    from omega_fire.plugins.loader import PluginLoader


# ----------------------------------------------------------------------
# Default paths
# ----------------------------------------------------------------------
DEFAULT_DB_PATH = Path("var/db/omega.db")
DEFAULT_LOG_DIR = Path("var/logs")
DEFAULT_EXPORT_DIR = Path("var/exports")
DEFAULT_PLUGIN_DIR = Path("plugins/external")


# ----------------------------------------------------------------------
# Dependency container
# ----------------------------------------------------------------------
class DependencyContainer:
    """Central dependency injection container.
    
    Provides lazy-initialized access to all application services.
    Each service is created on first access and cached for subsequent calls.
    """
    
    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize the container."""
        self.config = config or {}
        self._cache: dict[str, Any] = {}
    
    # ------------------------------------------------------------------
    # Core services
    # ------------------------------------------------------------------
    
    @property
    def capability_registry(self) -> Any:
        return self._get_or_create("capability_registry", self._create_capability_registry)
    
    def _create_capability_registry(self) -> Any:
        from omega_fire.core.capability_registry import CapabilityRegistry
        return CapabilityRegistry()
    
    @property
    def scanner(self) -> Any:
        return self._get_or_create("scanner", self._create_scanner)
    
    def _create_scanner(self) -> Any:
        from omega_fire.infrastructure.probe.scanner import SystemScanner
        from omega_fire.infrastructure.config.settings import load_settings
        
        return SystemScanner(
            registry=self.capability_registry,
            settings=load_settings(),
        )
    
    # ------------------------------------------------------------------
    # Infrastructure - Service Manager
    # ------------------------------------------------------------------
    
    @property
    def service_manager(self) -> Any:
        return self._get_or_create("service_manager", self._create_service_manager)
    
    def _create_service_manager(self) -> Any:
        from omega_fire.infrastructure.backends.service_manager.detector import detect_service_manager
        return detect_service_manager()
    
    # ------------------------------------------------------------------
    # Infrastructure - Backend adapters (Lazy imports)
    # ------------------------------------------------------------------
    
    @property
    def nftables_adapter(self) -> Any:
        return self._get_or_create("nftables_adapter", self._create_nftables_adapter)
    
    def _create_nftables_adapter(self) -> Any:
        from omega_fire.infrastructure.backends.nftables.adapter import NftablesAdapter
        return NftablesAdapter()
    
    @property
    def iptables_adapter(self) -> Any:
        return self._get_or_create("iptables_adapter", self._create_iptables_adapter)

    def _create_iptables_adapter(self) -> Any:
        from omega_fire.infrastructure.backends.iptables.adapter import IptablesAdapter
        return IptablesAdapter()

    @property
    def ip6tables_adapter(self) -> Any:
        return self._get_or_create("ip6tables_adapter", self._create_ip6tables_adapter)

    def _create_ip6tables_adapter(self) -> Any:
        from omega_fire.infrastructure.backends.ip6tables.adapter import Ip6tablesAdapter
        return Ip6tablesAdapter()

    @property
    def fail2ban_adapter(self) -> Any:
        return self._get_or_create("fail2ban_adapter", self._create_fail2ban_adapter)
    
    def _create_fail2ban_adapter(self) -> Any:
        from omega_fire.infrastructure.backends.fail2ban.adapter import Fail2banAdapter
        return Fail2banAdapter(service_manager=self.service_manager)
    
    @property
    def conntrack_adapter(self) -> Any:
        return self._get_or_create("conntrack_adapter", self._create_conntrack_adapter)
    
    def _create_conntrack_adapter(self) -> Any:
        from omega_fire.infrastructure.backends.conntrack.adapter import ConntrackAdapter
        return ConntrackAdapter()
    
    # ------------------------------------------------------------------
    # Infrastructure - Storage
    # ------------------------------------------------------------------
    
    @property
    def db_connection(self) -> Any:
        return self._get_or_create("db_connection", self._create_db_connection)
    
    def _create_db_connection(self) -> Any:
        from omega_fire.infrastructure.storage.sqlite.connection import DatabaseConnection
        from omega_fire.infrastructure.storage.sqlite.schema import create_schema
        from omega_fire.infrastructure.storage.sqlite.migrations import MigrationManager
        from omega_fire.infrastructure.config.paths import MIGRATIONS_DIR

        db_path = Path(self.config.get("db_path", DEFAULT_DB_PATH))
        connection = DatabaseConnection(db_path)
        connection.connect()

        create_schema(connection)

        migration_manager = MigrationManager(connection, MIGRATIONS_DIR)
        migration_manager.ensure_schema_version_table()
        migration_manager.apply_all_pending()

        return connection
    
    @property
    def ban_repository(self) -> Any:
        return self._get_or_create("ban_repository", self._create_ban_repository)
    
    def _create_ban_repository(self) -> Any:
        from omega_fire.infrastructure.storage.sqlite.repositories import BanRepository
        return BanRepository(self.db_connection)
    
    @property
    def rule_repository(self) -> Any:
        return self._get_or_create("rule_repository", self._create_rule_repository)
    
    def _create_rule_repository(self) -> Any:
        from omega_fire.infrastructure.storage.sqlite.repositories import RuleRepository
        return RuleRepository(self.db_connection)
    
    @property
    def audit_repository(self) -> Any:
        return self._get_or_create("audit_repository", self._create_audit_repository)
    
    def _create_audit_repository(self) -> Any:
        from omega_fire.infrastructure.storage.sqlite.repositories import AuditRepository
        return AuditRepository(self.db_connection)
    @property
    def archive_store(self) -> Any:
        return self._get_or_create("archive_store", self._create_archive_store)
    
    def _create_archive_store(self) -> Any:
        from omega_fire.infrastructure.storage.files.archive_store import ArchiveStore
        from omega_fire.infrastructure.config.paths import BACKUPS_DIR
        backup_dir = Path(self.config.get("backup_dir", BACKUPS_DIR))
        return ArchiveStore(base_dir=backup_dir)
    
    @property
    def persistence_adapter(self) -> Any:
        return self._get_or_create("persistence_adapter", self._create_persistence_adapter)
    
    def _create_persistence_adapter(self) -> Any:
        from omega_fire.infrastructure.storage.files.persistence_adapter import FileBackupAdapter
        return FileBackupAdapter(archive_store=self.archive_store)

    
    # ------------------------------------------------------------------
    # Infrastructure - Exporters
    # ------------------------------------------------------------------
    
    @property
    def json_exporter(self) -> Any:
        return self._get_or_create("json_exporter", self._create_json_exporter)
    
    def _create_json_exporter(self) -> Any:
        from omega_fire.infrastructure.exporters.json_exporter import JsonExporter
        return JsonExporter()
    
    @property
    def txt_exporter(self) -> Any:
        return self._get_or_create("txt_exporter", self._create_txt_exporter)
    
    def _create_txt_exporter(self) -> Any:
        from omega_fire.infrastructure.exporters.txt_exporter import TxtExporter
        return TxtExporter()
    
    @property
    def html_exporter(self) -> Any:
        return self._get_or_create("html_exporter", self._create_html_exporter)
    
    def _create_html_exporter(self) -> Any:
        from omega_fire.infrastructure.exporters.html_exporter import HtmlExporter
        from omega_fire.infrastructure.config.paths import TEMPLATES_DIR
        return HtmlExporter(templates_dir=TEMPLATES_DIR)
    
    # ------------------------------------------------------------------
    # Infrastructure - Logging
    # ------------------------------------------------------------------
    
    @property
    def app_logger(self) -> Any:
        return self._get_or_create("app_logger", self._create_app_logger)
    
    def _create_app_logger(self) -> Any:
        from omega_fire.infrastructure.logging.app_logger import AppLogger
        log_dir = Path(self.config.get("log_dir", DEFAULT_LOG_DIR))
        return AppLogger(log_dir=log_dir)
    
    @property
    def audit_logger(self) -> Any:
        return self._get_or_create("audit_logger", self._create_audit_logger)
    
    def _create_audit_logger(self) -> Any:
        from omega_fire.infrastructure.logging.audit_logger import AuditLogger
        log_dir = Path(self.config.get("log_dir", DEFAULT_LOG_DIR))
        try:
            return AuditLogger(log_dir=log_dir)
        except TypeError:
            # Fallback si AuditLogger n'accepte pas log_dir ou prend un autre argument
            return AuditLogger()
    
    # ------------------------------------------------------------------
    # Infrastructure - TUI (theme/terminal, migration Textual)
    # ------------------------------------------------------------------

    @property
    def settings_store(self) -> Any:
        return self._get_or_create("settings_store", self._create_settings_store)

    def _create_settings_store(self) -> Any:
        from omega_fire.infrastructure.storage.files.json_settings_store import JsonSettingsStore
        from omega_fire.infrastructure.config.paths import RUNTIME_DIR
        return JsonSettingsStore(RUNTIME_DIR / "settings.json")

    @property
    def terminal_detector(self) -> Any:
        return self._get_or_create("terminal_detector", self._create_terminal_detector)

    def _create_terminal_detector(self) -> Any:
        from omega_lib.infrastructure.terminal.detector import SystemTerminalDetector
        return SystemTerminalDetector()

    @property
    def default_screenshots_dir(self) -> Path:
        """Sans ce chemin explicite, `App.deliver_screenshot()` ecrirait
        par defaut dans le dossier Telechargements de l'utilisateur,
        jamais dans var/ — meme piege deja documente et corrige cote
        omega-check/omega-stress."""
        from omega_fire.infrastructure.config.paths import VAR_DIR
        return Path(self.config.get("screenshots_dir", VAR_DIR / "screenshots"))

    # ------------------------------------------------------------------
    # Plugins
    # ------------------------------------------------------------------
    
    @property
    def plugin_loader(self) -> Any:
        return self._get_or_create("plugin_loader", self._create_plugin_loader)
    
    def _create_plugin_loader(self) -> Any:
        from omega_fire.plugins.loader import PluginLoader
        plugin_dir = Path(self.config.get("plugin_dir", DEFAULT_PLUGIN_DIR))
        return PluginLoader(external_dir=plugin_dir)
    
    @property
    def plugin_manager(self) -> Any:
        return self._get_or_create("plugin_manager", self._create_plugin_manager)
    
    def _create_plugin_manager(self) -> Any:
        from omega_fire.plugins.manager import PluginManager
        return PluginManager(loader=self.plugin_loader)
    
    # ------------------------------------------------------------------
    # Port accessors (for application/ use cases)
    # ------------------------------------------------------------------
    
    def get_firewall_port(self, backend: str = "nftables") -> Any:
        if backend == "nftables":
            return self.nftables_adapter
        elif backend == "iptables":
            return self.iptables_adapter
        elif backend == "ip6tables":
            return self.ip6tables_adapter
        else:
            raise ValueError(f"Unknown firewall backend: {backend}")
    
    def get_blacklist_port(self) -> Any:
        return self.nftables_adapter  # Simplified for now
    
    def get_fail2ban_port(self) -> Any:
        return self.fail2ban_adapter
    
    def get_monitoring_port(self) -> Any:
        return self.conntrack_adapter
    
    def get_exporter_port(self, format: str = "json") -> Any:
        if format == "json":
            return self.json_exporter
        elif format == "txt":
            return self.txt_exporter
        elif format == "html":
            return self.html_exporter
        else:
            raise ValueError(f"Unknown export format: {format}")
    
    def get_audit_port(self) -> Any:
        return self.audit_logger
    
    def get_persistence_port(self) -> Any:
        return self.persistence_adapter

    def get_system_port(self) -> Any:
        return self.service_manager
    
    # ------------------------------------------------------------------
    # Lifecycle methods
    # ------------------------------------------------------------------
    
    def initialize(self) -> None:
        """Initialize critical services (registry, scanner)."""
        self.scanner.scan()
    
    def shutdown(self) -> None:
        """Shutdown and cleanup resources."""
        if "db_connection" in self._cache:
            try:
                self.db_connection.close()
            except Exception:
                pass
        
        if "app_logger" in self._cache:
            try:
                self.app_logger.flush()
            except Exception:
                pass
        
        if "audit_logger" in self._cache:
            try:
                self.audit_logger.flush()
            except Exception:
                pass
        
        self._cache.clear()
    
    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    
    def _get_or_create(self, key: str, factory) -> Any:
        if key not in self._cache:
            self._cache[key] = factory()
        return self._cache[key]
    
    def reset(self) -> None:
        """Reset the container (clear cache)."""
        self.shutdown()
        self._cache.clear()

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Conteneur d'injection de dépendances (DI container) pour Omega-Fire.
# - SEUL endroit où infrastructure/ est connecté à application/ via ports/.
# - Fournit un accès lazy-initialized à tous les services de l'application.
#
# Pourquoi dans app/ (charte) :
# - C'est du câblage pur, aucune logique métier.
# - Aucun appel système direct (sauf via les adapters).
# - Aucune décision sur QUAND appeler quoi.
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (c'est le rôle de domain/).
# ❌ Pas d'orchestration de cas d'usage (c'est le rôle de application/).
# ❌ Pas d'appels système directs (c'est le rôle de infrastructure/).
# ❌ Pas de rendu utilisateur (c'est le rôle de interfaces/).
#
# Points clés :
# - Tous les imports concrets sont DÉFÉRÉS à l'intérieur des méthodes de factory.
#   Cela évite les erreurs d'import si un module d'infrastructure n'existe pas encore.
# - _get_or_create() : helper pour cache + factory pattern.
# - initialize() : lance le scanner au démarrage pour peupler le registre.
# - shutdown() : ferme les connexions et flush les logs à la sortie.
# - reset() : vide le cache (utile pour tests ou rechargement config).
# - get_*_port() : accesseurs typés pour les ports (firewall, blacklist, etc.).
# - archive_store / persistence_adapter : gèrent les backups fichiers
#   (menus 5.4/5.5/5.6) via ArchiveStore + FileBackupAdapter. Les
#   snapshots d'état complet (7.x/3.4) ne sont pas encore câblés ici.
#---------------------------------------------------------------------->        
