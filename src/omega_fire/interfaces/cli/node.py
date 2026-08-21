# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Menu node definition.

Defines the structure of a menu node in the CLI tree. Each node represents
a menu entry with its label, action, prerequisites (capabilities), and children.

This module performs no I/O — it only defines data structures for the menu tree.
"""
from dataclasses import dataclass, field
from typing import Optional, Callable, Any


@dataclass
class MenuNode:
    """A single node in the menu tree.
    
    Represents a menu entry with its label, action callback, prerequisites,
    and child nodes. The tree_builder uses these nodes to construct the
    conditional menu based on capability availability.
    """
    id: str
    label: str
    action: Optional[Callable[[], Any]] = None
    requires: list[str] = field(default_factory=list)
    requires_any: list[str] = field(default_factory=list)
    children: list['MenuNode'] = field(default_factory=list)
    parent: Optional['MenuNode'] = None
    enabled: bool = True
    description: str = ""
    shortcut: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def add_child(self, child: 'MenuNode') -> 'MenuNode':
        """Add a child node."""
        child.parent = self
        self.children.append(child)
        return child
    
    def is_leaf(self) -> bool:
        """Check if this node is a leaf (no children)."""
        return len(self.children) == 0
    
    def is_actionable(self) -> bool:
        """Check if this node has an action."""
        return self.action is not None
    
    def get_path(self) -> str:
        """Get the full path from root to this node."""
        if self.parent is None:
            return self.id
        parent_path = self.parent.get_path()
        return f"{parent_path}.{self.id}"
    
    def find_child(self, child_id: str) -> Optional['MenuNode']:
        """Find a child node by ID."""
        for child in self.children:
            if child.id == child_id:
                return child
        return None
    
    def find_by_path(self, path: str) -> Optional['MenuNode']:
        """Find a node by its full path."""
        parts = path.split(".")
        current = self
        for part in parts[1:]:
            child = current.find_child(part)
            if child is None:
                return None
            current = child
        return current
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the node to a dictionary."""
        return {
            "id": self.id,
            "label": self.label,
            "requires": self.requires,
            "requires_any": self.requires_any,
            "enabled": self.enabled,
            "description": self.description,
            "shortcut": self.shortcut,
            "is_leaf": self.is_leaf(),
            "is_actionable": self.is_actionable(),
            "children_count": len(self.children),
            "metadata": self.metadata,
        }
    
    def __str__(self) -> str:
        """Return string representation."""
        return f"MenuNode(id='{self.id}', label='{self.label}')"


def create_node(
    node_id: str,
    label: str,
    action: Optional[Callable[[], Any]] = None,
    requires: Optional[list[str]] = None,
    requires_any: Optional[list[str]] = None,
    description: str = "",
    shortcut: Optional[str] = None,
) -> MenuNode:
    """Factory function to create a MenuNode.
    
    Args:
        node_id: Node identifier
        label: Display label
        action: Optional action callback
        requires: Optional list of required capabilities (ALL must be available)
        requires_any: Optional list of capabilities where AT LEAST ONE must be available
        description: Optional description
        shortcut: Optional keyboard shortcut
    
    Returns:
        MenuNode instance
    """
    return MenuNode(
        id=node_id,
        label=label,
        action=action,
        requires=requires or [],
        requires_any=requires_any or [],
        description=description,
        shortcut=shortcut,
    )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit la structure d'un nœud de menu dans l'arbre CLI
# - Chaque nœud a un label, une action, des prérequis (capacités) et des enfants
# - Le tree_builder utilise ces nœuds pour construire le menu conditionnel
# Pourquoi dans interfaces/cli/ (charte) :
# - C'est une structure de données pour l'interface utilisateur
# - Le domaine ne doit pas connaître les menus
# - L'application/ ne doit pas connaître la structure des menus
# - Seul interfaces/ manipule ces nœuds
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas d'appels système (juste des définitions de structures)
# ❌ Pas de dépendance vers domain/, application/ ou infrastructure/
# ❌ Pas de rendu Rich (c'est le rôle des renderers/)
# Points clés :
# - MenuNode : dataclass principale avec id, label, action, requires, requires_any, children
# - requires : liste de capacités requises (TOUTES doivent être disponibles - ET logique)
# - requires_any : liste de capacités dont AU MOINS UNE doit être disponible (OU logique)
# - Méthodes de navigation : add_child(), find_child(), find_by_path(), get_path()
# - Méthodes de vérification : is_leaf(), is_actionable()
# - Sérialisation : to_dict() pour export/debug
# - Factory function : create_node() pour création simplifiée
# Comment il sera utilisé (aperçu) :
# - interfaces/cli/tree_builder.py construira l'arbre à partir de MenuNode
# - interfaces/cli/menu_builder.py définira les nœuds du menu principal
# - interfaces/cli/actions.py définira les callbacks des actions
#---------------------------------------------------------------------->
