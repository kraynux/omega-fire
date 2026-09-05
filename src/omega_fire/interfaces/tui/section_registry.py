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
from omega_fire.interfaces.tui.screens.log_stats_screen import LogStatsScreen
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

_FAIL2BAN_SERVICE_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("4.10.1", "Verifier le statut du service & persistance", "",
                direct_action=fail2ban_service_status, direct_action_title="4.10 Statut du service Fail2ban"),
    SectionItem("4.10.2", "Demarrer le service", "",
                direct_action=fail2ban_service_start, direct_action_title="4.10 Demarrer Fail2ban"),
    SectionItem("4.10.3", "Stopper le service", "",
                direct_action=fail2ban_service_stop, direct_action_title="4.10 Stopper Fail2ban",
                confirm_title="CONFIRMER L'ARRET", confirm_message="Arreter le service Fail2ban ?"),
    SectionItem("4.10.4", "Redemarrer le service", "",
                direct_action=fail2ban_service_restart, direct_action_title="4.10 Redemarrer Fail2ban",
                confirm_title="CONFIRMER LE REDEMARRAGE", confirm_message="Redemarrer le service Fail2ban ?"),
    SectionItem("4.10.5", "Activer le service au demarrage", "",
                direct_action=fail2ban_service_enable, direct_action_title="4.10 Activer Fail2ban au demarrage"),
    SectionItem("4.10.6", "Desactiver le service au demarrage", "",
                direct_action=fail2ban_service_disable, direct_action_title="4.10 Desactiver Fail2ban au demarrage"),
)


def _fail2ban_service_screen(container):
    return SectionScreen(
        container=container, section_id="4.10",
        title="GERER LE SERVICE FAIL2BAN", items=_FAIL2BAN_SERVICE_ITEMS,
    )

SECTION_1_TITLE = "ETAT DES CAPACITES & DIAGNOSTICS"
SECTION_1_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("1.1", "Afficher le registre des capacites", "Liste des composants et leur status",
                screen_factory=lambda c: CapabilitiesScreen(container=c, only_issues=False)),
    SectionItem("1.2", "Detail d'une capacite", "Selection d'un composant",
                screen_factory=lambda c: CapabilityPickerScreen(container=c)),
    SectionItem("1.3", "Re-scanner le systeme", "Relance des probes systeme",
                direct_action=rescan_system, direct_action_title="1.3 Re-scan du systeme",
                confirm_title="RE-SCANNER LE SYSTEME",
                confirm_message="Relancer un scan complet du systeme (nftables, iptables, fail2ban, systemd) ?"),
    SectionItem("1.4", "Voir les diagnostics recents", "Liste les erreurs et degradations",
                screen_factory=lambda c: CapabilitiesScreen(container=c, only_issues=True)),
    SectionItem("1.5", "Voir le journal applicatif", "voir les logs d'evenements applicatif",
                screen_factory=lambda c: AppLogScreen(container=c)),
    SectionItem("1.6", "Rechercher dans les diagnostics", "Recherche par mot-cle",
                screen_factory=lambda c: SearchDiagnosticsScreen(container=c)),
    SectionItem("1.7", "Exporter l'etat et les diagnostics", "Donnees JSON (brut), TXT (data) ou HTML (visuel)",
                screen_factory=lambda c: ExportStateScreen(container=c)),
)

