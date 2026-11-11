# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Registre des 8 sections et de leurs 52 actions, designations reprises
telles quelles de interfaces/cli/menu_builder.py (meme id/label/
description). `screen_factory`/`direct_action` ne sont renseignes QUE
pour les actions deja migrees (Phase 3 de la feuille de route) — les
autres restent None et s'affichent normalement dans la navigation avec
une notification "pas encore migre" au clic (SectionScreen), plutot que
d'etre absentes du menu."""
from __future__ import annotations

from omega_fire.interfaces.tui.screens.action_history_screen import ActionHistoryScreen
from omega_fire.interfaces.tui.screens.advanced_cleanup_screen import AdvancedCleanupScreen
from omega_fire.interfaces.tui.screens.app_log_screen import AppLogScreen
from omega_fire.interfaces.tui.screens.apply_preset_screen import ApplyPresetScreen
from omega_fire.interfaces.tui.screens.backup_state_screen import BackupStateScreen
from omega_fire.interfaces.tui.screens.ban_ip_list_screen import BanIpListScreen
from omega_fire.interfaces.tui.screens.ban_ip_screen import BanIpScreen
from omega_fire.interfaces.tui.screens.blocklist_files_screen import BlocklistFilesScreen
from omega_fire.interfaces.tui.screens.capabilities_screen import CapabilitiesScreen
from omega_fire.interfaces.tui.screens.capability_picker_screen import CapabilityPickerScreen
from omega_fire.interfaces.tui.screens.clear_jail_screen import ClearJailScreen
from omega_fire.interfaces.tui.screens.conntrack_screen import ConntrackScreen
from omega_fire.interfaces.tui.screens.create_jail_screen import CreateJailScreen
from omega_fire.interfaces.tui.screens.dashboard_screen import DashboardScreen
from omega_fire.interfaces.tui.screens.create_rule_screen import CreateRuleScreen
from omega_fire.interfaces.tui.screens.delete_jail_screen import DeleteJailScreen
from omega_fire.interfaces.tui.screens.delete_rule_screen import DeleteRuleScreen
from omega_fire.interfaces.tui.screens.export_audit_screen import ExportAuditScreen
from omega_fire.interfaces.tui.screens.export_blacklist_screen import ExportBlacklistScreen
from omega_fire.interfaces.tui.screens.export_blocklist_file_screen import ExportBlocklistFileScreen
from omega_fire.interfaces.tui.screens.export_f2b_stats_screen import ExportF2bStatsScreen
from omega_fire.interfaces.tui.screens.export_log_stats_screen import ExportLogStatsScreen
from omega_fire.interfaces.tui.screens.exports_screen import ExportsScreen
from omega_fire.interfaces.tui.screens.export_jail_screen import ExportJailScreen
from omega_fire.interfaces.tui.screens.export_rules_screen import ExportRulesScreen
from omega_fire.interfaces.tui.screens.export_state_screen import ExportStateScreen
from omega_fire.interfaces.tui.screens.fail2ban_diagnostics_screen import Fail2banDiagnosticsScreen
from omega_fire.interfaces.tui.screens.flush_backends_screen import FlushBackendsScreen
from omega_fire.interfaces.tui.screens.jail_ban_unban_screen import JailBanUnbanScreen
from omega_fire.interfaces.tui.screens.jail_transfer_screen import JailTransferScreen
from omega_fire.interfaces.tui.screens.jails_status_screen import JailsStatusScreen
from omega_fire.interfaces.tui.screens.live_tail_screen import LiveTailScreen
from omega_fire.interfaces.tui.screens.lnav_screen import LnavScreen
from omega_fire.interfaces.tui.screens.log_favorites_screen import LogFavoritesScreen
from omega_fire.interfaces.tui.screens.log_library_screen import LogLibraryScreen
from omega_fire.interfaces.tui.screens.log_stats_screen import LogStatsScreen
from omega_fire.interfaces.tui.screens.log_view_screen import LogViewScreen
from omega_fire.interfaces.tui.screens.list_banned_ips_screen import ListBannedIpsScreen
from omega_fire.interfaces.tui.screens.list_rules_screen import ListRulesScreen
from omega_fire.interfaces.tui.screens.purge_all_jails_screen import PurgeAllJailsScreen
from omega_fire.interfaces.tui.screens.purge_backups_screen import PurgeBackupsScreen
from omega_fire.interfaces.tui.screens.remove_ip_from_log_screen import RemoveIpFromLogScreen
from omega_fire.interfaces.tui.screens.restore_backup_screen import RestoreBackupScreen
from omega_fire.interfaces.tui.screens.restore_state_screen import RestoreStateScreen
from omega_fire.interfaces.tui.screens.rotate_logs_screen import RotateLogsScreen
from omega_fire.interfaces.tui.screens.unban_ip_list_screen import UnbanIpListScreen
from omega_fire.interfaces.tui.screens.search_diagnostics_screen import SearchDiagnosticsScreen
from omega_fire.interfaces.tui.screens.section_screen import SectionItem, SectionScreen
from omega_fire.interfaces.tui.screens.stats_report_screen import StatsReportScreen
from omega_fire.interfaces.tui.screens.sync_backends_screen import SyncBackendsScreen
from omega_fire.interfaces.tui.screens.table_management_screen import TableManagementScreen
from omega_fire.interfaces.tui.screens.top_ips_screen import TopIpsScreen
from omega_fire.interfaces.tui.screens.unban_ip_screen import UnbanIpScreen
from omega_fire.interfaces.tui.support.direct_actions import (
    fail2ban_service_disable,
    fail2ban_service_enable,
    fail2ban_service_restart,
    fail2ban_service_start,
    fail2ban_service_status,
    fail2ban_service_stop,
    reload_config,
    rescan_system,
)
from omega_fire.shared.i18n import N_, _

