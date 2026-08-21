-- v004: Ajout de la date de création d'une règle
-- created_at : timestamp ISO de l'insertion en base, utilisé par le
--              dashboard (menu 8.1) pour détecter si un profil actif
--              a été modifié depuis son application (comparaison du
--              nombre de règles managées actuelles vs le nombre posé
--              au moment de l'application, stocké dans
--              active_preset_{backend}.json). NULL pour les lignes
--              existantes avant cette migration (rétrocompatible).
ALTER TABLE rules ADD COLUMN created_at TEXT;