SECTION_2_TITLE = "GESTION DES IPs (Blacklist unifiee NFt-IPt)"
SECTION_2_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("2.1", "Bannir une IP", "Bannir une IP unique",
                screen_factory=lambda c: BanIpScreen(container=c)),
    SectionItem("2.2", "Bannir une liste d'IPs", "Saisie multiple ou fichier",
                screen_factory=lambda c: BanIpListScreen(container=c)),
    SectionItem("2.3", "Debannir une IP", "Debannir une IP unique",
                screen_factory=lambda c: UnbanIpScreen(container=c)),
    SectionItem("2.4", "Debannir une liste d'IPs", "Saisie multiple ou fichier",
                screen_factory=lambda c: UnbanIpListScreen(container=c)),
    SectionItem("2.5", "Lister les IPs bannies", "Tableau avec filtres",
                screen_factory=lambda c: ListBannedIpsScreen(container=c)),
    SectionItem("2.6", "Synchroniser les backends NFt-IPt", "Nft <-> Ipt",
                screen_factory=lambda c: SyncBackendsScreen(container=c)),
    SectionItem("2.7", "Importer depuis un fichier", "Gestion, Edition des fichiers et IP blocklist",
                screen_factory=lambda c: BlocklistFilesScreen(container=c)),
    SectionItem("2.8", "Exporter vers un fichier", "Transfert des IPs vers fichiers, archives",
                screen_factory=lambda c: ExportBlocklistFileScreen(container=c)),
    SectionItem("2.9", "Nettoyer (Flush) complet", "Vider un ou tous les backends",
                screen_factory=lambda c: FlushBackendsScreen(container=c)),
    SectionItem("2.10", "Interoperabilite des IPs", "Transfert/Injection (Jails, Backends, Fichiers (idem que 4.3)",
                screen_factory=lambda c: JailTransferScreen(container=c)),
)

SECTION_3_TITLE = "GESTION DES REGLES (Politiques / Filtres)"
SECTION_3_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("3.1", "Creer une regle avancee", "Assistant pas-a-pas pour creer une regle",
                screen_factory=lambda c: CreateRuleScreen(container=c)),
    SectionItem("3.2", "Supprimer une regle", "Supression simplifie d'une regle",
                screen_factory=lambda c: DeleteRuleScreen(container=c)),
    SectionItem("3.3", "Lister les regles", "Tableau avec detail & compteurs par backend",
                screen_factory=lambda c: ListRulesScreen(container=c)),
    SectionItem("3.4", "Appliquer une politique pre-definie", "Profils activable (sauvegarde-auto de l'etat)",
                screen_factory=lambda c: ApplyPresetScreen(container=c)),
)

SECTION_4_TITLE = "GESTION FAIL2BAN (Jails & Transferts)"
SECTION_4_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("4.1", "Analyse et Etat des jails", "Tableau recapitulatif + recherche d'IP par jail",
                screen_factory=lambda c: JailsStatusScreen(container=c)),
    SectionItem("4.2", "Bannir / Debannir dans un jail", "Ban et Unban, IP unique ou liste d'IP",
                screen_factory=lambda c: JailBanUnbanScreen(container=c)),
    SectionItem("4.3", "Interoperabilite des IPs", "Transfert / Import / Export (Jails, Backends, Fichiers)",
                screen_factory=lambda c: JailTransferScreen(container=c)),
    SectionItem("4.4", "Creer un jail", "Assistant de creation",
                screen_factory=lambda c: CreateJailScreen(container=c)),
    SectionItem("4.5", "Supprimer un jail", "choisir le jail et confirmer sa suppression",
                screen_factory=lambda c: DeleteJailScreen(container=c)),
    SectionItem("4.6", "Vider un jail", "Vider toutes les IPs d'un jail",
                screen_factory=lambda c: ClearJailScreen(container=c)),
    SectionItem("4.7", "Vider tous les jails", "PURGE GENERALE - Vider toutes les IPs de tous les jails",
                screen_factory=lambda c: PurgeAllJailsScreen(container=c)),
    SectionItem("4.8", "Exporter un jail", "FORMAT: Brut/JSON, Injection/TXT, visualisation/HTML",
                screen_factory=lambda c: ExportJailScreen(container=c)),
    SectionItem("4.9", "Verifier la configuration Fail2ban", "utilisation de fail2ban-client -d",
                screen_factory=lambda c: Fail2banDiagnosticsScreen(container=c)),
    SectionItem("4.10", "Gerer le service Fail2ban", "Controle du service Fail2ban (status, start, stop,...)",
                screen_factory=_fail2ban_service_screen),
)

