# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Menu tree builder.

Builds the conditional menu tree based on the capability registry.
Checks each node's prerequisites (requires and requires_any) against the registry and
disables nodes whose capabilities are not available.

This module performs no I/O — it only builds the tree structure in memory.
"""
from typing import Optional
from omega_fire.core.capability_registry import CapabilityRegistry
from omega_fire.interfaces.cli.node import MenuNode
from omega_fire.interfaces.exceptions import MenuBuildError


class TreeBuilder:
    """Builds the conditional menu tree from capability registry.
    
    Traverses the menu tree, checks each node's prerequisites against
    the capability registry, and disables nodes whose capabilities
    are not available.
    """
    
    def __init__(self, registry: CapabilityRegistry):
        """Initialize the tree builder.
        
        Args:
            registry: The capability registry to query
        """
        self._registry = registry
    
    def build(self, root: MenuNode) -> MenuNode:
        """Build the menu tree by checking all prerequisites.
        
        Traverses the tree recursively, checking each node's requires
        and requires_any against the registry. Disables nodes whose capabilities
        are not available.
        
        Args:
            root: Root MenuNode of the tree
        
        Returns:
            The root node with updated enabled/disabled states
        
        Raises:
            MenuBuildError: If tree building fails
        """
        try:
            self._process_node(root)
            return root
        except Exception as e:
            raise MenuBuildError(reason=str(e)) from e
    
    def _process_node(self, node: MenuNode) -> None:
        """Process a single node and its children recursively.
        
        Args:
            node: MenuNode to process
        """
        # Check if this node's prerequisites are met
        if node.requires or node.requires_any:
            node.enabled = self._check_requirements(node.requires, node.requires_any)
        
        # Process children recursively
        for child in node.children:
            self._process_node(child)
        
        # If all children are disabled, disable this node too (if it's not actionable)
        if not node.is_actionable() and node.children:
            all_children_disabled = all(not child.enabled for child in node.children)
            if all_children_disabled:
                node.enabled = False
    
    def _check_requirements(self, requires: list[str], requires_any: list[str]) -> bool:
        """Check if requirements are met.
        
        Args:
            requires: List of required capability IDs (ALL must be available - AND logic)
            requires_any: List of capability IDs where AT LEAST ONE must be available (OR logic)
        
        Returns:
            True if all requirements are met
        """
        # Check requires (AND logic)
        if requires:
            all_required = all(
                self._registry.is_available(cap_id)
                for cap_id in requires
            )
            if not all_required:
                return False
        
        # Check requires_any (OR logic)
        if requires_any:
            any_available = any(
                self._registry.is_available(cap_id)
                for cap_id in requires_any
            )
            if not any_available:
                return False
        
        return True
    
    def get_enabled_nodes(self, root: MenuNode) -> list[MenuNode]:
        """Get all enabled nodes in the tree."""
        enabled = []
        self._collect_enabled(root, enabled)
        return enabled
    
    def _collect_enabled(self, node: MenuNode, result: list[MenuNode]) -> None:
        """Recursively collect enabled nodes."""
        if node.enabled:
            result.append(node)
        for child in node.children:
            self._collect_enabled(child, result)
    
    def get_disabled_nodes(self, root: MenuNode) -> list[MenuNode]:
        """Get all disabled nodes in the tree."""
        disabled = []
        self._collect_disabled(root, disabled)
        return disabled
    
    def _collect_disabled(self, node: MenuNode, result: list[MenuNode]) -> None:
        """Recursively collect disabled nodes."""
        if not node.enabled:
            result.append(node)
        for child in node.children:
            self._collect_disabled(child, result)
    
    def get_summary(self, root: MenuNode) -> dict:
        """Get a summary of the tree state."""
        enabled = self.get_enabled_nodes(root)
        disabled = self.get_disabled_nodes(root)
        
        return {
            "total_nodes": len(enabled) + len(disabled),
            "enabled_nodes": len(enabled),
            "disabled_nodes": len(disabled),
            "enabled_ratio": len(enabled) / (len(enabled) + len(disabled)) if (len(enabled) + len(disabled)) > 0 else 0,
        }
    
    def is_node_enabled(self, node: MenuNode) -> bool:
        """Check if a specific node is enabled."""
        return node.enabled


def build_menu_tree(root: MenuNode, registry: CapabilityRegistry) -> MenuNode:
    """Convenience function to build a menu tree."""
    builder = TreeBuilder(registry)
    return builder.build(root)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Construit l'arbre de menu conditionnel basé sur le registre de capacités
# - Vérifie les prérequis (requires ET requires_any) de chaque nœud contre le registre
# - Désactive les nœuds dont les capacités ne sont pas disponibles
# - C'est le mécanisme officiel de grisage des menus (clause omega-fire)
# Pourquoi dans interfaces/cli/ (charte) :
# - C'est de la logique d'interface (construction de menu)
# - Le domaine ne doit pas connaître les menus
# - L'application/ ne doit pas connaître la structure des menus
# - Seul interfaces/ manipule l'arbre de menu
# - Le grisage passe par le registre et l'arbre conditionnel (clause omega-fire)
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas d'appels système (juste de la logique de tree building)
# ❌ Pas de dépendance vers domain/, application/ ou infrastructure/
# ❌ Pas de rendu Rich (c'est le rôle des renderers/)
# Points clés :
# - TreeBuilder : classe principale qui prend un CapabilityRegistry
# - build() : méthode principale qui parcourt l'arbre et vérifie les prérequis
# - _process_node() : vérifie récursivement chaque nœud et ses enfants
# - _check_requirements() : vérifie les deux types de prérequis
#   - requires : ET logique (toutes les capacités doivent être disponibles)
#   - requires_any : OU logique (au moins une capacité doit être disponible)
# - get_enabled_nodes() / get_disabled_nodes() : retournent les nœuds activés/désactivés
# - get_summary() : retourne un résumé de l'état de l'arbre
# - Si tous les enfants d'un nœud sont désactivés, le nœud parent est aussi désactivé
#   (sauf s'il a une action propre)
# - Fonction de convenance : build_menu_tree()
# Comment il sera utilisé (aperçu) :
# - interfaces/cli/app.py appellera build() au démarrage pour construire le menu
# - interfaces/cli/menu_builder.py définira les nœuds avec leurs prérequis
# - interfaces/cli/renderers/ utilisera l'état enabled/disabled pour le rendu
#---------------------------------------------------------------------->