_FAIL2BAN_SERVICE_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("4.10.1", N_("Vérifier le statut du service & persistance"), "",
                direct_action=fail2ban_service_status, direct_action_title=N_("4.10 Statut du service Fail2ban")),
    SectionItem("4.10.2", N_("Démarrer le service"), "",
                direct_action=fail2ban_service_start, direct_action_title=N_("4.10 Démarrer Fail2ban")),
    SectionItem("4.10.3", N_("Stopper le service"), "",
                direct_action=fail2ban_service_stop, direct_action_title=N_("4.10 Stopper Fail2ban"),
                confirm_title=_("CONFIRMER L'ARRÊT"), confirm_message=_("Arrêter le service Fail2ban ?")),
    SectionItem("4.10.4", N_("Redémarrer le service"), "",
                direct_action=fail2ban_service_restart, direct_action_title=N_("4.10 Redémarrer Fail2ban"),
                confirm_title=_("CONFIRMER LE REDÉMARRAGE"), confirm_message=_("Redémarrer le service Fail2ban ?")),
    SectionItem("4.10.5", N_("Activer le service au démarrage"), "",
                direct_action=fail2ban_service_enable, direct_action_title=N_("4.10 Activer Fail2ban au démarrage")),
    SectionItem("4.10.6", N_("Désactiver le service au démarrage"), "",
                direct_action=fail2ban_service_disable, direct_action_title=N_("4.10 Désactiver Fail2ban au démarrage")),
)


def _fail2ban_service_screen(container):
    return SectionScreen(
        container=container, section_id="4.10",
        title=_("GÉRER LE SERVICE FAIL2BAN"), items=_FAIL2BAN_SERVICE_ITEMS,
    )

