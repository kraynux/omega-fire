# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contenu d'aide contextuelle pour le TUI Omega-Fire.

Fournit un guide d'utilisation détaillé par nœud de menu (section ou
action), indexé par l'id du nœud tel que défini dans menu_builder.py
(ex: "4", "4.2"). Consommé par interfaces/cli/app.py::_build_help_body()
pour l'overlay d'aide contextuelle (touche [a]).

Priorité du contenu : aider et guider l'utilisateur (comment utiliser,
conséquences concrètes, points d'attention) — la transparence technique
("sous le capot") est secondaire, ajoutée seulement quand elle apporte
une vraie clarté, pas systématiquement.

Il ne contient aucune logique métier, aucune couleur ni rendu Rich —
uniquement des données texte. Le style (theme_registry) est appliqué
par le renderer, pas ici.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class HelpEntry:
    """Contenu d'aide détaillé pour un seul nœud de menu.

    Tous les champs sont optionnels sauf summary — une entrée peut se
    limiter à un résumé si le reste n'apporte rien (ex: une action
    purement en lecture seule n'a pas besoin de "conséquences").

    Attributes:
        summary: Résumé pragmatique — à quoi ça sert concrètement.
        usage: Points "comment l'utiliser" (étapes, saisies attendues).
        consequences: Ce qui se passe réellement une fois validé (état
            modifié, fichiers écrits, service rechargé...).
        warnings: Pièges ou précautions à connaître avant de valider.
        mechanism: Transparence technique optionnelle ("sous le capot")
            — laissé vide par défaut, renseigné seulement quand ça aide
            vraiment à comprendre (ex: pourquoi une opération est rapide
            ou lente, quelle source de données est lue).
        see_also: Ids d'autres nœuds de menu liés (ex: "4.6" -> ["4.7"]).
    """
    summary: str
    usage: list[str] = field(default_factory=list)
    consequences: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    mechanism: str = ""
    see_also: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------
# Section 1 — État des capacités & diagnostics
# ----------------------------------------------------------------------

