# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Menu builder.

Constructs the main menu tree from MenuNode definitions.
Defines prerequisites (requires) for each node based on capability IDs.
Does NOT execute any action — only builds the tree structure.

IMPORTANT: Labels do NOT contain emojis. Icons are added by menu_icon()
in app.py based on terminal capability detection.

Conforms to Omega-Fire architecture charter:
- Pure tree structure, no business logic
- No direct backend calls
- Actions are wired via ActionRegistry (injected from app.py)
- Prerequisites (requires/requires_any) are evaluated by tree_builder.py
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from omega_fire.interfaces.cli.node import MenuNode, create_node


class MenuBuilder:
    """Builds the main menu tree structure."""
    
    def __init__(self) -> None:
        self._root: Optional[MenuNode] = None
    
    def build(self, action_registry: Optional[dict[str, Callable[[Any], None]]] = None) -> MenuNode:
        """Build the complete menu tree.
        
        Args:
            action_registry: Dictionary mapping menu IDs (e.g., "1.1") to action callables.
                           Each callable receives an ActionContext.
        
        Returns:
            Root MenuNode with all children and actions wired.
        """
        actions = action_registry or {}
        
        # Root node
        self._root = create_node(
            node_id="root",
            label="OMEGA-FIRE - MENU PRINCIPAL",
            description="Menu principal",
        )
        
        # ====================================================================
        # Section 1: État des capacités & diagnostics
        # ====================================================================
        section_1 = create_node(
            node_id="1",
            label="ÉTAT DES CAPACITÉS & DIAGNOSTICS",
            description="Vue globale des backends et services",
        )
        section_1.add_child(create_node("1.1", "Afficher le registre des capacités", action=actions.get("1.1"), description="Liste des composants et leur status"))
        section_1.add_child(create_node("1.2", "Détail d'une capacité", action=actions.get("1.2"), description="Sélection d'un composant"))
        section_1.add_child(create_node("1.3", "Re-scanner le système", action=actions.get("1.3"), description="Relance des probes système"))
        section_1.add_child(create_node("1.4", "Voir les diagnostics récents", action=actions.get("1.4"), description="Liste les erreurs et dégradations"))
        section_1.add_child(create_node("1.5", "Voir le journal applicatif", action=actions.get("1.5"), description="voir les logs d'evenements applicatif"))
        section_1.add_child(create_node("1.6", "Rechercher dans les diagnostics", action=actions.get("1.6"), description="Recherche par mot-clé"))
        section_1.add_child(create_node("1.7", "Exporter l'état et les diagnostics", action=actions.get("1.7"), description="Données JSON (brut), TXT (data) ou HTML (visuel)"))
        self._root.add_child(section_1)
        
        # ====================================================================
        # Section 2: Gestion des IPs (Blacklist unifiée)
        # ====================================================================
        section_2 = create_node(
            node_id="2",
            label="GESTION DES IPs (Blacklist unifiée NFt-IPt)",
            description="Actions sur les adresses IP",
        )
        section_2.add_child(create_node("2.1", "Bannir une IP", requires_any=["nftables", "iptables", "fail2ban_client"], action=actions.get("2.1"), description="Bannir une IP unique"))
        section_2.add_child(create_node("2.2", "Bannir une liste d'IPs", requires_any=["nftables", "iptables", "fail2ban_client"], action=actions.get("2.2"), description="Saisie multiple ou fichier"))
        section_2.add_child(create_node("2.3", "Débannir une IP", requires_any=["nftables", "iptables", "fail2ban_client"], action=actions.get("2.3"), description="Débannir une IP unique"))
        section_2.add_child(create_node("2.4", "Débannir une liste d'IPs", requires_any=["nftables", "iptables", "fail2ban_client"], action=actions.get("2.4"), description="Saisie multiple ou fichier"))
        section_2.add_child(create_node("2.5", "Lister les IPs bannies", requires_any=["nftables", "iptables", "fail2ban_client"], action=actions.get("2.5"), description="Tableau avec filtres"))
        section_2.add_child(create_node("2.6", "Synchroniser les backends NFt-IPt", requires_any=["nftables", "iptables", "ip6tables"], action=actions.get("2.6"), description="Nft ↔ Ipt"))
        section_2.add_child(create_node("2.7", "Importer depuis un fichier", requires_any=["nftables", "iptables", "ip6tables"], action=actions.get("2.7"), description="Gestion, Edition des fichiers et IP blocklist"))
        section_2.add_child(create_node("2.8", "Exporter vers un fichier", requires_any=["nftables", "iptables", "ip6tables"], action=actions.get("2.8"), description="Transfert des IPs vers fichiers, archives"))
        section_2.add_child(create_node("2.9", "Nettoyer (Flush) complet", requires_any=["nftables", "iptables", "fail2ban_client"], action=actions.get("2.9"), description="Vider un ou tous les backends"))
        section_2.add_child(create_node("2.10", "Interopérabilité des IPs", requires=["fail2ban_client", "nftables"], action=actions.get("4.3"), description="Transfert/Injection (Jails, Backends, Fichiers (idem que 4.3)"))
        self._root.add_child(section_2)
        
        # ====================================================================
        # Section 3: Gestion des règles
        # ====================================================================
        section_3 = create_node(
            node_id="3",
            label="GESTION DES RÈGLES (Politiques / Filtres)",
            description="Gestion fine des ports, protocoles et réseaux",
        )
        section_3.add_child(create_node("3.1", "Créer une règle avancée", requires_any=["nftables", "iptables", "ip6tables"], action=actions.get("3.1"), description="Assistant pas-à-pas pour créer une regle"))
        section_3.add_child(create_node("3.2", "Supprimer une règle", requires_any=["nftables", "iptables", "ip6tables"], action=actions.get("3.2"), description="Supression simplifié d'une regle"))
        section_3.add_child(create_node("3.3", "Lister les règles", requires_any=["nftables", "iptables", "ip6tables"], action=actions.get("3.3"), description="Tableau avec detail & compteurs par backend "))
        section_3.add_child(create_node("3.4", "Appliquer une politique pré-définie", requires_any=["nftables", "iptables", "ip6tables"], action=actions.get("3.4"), description="Profils activable (sauvegarde-auto de l'état)"))
        self._root.add_child(section_3)
        
        # ====================================================================
        # Section 4: Gestion Fail2ban
        # ====================================================================
        section_4 = create_node(
            node_id="4",
            label="GESTION FAIL2BAN (Jails & Transferts)",
            description="Interaction avec le daemon fail2ban",
        )
        section_4.add_child(create_node("4.1", "Analyse et État des jails", requires=["fail2ban_client"], action=actions.get("4.1"), description="Tableau récapitulatif + recherche d'IP par jail"))
        section_4.add_child(create_node("4.2", "Bannir / Débannir dans un jail", requires=["fail2ban_client"], action=actions.get("4.2"), description="Ban et Unban, IP unique ou liste d'IP"))
        section_4.add_child(create_node("4.3", "Interopérabilité des IPs", requires=["fail2ban_client", "nftables"], action=actions.get("4.3"), description="Transfert / Import / Export (Jails, Backends, Fichiers)"))
        section_4.add_child(create_node("4.4", "Créer un jail", requires=["fail2ban_client"], action=actions.get("4.4"), description="Assistant de création"))
        section_4.add_child(create_node("4.5", "Supprimer un jail", requires=["fail2ban_client"], action=actions.get("4.5"), description="choisir le jail et confirmer sa suppression"))
        section_4.add_child(create_node("4.6", "Vider un jail", requires=["fail2ban_client"], action=actions.get("4.6"), description="Vider toutes les IPs d'un jail"))
        section_4.add_child(create_node("4.7", "Vider tous les jails", requires=["fail2ban_client"], action=actions.get("4.7"), description="PURGE GENERALE - Vider toutes les IPs de tous les jails"))
        section_4.add_child(create_node("4.8", "Exporter un jail", requires=["fail2ban_client"], action=actions.get("4.8"), description="FORMAT: Brut/JSON, Injection/TXT, visualisation/HTML"))
        section_4.add_child(create_node("4.9", "Vérifier la configuration Fail2ban", requires=["fail2ban_client"], action=actions.get("4.9"), description=" utilisation de fail2ban-client -d"))
        section_4.add_child(create_node("4.10", "Gerer le service Fail2ban", requires=["fail2ban_service_control"], action=actions.get("4.10"), description="Contrôle du service Fail2ban (status, start, stop,...)"))
        self._root.add_child(section_4)
        
        # ====================================================================
        # Section 5: Gestion des logs
        # ====================================================================
        section_5 = create_node(
            node_id="5",
            label="GESTION DES LOGS (Analyse & Maintenance)",
            description="Analyse et maintenance des logs",
        )
        section_5.add_child(create_node("5.1", "Visualiser les logs en direct (Live Tail)", action=actions.get("5.1"), description="Tableau de bord temps réel : trafic + stats + logs "))
        section_5.add_child(create_node("5.2", "Analyser les IPs (Top N)", action=actions.get("5.2"), description="Classement des IPs actives"))
        section_5.add_child(create_node("5.3", "Supprimer une IP des logs", action=actions.get("5.3"), description="Nettoyage ciblé"))
        section_5.add_child(create_node("5.4", "Rotation / Backup des logs", action=actions.get("5.4"), description="Compression et archivage"))
        section_5.add_child(create_node("5.5", "Restaurer un backup", action=actions.get("5.5"), description="Sélection et restauration"))
        section_5.add_child(create_node("5.6", "Purge des backups", action=actions.get("5.6"), description="Suppression massive"))
        section_5.add_child(create_node("5.7", "Nettoyage avancé", action=actions.get("5.7"), description="Par âge ou taille"))
        section_5.add_child(create_node("5.8", "Statistiques des logs", action=actions.get("5.8"), description="recapitulatifs des evenements des logs"))
        section_5.add_child(create_node("5.9", "Visualiser les logs serveurs avec lnav", action=actions.get("8.6"), description="Sélection multi-fichiers, parsing complet analyse en fusion automatique (8.6 Bis)"))
        self._root.add_child(section_5)
        
        # ====================================================================
        # Section 6: Exports & Rapports
        # ====================================================================
        section_6 = create_node(
            node_id="6",
            label="EXPORTS & RAPPORTS (Audit centralisé)",
            description="Centralisation des exports",
        )
        section_6.add_child(create_node("6.1", "Exporter la Blacklist complète", action=actions.get("6.1"), description="FORMAT: Brut/JSON, Injection/TXT, visualisation/HTML"))
        section_6.add_child(create_node("6.2", "Exporter les Règles (ruleset)", requires_any=["nftables", "iptables", "ip6tables"], action=actions.get("6.2"), description="Règleset structuré"))
        section_6.add_child(create_node("6.3", "Exporter un rapport d'audit complet", action=actions.get("6.3"), description="État, historique, top IPs,..."))
        section_6.add_child(create_node("6.4", "Exporter les statistiques Fail2Ban", requires=["fail2ban_client"], action=actions.get("6.4"), description="Jails et bans"))
        self._root.add_child(section_6)
        
        # ====================================================================
        # Section 7: Système & Persistance
        # ====================================================================
        section_7 = create_node(
            node_id="7",
            label="SYSTÈME & PERSISTANCE (État & Sauvegarde)",
            description="Gestion de l'état interne",
        )
        section_7.add_child(create_node("7.1", "Sauvegarder l'état complet", action=actions.get("7.1"), description="Archive tar.gz horodatée"))
        section_7.add_child(create_node("7.2", "Restaurer un état", action=actions.get("7.2"), description="Sélection d'archive"))
        section_7.add_child(create_node("7.3", "Voir l'historique des actions", action=actions.get("7.3"), description="Log applicatif paginé"))
        section_7.add_child(create_node("7.4", "Recharger la configuration", action=actions.get("7.4"), description="Re-scan sans redémarrage"))
        self._root.add_child(section_7)
        
        # ====================================================================
        # Section 8: Monitoring & Statistiques
        # ====================================================================
        section_8 = create_node(
            node_id="8",
            label="MONITORING & STATISTIQUES",
            description="Vue d'ensemble de l'activité réseau",
        )
        section_8.add_child(create_node("8.1", "Tableau de bord en temps réel", requires=[], action=actions.get("8.1"), description="Dashboard Live complet (Refresh 2s)"))
        section_8.add_child(create_node("8.2", "État des connexions (Conntrack)", requires=["conntrack"], action=actions.get("8.2"), description="Sessions actives (snapshots)"))
        section_8.add_child(create_node("8.3", "Rapports statistiques (7 jours)", action=actions.get("8.3"), description="Graphiques sur 7 jours visu/export"))
        section_8.add_child(create_node("8.4", "Rapports statistiques (30 jours)", action=actions.get("8.4"), description="Vue macro 30 jours visu/export"))
        section_8.add_child(create_node("8.5", "Visualiser les logs serveurs avec Tail", action=actions.get("5.1"), description="Tableau de bord temps réel : trafic + stats + logs  (5.1 Bis) "))
        section_8.add_child(create_node("8.6", "Visualiser les logs serveurs avec lnav", action=actions.get("8.6"), description="Sélection multi-fichiers, analyse via lnav (fusion automatique)"))
        self._root.add_child(section_8)
        
        # ====================================================================
        # Section 0: Quitter
        # ====================================================================
        section_0 = create_node(
            node_id="0",
            label="QUITTER L'APPLICATION",
            description="Sauvegarde et fermeture",
            action=actions.get("0"),
        )
        self._root.add_child(section_0)
        
        return self._root
    
    def get_root(self) -> Optional[MenuNode]:
        """Get the root node of the menu tree."""
        return self._root