SECTION_1_TITLE = N_("CAPACITÉS & DIAGNOSTICS")
SECTION_1_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("1.1", N_("Afficher le registre des capacités"), _("Liste des composants et leur status"),
                screen_factory=lambda c: CapabilitiesScreen(container=c, only_issues=False)),
    SectionItem("1.2", N_("Détail d'une capacité"), _("Sélection d'un composant"),
                screen_factory=lambda c: CapabilityPickerScreen(container=c)),
    SectionItem("1.3", N_("Re-scanner le système"), _("Relance des probes système"),
                direct_action=rescan_system, direct_action_title=N_("1.3 Re-scan du système"),
                confirm_title=_("RE-SCANNER LE SYSTÈME"),
                confirm_message=_("Relancer un scan complet du système (nftables, iptables, fail2ban, systemd) ?")),
    SectionItem("1.4", N_("Voir les diagnostics récents"), _("Liste les erreurs et dégradations"),
                screen_factory=lambda c: CapabilitiesScreen(container=c, only_issues=True)),
    SectionItem("1.5", N_("Voir le journal applicatif"), _("voir les logs d'événements applicatif"),
                screen_factory=lambda c: AppLogScreen(container=c)),
    SectionItem("1.6", N_("Rechercher dans les diagnostics"), _("Recherche par mot-clé"),
                screen_factory=lambda c: SearchDiagnosticsScreen(container=c)),
    SectionItem("1.7", N_("Exporter l'état et les diagnostics"), _("Données JSON (brut), TXT (data) ou HTML (visuel)"),
                screen_factory=lambda c: ExportStateScreen(container=c)),
)

SECTION_2_TITLE = N_("GESTION DES IPs (Blacklist unifiée NFt-IPt)")
SECTION_2_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("2.1", N_("Bannir une IP"), _("Bannir une IP unique"),
                screen_factory=lambda c: BanIpScreen(container=c)),
    SectionItem("2.2", N_("Bannir une liste d'IPs"), _("Saisie multiple ou fichier"),
                screen_factory=lambda c: BanIpListScreen(container=c)),
    SectionItem("2.3", N_("Débannir une IP"), _("Débannir une IP unique"),
                screen_factory=lambda c: UnbanIpScreen(container=c)),
    SectionItem("2.4", N_("Débannir une liste d'IPs"), _("Saisie multiple ou fichier"),
                screen_factory=lambda c: UnbanIpListScreen(container=c)),
    SectionItem("2.5", N_("Lister les IPs bannies"), _("Tableau avec filtres"),
                screen_factory=lambda c: ListBannedIpsScreen(container=c)),
    SectionItem("2.6", N_("Synchroniser les backends NFt-IPt"), _("Nft <-> Ipt"),
                screen_factory=lambda c: SyncBackendsScreen(container=c)),
    SectionItem("2.7", N_("Importer depuis un fichier"), _("Gestion, Édition des fichiers et IP blocklist"),
                screen_factory=lambda c: BlocklistFilesScreen(container=c)),
    SectionItem("2.8", N_("Exporter vers un fichier"), _("Transfert des IPs vers fichiers, archives"),
                screen_factory=lambda c: ExportBlocklistFileScreen(container=c)),
    SectionItem("2.9", N_("Nettoyer (Flush) complet"), _("Vider un ou tous les backends"),
                screen_factory=lambda c: FlushBackendsScreen(container=c)),
    SectionItem("2.10", N_("Interopérabilité des IPs"), _("Transfert/Injection (Jails, Backends, Fichiers (idem que 4.3)"),
                screen_factory=lambda c: JailTransferScreen(container=c)),
)

SECTION_3_TITLE = N_("GESTION DES RÈGLES (Politiques / Filtres)")
SECTION_3_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("3.1", N_("Créer une règle avancée"), _("Assistant pas-à-pas pour créer une règle"),
                screen_factory=lambda c: CreateRuleScreen(container=c)),
    SectionItem("3.2", N_("Supprimer une règle"), _("Suppression simplifiée d'une règle"),
                screen_factory=lambda c: DeleteRuleScreen(container=c)),
    SectionItem("3.3", N_("Lister les règles"), _("Tableau avec détail & compteurs par backend"),
                screen_factory=lambda c: ListRulesScreen(container=c)),
    SectionItem("3.4", N_("Appliquer une politique pré-définie"), _("Profils activable (sauvegarde-auto de l'état)"),
                screen_factory=lambda c: ApplyPresetScreen(container=c)),
    SectionItem("3.5", N_("Gestion des tables"), _("Diagnostic, initialisation, reset des politiques, flush cible ou synchronisé"),
                screen_factory=lambda c: TableManagementScreen(container=c)),
)