HELP_ENTRIES: dict[str, HelpEntry] = {
    "1": HelpEntry(
        summary=(
            "Vue globale des backends détectés (nftables, iptables, fail2ban, "
            "systemd...) et de leur état : disponible, dégradé ou manquant. "
            "Point de départ pour comprendre pourquoi une fonctionnalité est "
            "grisée ailleurs dans le menu."
        ),
        usage=[
            "Consulte 1.1 pour la vue d'ensemble, 1.3 si l'état affiché "
            "semble périmé (après une installation ou un changement système).",
        ],
        see_also=["1.1", "1.3"],
    ),
    "1.1": HelpEntry(
        summary=(
            "Liste toutes les capacités détectées par le dernier scan "
            "système : quels backends/services sont disponibles, dégradés "
            "ou manquants."
        ),
        usage=["Aucune saisie requise — affiche directement le registre actuel."],
        consequences=[
            "Lecture seule : ne relance aucun scan, affiche l'état déjà en "
            "mémoire (voir 1.3 pour rafraîchir).",
        ],
        warnings=[
            "Si l'appli vient de démarrer sur une machine où un service a "
            "changé d'état entre-temps, l'information peut être obsolète "
            "— relance un scan (1.3) si besoin.",
        ],
        see_also=["1.2", "1.3"],
    ),
    "1.2": HelpEntry(
        summary=(
            "Affiche le détail complet d'une capacité précise (ex: nftables, "
            "fail2ban) : statut, raison si dégradée/manquante, informations "
            "de diagnostic."
        ),
        usage=[
            "Sélectionne par numéro, ou saisis directement l'identifiant de "
            "la capacité (visible via 1.1).",
        ],
        consequences=["Lecture seule."],
        see_also=["1.1"],
    ),
    "1.3": HelpEntry(
        summary=(
            "Relance les sondes système (nftables, iptables, fail2ban, "
            "systemd...) pour mettre à jour le registre des capacités."
        ),
        usage=["Aucune saisie — lance directement le scan."],
        consequences=[
            "Met à jour le registre en mémoire — peut changer ce qui est "
            "grisé/disponible ailleurs dans les menus. Une capacité "
            "redevenue disponible débloque immédiatement les actions qui "
            "en dépendent, sans redémarrer l'application.",
        ],
        warnings=[
            "Des erreurs partielles sont possibles (ex: une sonde échoue) "
            "sans faire échouer tout le scan — le résumé affiché indique "
            "combien d'erreurs ont eu lieu, à vérifier si le nombre de "
            "composants disponibles semble anormalement bas.",
        ],
        see_also=["1.1", "1.4"],
    ),
    "1.4": HelpEntry(
        summary=(
            "Affiche les erreurs et dégradations récentes détectées sur le "
            "système (capacités manquantes/dégradées et pourquoi)."
        ),
        usage=["Aucune saisie requise."],
        consequences=["Lecture seule."],
        see_also=["1.1", "1.6"],
    ),
    "1.5": HelpEntry(
        summary=(
            "Consulte ou purge le journal interne d'Omega-Fire (actions "
            "effectuées, erreurs, avertissements) — pas les logs système "
            "(Nginx, auth.log...), voir la section 5 pour ceux-là."
        ),
        usage=[
            "Mode consultation : choisis un nombre de lignes (50/100/"
            "personnalisé), un mot-clé optionnel, puis navigue page par "
            "page (Entrée pour continuer, q pour arrêter).",
            "Mode gestion/purge : supprime les entrées de plus de 30/120 "
            "jours, avant une date précise, ou les N plus anciennes — une "
            "confirmation est toujours demandée avant suppression.",
        ],
        consequences=[
            "La consultation est en lecture seule. La purge supprime "
            "réellement des entrées du journal, de façon irréversible.",
        ],
        warnings=[
            "Erreurs et alertes critiques sont mises en évidence par "
            "couleur — pour chercher un problème précis, filtre par "
            "mot-clé plutôt que de tout parcourir.",
        ],
        see_also=["1.4", "1.6"],
    ),
    "1.6": HelpEntry(
        summary=(
            "Recherche un mot-clé (IP, nom de backend, message d'erreur...) "
            "à la fois dans les diagnostics système et dans le journal "
            "applicatif, en une seule requête."
        ),
        usage=[
            "Saisis un mot-clé — la recherche combine automatiquement les "
            "deux sources (diagnostics + journal), jusqu'à 15 résultats du "
            "journal affichés.",
        ],
        consequences=["Lecture seule."],
        see_also=["1.4", "1.5"],
    ),
    "1.7": HelpEntry(
        summary=(
            "Exporte un rapport de l'état système et des diagnostics dans "
            "un fichier : JSON (données brutes), HTML (rapport visuel, par "
            "défaut) ou TXT (texte brut)."
        ),
        usage=[
            "Choisis le format, puis valide le chemin de destination "
            "proposé ou saisis-en un autre.",
        ],
        consequences=[
            "Écrit un fichier réel sur disque (par défaut dans le dossier "
            "d'exports) — ne modifie rien côté système.",
        ],
        see_also=["6.3"],
    ),

    # ------------------------------------------------------------------
    # Section 2 — Gestion des IPs (Blacklist unifiée NFt-IPt)
    # ------------------------------------------------------------------

    "2": HelpEntry(
        summary=(
            "Gestion unifiée des IPs bannies à travers tous les backends "
            "détectés (nftables, iptables, fail2ban) : bannir, débannir, "
            "lister, synchroniser, importer/exporter, purger."
        ),
        usage=[
            "La plupart des actions agissent par défaut sur tous les "
            "backends disponibles simultanément — cibler un seul backend "
            "reste possible mais est pensé pour du diagnostic, pas un "
            "usage courant.",
        ],
        see_also=["2.1", "2.6", "2.9"],
    ),
    "2.1": HelpEntry(
        summary="Bannit une seule IP, sur tous les backends détectés par défaut (nftables/iptables/fail2ban).",
        usage=[
            "Saisis l'IP, choisis les backends cibles (tous par défaut, ou "
            "un seul pour diagnostic), ajoute un commentaire optionnel, "
            "puis confirme.",
        ],
        consequences=[
            "L'IP est bloquée immédiatement sur chaque backend ciblé. Un "
            "rapport par backend indique succès, doublon (déjà bannie) ou échec.",
        ],
        warnings=[
            "Cibler un seul backend est un mode diagnostic : si un autre "
            "backend est actif, l'IP pourrait rester accessible via ce dernier.",
        ],
        see_also=["2.3", "2.2"],
    ),
    "2.2": HelpEntry(
        summary=(
            "Bannit une liste d'IPs en une fois, depuis une saisie manuelle "
            "ou un fichier (défaut, fichier fail2ban par défaut, dossier "
            "var/blocklist/, fichier épinglé, ou chemin personnalisé)."
        ),
        usage=["Choisis la méthode d'approvisionnement, puis valide la liste d'IPs extraite avant le bannissement effectif."],
        consequences=["Chaque IP valide extraite est bannie sur les backends ciblés, comme pour 2.1 mais en masse."],
        see_also=["2.1", "2.7"],
    ),
    "2.3": HelpEntry(
        summary="Débannit une seule IP, sur tous les backends détectés par défaut.",
        usage=["Même déroulé que 2.1, en sens inverse : saisis l'IP, choisis les backends, confirme."],
        consequences=["L'IP redevient accessible immédiatement sur chaque backend ciblé."],
        see_also=["2.1", "2.4"],
    ),
    "2.4": HelpEntry(
        summary="Débannit une liste d'IPs en une fois — même logique d'approvisionnement que 2.2.",
        usage=["Choisis la méthode d'approvisionnement, valide la liste, confirme."],
        consequences=["Chaque IP de la liste est débannie sur les backends ciblés."],
        see_also=["2.3", "2.2"],
    ),
    "2.5": HelpEntry(
        summary="Liste toutes les IPs actuellement bannies, avec leur backend d'origine et leur commentaire/source.",
        usage=["Choisis un backend précis ou consulte tous les backends d'un coup."],
        consequences=["Lecture seule."],
        see_also=["2.1", "2.9"],
    ),
    "2.6": HelpEntry(
        summary="Réconcilie les backends entre eux : ajoute sur chaque backend cible les IPs déjà bannies ailleurs mais manquantes chez lui.",
        usage=["Choisis les backends à synchroniser (tous par défaut)."],
        consequences=["Additif uniquement : ne retire jamais une IP, ajoute seulement celles manquantes pour aligner les backends."],
        see_also=["2.5", "2.1"],
    ),
    "2.7": HelpEntry(
        summary=(
            "Gestion complète des fichiers de blocklist dans var/blocklist/ : "
            "créer, importer depuis un autre dossier, éditer IP par IP, "
            "renommer, supprimer, et bannir directement le contenu d'un fichier."
        ),
        usage=["Sélectionne un fichier existant pour l'éditer, ou utilise [I]/[N] pour en importer/créer un nouveau."],
        consequences=[
            "Les modifications (ajout/retrait d'IP, renommage, suppression) "
            "touchent le fichier réel sur disque — bannir depuis un fichier "
            "ici bannit réellement les IPs valides qu'il contient.",
        ],
        see_also=["2.2", "2.8"],
    ),
    "2.8": HelpEntry(
        summary="Exporte les IPs actuellement bannies vers un fichier (défaut, backup horodaté, fichier existant, récent, chemin manuel, ou fichier épinglé).",
        usage=["Choisis la destination et le mode d'écriture (écraser ou ajouter au fichier existant)."],
        consequences=["Écrit un fichier réel — ne modifie aucun état de bannissement."],
        see_also=["2.5", "2.7"],
    ),
    "2.9": HelpEntry(
        summary="PURGE : débannit toutes les IPs sur les backends ciblés (tous par défaut).",
        usage=["Une confirmation explicite est demandée avant exécution."],
        consequences=[
            "Toutes les IPs actuellement bannies sur les backends ciblés "
            "sont débannies. Les règles de filtrage principales (ports "
            "autorisés, accès SSH...) restent intactes — seule la liste "
            "des IPs bannies est vidée.",
        ],
        warnings=["Cibler un seul backend est un mode diagnostic — une IP bannie ailleurs resterait bloquée malgré cette purge."],
        see_also=["2.5", "4.7"],
    ),
    "2.10": HelpEntry(
        summary=(
            "Transfère des IPs entre jails fail2ban, vers/depuis les backends "
            "firewall (nftables/iptables), ou depuis/vers des fichiers — "
            "raccourci vers la même action que 4.3, accessible directement "
            "depuis la section IPs."
        ),
        usage=[
            "Choisis d'abord une source (un jail, un backend, un fichier), "
            "puis une destination.",
            "Un récapitulatif (IPs déjà présentes / nouvelles / échecs) "
            "s'affiche après l'opération — vérifie-le avant de continuer.",
        ],
        consequences=[
            "Les IPs transférées vers un jail ou un backend sont réellement "
            "bannies à la destination, pas juste copiées dans une liste.",
        ],
        warnings=[
            "Le transfert vers nftables crée automatiquement la chaîne de "
            "blocage si elle n'existe pas encore — normal, pas une erreur "
            "si tu la vois apparaître pour la première fois.",
        ],
        see_also=["4.3", "2.6"],
    ),

    # ------------------------------------------------------------------
    # Section 3 — Gestion des règles (Politiques / Filtres)
    # ------------------------------------------------------------------

    "3": HelpEntry(
        summary="Gestion fine des règles de pare-feu (ports, protocoles, réseaux) sur nftables/iptables, indépendamment du bannissement d'IP (section 2).",
        usage=[
            "Une règle est en général créée sur les deux backends "
            "disponibles simultanément — un profil restrictif actif sur "
            "un seul backend peut annuler l'effet d'une règle posée sur "
            "l'autre (voir 3.1).",
        ],
        see_also=["3.1", "3.4"],
    ),
    "3.1": HelpEntry(
        summary="Assistant pas-à-pas pour créer une règle avancée (source, port, protocole, action) sur un ou plusieurs backends.",
        usage=["Réponds aux questions successives : backend(s) cible(s), puis les paramètres de la règle."],
        consequences=["La règle est appliquée immédiatement sur les backends ciblés et enregistrée en base pour réapparaître dans 3.2/3.3."],
        warnings=[
            "Deux backends actifs au même point de contrôle fonctionnent "
            "en INTERSECTION, pas en union : créer une règle ACCEPT sur un "
            "seul backend ne suffit pas si l'autre bloque toujours ce "
            "trafic — il reste refusé tant que les deux ne l'autorisent "
            "pas. Cibler un seul backend est réservé au diagnostic.",
        ],
        see_also=["3.3", "3.4"],
    ),
    "3.2": HelpEntry(
        summary="Supprime une ou plusieurs règles, sélectionnées par ID (règles Omega-Fire créées via 3.1, règles système importées, ou les deux) — ou nettoie en un clic toutes les règles INACTIVES.",
        usage=[
            "Filtre l'affichage (Omega-Fire / Système / Toutes), puis saisis un ou plusieurs IDs séparés par une virgule.",
            "Si des règles inactives existent, une option [4] apparaît pour toutes les supprimer d'un coup (une seule confirmation, sans sélection ID par ID) — utile quand la majorité des règles importées du système sont inactives.",
        ],
        consequences=["Suppression réelle et immédiate sur le(s) backend(s) où la règle est active."],
        warnings=["Les règles système importées (déjà présentes avant Omega-Fire) peuvent être supprimées ici aussi — vérifie l'origine affichée avant de confirmer."],
        see_also=["3.1", "3.3"],
    ),
    "3.3": HelpEntry(
        summary="Liste toutes les règles détaillées, avec compteurs par backend.",
        usage=["Aucune saisie — une synchronisation depuis les backends actifs est faite automatiquement avant l'affichage."],
        consequences=[
            "Lecture seule, mais met à jour la base locale de règles avec "
            "l'état réel du noyau avant de l'afficher — ce que tu vois "
            "reflète toujours l'état courant, pas un instantané périmé.",
        ],
        see_also=["3.1", "3.2"],
    ),
    "3.4": HelpEntry(
        summary="Applique un profil de sécurité pré-défini (politique complète de règles) sur les backends disponibles.",
        usage=["L'état du profil actuellement actif (le cas échéant) est affiché avant de proposer les profils disponibles."],
        consequences=["Remplace la politique de filtrage active par celle du profil choisi, sur les deux backends simultanément."],
        see_also=["3.1", "3.3"],
    ),

    # ------------------------------------------------------------------
    # Section 4 — Gestion Fail2ban
    # ------------------------------------------------------------------

    "4": HelpEntry(
        summary=(
            "Gestion complète du démon fail2ban : consulter l'état des jails, "
            "bannir/débannir des IPs, transférer des IPs entre jails ou vers "
            "les backends firewall, créer/supprimer/vider des jails, exporter, "
            "vérifier la configuration, piloter le service."
        ),
        usage=[
            "Nécessite fail2ban installé et fail2ban-client accessible.",
            "Chaque sous-menu agit sur un jail précis ou sur l'ensemble des "
            "jails — vérifie bien le nom du jail affiché avant de valider une "
            "action large (Vider un jail, Vider tous les jails).",
        ],
        see_also=["4.1", "4.6", "4.7"],
    ),
    "4.1": HelpEntry(
        summary=(
            "Affiche un tableau récapitulatif de tous les jails configurés "
            "(nom, statut, nombre d'IPs bannies) puis propose un sous-menu "
            "d'analyse : lister les IPs d'un jail, de tous les jails, ou "
            "rechercher dans quel(s) jail(s) une IP précise est bannie."
        ),
        usage=[
            "Le scan est lancé automatiquement à l'ouverture. Ensuite, choisis "
            "[1] pour un jail précis (par son numéro dans le tableau), [2] "
            "pour tout lister, ou [3] pour rechercher une IP spécifique.",
        ],
        consequences=["Lecture seule : ne modifie rien."],
        mechanism=(
            "Lit directement la base de données de fail2ban et les fichiers "
            "de configuration pour rester rapide même avec beaucoup de "
            "jails, plutôt que d'interroger fail2ban-client un par un."
        ),
        see_also=["4.2"],
    ),
    "4.2": HelpEntry(
        summary="Bannit ou débannit une ou plusieurs IPs dans un jail précis que tu choisis.",
        usage=[
            "Sélectionne d'abord le jail cible, puis l'action (bannir/débannir), "
            "puis saisis une IP unique ou une liste.",
        ],
        consequences=[
            "Modifie l'état réel du jail immédiatement — l'IP est bloquée/débloquée "
            "dès validation, pas seulement enregistrée quelque part.",
        ],
        warnings=[
            "Une IP déjà bannie ne peut pas être bannie une seconde fois (et "
            "inversement pour le débannissement) — l'action échoue proprement "
            "dans ce cas plutôt que de prétendre avoir réussi.",
            "Vérifie le nom du jail affiché avant de valider : une IP bannie "
            "dans le mauvais jail ne protège pas la bonne surface.",
        ],
        see_also=["4.1", "4.3"],
    ),
    "4.3": HelpEntry(
        summary=(
            "Transfère des IPs entre jails fail2ban, vers/depuis les backends "
            "firewall (nftables/iptables), ou depuis/vers des fichiers."
        ),
        usage=[
            "Choisis d'abord une source (un jail, un backend, un fichier), "
            "puis une destination.",
            "Un récapitulatif (IPs déjà présentes / nouvelles / échecs) "
            "s'affiche après l'opération — vérifie-le avant de continuer.",
        ],
        consequences=[
            "Les IPs transférées vers un jail ou un backend sont réellement "
            "bannies à la destination, pas juste copiées dans une liste.",
        ],
        warnings=[
            "Le transfert vers nftables crée automatiquement la chaîne de "
            "blocage si elle n'existe pas encore — normal, pas une erreur "
            "si tu la vois apparaître pour la première fois.",
        ],
        see_also=["2.6", "2.7"],
    ),
    "4.4": HelpEntry(
        summary=(
            "Assistant de création d'un nouveau jail : mode sur-mesure (tu "
            "choisis chaque paramètre) ou mode preset (modèles pré-configurés "
            "pour Nginx, Apache, Caddy, SSH...)."
        ),
        usage=[
            "Mode sur-mesure : nom du jail, chemin de log à surveiller (liste "
            "épinglée modifiable directement depuis cet écran), ports "
            "concernés, nom du filtre, règles de bannissement (maxretry / "
            "findtime / bantime).",
            "Mode preset : choisis directement un modèle déjà réglé.",
        ],
        consequences=[
            "Écrit un fichier de configuration réel et recharge fail2ban — "
            "le jail devient actif immédiatement.",
            "Si le filtre demandé n'existe pas encore, un filtre générique "
            "(détection d'erreurs HTTP 400/401/403/404/500) est créé "
            "automatiquement.",
        ],
        warnings=[
            "Le filtre générique automatique est pensé pour des logs HTTP "
            "(Nginx/Apache/Caddy/Lighttpd) — appliqué à un log qui n'a pas "
            "ce format (ex: syslog), il ne détectera jamais rien.",
        ],
        see_also=["4.5", "4.9"],
    ),
    "4.5": HelpEntry(
        summary="Supprime un jail : arrête son suivi, retire sa configuration et recharge fail2ban.",
        usage=["Choisis le jail à supprimer et confirme."],
        consequences=[
            "Les IPs actuellement bannies dans ce jail sont libérées quand "
            "le jail est arrêté — consulte 4.1 avant si tu veux connaître son contenu.",
        ],
        warnings=["Irréversible sans recréer le jail depuis zéro (4.4)."],
        see_also=["4.4", "4.1"],
    ),
    "4.6": HelpEntry(
        summary="Débannit toutes les IPs d'un seul jail (celui que tu choisis), sans toucher aux autres.",
        usage=["Sélectionne le jail à vider et confirme."],
        consequences=["Toutes les IPs actuellement bannies dans ce jail précis sont débannies immédiatement."],
        warnings=[
            "Ne touche qu'au jail sélectionné — pour vider tous les jails "
            "d'un coup, utilise 4.7, pas cette option répétée plusieurs fois.",
        ],
        see_also=["4.7", "4.1"],
    ),
    "4.7": HelpEntry(
        summary="PURGE GÉNÉRALE : débannit toutes les IPs de tous les jails configurés, en une seule opération.",
        usage=["Une confirmation est demandée avant exécution — lis-la attentivement, l'opération touche l'ensemble des jails."],
        consequences=["Toutes les IPs actuellement bannies, dans tous les jails, sont débannies immédiatement. Non sélectif."],
        warnings=["Opération large et irréversible — pour ne vider qu'un seul jail, utilise 4.6."],
        see_also=["4.6"],
    ),
    "4.8": HelpEntry(
        summary=(
            "Exporte le contenu d'un jail (IPs bannies, configuration) dans "
            "un fichier : brut, JSON, TXT (réinjectable), ou HTML (rapport visuel)."
        ),
        usage=["Choisis le jail, puis le format de sortie."],
        consequences=["Lecture seule côté fail2ban — l'export ne modifie aucun jail."],
        see_also=["6.4"],
    ),
    "4.9": HelpEntry(
        summary=(
            "Teste la validité de la configuration fail2ban actuelle "
            "(jails, filtres) sans rien modifier ni redémarrer le service."
        ),
        usage=["Aucune saisie — lance directement le test."],
        consequences=["Lecture seule."],
        mechanism=(
            "Valide la configuration sur disque sans nécessiter que le "
            "démon soit déjà démarré."
        ),
        see_also=["4.4"],
    ),
    "4.10": HelpEntry(
        summary=(
            "Contrôle du service fail2ban lui-même (pas d'un jail précis) : "
            "statut, démarrage, arrêt, redémarrage, activation/désactivation "
            "au démarrage du système."
        ),
        usage=["Choisis l'action à effectuer sur le service."],
        consequences=[
            "Arrêter le service désactive toute la protection fail2ban le "
            "temps qu'il est arrêté, pas seulement un jail.",
        ],
        warnings=[
            "À utiliser avec précaution sur une machine en production — un "
            "arrêt du service, même bref, laisse temporairement passer les "
            "tentatives que fail2ban aurait bloquées.",
        ],
        see_also=["4.9"],
    ),

    # ------------------------------------------------------------------
    # Section 5 — Gestion des logs (Analyse & Maintenance)
    # ------------------------------------------------------------------

    "5": HelpEntry(
        summary=(
            "Analyse et maintenance des logs : consultation en direct, "
            "analyse de fréquence par IP, purge ciblée, rotation/backup, "
            "restauration, statistiques."
        ),
        usage=[
            "Les sources de logs et fichiers de blocklist proposés ici "
            "sont indépendants de ceux du menu 4.4 (fail2ban) — chaque "
            "contexte gère sa propre liste épinglée.",
        ],
        see_also=["5.1", "5.4"],
    ),
    "5.1": HelpEntry(
        summary=(
            "Visualise en direct les logs serveur (Nginx, Apache, Caddy, "
            "Lighttpd) ou le journal applicatif, avec analyse des requêtes "
            "HTTP en temps réel."
        ),
        usage=[
            "Choisis une source épinglée, l'historique récent, ou saisis "
            "un chemin/URL manuellement.",
            "Utilise [G] pour gérer les épingles (ajouter/retirer) et "
            "l'historique — un [0] Annuler est disponible à chaque étape.",
        ],
        consequences=["Lecture seule sur la source suivie — aucune modification du fichier ou du serveur observé."],
        mechanism=(
            "Les épingles et l'historique sont persistés (survivent à un "
            "redémarrage), contrairement à une ancienne version qui les "
            "stockait dans un dossier temporaire effacé à chaque relance."
        ),
        see_also=["5.2", "1.5"],
    ),
    "5.2": HelpEntry(
        summary="Analyse un fichier log ou une blocklist pour en extraire le classement des IPs les plus actives (Top N), sur une période choisie.",
        usage=["Choisis la source (épinglée, manuelle, ou ajout/retrait d'épingle), la période d'analyse (1h/1j/7j/personnalisée), puis le nombre N d'IPs à afficher."],
        consequences=["Lecture seule."],
        warnings=[
            "Les épingles de cet écran sont propres à 5.2/5.3/5.4/5.5 (en "
            "mémoire, non partagées avec celles de 5.1 ou du menu 4.4) — "
            "perdues au redémarrage de l'application.",
        ],
        see_also=["5.3", "1.6"],
    ),
    "5.3": HelpEntry(
        summary="Retire toutes les lignes contenant une IP précise dans un fichier source (log ou blocklist) — édition directe du fichier, pas un débannissement.",
        usage=["Choisis le fichier source, saisis l'IP à retirer, vérifie le récapitulatif (nombre d'occurrences trouvées) avant de confirmer."],
        consequences=["Modifie réellement le fichier — les lignes correspondantes sont supprimées, les autres conservées."],
        warnings=["N'agit que sur le fichier choisi, pas sur l'état réel du firewall/fail2ban — pour débannir une IP, utilise 2.3 ou 4.2."],
        see_also=["5.2", "2.3"],
    ),
    "5.4": HelpEntry(
        summary="Sauvegarde (backup) manuelle ou automatisée de fichiers logs/blocklists dans une archive.",
        usage=["Choisis la source à sauvegarder, puis le mode : sauvegarde immédiate, planification d'une automatisation récurrente, ou gestion des automatisations existantes."],
        consequences=[
            "Crée une archive réelle dans var/backups/. Une automatisation "
            "configurée continue de s'exécuter aux intervalles définis "
            "tant qu'elle n'est pas supprimée via [3].",
        ],
        see_also=["5.5", "5.6"],
    ),
    "5.5": HelpEntry(
        summary="Restaure une archive de logs précédemment sauvegardée (menu 5.4), immédiatement ou selon une automatisation planifiée.",
        usage=["Choisis le mode (restauration immédiate, planification, gestion des automatisations existantes), puis l'archive et la stratégie de restauration."],
        consequences=["Écrit réellement les fichiers restaurés — une restauration peut écraser des fichiers actuels selon le mode choisi."],
        warnings=["Vérifie la stratégie/mode proposés avant de confirmer."],
        see_also=["5.4", "5.6"],
    ),
    "5.6": HelpEntry(
        summary="Purge et nettoie les archives de backup (var/backups/) selon différents critères : ancienneté, quota, type (sauvegardes automatiques de sécurité), ou sélection manuelle.",
        usage=["Consulte d'abord les statistiques de stockage affichées (nombre d'archives, volume, espace disque libre), puis choisis le critère de purge."],
        consequences=["Suppression réelle et irréversible des archives ciblées — une confirmation avec aperçu des fichiers concernés est demandée avant exécution."],
        see_also=["5.4", "5.7"],
    ),
    "5.7": HelpEntry(
        summary="Nettoyage avancé de l'espace de stockage interne d'Omega-Fire (logs, cache, exports, backups, ou tout var/), filtré par âge ou taille.",
        usage=["Choisis le(s) dossier(s) cible(s), puis les critères de filtrage, et vérifie l'aperçu des fichiers concernés avant de confirmer."],
        consequences=["Suppression réelle et irréversible des fichiers correspondants."],
        warnings=[
            "app.log et audit.log sont toujours exclus de ce nettoyage, "
            "même si le dossier logs/ est ciblé — ce sont des fichiers "
            "actifs en écriture continue ; utilise 1.5 ou 7.3 pour les "
            "gérer spécifiquement.",
        ],
        see_also=["5.6", "1.5", "7.3"],
    ),
    "5.8": HelpEntry(
        summary="Affiche un tableau de bord de statistiques sur les logs (volumes, tendances).",
        usage=["Aucune saisie requise."],
        consequences=["Lecture seule."],
        see_also=["8.3", "8.4"],
    ),
    "5.9": HelpEntry(
        summary=(
            "Sélectionne un ou plusieurs fichiers de logs serveur pour "
            "analyse via lnav — raccourci vers la même action que 8.6, "
            "accessible directement depuis la section Logs."
        ),
        usage=[
            "Numéros séparés par des virgules pour choisir plusieurs sources "
            "épinglées/historique à la fois (ex: 1,3).",
            "[M] pour un ou plusieurs chemins/URL saisis à la main (mêmes "
            "virgules), [G] pour gérer les épingles — un [0]/Entrée annule "
            "à chaque étape.",
        ],
        consequences=["Lecture seule sur les fichiers sélectionnés — aucune modification."],
        mechanism=(
            "Même écran et mêmes épingles/historique que 8.6 — atteignable "
            "depuis deux emplacements du menu."
        ),
        see_also=["8.6"],
    ),

    # ------------------------------------------------------------------
    # Section 6 — Exports & Rapports (Audit centralisé)
    # ------------------------------------------------------------------

    "6": HelpEntry(
        summary="Centralise les exports et rapports : blacklist complète, règles de pare-feu, audit système complet, statistiques fail2ban.",
        usage=["Chaque export propose un format (JSON/TXT/HTML selon le rapport) et un chemin de destination modifiable."],
        see_also=["6.1", "6.3"],
    ),
    "6.1": HelpEntry(
        summary="Exporte la blacklist complète (IPs bannies) depuis un fichier source choisi, au format JSON, TXT ou HTML.",
        usage=["Choisis la source (épinglée, manuelle, ou gestion des épingles), puis le format de sortie."],
        consequences=["Écrit un fichier réel — lecture seule côté bannissement."],
        see_also=["2.8", "2.5"],
    ),
    "6.2": HelpEntry(
        summary="Exporte les règles de pare-feu nftables/iptables (fail2ban a son propre export, voir 4.8) — toutes, actives seulement, Omega-Fire uniquement, ou système importées uniquement.",
        usage=["Choisis le contenu à exporter, puis le format (JSON/HTML/TXT)."],
        consequences=["Écrit un fichier réel — lecture seule côté règles."],
        see_also=["3.3", "4.8"],
    ),
    "6.3": HelpEntry(
        summary="Génère un rapport d'audit complet : état système, historique, top IPs, en un seul document.",
        usage=["Choisis le format (TXT ou HTML), valide le chemin de destination proposé ou saisis-en un autre."],
        consequences=["Écrit un fichier réel — lecture seule côté système."],
        see_also=["1.7", "7.3"],
    ),
    "6.4": HelpEntry(
        summary="Exporte un rapport détaillé sur fail2ban (jails et bans), au format TXT ou HTML.",
        usage=["Choisis le format, valide ou modifie le chemin de destination proposé."],
        consequences=["Écrit un fichier réel — lecture seule côté fail2ban."],
        see_also=["4.8", "4.1"],
    ),

    # ------------------------------------------------------------------
    # Section 7 — Système & Persistance (État & Sauvegarde)
    # ------------------------------------------------------------------

    "7": HelpEntry(
        summary=(
            "Gestion de l'état interne d'Omega-Fire : sauvegarde/"
            "restauration complète (règles + IPs bannies), historique "
            "d'audit, rechargement de la configuration."
        ),
        usage=["Distinct du menu 5 (qui gère les fichiers de logs) — ici, c'est l'état du firewall/fail2ban lui-même qui est sauvegardé/restauré."],
        see_also=["7.1", "7.2"],
    ),
    "7.1": HelpEntry(
        summary="Capture un instantané (snapshot) complet de l'état actuel : règles firewall et IPs bannies (nftables/iptables/fail2ban).",
        usage=["Une description optionnelle peut être ajoutée pour identifier facilement le snapshot plus tard."],
        consequences=["Crée une archive réelle — n'affecte aucun état actuel, uniquement une sauvegarde."],
        see_also=["7.2", "5.4"],
    ),
    "7.2": HelpEntry(
        summary="Restaure un snapshot précédemment sauvegardé (menu 7.1).",
        usage=["Sélectionne le snapshot à restaurer dans la liste paginée, puis confirme."],
        consequences=[
            "Les règles firewall actuellement gérées par Omega-Fire sont "
            "RETIRÉES puis REMPLACÉES par celles du snapshot.",
            "Les IPs bannies du snapshot sont AJOUTÉES — rien n'est retiré "
            "des bannissements actuels.",
            "Les jails fail2ban ne sont PAS restaurées automatiquement "
            "(information seulement).",
            "Les règles/IPs gérées par d'autres outils (UFW, etc.) ne "
            "sont jamais touchées.",
        ],
        warnings=["Opération significative sur les règles firewall — vérifie bien le snapshot choisi avant de confirmer."],
        see_also=["7.1", "4.4"],
    ),
    "7.3": HelpEntry(
        summary="Consulte ou purge l'historique d'audit (le journal des actions effectuées par Omega-Fire, avec succès/échec) — distinct du journal applicatif technique (1.5).",
        usage=["Recherche par mot-clé possible. Le sous-menu de gestion permet de purger les entrées anciennes."],
        consequences=["La consultation est en lecture seule. La purge supprime réellement des entrées, irréversible."],
        see_also=["1.5", "6.3"],
    ),
    "7.4": HelpEntry(
        summary="Recharge la configuration système sans redémarrer l'application.",
        usage=["Aucune saisie — lance directement le rechargement."],
        consequences=[
            "Même mécanisme que 1.3 (re-scan complet des sondes système "
            "et de la configuration), avec un affichage minimal plutôt "
            "que le détail diagnostic complet.",
        ],
        see_also=["1.3"],
    ),

    # ------------------------------------------------------------------
    # Section 8 — Monitoring & Statistiques
    # ------------------------------------------------------------------

    "8": HelpEntry(
        summary="Vue d'ensemble de l'activité réseau en temps réel et sur la durée : tableau de bord live, connexions actives, tendances 7/30 jours.",
        see_also=["8.1", "8.3"],
    ),
    "8.1": HelpEntry(
        summary="Tableau de bord en temps réel combinant statistiques firewall, monitoring, audit et logs — rafraîchi automatiquement.",
        usage=["Aucune saisie au lancement — consulte l'écran, quitte avec la touche indiquée à l'écran."],
        consequences=["Lecture seule."],
        see_also=["8.2", "5.8"],
    ),
    "8.2": HelpEntry(
        summary="Affiche les connexions réseau actives (conntrack) : protocole, état, adresses, ports.",
        usage=["Filtre par protocole et/ou état une fois la liste initiale affichée, limite le nombre d'entrées affichées."],
        consequences=["Lecture seule."],
        see_also=["8.1"],
    ),
    "8.3": HelpEntry(
        summary="Rapport statistique sur les 7 derniers jours (tendances, graphiques).",
        usage=["Aucune saisie requise."],
        consequences=["Lecture seule."],
        see_also=["8.4", "5.8"],
    ),
    "8.4": HelpEntry(
        summary="Rapport statistique sur les 30 derniers jours — vue macro, même mécanisme que 8.3 avec une fenêtre plus large.",
        usage=["Aucune saisie requise."],
        consequences=["Lecture seule."],
        see_also=["8.3"],
    ),
    "8.5": HelpEntry(
        summary=(
            "Visualise en direct les logs serveur (Nginx, Apache, Caddy, "
            "Lighttpd) ou le journal applicatif, avec analyse des requêtes "
            "HTTP en temps réel — raccourci vers la même action que 5.1, "
            "accessible directement depuis la section Monitoring."
        ),
        usage=[
            "Choisis une source épinglée, l'historique récent, ou saisis "
            "un chemin/URL manuellement.",
            "Utilise [G] pour gérer les épingles (ajouter/retirer) et "
            "l'historique — un [0] Annuler est disponible à chaque étape.",
        ],
        consequences=["Lecture seule sur la source suivie — aucune modification du fichier ou du serveur observé."],
        mechanism=(
            "Les épingles et l'historique sont persistés (survivent à un "
            "redémarrage) et partagés avec 5.1 — c'est le même écran, "
            "atteignable depuis deux emplacements du menu."
        ),
        see_also=["5.1", "8.1"],
    ),
    "8.6": HelpEntry(
        summary=(
            "Sélectionne un ou plusieurs fichiers de logs serveur (Nginx, "
            "Apache, Lighttpd, Caddy) pour analyse via lnav — contrairement "
            "à 5.1/8.5, plusieurs fichiers peuvent être choisis à la fois : "
            "lnav les fusionne automatiquement en une seule vue chronologique."
        ),
        usage=[
            "Numéros séparés par des virgules pour choisir plusieurs sources "
            "épinglées/historique à la fois (ex: 1,3).",
            "[M] pour un ou plusieurs chemins saisis à la main (mêmes "
            "virgules), [G] pour gérer les épingles — un [0]/Entrée annule "
            "à chaque étape.",
        ],
        consequences=["Lecture seule sur les fichiers sélectionnés — aucune modification."],
        mechanism=(
            "Épingles et historique propres à 8.6 (séparés de ceux de "
            "5.1/8.5, mêmes mécanismes de stockage). lnav s'ouvre ensuite "
            "en plein écran, encapsulé dans un header/footer Omega-Fire — "
            "Ctrl-Q pour quitter, Ctrl-C pour copier la ligne courante, "
            "[t] pour changer de thème."
        ),
        see_also=["5.1", "5.9", "8.5"],
    ),

    # ------------------------------------------------------------------
    # Section 0 — Quitter l'application
    # ------------------------------------------------------------------

    "0": HelpEntry(
        summary="Ferme Omega-Fire, avec une confirmation avant de quitter réellement.",
        usage=["Réponds 'o' pour confirmer la fermeture, ou toute autre réponse pour rester dans l'application."],
        consequences=["Aucune sauvegarde automatique n'est déclenchée par cette confirmation — pense à utiliser 7.1 avant de quitter si tu veux capturer l'état actuel."],
        see_also=["7.1"],
    ),
}