def build_main_menu(action_registry: Optional[dict[str, Callable[[Any], None]]] = None) -> MenuNode:
    """Convenience function to build the main menu tree.
    
    Args:
        action_registry: Dictionary mapping menu IDs to action callables.
    
    Returns:
        Root MenuNode with all children and actions wired.
    """
    builder = MenuBuilder()
    return builder.build(action_registry)

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Construit l'arbre de menu principal avec tous les nœuds et sous-menus.
# - Chaque nœud a un id, label, description, requires/requires_any, action.
# - Les actions sont injectées via un dictionnaire {menu_id: callable}.
# - Les prérequis (requires) sont évalués par tree_builder.py via le registre.
#
# Pourquoi dans interfaces/cli/ (charte) :
# - Pure structure de menu, pas de logique métier.
# - Pas d'appels directs aux backends.
# - Actions câblées via injection (pas de dépendance directe).
# - Le grisage est géré par tree_builder.py, pas ici.
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (c'est le rôle de domain/).
# ❌ Pas d'appels système (c'est le rôle de infrastructure/).
# ❌ Pas de rendu Rich (c'est le rôle de renderers/).
# ❌ Pas de décision de grisage (c'est le rôle de tree_builder.py).
# ❌ Pas de dépendance vers application/ ou infrastructure/.
#
# Points clés :
# - MenuBuilder : classe qui construit l'arbre complet.
# - build() : méthode principale qui prend un dict d'actions.
# - build_main_menu() : fonction convenience qui instancie MenuBuilder.
# - Chaque nœud utilise actions.get("X.Y") pour récupérer le callable.
# - requires : liste de capacités requises (ET logique).
# - requires_any : liste dont AU MOINS UNE doit être disponible (OU logique).
# - requires=[] : toujours accessible (pas de prérequis).
#---------------------------------------------------------------------->