SECTION_4_TITLE = N_("GESTION FAIL2BAN (Jails & Transferts)")
SECTION_4_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("4.1", N_("Analyse et État des jails"), _("Tableau récapitulatif + recherche d'IP par jail"),
                screen_factory=lambda c: JailsStatusScreen(container=c)),
    SectionItem("4.2", N_("Bannir / Débannir dans un jail"), _("Ban et Unban, IP unique ou liste d'IP"),
                screen_factory=lambda c: JailBanUnbanScreen(container=c)),
    SectionItem("4.3", N_("Interopérabilité des IPs"), _("Transfert / Import / Export (Jails, Backends, Fichiers)"),
                screen_factory=lambda c: JailTransferScreen(container=c)),
    SectionItem("4.4", N_("Créer un jail"), _("Assistant de création"),
                screen_factory=lambda c: CreateJailScreen(container=c)),
    SectionItem("4.5", N_("Supprimer un jail"), _("choisir le jail et confirmer sa suppression"),
                screen_factory=lambda c: DeleteJailScreen(container=c)),
    SectionItem("4.6", N_("Vider un jail"), _("Vider toutes les IPs d'un jail"),
                screen_factory=lambda c: ClearJailScreen(container=c)),
    SectionItem("4.7", N_("Vider tous les jails"), _("PURGE GÉNÉRALE - Vider toutes les IPs de tous les jails"),
                screen_factory=lambda c: PurgeAllJailsScreen(container=c)),
    SectionItem("4.8", N_("Exporter un jail"), _("FORMAT: Brut/JSON, Injection/TXT, visualisation/HTML"),
                screen_factory=lambda c: ExportJailScreen(container=c)),
    SectionItem("4.9", N_("Vérifier la configuration Fail2ban"), _("utilisation de fail2ban-client -d"),
                screen_factory=lambda c: Fail2banDiagnosticsScreen(container=c)),
    SectionItem("4.10", N_("Gérer le service Fail2ban"), _("Contrôle du service Fail2ban (status, start, stop,...)"),
                screen_factory=_fail2ban_service_screen),
)

SECTION_5_TITLE = N_("GESTION DES LOGS (Analyse & Maintenance)")
SECTION_5_ITEMS: tuple[SectionItem, ...] = (
    # Version 3.5 (decisions utilisateur 2026-10-28) : Bibliotheque / Favoris / Voir les logs en
    # tete ; l'ancien 5.1 (Live Tail) et l'ancien 5.9 (lnav) restent en 8.5 et 8.6 ; 5.2 a 5.8
    # decales en 5.4 a 5.10. Anciens libelles : MENU_5_BEFORE_3_5 ci-dessous.
    SectionItem("5.1", N_("Bibliothèque"), _("Import des logs : omega-serv automatique, épinglage, SSH"),
                screen_factory=lambda c: LogLibraryScreen(container=c)),
    SectionItem("5.2", N_("Favoris"), _("Logs combinés, enregistrés et lancés directement"),
                screen_factory=lambda c: LogFavoritesScreen(container=c)),
    SectionItem("5.3", N_("Voir les logs"), _("Un log, lecteur au choix : Simple, Classique, lnav"),
                screen_factory=lambda c: LogViewScreen(container=c)),
    SectionItem("5.4", N_("Analyser les IPs (Top N)"), _("Classement des IPs actives"),
                screen_factory=lambda c: TopIpsScreen(container=c)),
    SectionItem("5.5", N_("Supprimer une IP des logs"), _("Nettoyage cible"),
                screen_factory=lambda c: RemoveIpFromLogScreen(container=c)),
    SectionItem("5.6", N_("Rotation / Backup des logs"), _("Compression et archivage"),
                screen_factory=lambda c: RotateLogsScreen(container=c)),
    SectionItem("5.7", N_("Restaurer un backup"), _("Sélection et restauration"),
                screen_factory=lambda c: RestoreBackupScreen(container=c)),
    SectionItem("5.8", N_("Purge des backups"), _("Suppression massive"),
                screen_factory=lambda c: PurgeBackupsScreen(container=c)),
    SectionItem("5.9", N_("Nettoyage avancé"), _("Par âge ou taille"),
                screen_factory=lambda c: AdvancedCleanupScreen(container=c)),
    SectionItem("5.10", N_("Statistiques des logs"), _("récapitulatifs des événements des logs"),
                screen_factory=lambda c: LogStatsScreen(container=c)),
)