def get_help_entry(node_id: str) -> Optional[HelpEntry]:
    """Retourne le contenu d'aide détaillé pour un nœud de menu, si écrit.

    Args:
        node_id: Id du nœud tel que défini dans menu_builder.py (ex: "4.2").

    Returns:
        La HelpEntry correspondante, ou None si aucun contenu détaillé
        n'a encore été rédigé pour ce nœud — l'appelant doit alors se
        replier sur le label/description court déjà disponible dans le
        menu (menu_builder.py), jamais sur un overlay vide.
    """
    return HELP_ENTRIES.get(node_id)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Centralise le contenu d'aide contextuelle détaillé du TUI (touche
#   [a]) : un guide d'utilisation par nœud de menu (section ou action),
#   au-delà du simple label/description déjà présent dans
#   menu_builder.py.
#
# Pourquoi dans interfaces/cli/ (charte) :
# - L'aide fait partie de l'interface utilisateur, pas du métier.
# - Ce module ne contient aucune logique métier ni I/O système.
# - Aucun rendu Rich ici — juste des données (HelpEntry), le style est
#   appliqué par app.py::_build_help_body() via theme_registry.
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier
# ❌ Pas d'appels système
# ❌ Pas de dépendance vers infrastructure/ ou domain/
# ❌ Pas de rendu Rich (juste du texte structuré)
#
# Ce qu'il contient :
# - HelpEntry : structure d'une entrée d'aide (summary/usage/
#   consequences/warnings/mechanism/see_also)
# - HELP_ENTRIES : dict {id_du_nœud: HelpEntry} — couverture complète :
#   les 61 nœuds réels du menu (sections 1-8, section 0, tous les
#   sous-menus dont les alias 2.10 → même action que 4.3 et 8.5 → même
#   action que 5.1, ajoutés le 2026-08-17, référentiel §46), vérifiée par
#   test (aucun id manquant, aucun id
#   fantôme) dans tests/unit/interfaces/cli/test_help_text.py
# - get_help_entry() : lookup sûr (None si pas encore rédigé)
#
# Points clés :
# - Priorité au guide d'utilisation (usage/consequences/warnings) — le
#   champ mechanism (transparence technique) est secondaire, renseigné
#   seulement quand il apporte une vraie clarté.
# - Un id de nœud sans entrée n'est pas une erreur : l'appelant se
#   replie sur le label/description court du menu.
#
# Comment il est utilisé :
# - interfaces/cli/app.py::_build_help_body() l'interroge via
#   get_help_entry(node.id) pour l'overlay d'aide contextuelle (touche [a]),
#   basé sur le nœud actuellement surligné dans la navigation.
#---------------------------------------------------------------------->