SECTION_5_TITLE = "GESTION DES LOGS (Analyse & Maintenance)"
SECTION_5_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("5.1", "Visualiser les logs en direct (Live Tail)", "Tableau de bord temps reel : trafic + stats + logs",
                screen_factory=lambda c: LiveTailScreen(container=c)),
    SectionItem("5.2", "Analyser les IPs (Top N)", "Classement des IPs actives",
                screen_factory=lambda c: TopIpsScreen(container=c)),
    SectionItem("5.3", "Supprimer une IP des logs", "Nettoyage cible",
                screen_factory=lambda c: RemoveIpFromLogScreen(container=c)),
    SectionItem("5.4", "Rotation / Backup des logs", "Compression et archivage",
                screen_factory=lambda c: RotateLogsScreen(container=c)),
    SectionItem("5.5", "Restaurer un backup", "Selection et restauration",
                screen_factory=lambda c: RestoreBackupScreen(container=c)),
    SectionItem("5.6", "Purge des backups", "Suppression massive",
                screen_factory=lambda c: PurgeBackupsScreen(container=c)),
    SectionItem("5.7", "Nettoyage avance", "Par age ou taille",
                screen_factory=lambda c: AdvancedCleanupScreen(container=c)),
    SectionItem("5.8", "Statistiques des logs", "recapitulatifs des evenements des logs",
                screen_factory=lambda c: LogStatsScreen(container=c)),
    SectionItem("5.9", "Visualiser les logs serveurs avec lnav", "Selection multi-fichiers, parsing complet analyse en fusion automatique (8.6 Bis)",
                screen_factory=lambda c: LnavScreen(container=c)),
)

SECTION_6_TITLE = "EXPORTS & RAPPORTS (Audit centralise)"
SECTION_6_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("6.1", "Exporter la Blacklist complete", "FORMAT: Brut/JSON, Injection/TXT, visualisation/HTML",
                screen_factory=lambda c: ExportBlacklistScreen(container=c)),
    SectionItem("6.2", "Exporter les Regles (ruleset)", "Regleset structure",
                screen_factory=lambda c: ExportRulesScreen(container=c)),
    SectionItem("6.3", "Exporter un rapport d'audit complet", "Etat, historique, top IPs,...",
                screen_factory=lambda c: ExportAuditScreen(container=c)),
    SectionItem("6.4", "Exporter les statistiques Fail2Ban", "Jails et bans",
                screen_factory=lambda c: ExportF2bStatsScreen(container=c)),
)

SECTION_7_TITLE = "SYSTEME & PERSISTANCE (Etat & Sauvegarde)"
SECTION_7_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("7.1", "Sauvegarder l'etat complet", "Archive tar.gz horodatee",
                screen_factory=lambda c: BackupStateScreen(container=c)),
    SectionItem("7.2", "Restaurer un etat", "Selection d'archive",
                screen_factory=lambda c: RestoreStateScreen(container=c)),
    SectionItem("7.3", "Voir l'historique des actions", "Log applicatif pagine",
                screen_factory=lambda c: ActionHistoryScreen(container=c)),
    SectionItem("7.4", "Recharger la configuration", "Re-scan sans redemarrage",
                direct_action=reload_config, direct_action_title="7.4 Recharger config"),
)

SECTION_8_TITLE = "MONITORING & STATISTIQUES"
SECTION_8_ITEMS: tuple[SectionItem, ...] = (
    SectionItem("8.1", "Tableau de bord en temps reel", "Dashboard Live complet (Refresh 2s)",
                screen_factory=lambda c: DashboardScreen(container=c)),
    SectionItem("8.2", "Etat des connexions (Conntrack)", "Sessions actives (snapshots)",
                screen_factory=lambda c: ConntrackScreen(container=c)),
    SectionItem("8.3", "Rapports statistiques (7 jours)", "Graphiques sur 7 jours visu/export",
                screen_factory=lambda c: StatsReportScreen(
                    container=c, period_code="7d", period_label="7 jours",
                    title="RAPPORT STATISTIQUE — 7 JOURS", period_suffix="7j",
                )),
    SectionItem("8.4", "Rapports statistiques (30 jours)", "Vue macro 30 jours visu/export",
                screen_factory=lambda c: StatsReportScreen(
                    container=c, period_code="30d", period_label="30 jours",
                    title="RAPPORT STATISTIQUE — 30 JOURS", period_suffix="30j",
                )),
    SectionItem("8.5", "Visualiser les logs serveurs avec Tail", "Tableau de bord temps reel : trafic + stats + logs (5.1 Bis)",
                screen_factory=lambda c: LiveTailScreen(container=c)),
    SectionItem("8.6", "Visualiser les logs serveurs avec lnav", "Selection multi-fichiers, analyse via lnav (fusion automatique)",
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