# Menu 5 avant la version 3.5 : numero -> libelle. Sert a afficher correctement les anciennes
# entrees de l'historique d'audit (et celles de --legacy-cli, qui garde cette numerotation) :
# « 5.2 Analyser les IPs (Top N) » ne doit pas s'afficher « 5.2 Favoris ».
MENU_5_BEFORE_3_5: dict[str, tuple[str, ...]] = {
    "5.1": (N_("Visualiser les logs en direct (Live Tail)"),),
    "5.2": (N_("Analyser les IPs (Top N)"),),
    "5.3": (N_("Supprimer une IP des logs"),),
    "5.4": (N_("Rotation / Backup des logs"),),
    "5.5": (N_("Restaurer un backup"),),
    "5.6": (N_("Purge des backups"),),
    "5.7": (N_("Nettoyage avancé"),),
    "5.8": (N_("Statistiques des logs"),),
    "5.9": (N_("Visualiser les logs serveurs avec lnav"),),
}
# Menu 6 avant la version 3.6 : « 6.5 Voir tous les exports » (devenu 6.6) garde son libelle dans
# l'historique d'audit au lieu de s'afficher « 6.5 Exporter les statistiques des logs ».
MENU_6_BEFORE_3_6: dict[str, tuple[str, ...]] = {
    "6.5": (N_("Voir tous les exports"),),
}
# Titres courts ecrits dans l'historique par les ecrans et par --legacy-cli -> libelle du menu.
AUDIT_TITLE_ALIASES: dict[str, str] = {
    "Live Tail": N_("Visualiser les logs en direct (Live Tail)"),
    "Top IPs": N_("Analyser les IPs (Top N)"),
    "Supprimer IP": N_("Supprimer une IP des logs"),
    "Rotation & Backup Logs": N_("Rotation / Backup des logs"),
    "Restaurer Backup": N_("Restaurer un backup"),
    "Purge Backups": N_("Purge des backups"),
}

SECTION_6_TITLE = N_("EXPORTS & RAPPORTS (Audit centralisé)")
SECTION_6_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("6.1", N_("Exporter la Blacklist complète"), _("FORMAT: Brut/JSON, Injection/TXT, visualisation/HTML"),
                screen_factory=lambda c: ExportBlacklistScreen(container=c)),
    SectionItem("6.2", N_("Exporter les Règles (ruleset)"), _("Regleset structure"),
                screen_factory=lambda c: ExportRulesScreen(container=c)),
    SectionItem("6.3", N_("Exporter un rapport d'audit complet"), _("État, historique, top IPs,..."),
                screen_factory=lambda c: ExportAuditScreen(container=c)),
    SectionItem("6.4", N_("Exporter les statistiques Fail2Ban"), _("Jails et bans"),
                screen_factory=lambda c: ExportF2bStatsScreen(container=c)),
    # 3.6 (2026-11-09) : 6.5 = statistiques des logs (meme rapport qu'omega-serv / omega-log, logs
    # seulement) ; « Voir tous les exports » passe en 6.6. Ancien libelle : MENU_6_BEFORE_3_6.
    SectionItem("6.5", N_("Exporter les statistiques des logs"), _("Rapport des logs : statuts, top IP, chemins, horaires"),
                screen_factory=lambda c: ExportLogStatsScreen(container=c)),
    SectionItem("6.6", N_("Voir tous les exports"), _("Ouvrir, copier le chemin, supprimer"),
                screen_factory=lambda c: ExportsScreen(container=c)),
)

