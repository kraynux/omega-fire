# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrat pour le système de plugins (chargement, cycle de vie)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class PluginStatus(str, Enum):
    """Statut d'un plugin."""
    LOADED = "loaded"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class PluginInfo:
    """Informations sur un plugin.

    Attributs:
        name: nom du plugin.
        version: version du plugin.
        author: auteur du plugin.
        description: description du plugin.
        status: statut actuel (loaded, active, disabled, error).
        capabilities: liste des capacités fournies par le plugin.
        error_message: message d'erreur si status=ERROR.
    """
    name: str
    version: str
    author: str
    description: str
    status: PluginStatus
    capabilities: list[str]
    error_message: str | None = None


class PluginPort(Protocol):
    """Contrat pour le système de plugins.

    Définit les opérations attendues pour charger, activer, désactiver
    et gérer le cycle de vie des plugins.
    """

    @abstractmethod
    def discover_plugins(self, plugin_dir: str | None = None) -> list[PluginInfo]:
        """Découvre les plugins disponibles.

        Args:
            plugin_dir: répertoire des plugins (None = répertoire par défaut).

        Returns:
            Liste de PluginInfo des plugins trouvés.
        """
        ...

    @abstractmethod
    def load_plugin(self, plugin_name: str) -> PluginInfo:
        """Charge un plugin.

        Args:
            plugin_name: nom du plugin à charger.

        Returns:
            PluginInfo du plugin chargé.

        Raises:
            PluginNotFoundError: si le plugin n'existe pas.
            PluginLoadError: si le chargement échoue.
        """
        ...

    @abstractmethod
    def unload_plugin(self, plugin_name: str) -> None:
        """Décharge un plugin.

        Args:
            plugin_name: nom du plugin à décharger.

        Raises:
            PluginNotFoundError: si le plugin n'est pas chargé.
        """
        ...

    @abstractmethod
    def activate_plugin(self, plugin_name: str) -> None:
        """Active un plugin chargé.

        Args:
            plugin_name: nom du plugin à activer.

        Raises:
            PluginNotFoundError: si le plugin n'est pas chargé.
        """
        ...

    @abstractmethod
    def deactivate_plugin(self, plugin_name: str) -> None:
        """Désactive un plugin actif.

        Args:
            plugin_name: nom du plugin à désactiver.
        """
        ...

    @abstractmethod
    def list_plugins(self, *, status: PluginStatus | None = None) -> list[PluginInfo]:
        """Liste les plugins.

        Args:
            status: filtre par statut (None = tous).

        Returns:
            Liste de PluginInfo.
        """
        ...

    @abstractmethod
    def get_plugin(self, plugin_name: str) -> PluginInfo:
        """Récupère les informations d'un plugin.

        Args:
            plugin_name: nom du plugin.

        Returns:
            PluginInfo du plugin.

        Raises:
            PluginNotFoundError: si le plugin n'existe pas.
        """
        ...

    @abstractmethod
    def get_plugin_instance(self, plugin_name: str) -> Any:
        """Récupère l'instance d'un plugin actif.

        Args:
            plugin_name: nom du plugin.

        Returns:
            Instance du plugin.

        Raises:
            PluginNotFoundError: si le plugin n'est pas chargé.
            PluginNotActiveError: si le plugin n'est pas actif.
        """
        ...

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit le contrat (Protocol) pour le système de plugins.
# - Fournit PluginInfo (dataclass frozen) et PluginStatus (enum).
# - Spécifie les opérations : discover_plugins(), load_plugin(), unload_plugin(),
#   activate_plugin(), deactivate_plugin(), list_plugins(), get_plugin(),
#   get_plugin_instance().
#
# Pourquoi dans ports/ (charte) :
# - C'est un contrat attendu par le cœur applicatif (plugins/manager.py)
# - Pas d'implémentation concrète (c'est le rôle de plugins/loader.py)
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'implémentation concrète (importlib, chargement dynamique)
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de logique de validation de plugin
#
# Points clés :
# - PluginStatus : enum (loaded, active, disabled, error)
# - PluginInfo : dataclass frozen avec name, version, author, description, status,
#   capabilities, error_message
# - PluginPort : Protocol définissant toutes les opérations sur plugins
# - Toutes les méthodes sont abstraites (via Protocol)
#
# Comment il sera utilisé (aperçu) :
# - plugins/manager.py implémentera PluginPort
# - plugins/loader.py utilisera PluginPort pour charger les plugins
# - app/bootstrap.py appellera plugin_port.discover_plugins() au démarrage
# - interfaces/cli/actions.py affichera la liste des plugins actifs
#---------------------------------------------------------------------->        
