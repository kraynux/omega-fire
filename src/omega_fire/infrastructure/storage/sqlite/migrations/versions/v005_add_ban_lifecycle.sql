-- v005: Cycle de vie complet d'un ban — colonnes déjà déclarées dans le
--       modèle de domaine BanEntry (domain/ip_blacklist/models.py) mais
--       jamais persistées jusqu'ici : removed_at/removed_by permettent
--       de savoir QUAND et COMMENT un ban a été levé (menu 8.1 "dernier
--       unban", audit 6.3). jail_name identifie le jail fail2ban
--       d'origine quand applicable.
-- NULL pour toutes les lignes existantes (rétrocompatible, aucune ligne
-- historique ne peut avoir cette info).
ALTER TABLE bans ADD COLUMN removed_at TEXT;
ALTER TABLE bans ADD COLUMN removed_by TEXT;
ALTER TABLE bans ADD COLUMN jail_name TEXT;