SECTION_7_TITLE = N_("SYSTÈME & PERSISTANCE (État & Sauvegarde)")
SECTION_7_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("7.1", N_("Sauvegarder l'état complet"), _("Archive tar.gz horodatee"),
                screen_factory=lambda c: BackupStateScreen(container=c)),
    SectionItem("7.2", N_("Restaurer un état"), _("Sélection d'archive"),
                screen_factory=lambda c: RestoreStateScreen(container=c)),
    SectionItem("7.3", N_("Voir l'historique des actions"), _("Log applicatif paginé"),
                screen_factory=lambda c: ActionHistoryScreen(container=c)),
    SectionItem("7.4", N_("Recharger la configuration"), _("Re-scan sans redémarrage"),
                direct_action=reload_config, direct_action_title=N_("7.4 Recharger config")),
)

SECTION_8_TITLE = N_("MONITORING & STATISTIQUES")
SECTION_8_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("8.1", N_("Tableau de bord en temps réel"), _("Dashboard Live complet (Refresh 2s)"),
                screen_factory=lambda c: DashboardScreen(container=c)),
    SectionItem("8.2", N_("État des connexions (Conntrack)"), _("Sessions actives (snapshots)"),
                screen_factory=lambda c: ConntrackScreen(container=c)),
    SectionItem("8.3", N_("Rapports statistiques (7 jours)"), _("Graphiques sur 7 jours visu/export"),
                screen_factory=lambda c: StatsReportScreen(
                    container=c, period_code="7d", period_label=N_("7 jours"),
                    title=N_("RAPPORT STATISTIQUE — 7 JOURS"), period_suffix="7j",
                )),
    SectionItem("8.4", N_("Rapports statistiques (30 jours)"), _("Vue macro 30 jours visu/export"),
                screen_factory=lambda c: StatsReportScreen(
                    container=c, period_code="30d", period_label=N_("30 jours"),
                    title=N_("RAPPORT STATISTIQUE — 30 JOURS"), period_suffix="30j",
                )),
    SectionItem("8.5", N_("Visualiser les logs serveurs avec Tail"), _("Tableau de bord temps réel : trafic + stats + logs"),
                screen_factory=lambda c: LiveTailScreen(container=c)),
    SectionItem("8.6", N_("Visualiser les logs serveurs avec lnav"), _("Sélection multi-fichiers, analyse via lnav (fusion automatique)"),
                screen_factory=lambda c: LnavScreen(container=c)),
)

SECTIONS: dict[str, tuple[str, tuple[SectionItem, ...]]] = {
    "1": (SECTION_1_TITLE, SECTION_1_ITEMS),
    "2": (SECTION_2_TITLE, SECTION_2_ITEMS),
    "3": (SECTION_3_TITLE, SECTION_3_ITEMS),
    "4": (SECTION_4_TITLE, SECTION_4_ITEMS),
    "5": (SECTION_5_TITLE, SECTION_5_ITEMS),
    "6": (SECTION_6_TITLE, SECTION_6_ITEMS),
    "7": (SECTION_7_TITLE, SECTION_7_ITEMS),
    "8": (SECTION_8_TITLE, SECTION_8_ITEMS),
}


def find_item(action_id: str) -> tuple[str, SectionItem] | None:
    """Cherche une action par son identifiant complet (ex. "5.1",
    "4.10.3") dans toutes les sections, y compris le sous-menu imbrique
    du service Fail2ban (4.10.x) — pour l'acces direct clavier
    (saisie du numero + Entree, voir home.py)."""
    for section_id, (_title, items) in SECTIONS.items():
        for item in items:
            if item.action_id == action_id:
                return section_id, item
    for item in _FAIL2BAN_SERVICE_ITEMS:
        if item.action_id == action_id:
            return "4", item
    return None
