-- v003: Ajout de l'interface réseau associée à une règle
-- interface : nom de l'interface réseau (ex: eth0, wlan0, tailscale0),
--             saisie par l'utilisateur à la création (3.1), détectée ou
--             manuelle. NULL = ANY (toutes interfaces).
ALTER TABLE rules ADD COLUMN interface TEXT;
