-- v002: Ajout du suivi d'origine et de référence externe pour les règles
-- external_ref : identifiant technique backend (handle nftables, ligne iptables),
--                stocké séparément du commentaire pour un dédoublonnage fiable.
-- origin       : 'managed' (créée par Omega-Fire) ou 'imported' (règle système
--                détectée lors d'une synchronisation).
ALTER TABLE rules ADD COLUMN external_ref TEXT;
ALTER TABLE rules ADD COLUMN origin TEXT DEFAULT 'imported';
