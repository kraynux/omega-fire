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
# Textes MARQUES (N_), traduits a l'affichage (screens/_base.py::format_help_entry, guide) :
# traduits ici a l'import, ils resteraient figes dans la langue de l'interface au demarrage et
# l'export du guide ne pourrait pas suivre la « Langue des exports » (retour utilisateur
# 2026-10-28). --legacy-cli affiche le texte source, donc le francais.
from omega_fire.shared.i18n import N_


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
            N_("Vue globale des backends détectés (nftables, iptables, fail2ban, "
            "systemd...) et de leur état : disponible, dégradé ou manquant. "
            "Point de départ pour comprendre pourquoi une fonctionnalité est "
            "grisée ailleurs dans le menu.")
        ),
        usage=[
            N_("Consulte 1.1 pour la vue d'ensemble, 1.3 si l'état affiché "
            "semble périmé (après une installation ou un changement système)."),
        ],
        see_also=["1.1", "1.3"],
    ),
    "1.1": HelpEntry(
        summary=(
            N_("Liste toutes les capacités détectées par le dernier scan "
            "système : quels backends/services sont disponibles, dégradés "
            "ou manquants.")
        ),
        usage=[
            N_("Aucune saisie requise — affiche directement le registre actuel."),
            N_("Suite omega : omega-serv (instances détectées et en service ; « dégradé » si aucune "
               "ne tourne), omega-waf (extra magnet activé dans une instance) et omega-jail (jails "
               "installés dans /etc/fail2ban/jail.d)."),
        ],
        consequences=[
            N_("Lecture seule : ne relance aucun scan, affiche l'état déjà en "
            "mémoire (voir 1.3 pour rafraîchir)."),
        ],
        warnings=[
            N_("Si l'appli vient de démarrer sur une machine où un service a "
            "changé d'état entre-temps, l'information peut être obsolète "
            "— relance un scan (1.3) si besoin."),
        ],
        see_also=["1.2", "1.3"],
    ),
    "1.2": HelpEntry(
        summary=(
            N_("Affiche le détail complet d'une capacité précise (ex: nftables, "
            "fail2ban) : statut, raison si dégradée/manquante, informations "
            "de diagnostic.")
        ),
        usage=[
            N_("Sélectionne par numéro, ou saisis directement l'identifiant de "
            "la capacité (visible via 1.1)."),
        ],
        consequences=[N_("Lecture seule.")],
        see_also=["1.1"],
    ),
    "1.3": HelpEntry(
        summary=(
            N_("Relance les sondes système (nftables, iptables, fail2ban, "
            "systemd...) pour mettre à jour le registre des capacités.")
        ),
        usage=[N_("Aucune saisie — lance directement le scan.")],
        consequences=[
            N_("Met à jour le registre en mémoire — peut changer ce qui est "
            "grisé/disponible ailleurs dans les menus. Une capacité "
            "redevenue disponible débloque immédiatement les actions qui "
            "en dépendent, sans redémarrer l'application."),
        ],
        warnings=[
            N_("Des erreurs partielles sont possibles (ex: une sonde échoue) "
            "sans faire échouer tout le scan — le résumé affiché indique "
            "combien d'erreurs ont eu lieu, à vérifier si le nombre de "
            "composants disponibles semble anormalement bas."),
        ],
        see_also=["1.1", "1.4"],
    ),
    "1.4": HelpEntry(
        summary=(
            N_("Affiche les erreurs et dégradations récentes détectées sur le "
            "système (capacités manquantes/dégradées et pourquoi).")
        ),
        usage=[N_("Aucune saisie requise.")],
        consequences=[N_("Lecture seule.")],
        see_also=["1.1", "1.6"],
    ),
    "1.5": HelpEntry(
        summary=(
            N_("Consulte ou purge le journal interne d'Omega-Fire (actions "
            "effectuées, erreurs, avertissements) — pas les logs système "
            "(Nginx, auth.log...), voir la section 5 pour ceux-là.")
        ),
        usage=[
            N_("Mode consultation : choisis un nombre de lignes (50/100/"
            "personnalisé), un mot-clé optionnel, puis navigue page par "
            "page (Entrée pour continuer, q pour arrêter)."),
            N_("Mode gestion/purge : supprime les entrées de plus de 30/120 "
            "jours, avant une date précise, ou les N plus anciennes — une "
            "confirmation est toujours demandée avant suppression."),
        ],
        consequences=[
            N_("La consultation est en lecture seule. La purge supprime "
            "réellement des entrées du journal, de façon irréversible."),
        ],
        warnings=[
            N_("Erreurs et alertes critiques sont mises en évidence par "
            "couleur — pour chercher un problème précis, filtre par "
            "mot-clé plutôt que de tout parcourir."),
        ],
        see_also=["1.4", "1.6"],
    ),
    "1.6": HelpEntry(
        summary=(
            N_("Recherche un mot-clé (IP, nom de backend, message d'erreur...) "
            "à la fois dans les diagnostics système et dans le journal "
            "applicatif, en une seule requête.")
        ),
        usage=[
            N_("Saisis un mot-clé — la recherche combine automatiquement les "
            "deux sources (diagnostics + journal), jusqu'à 15 résultats du "
            "journal affichés."),
        ],
        consequences=[N_("Lecture seule.")],
        see_also=["1.4", "1.5"],
    ),
    "1.7": HelpEntry(
        summary=(
            N_("Exporte un rapport de l'état système et des diagnostics dans "
            "un fichier : JSON (données brutes), HTML (rapport visuel, par "
            "défaut) ou TXT (texte brut).")
        ),
        usage=[
            N_("Choisis le format, puis valide le chemin de destination "
            "proposé ou saisis-en un autre."),
        ],
        consequences=[
            N_("Écrit un fichier réel sur disque (par défaut dans le dossier "
            "d'exports) — ne modifie rien côté système."),
        ],
        see_also=["6.3"],
    ),

    # ------------------------------------------------------------------
    # Section 2 — Gestion des IPs (Blacklist unifiée NFt-IPt)
    # ------------------------------------------------------------------

    "2": HelpEntry(
        summary=(
            N_("Gestion unifiée des IPs bannies à travers tous les backends "
            "détectés (nftables, iptables, fail2ban) : bannir, débannir, "
            "lister, synchroniser, importer/exporter, purger.")
        ),
        usage=[
            N_("La plupart des actions agissent par défaut sur tous les "
            "backends disponibles simultanément — cibler un seul backend "
            "reste possible mais est pensé pour du diagnostic, pas un "
            "usage courant."),
        ],
        see_also=["2.1", "2.6", "2.9"],
    ),
    "2.1": HelpEntry(
        summary=N_("Bannit une seule IP, sur tous les backends détectés par défaut (nftables/iptables/fail2ban)."),
        usage=[
            N_("Saisis l'IP, choisis les backends cibles (tous par défaut, ou "
            "un seul pour diagnostic), ajoute un commentaire optionnel, "
            "puis confirme."),
        ],
        consequences=[
            N_("L'IP est bloquée immédiatement sur chaque backend ciblé. Un "
            "rapport par backend indique succès, doublon (déjà bannie) ou échec."),
        ],
        warnings=[
            N_("Cibler un seul backend est un mode diagnostic : si un autre "
            "backend est actif, l'IP pourrait rester accessible via ce dernier."),
        ],
        see_also=["2.3", "2.2"],
    ),
    "2.2": HelpEntry(
        summary=(
            N_("Bannit une liste d'IPs en une fois, depuis une saisie manuelle "
            "ou un fichier (défaut, fichier fail2ban par défaut, dossier "
            "var/blocklist/, fichier épinglé, ou chemin personnalisé).")
        ),
        usage=[N_("Choisis la méthode d'approvisionnement, puis valide la liste d'IPs extraite avant le bannissement effectif.")],
        consequences=[N_("Chaque IP valide extraite est bannie sur les backends ciblés, comme pour 2.1 mais en masse.")],
        see_also=["2.1", "2.7"],
    ),
    "2.3": HelpEntry(
        summary=N_("Débannit une seule IP, sur tous les backends détectés par défaut."),
        usage=[N_("Même déroulé que 2.1, en sens inverse : saisis l'IP, choisis les backends, confirme.")],
        consequences=[N_("L'IP redevient accessible immédiatement sur chaque backend ciblé.")],
        see_also=["2.1", "2.4"],
    ),
    "2.4": HelpEntry(
        summary=N_("Débannit une liste d'IPs en une fois — même logique d'approvisionnement que 2.2."),
        usage=[N_("Choisis la méthode d'approvisionnement, valide la liste, confirme.")],
        consequences=[N_("Chaque IP de la liste est débannie sur les backends ciblés.")],
        see_also=["2.3", "2.2"],
    ),
    "2.5": HelpEntry(
        summary=N_("Liste toutes les IPs actuellement bannies, avec leur backend d'origine et leur commentaire/source."),
        usage=[N_("Choisis un backend précis ou consulte tous les backends d'un coup.")],
        consequences=[N_("Lecture seule.")],
        see_also=["2.1", "2.9"],
    ),
    "2.6": HelpEntry(
        summary=N_("Réconcilie les backends entre eux : ajoute sur chaque backend cible les IPs déjà bannies ailleurs mais manquantes chez lui."),
        usage=[N_("Choisis les backends à synchroniser (tous par défaut).")],
        consequences=[N_("Additif uniquement : ne retire jamais une IP, ajoute seulement celles manquantes pour aligner les backends.")],
        see_also=["2.5", "2.1"],
    ),
    "2.7": HelpEntry(
        summary=(
            N_("Gestion complète des fichiers de blocklist dans var/blocklist/ : "
            "créer, importer depuis un autre dossier, éditer IP par IP, "
            "renommer, supprimer, et bannir directement le contenu d'un fichier.")
        ),
        usage=[N_("Sélectionne un fichier existant pour l'éditer, ou utilise [I]/[N] pour en importer/créer un nouveau.")],
        consequences=[
            N_("Les modifications (ajout/retrait d'IP, renommage, suppression) "
            "touchent le fichier réel sur disque — bannir depuis un fichier "
            "ici bannit réellement les IPs valides qu'il contient."),
        ],
        see_also=["2.2", "2.8"],
    ),
    "2.8": HelpEntry(
        summary=N_("Exporte les IPs actuellement bannies vers un fichier (défaut, backup horodaté, fichier existant, récent, chemin manuel, ou fichier épinglé)."),
        usage=[N_("Choisis la destination et le mode d'écriture (écraser ou ajouter au fichier existant).")],
        consequences=[N_("Écrit un fichier réel — ne modifie aucun état de bannissement.")],
        see_also=["2.5", "2.7"],
    ),
    "2.9": HelpEntry(
        summary=N_("PURGE : débannit toutes les IPs sur les backends ciblés (tous par défaut)."),
        usage=[N_("Une confirmation explicite est demandée avant exécution.")],
        consequences=[
            N_("Toutes les IPs actuellement bannies sur les backends ciblés "
            "sont débannies. Les règles de filtrage principales (ports "
            "autorisés, accès SSH...) restent intactes — seule la liste "
            "des IPs bannies est vidée."),
        ],
        warnings=[N_("Cibler un seul backend est un mode diagnostic — une IP bannie ailleurs resterait bloquée malgré cette purge.")],
        see_also=["2.5", "4.7"],
    ),
    "2.10": HelpEntry(
        summary=(
            N_("Transfère des IPs entre jails fail2ban, vers/depuis les backends "
            "firewall (nftables/iptables), ou depuis/vers des fichiers — "
            "raccourci vers la même action que 4.3, accessible directement "
            "depuis la section IPs.")
        ),
        usage=[
            N_("Choisis d'abord une source (un jail, un backend, un fichier), "
            "puis une destination."),
            N_("Un récapitulatif (IPs déjà présentes / nouvelles / échecs) "
            "s'affiche après l'opération — vérifie-le avant de continuer."),
        ],
        consequences=[
            N_("Les IPs transférées vers un jail ou un backend sont réellement "
            "bannies à la destination, pas juste copiées dans une liste."),
        ],
        warnings=[
            N_("Le transfert vers nftables crée automatiquement la chaîne de "
            "blocage si elle n'existe pas encore — normal, pas une erreur "
            "si tu la vois apparaître pour la première fois."),
        ],
        see_also=["4.3", "2.6"],
    ),

    # ------------------------------------------------------------------
    # Section 3 — Gestion des règles (Politiques / Filtres)
    # ------------------------------------------------------------------

    "3": HelpEntry(
        summary=N_("Gestion fine des règles de pare-feu (ports, protocoles, réseaux) sur nftables/iptables, indépendamment du bannissement d'IP (section 2)."),
        usage=[
            N_("Une règle est en général créée sur les deux backends "
            "disponibles simultanément — un profil restrictif actif sur "
            "un seul backend peut annuler l'effet d'une règle posée sur "
            "l'autre (voir 3.1)."),
        ],
        see_also=["3.1", "3.4"],
    ),
    "3.1": HelpEntry(
        summary=N_("Assistant pas-à-pas pour créer une règle avancée (source, port, protocole, action) sur un ou plusieurs backends."),
        usage=[N_("Réponds aux questions successives : backend(s) cible(s), puis les paramètres de la règle.")],
        consequences=[N_("La règle est appliquée immédiatement sur les backends ciblés et enregistrée en base pour réapparaître dans 3.2/3.3.")],
        warnings=[
            N_("Deux backends actifs au même point de contrôle fonctionnent "
            "en INTERSECTION, pas en union : créer une règle ACCEPT sur un "
            "seul backend ne suffit pas si l'autre bloque toujours ce "
            "trafic — il reste refusé tant que les deux ne l'autorisent "
            "pas. Cibler un seul backend est réservé au diagnostic."),
        ],
        see_also=["3.3", "3.4"],
    ),
    "3.2": HelpEntry(
        summary=N_("Supprime une ou plusieurs règles, sélectionnées par ID (règles Omega-Fire créées via 3.1, règles système importées, ou les deux) — ou nettoie en un clic toutes les règles INACTIVES."),
        usage=[
            N_("Filtre l'affichage (Omega-Fire / Système / Toutes), puis saisis un ou plusieurs IDs séparés par une virgule."),
            N_("Si des règles inactives existent, une option [4] apparaît pour toutes les supprimer d'un coup (une seule confirmation, sans sélection ID par ID) — utile quand la majorité des règles importées du système sont inactives."),
            N_("« Nettoyer et resynchroniser la base » : remet la liste des règles d'accord avec ce que le pare-feu contient vraiment. Un aperçu s'affiche d'abord (lignes gardées, doublons, lignes absentes du noyau, lignes d'un backend absent de la machine, règles du noyau à importer) ; les lignes qui seront retirées apparaissent dans le tableau."),
        ],
        consequences=[
            N_("Suppression réelle et immédiate sur le(s) backend(s) où la règle est active."),
            N_("Nettoyer et resynchroniser : seule la base d'Omega-Fire change, aucune règle n'est ajoutée ni retirée du pare-feu. La base est sauvegardée avant, dans var/backups/db/."),
        ],
        warnings=[
            N_("Les règles système importées (déjà présentes avant Omega-Fire) peuvent être supprimées ici aussi — vérifie l'origine affichée avant de confirmer."),
            N_("Une règle posée par un autre outil (UFW, Tailscale, Docker…, nom affiché dans la colonne Origine) n'est pas supprimée ici : elle se gère avec son outil, qui la recréerait ou deviendrait incohérent."),
            N_("Nettoyer et resynchroniser : un backend illisible (droits, erreur) n'est jamais touché ; un backend dont la commande est absente de la machine voit ses lignes retirées."),
        ],
        see_also=["3.1", "3.3"],
    ),
    "3.3": HelpEntry(
        summary=N_("Liste toutes les règles détaillées, avec compteurs par backend."),
        usage=[N_("Aucune saisie — une synchronisation depuis les backends actifs est faite automatiquement avant l'affichage.")],
        consequences=[
            N_("Lecture seule, mais met à jour la base locale de règles avec "
            "l'état réel du noyau avant de l'afficher — ce que tu vois "
            "reflète toujours l'état courant, pas un instantané périmé."),
            N_("Colonne Origine : OMEGA (créée par Omega-Fire), SYSTEME (présente avant, ou ajoutée à la main), ou le nom de l'outil qui l'a posée (UFW, Tailscale, Docker, Fail2Ban, firewalld…). Les règles d'autres outils sont affichées pour information : Omega-Fire ne les modifie pas."),
        ],
        see_also=["3.1", "3.2"],
    ),
    "3.4": HelpEntry(
        summary=N_("Applique un profil de sécurité pré-défini (politique complète de règles) sur les backends disponibles."),
        usage=[
            N_("L'état du profil actuellement actif (le cas échéant) est affiché avant de proposer les profils disponibles."),
            N_("Si des règles d'autres outils (UFW, Tailscale, Docker…) sont présentes sur iptables / ip6tables, tu choisis : appliquer sur tous les backends, appliquer seulement sur nftables, ou annuler. Le message indique combien de règles de chaque outil sont concernées."),
        ],
        consequences=[
            N_("Remplace la politique de filtrage active par celle du profil choisi, sur tous les backends disponibles en même temps (nftables, iptables, ip6tables)."),
            N_("Réappliquer le même profil ne crée pas de doublons : chaque backend est vidé puis reconstruit, et la base d'Omega-Fire est remise d'accord avec lui."),
            N_("nftables : seule la table d'Omega-Fire (inet filter) est vidée ; les tables des autres outils ne sont pas touchées."),
            N_("iptables / ip6tables : toute la table filter est vidée (iptables -F, -X), y compris les chaînes et les règles des autres outils (ufw-*, ts-*…). La politique par défaut d'INPUT / OUTPUT / FORWARD devient celle du profil."),
            N_("Une sauvegarde automatique (snapshot) est tentée avant application ; 7.2 peut la restaurer."),
        ],
        warnings=[
            N_("Tous les backends, avec UFW ou Tailscale : leurs règles disparaissent du noyau jusqu'au prochain rechargement de l'outil (« ufw reload », redémarrage du service Tailscale ou de la machine). Entre-temps, seul le profil d'Omega-Fire protège la machine — et un accès autorisé par UFW (ex. Samba, VNC limités au réseau local) peut être bloqué."),
            N_("Seulement nftables : les règles des autres outils restent en place. Les deux pare-feu s'appliquent alors ensemble : un paquet doit être accepté par les deux. Un profil strict peut bloquer un accès qu'UFW autorise, et inversement."),
            N_("La restauration 7.2 d'un snapshot ne repose pas les règles des autres outils : c'est à l'outil lui-même de les recréer."),
        ],
        see_also=["3.1", "3.3", "3.5", "7.2"],
    ),
    "3.5": HelpEntry(
        summary=N_("Gestion des tables : diagnostic des tables et des politiques, initialisation de la table nftables d'Omega-Fire, remise des politiques à ACCEPT, vidage d'un backend ou de tous, suppression de la table nftables (avancé)."),
        usage=[
            N_("Le diagnostic s'affiche toujours en haut ; choisis ensuite l'action, et le backend quand elle en demande un."),
            N_("Politiques différentes selon les backends : le noyau fait passer chaque paquet par toutes les chaînes branchées au même endroit (table nftables d'Omega-Fire et tables d'UFW via iptables-nft) ; un paquet doit être accepté par chacune, la politique la plus stricte l'emporte. « nftables ACCEPT, iptables DROP » n'ouvre donc rien : c'est iptables qui décide."),
            N_("Pour chaque politique DROP, la cause est indiquée : outil qui l'a posée (UFW…, rien à faire), profil Omega-Fire actif (rien à faire), politique orpheline sans aucune règle (affichée en jaune : tout est bloqué sur ce backend, remède « Remettre les politiques à ACCEPT » ou appliquer un profil), ou politique DROP avec des règles mais sans profil (vérifier en 3.3)."),
            N_("Initialiser la table nftables crée ses chaînes en ACCEPT : sur une machine filtrée par UFW, une différence de politique apparaît alors, c'est normal."),
            N_("Si des règles d'autres outils (UFW, Tailscale, Docker…) sont présentes sur iptables / ip6tables, la confirmation l'indique, avec le nombre de règles par outil ; pour « vider tous les backends », tu peux choisir de ne vider que nftables."),
        ],
        consequences=[
            N_("Vider nftables : seule la table d'Omega-Fire est vidée."),
            N_("Vider iptables / ip6tables : toute la table filter est vidée (iptables -F), règles des autres outils comprises ; leurs chaînes restent, vides. La politique par défaut ne change pas."),
            N_("Remettre les politiques à ACCEPT : input, output et forward acceptent tout paquet qu'aucune règle ne bloque explicitement."),
        ],
        warnings=[
            N_("Vider iptables avec UFW : si la politique d'INPUT est DROP (cas d'UFW), plus aucun paquet entrant n'est accepté sur ce backend, connexions déjà ouvertes comprises — risque de perdre un accès distant (SSH). « ufw reload » repose les règles d'UFW."),
            N_("Remettre les politiques à ACCEPT avec UFW : UFW compte sur INPUT en DROP ; à ACCEPT, la machine accepte tout ce qu'UFW n'interdit pas explicitement. « ufw reload » rétablit sa politique."),
            N_("Les deux actions combinées (vider puis ACCEPT) laissent la machine sans aucun filtrage sur ce backend."),
        ],
        see_also=["3.4", "3.3"],
    ),

    # ------------------------------------------------------------------
    # Section 4 — Gestion Fail2ban
    # ------------------------------------------------------------------

    "4": HelpEntry(
        summary=(
            N_("Gestion complète du démon fail2ban : consulter l'état des jails, "
            "bannir/débannir des IPs, transférer des IPs entre jails ou vers "
            "les backends firewall, créer/supprimer/vider des jails, exporter, "
            "vérifier la configuration, piloter le service.")
        ),
        usage=[
            N_("Nécessite fail2ban installé et fail2ban-client accessible."),
            N_("Chaque sous-menu agit sur un jail précis ou sur l'ensemble des "
            "jails — vérifie bien le nom du jail affiché avant de valider une "
            "action large (Vider un jail, Vider tous les jails)."),
        ],
        see_also=["4.1", "4.6", "4.7"],
    ),
    "4.1": HelpEntry(
        summary=(
            N_("Affiche un tableau récapitulatif de tous les jails configurés "
            "(nom, statut, nombre d'IPs bannies) puis propose un sous-menu "
            "d'analyse : lister les IPs d'un jail, de tous les jails, ou "
            "rechercher dans quel(s) jail(s) une IP précise est bannie.")
        ),
        usage=[
            N_("Le scan est lancé automatiquement à l'ouverture. Ensuite, choisis "
            "[1] pour un jail précis (par son numéro dans le tableau), [2] "
            "pour tout lister, ou [3] pour rechercher une IP spécifique."),
        ],
        consequences=[N_("Lecture seule : ne modifie rien. La colonne Origine indique qui a défini le jail : Omega-Fire (4.4), omega-jail, la configuration principale de fail2ban (jail.local / jail.conf) ou un autre fichier.")],
        mechanism=(
            N_("Lit directement la base de données de fail2ban et les fichiers "
            "de configuration pour rester rapide même avec beaucoup de "
            "jails, plutôt que d'interroger fail2ban-client un par un.")
        ),
        see_also=["4.2"],
    ),
    "4.2": HelpEntry(
        summary=N_("Bannit ou débannit une ou plusieurs IPs dans un jail précis que tu choisis."),
        usage=[
            N_("Sélectionne d'abord le jail cible, puis l'action (bannir/débannir), "
            "puis saisis une IP unique ou une liste."),
        ],
        consequences=[
            N_("Modifie l'état réel du jail immédiatement — l'IP est bloquée/débloquée "
            "dès validation, pas seulement enregistrée quelque part."),
        ],
        warnings=[
            N_("Une IP déjà bannie ne peut pas être bannie une seconde fois (et "
            "inversement pour le débannissement) — l'action échoue proprement "
            "dans ce cas plutôt que de prétendre avoir réussi."),
            N_("Vérifie le nom du jail affiché avant de valider : une IP bannie "
            "dans le mauvais jail ne protège pas la bonne surface."),
        ],
        see_also=["4.1", "4.3"],
    ),
    "4.3": HelpEntry(
        summary=(
            N_("Transfère des IPs entre jails fail2ban, vers/depuis les backends "
            "firewall (nftables/iptables), ou depuis/vers des fichiers.")
        ),
        usage=[
            N_("Choisis d'abord une source (un jail, un backend, un fichier), "
            "puis une destination."),
            N_("Un récapitulatif (IPs déjà présentes / nouvelles / échecs) "
            "s'affiche après l'opération — vérifie-le avant de continuer."),
        ],
        consequences=[
            N_("Les IPs transférées vers un jail ou un backend sont réellement "
            "bannies à la destination, pas juste copiées dans une liste."),
        ],
        warnings=[
            N_("Le transfert vers nftables crée automatiquement la chaîne de "
            "blocage si elle n'existe pas encore — normal, pas une erreur "
            "si tu la vois apparaître pour la première fois."),
        ],
        see_also=["2.6", "2.7"],
    ),
    "4.4": HelpEntry(
        summary=(
            N_("Assistant de création d'un nouveau jail : mode sur-mesure (tu "
            "choisis chaque paramètre) ou mode preset (modèles pré-configurés "
            "pour Nginx, Apache, Caddy, SSH...).")
        ),
        usage=[
            N_("Mode sur-mesure : nom du jail, chemin de log à surveiller (liste "
            "épinglée modifiable directement depuis cet écran), ports "
            "concernés, nom du filtre, règles de bannissement (maxretry / "
            "findtime / bantime)."),
            N_("Mode preset : choisis directement un modèle déjà réglé."),
        ],
        consequences=[
            N_("Écrit un fichier de configuration réel et recharge fail2ban — "
            "le jail devient actif immédiatement."),
            N_("Si le filtre demandé n'existe pas encore, un filtre générique "
            "(détection d'erreurs HTTP 400/401/403/404/500) est créé "
            "automatiquement."),
        ],
        warnings=[
            N_("Le filtre générique automatique est pensé pour des logs HTTP "
            "(Nginx/Apache/Caddy/Lighttpd) — appliqué à un log qui n'a pas "
            "ce format (ex: syslog), il ne détectera jamais rien."),
            N_("Pour omega-serv et omega-waf, omega-jail installe en une commande des jails déjà réglés (WAF, Active Defense, scans, force brute) : l'écran le rappelle quand omega-serv est détecté sans omega-jail."),
        ],
        see_also=["4.5", "4.9"],
    ),
    "4.5": HelpEntry(
        summary=N_("Supprime un jail : arrête son suivi, retire sa configuration et recharge fail2ban."),
        usage=[
            N_("Choisis le jail à supprimer et confirme. Chaque jail est listé avec son origine et le fichier qui le définit, retrouvé par le nom de sa section, quel que soit le nom du fichier."),
        ],
        consequences=[
            N_("Les IPs actuellement bannies dans ce jail sont libérées quand "
            "le jail est arrêté — consulte 4.1 avant si tu veux connaître son contenu."),
            N_("Son fichier de jail.d est supprimé, ainsi que son filtre s'il lui est propre (créé par Omega-Fire ou par omega-jail) ; un filtre standard de fail2ban (sshd…) n'est jamais supprimé."),
        ],
        warnings=[
            N_("Irréversible sans recréer le jail depuis zéro (4.4)."),
            N_("Jail installé par omega-jail : la confirmation le signale ; omega-jail le recréera à sa prochaine installation (« omega-jail --apply »)."),
            N_("Jail défini dans jail.local / jail.conf, ou dans un fichier de jail.d qui définit aussi d'autres jails : rien n'est supprimé, le message explique comment le désactiver ou retirer sa section à la main."),
        ],
        see_also=["4.4", "4.1"],
    ),
    "4.6": HelpEntry(
        summary=N_("Débannit toutes les IPs d'un seul jail (celui que tu choisis), sans toucher aux autres."),
        usage=[N_("Sélectionne le jail à vider et confirme.")],
        consequences=[N_("Toutes les IPs actuellement bannies dans ce jail précis sont débannies immédiatement.")],
        warnings=[
            N_("Ne touche qu'au jail sélectionné — pour vider tous les jails "
            "d'un coup, utilise 4.7, pas cette option répétée plusieurs fois."),
        ],
        see_also=["4.7", "4.1"],
    ),
    "4.7": HelpEntry(
        summary=N_("PURGE GÉNÉRALE : débannit toutes les IPs de tous les jails configurés, en une seule opération."),
        usage=[N_("Une confirmation est demandée avant exécution — lis-la attentivement, l'opération touche l'ensemble des jails.")],
        consequences=[N_("Toutes les IPs actuellement bannies, dans tous les jails, sont débannies immédiatement. Non sélectif.")],
        warnings=[N_("Opération large et irréversible — pour ne vider qu'un seul jail, utilise 4.6.")],
        see_also=["4.6"],
    ),
    "4.8": HelpEntry(
        summary=(
            N_("Exporte le contenu d'un jail (IPs bannies, configuration) dans "
            "un fichier : brut, JSON, TXT (réinjectable), ou HTML (rapport visuel).")
        ),
        usage=[N_("Choisis le jail, puis le format de sortie.")],
        consequences=[N_("Lecture seule côté fail2ban — l'export ne modifie aucun jail.")],
        see_also=["6.4"],
    ),
    "4.9": HelpEntry(
        summary=(
            N_("Teste la validité de la configuration fail2ban actuelle "
            "(jails, filtres) sans rien modifier ni redémarrer le service.")
        ),
        usage=[N_("Aucune saisie — lance directement le test.")],
        consequences=[N_("Lecture seule.")],
        mechanism=(
            N_("Valide la configuration sur disque sans nécessiter que le "
            "démon soit déjà démarré.")
        ),
        see_also=["4.4"],
    ),
    "4.10": HelpEntry(
        summary=(
            N_("Contrôle du service fail2ban lui-même (pas d'un jail précis) : "
            "statut, démarrage, arrêt, redémarrage, activation/désactivation "
            "au démarrage du système.")
        ),
        usage=[N_("Choisis l'action à effectuer sur le service.")],
        consequences=[
            N_("Arrêter le service désactive toute la protection fail2ban le "
            "temps qu'il est arrêté, pas seulement un jail."),
        ],
        warnings=[
            N_("À utiliser avec précaution sur une machine en production — un "
            "arrêt du service, même bref, laisse temporairement passer les "
            "tentatives que fail2ban aurait bloquées."),
        ],
        see_also=["4.9"],
    ),

    # ------------------------------------------------------------------
    # Section 5 — Gestion des logs (Analyse & Maintenance)
    # ------------------------------------------------------------------

    "5": HelpEntry(
        summary=(
            N_("Analyse et maintenance des logs : Bibliothèque (import des "
            "logs), favoris, lecture avec trois lecteurs, analyse de fréquence "
            "par IP, purge ciblée, rotation/backup, restauration, statistiques.")
        ),
        usage=[
            N_("Les fichiers épinglés (« Gérer les épingles », avec ses presets) "
            "forment une seule liste, partagée par 5.4 à 5.6, 2.2, 2.4, 2.7, "
            "2.8, 4.3 (et 2.10), 4.4 et 6.1. La Bibliothèque 5.1, qui alimente "
            "5.2 et 5.3, est une liste distincte."),
        ],
        see_also=["5.1", "5.2", "5.3", "8.5", "8.6"],
    ),
    "5.1": HelpEntry(
        summary=N_("Bibliothèque de logs : l'import des logs qui alimentent 5.2 Favoris et 5.3 Voir les logs. Rien ne se lance d'ici."),
        usage=[
            N_("Mode automatique : à chaque ouverture, les journaux des instances omega-serv détectées sur la machine (access.log, error.log, waf-alerts.log du WAF natif, active-defense…) sont ajoutés, ainsi que ceux d'omega-waf aux chemins de l'extra magnet, même hors de var/log/. Un journal retiré à la main n'est plus réimporté automatiquement ; « Importer omega-serv » les réimporte tous."),
            N_("Épingler un chemin : saisis le chemin absolu d'un log (ex. /var/log/nginx/access.log)."),
            N_("Sources distantes (SSH) : enregistre une machine du réseau (hôte, chemin distant, utilisateur, port, clé), puis « Récupérer maintenant » copie le log par scp dans var/log/remote/ et l'ajoute à la Bibliothèque."),
        ],
        consequences=[
            N_("La Bibliothèque ne contient que des références : retirer un log ne supprime pas le fichier. L'état (taille, absent, vide) est relu à chaque affichage."),
            N_("Une copie distante n'est pas suivie en direct : relance « Récupérer maintenant » pour la mettre à jour."),
        ],
        warnings=[
            N_("SSH : aucune invite de mot de passe n'est possible depuis l'interface. Il faut une clé ou un agent SSH déjà configurés pour l'utilisateur qui lance omega-fire (root avec sudo)."),
            N_("Les instances omega-serv sont détectées par leur service systemd (omega-serv*.service) et par leur registre d'instances ; une instance lancée à la main n'est pas vue : épingle ses journaux."),
        ],
        see_also=["5.2", "5.3"],
    ),
    "5.2": HelpEntry(
        summary=N_("Favoris : combiner des logs de la Bibliothèque, les enregistrer sous un nom avec un lecteur, et les lancer directement."),
        usage=[
            N_("Choisis les numéros des logs (ex. 1,3), un nom et un lecteur, puis « Enregistrer ». « Lancer » ouvre le favori en surbrillance."),
        ],
        consequences=[N_("Lecture seule sur les logs ouverts.")],
        warnings=[
            N_("Plusieurs logs combinés : lnav seul, le seul lecteur qui sait les fusionner en une vue chronologique ; un autre lecteur est refusé à l'enregistrement."),
            N_("Un log retiré de la Bibliothèque reste dans le favori, mais ne s'ouvre plus s'il n'existe plus."),
        ],
        see_also=["5.1", "5.3"],
    ),
    "5.3": HelpEntry(
        summary=N_("Voir un log de la Bibliothèque sans configuration, avec le lecteur de ton choix."),
        usage=[
            N_("Choisis la ligne, puis le lecteur : Simple (tableau de bord temps réel : trafic, statistiques, dernières requêtes), Classique (dernières lignes puis suivi en direct à la demande), ou lnav (navigation, recherche, filtres)."),
        ],
        consequences=[N_("Lecture seule.")],
        warnings=[N_("lnav sur un gros fichier peut afficher un écran noir quelques secondes, le temps de l'indexation : ce n'est pas un blocage.")],
        see_also=["5.1", "5.2", "8.5", "8.6"],
    ),
    "5.4": HelpEntry(
        summary=N_("Analyse un fichier log ou une blocklist pour en extraire le classement des IPs les plus actives (Top N), sur une période choisie."),
        usage=[
            N_("Choisis la source (épinglée, manuelle, ou ajout/retrait d'épingle), la période d'analyse (1h/1j/7j/personnalisée), puis le nombre N d'IPs à afficher."),
            N_("Après l'analyse, « Exporter » enregistre le classement (JSON, TXT ou HTML) dans le dossier d'exports : 5.5 peut ensuite recharger ces IPs pour les retirer des logs, sans les recopier à la main, et 6.5 les affiche."),
            N_("« Gérer les épingles » → « Presets » propose les chemins usuels (logs système, serveurs web, blocklists d'omega-fire, logs de la Bibliothèque 5.1) présents sur cette machine : coche ceux à épingler."),
        ],
        consequences=[N_("Lecture seule. « Exporter » écrit un fichier top-ips_<date> dans le dossier d'exports.")],
        warnings=[
            N_("Les fichiers proposés ici viennent de la liste « fichiers de travail » "
            "partagée avec 5.5, 5.6 et les écrans de blocklists (épingles "
            "persistées), distincte de la Bibliothèque 5.1."),
        ],
        see_also=["5.5", "1.6"],
    ),
    "5.5": HelpEntry(
        summary=N_("Retire toutes les lignes contenant une IP précise dans un fichier source (log ou blocklist) — édition directe du fichier, pas un débannissement."),
        usage=[
            N_("Choisis le fichier source, saisis une ou plusieurs IPs (séparées par des virgules), vérifie le récapitulatif (lignes trouvées par IP) avant de confirmer."),
            N_("« Charger depuis un export » liste les exports contenant des IPs (Top N de 5.4 en premier, puis blacklist 6.1 et jails 4.8) : choisis le fichier, coche les IPs à retirer."),
        ],
        consequences=[N_("Modifie réellement le fichier — les lignes contenant l'une des IPs sont supprimées, les autres conservées.")],
        warnings=[N_("N'agit que sur le fichier choisi, pas sur l'état réel du firewall/fail2ban — pour débannir une IP, utilise 2.3 ou 4.2.")],
        see_also=["5.4", "2.3"],
    ),
    "5.6": HelpEntry(
        summary=N_("Sauvegarde (backup) manuelle ou automatisée de fichiers logs/blocklists dans une archive."),
        usage=[N_("Choisis la source à sauvegarder, puis le mode : sauvegarde immédiate, planification d'une automatisation récurrente, ou gestion des automatisations existantes.")],
        consequences=[
            N_("Crée une archive réelle dans var/backups/. Une automatisation "
            "configurée continue de s'exécuter aux intervalles définis "
            "tant qu'elle n'est pas supprimée via [3]."),
        ],
        see_also=["5.7", "5.8"],
    ),
    "5.7": HelpEntry(
        summary=N_("Restaure une archive de logs précédemment sauvegardée (menu 5.6), immédiatement ou selon une automatisation planifiée."),
        usage=[N_("Choisis le mode (restauration immédiate, planification, gestion des automatisations existantes), puis l'archive et la stratégie de restauration.")],
        consequences=[N_("Écrit réellement les fichiers restaurés — une restauration peut écraser des fichiers actuels selon le mode choisi.")],
        warnings=[N_("Vérifie la stratégie/mode proposés avant de confirmer.")],
        see_also=["5.6", "5.8"],
    ),
    "5.8": HelpEntry(
        summary=N_("Purge et nettoie les archives de backup (var/backups/) selon différents critères : ancienneté, quota, type (sauvegardes automatiques de sécurité), ou sélection manuelle."),
        usage=[N_("Consulte d'abord les statistiques de stockage affichées (nombre d'archives, volume, espace disque libre), puis choisis le critère de purge.")],
        consequences=[N_("Suppression réelle et irréversible des archives ciblées — une confirmation avec aperçu des fichiers concernés est demandée avant exécution.")],
        see_also=["5.6", "5.9"],
    ),
    "5.9": HelpEntry(
        summary=N_("Nettoyage avancé de l'espace de stockage interne d'Omega-Fire (logs, cache, exports, backups, ou tout var/), filtré par âge ou taille."),
        usage=[N_("Choisis le(s) dossier(s) cible(s), puis les critères de filtrage, et vérifie l'aperçu des fichiers concernés avant de confirmer.")],
        consequences=[N_("Suppression réelle et irréversible des fichiers correspondants.")],
        warnings=[
            N_("app.log et audit.log sont toujours exclus de ce nettoyage, "
            "même si le dossier logs/ est ciblé — ce sont des fichiers "
            "actifs en écriture continue ; utilise 1.5 ou 7.3 pour les "
            "gérer spécifiquement."),
        ],
        see_also=["5.8", "1.5", "7.3"],
    ),
    "5.10": HelpEntry(
        summary=N_("Affiche un tableau de bord de statistiques sur les logs (volumes, tendances)."),
        usage=[N_("Aucune saisie requise.")],
        consequences=[N_("Lecture seule.")],
        see_also=["8.3", "8.4"],
    ),

    # ------------------------------------------------------------------
    # Section 6 — Exports & Rapports (Audit centralisé)
    # ------------------------------------------------------------------

    "6": HelpEntry(
        summary=N_("Centralise les exports et rapports : blacklist complète, règles de pare-feu, audit système complet, statistiques fail2ban — et 6.5 pour les retrouver et les ouvrir."),
        usage=[N_("Chaque export propose un format (JSON/TXT/HTML selon le rapport) et un chemin de destination modifiable.")],
        see_also=["6.1", "6.3", "6.5"],
    ),
    "6.1": HelpEntry(
        summary=N_("Exporte la blacklist complète (IPs bannies) depuis un fichier source choisi, au format JSON, TXT ou HTML."),
        usage=[N_("Choisis la source (épinglée, manuelle, ou gestion des épingles), puis le format de sortie.")],
        consequences=[N_("Écrit un fichier réel — lecture seule côté bannissement.")],
        see_also=["2.8", "2.5"],
    ),
    "6.2": HelpEntry(
        summary=N_("Exporte les règles de pare-feu nftables/iptables (fail2ban a son propre export, voir 4.8) — toutes, actives seulement, Omega-Fire uniquement, ou système importées uniquement."),
        usage=[N_("Choisis le contenu à exporter, puis le format (JSON/HTML/TXT).")],
        consequences=[N_("Écrit un fichier réel — lecture seule côté règles.")],
        see_also=["3.3", "4.8"],
    ),
    "6.3": HelpEntry(
        summary=N_("Génère un rapport d'audit complet : état système, historique, top IPs, en un seul document."),
        usage=[N_("Choisis le format (TXT ou HTML), valide le chemin de destination proposé ou saisis-en un autre.")],
        consequences=[N_("Écrit un fichier réel — lecture seule côté système.")],
        see_also=["1.7", "7.3"],
    ),
    "6.4": HelpEntry(
        summary=N_("Exporte un rapport détaillé sur fail2ban (jails et bans), au format TXT ou HTML."),
        usage=[N_("Choisis le format, valide ou modifie le chemin de destination proposé.")],
        consequences=[N_("Écrit un fichier réel — lecture seule côté fail2ban.")],
        see_also=["4.8", "4.1"],
    ),
    "6.5": HelpEntry(
        summary=N_("Liste tous les fichiers exportés (dossier d'exports, et exports de blacklist de 6.1) : type, date, taille — sans ouvrir de terminal ni de gestionnaire de fichiers."),
        usage=[
            N_("« Ouvrir » : un rapport HTML s'ouvre dans votre navigateur ; un JSON ou TXT se lit dans omega-fire (lecteur Classique)."),
            N_("« Copier le chemin » copie le chemin complet du fichier ; « Supprimer » l'efface après confirmation."),
        ],
        consequences=[N_("Ouvrir et copier sont en lecture seule. Supprimer efface réellement le fichier.")],
        warnings=[
            N_("omega-fire tourne en root : le navigateur est lancé au nom de l'utilisateur qui a fait sudo, dans sa session graphique. Si le fichier ne lui est pas lisible, une copie lui appartenant est ouverte depuis un dossier temporaire."),
            N_("Sans session graphique (connexion SSH, serveur sans bureau), aucun navigateur ne peut s'ouvrir : le chemin du fichier est affiché pour l'ouvrir depuis un autre poste."),
        ],
        see_also=["5.4", "6.1", "6.3"],
    ),

    # ------------------------------------------------------------------
    # Section 7 — Système & Persistance (État & Sauvegarde)
    # ------------------------------------------------------------------

    "7": HelpEntry(
        summary=(
            N_("Gestion de l'état interne d'Omega-Fire : sauvegarde/"
            "restauration complète (règles + IPs bannies), historique "
            "d'audit, rechargement de la configuration.")
        ),
        usage=[N_("Distinct du menu 5 (qui gère les fichiers de logs) — ici, c'est l'état du firewall/fail2ban lui-même qui est sauvegardé/restauré.")],
        see_also=["7.1", "7.2"],
    ),
    "7.1": HelpEntry(
        summary=N_("Capture un instantané (snapshot) complet de l'état actuel : règles firewall et IPs bannies (nftables/iptables/fail2ban)."),
        usage=[N_("Une description optionnelle peut être ajoutée pour identifier facilement le snapshot plus tard.")],
        consequences=[N_("Crée une archive réelle — n'affecte aucun état actuel, uniquement une sauvegarde.")],
        see_also=["7.2", "5.6"],
    ),
    "7.2": HelpEntry(
        summary=N_("Restaure un snapshot précédemment sauvegardé (menu 7.1)."),
        usage=[N_("Sélectionne le snapshot à restaurer dans la liste paginée, puis confirme.")],
        consequences=[
            N_("Les règles firewall actuellement gérées par Omega-Fire sont "
            "RETIRÉES puis REMPLACÉES par celles du snapshot."),
            N_("Seules les règles que le snapshot peut recréer à l'identique sont réappliquées (chaîne de base, avec seulement protocole, port, adresses, commentaire et verdict). Les autres — règles d'autres outils ou avec des critères qu'Omega-Fire ne sait pas reproduire (état de connexion, interface, type ICMP, limite de débit) — restent telles quelles dans le pare-feu."),
            N_("Un snapshot créé avant la version 3.5 ne porte pas cette information : sa restauration ne touche à aucune règle, seules les IPs bannies sont ajoutées."),
            N_("La politique par défaut des chaînes n'est remise à ACCEPT que sur un backend où un profil (3.4) était actif."),
            N_("Les IPs bannies du snapshot sont AJOUTÉES — rien n'est retiré "
            "des bannissements actuels."),
            N_("Les jails fail2ban ne sont PAS restaurées automatiquement "
            "(information seulement)."),
            N_("Les règles/IPs gérées par d'autres outils (UFW, etc.) ne "
            "sont jamais touchées."),
        ],
        warnings=[N_("Opération significative sur les règles firewall — vérifie bien le snapshot choisi avant de confirmer.")],
        see_also=["7.1", "4.4"],
    ),
    "7.3": HelpEntry(
        summary=N_("Consulte ou purge l'historique d'audit (le journal des actions effectuées par Omega-Fire, avec succès/échec) — distinct du journal applicatif technique (1.5)."),
        usage=[N_("Recherche par mot-clé possible. Le sous-menu de gestion permet de purger les entrées anciennes.")],
        consequences=[N_("La consultation est en lecture seule. La purge supprime réellement des entrées, irréversible.")],
        see_also=["1.5", "6.3"],
    ),
    "7.4": HelpEntry(
        summary=N_("Recharge la configuration système sans redémarrer l'application."),
        usage=[N_("Aucune saisie — lance directement le rechargement.")],
        consequences=[
            N_("Même mécanisme que 1.3 (re-scan complet des sondes système "
            "et de la configuration), avec un affichage minimal plutôt "
            "que le détail diagnostic complet."),
        ],
        see_also=["1.3"],
    ),

    # ------------------------------------------------------------------
    # Section 8 — Monitoring & Statistiques
    # ------------------------------------------------------------------

    "8": HelpEntry(
        summary=N_("Vue d'ensemble de l'activité réseau en temps réel et sur la durée : tableau de bord live, connexions actives, tendances 7/30 jours."),
        see_also=["8.1", "8.3"],
    ),
    "8.1": HelpEntry(
        summary=N_("Tableau de bord en temps réel combinant statistiques firewall, monitoring, audit et logs — rafraîchi automatiquement."),
        usage=[N_("Aucune saisie au lancement — consulte l'écran, quitte avec la touche indiquée à l'écran.")],
        consequences=[N_("Lecture seule.")],
        see_also=["8.2", "5.10"],
    ),
    "8.2": HelpEntry(
        summary=N_("Affiche les connexions réseau actives (conntrack) : protocole, état, adresses, ports."),
        usage=[N_("Filtre par protocole et/ou état une fois la liste initiale affichée, limite le nombre d'entrées affichées.")],
        consequences=[N_("Lecture seule.")],
        see_also=["8.1"],
    ),
    "8.3": HelpEntry(
        summary=N_("Rapport statistique sur les 7 derniers jours (tendances, graphiques)."),
        usage=[N_("Aucune saisie requise.")],
        consequences=[N_("Lecture seule.")],
        see_also=["8.4", "5.10"],
    ),
    "8.4": HelpEntry(
        summary=N_("Rapport statistique sur les 30 derniers jours — vue macro, même mécanisme que 8.3 avec une fenêtre plus large."),
        usage=[N_("Aucune saisie requise.")],
        consequences=[N_("Lecture seule.")],
        see_also=["8.3"],
    ),
    "8.5": HelpEntry(
        summary=(
            N_("Visualise en direct les logs serveur (Nginx, Apache, Caddy, "
            "Lighttpd) ou le journal applicatif, avec analyse des requêtes "
            "HTTP en temps réel. C'est aussi le lecteur « Simple » de 5.2 "
            "Favoris et 5.3 Voir les logs.")
        ),
        usage=[
            N_("Choisis une source épinglée, l'historique récent, ou saisis "
            "un chemin/URL manuellement."),
            N_("Utilise [G] pour gérer les épingles (ajouter/retirer) et "
            "l'historique — un [0] Annuler est disponible à chaque étape."),
        ],
        consequences=[N_("Lecture seule sur la source suivie — aucune modification du fichier ou du serveur observé.")],
        mechanism=(
            N_("Les épingles et l'historique sont persistés (survivent à un "
            "redémarrage). Ouvert depuis 5.2 ou 5.3, il démarre directement "
            "sur le log choisi, sans toucher à cet historique.")
        ),
        see_also=["5.3", "8.1"],
    ),
    "8.6": HelpEntry(
        summary=(
            N_("Sélectionne un ou plusieurs fichiers de logs serveur (Nginx, "
            "Apache, Lighttpd, Caddy) pour analyse via lnav — contrairement "
            "à 8.5, plusieurs fichiers peuvent être choisis à la fois : "
            "lnav les fusionne automatiquement en une seule vue chronologique.")
        ),
        usage=[
            N_("Numéros séparés par des virgules pour choisir plusieurs sources "
            "épinglées/historique à la fois (ex: 1,3)."),
            N_("[M] pour un ou plusieurs chemins saisis à la main (mêmes "
            "virgules), [G] pour gérer les épingles — un [0]/Entrée annule "
            "à chaque étape."),
        ],
        consequences=[N_("Lecture seule sur les fichiers sélectionnés — aucune modification.")],
        mechanism=(
            N_("Épingles et historique propres à 8.6 (séparés de ceux de "
            "8.5, mêmes mécanismes de stockage). lnav s'ouvre ensuite "
            "en plein écran, encapsulé dans un header/footer Omega-Fire — "
            "Ctrl-Q pour quitter, Ctrl-C pour copier la ligne courante, "
            "la touche t pour changer de thème.")
        ),
        see_also=["5.2", "5.3", "8.5"],
    ),

    # ------------------------------------------------------------------
    # Section 0 — Quitter l'application
    # ------------------------------------------------------------------

    "0": HelpEntry(
        summary=N_("Ferme Omega-Fire, avec une confirmation avant de quitter réellement."),
        usage=[N_("Réponds 'o' pour confirmer la fermeture, ou toute autre réponse pour rester dans l'application.")],
        consequences=[N_("Aucune sauvegarde automatique n'est déclenchée par cette confirmation — pense à utiliser 7.1 avant de quitter si tu veux capturer l'état actuel.")],
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
