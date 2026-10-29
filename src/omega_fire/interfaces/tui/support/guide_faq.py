# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""FAQ du guide d'aide (version 3.5, « comme omega-serv ») : les pieges reels rencontres
et corriges (retours utilisateur de la version 3.5), chaque reponse decrivant le
comportement effectif du code et le menu a utiliser. Affichee par le guide (bouton FAQ)
et incluse dans son export HTML."""
from __future__ import annotations

from dataclasses import dataclass

from omega_fire.shared.i18n import _


@dataclass(frozen=True)
class FaqEntry:
    category: str
    question: str
    answer: str


def faq_entries() -> tuple[FaqEntry, ...]:
    rules = _("Règles et pare-feu")
    backup = _("Sauvegarde et restauration")
    f2b = _("Fail2ban")
    logs = _("Gestion des logs")
    exports = _("Exports et navigateur")
    ui = _("Interface")
    return (
        FaqEntry(rules, _("3.3 liste moins de règles que 3.2 n'en propose à la suppression. Pourquoi ?"),
                 _("La base d'Omega-Fire garde une trace des règles ; elle peut contenir des doublons ou "
                   "des règles qui n'existent plus dans le noyau (supprimées par un autre outil, "
                   "redémarrage…). Dans 3.2, « Nettoyer et resynchroniser la base (pare-feu non "
                   "modifié) » montre d'abord un aperçu, sauvegarde la base, puis retire ces lignes et "
                   "importe les règles manquantes. Le pare-feu lui-même n'est jamais touché, et un "
                   "backend illisible n'est jamais modifié.")),
        FaqEntry(rules, _("Je vois des règles d'UFW, Docker ou Tailscale. Puis-je les supprimer ici ?"),
                 _("Non. Ces règles sont listées avec l'outil qui les a posées (colonne Origine) pour que "
                   "vous sachiez ce qui filtre réellement, mais 3.2 refuse de les supprimer : elles se "
                   "gèrent dans leur propre outil, qui les recréerait de toute façon.")),
        FaqEntry(rules, _("Appliquer un profil (3.4) ou vider les tables (3.5) efface-t-il les règles d'UFW ?"),
                 _("Sur iptables et ip6tables, oui : l'opération vide toute la table filter, règles des "
                   "autres outils comprises. Omega-Fire le détecte et vous laisse choisir : tous les "
                   "backends (ces règles sont effacées) ou seulement nftables (elles sont gardées). Sur "
                   "nftables, Omega-Fire ne vide que sa propre table. La touche `a` dans la fenêtre de "
                   "choix détaille les conséquences.")),
        FaqEntry(rules, _("Que signifie « Politiques différentes selon les backends » (3.5) ?"),
                 _("Un paquet doit être accepté par chaque backend : la politique la plus stricte "
                   "l'emporte (« nftables ACCEPT · iptables DROP → en pratique DROP »). Pour chaque "
                   "politique DROP, 3.5 donne la cause et le remède : outil qui l'a posée (UFW…, rien à "
                   "faire), profil Omega-Fire actif, politique orpheline sans aucune règle (en jaune : "
                   "tout est bloqué sur ce backend), ou politique DROP avec des règles sans profil.")),
        FaqEntry(rules, _("nftables n'est pas initialisé, mais `nft list ruleset` montre des règles. Pourquoi ?"),
                 _("Ce sont les tables d'iptables-nft : la commande iptables moderne écrit dans nftables, "
                   "et `nft` les affiche avec un avertissement « managed by iptables-nft ». Omega-Fire les "
                   "reconnaît et les compte côté iptables, pas côté nftables, pour ne jamais les "
                   "modifier par le mauvais outil.")),
        FaqEntry(backup, _("La restauration d'un état (7.2) va-t-elle toucher aux règles des autres outils ?"),
                 _("Non. Seules les règles créées par Omega-Fire et recréables à l'identique sont "
                   "reposées ; seules les règles d'Omega-Fire sont retirées. Les politiques ne sont "
                   "remises à ACCEPT que sur un backend où un profil (3.4) était actif. Un snapshot créé "
                   "avant la version 3.5 ne contient pas cette information : sa restauration ne touche à "
                   "aucune règle.")),
        FaqEntry(f2b, _("J'ai démarré Fail2ban, mais le tableau de bord l'affichait toujours inactif."),
                 _("Corrigé en 3.5 : après Démarrer, Stopper ou Redémarrer (4.10), Omega-Fire attend "
                   "que le serveur Fail2ban réponde (15 s au plus) puis met à jour le registre des "
                   "capacités, que lit le tableau de bord. Si Fail2ban met plus de temps à démarrer, le "
                   "message propose de relancer 1.3 (Re-scanner le système).")),
        FaqEntry(f2b, _("Puis-je supprimer les modèles de jail livrés avec Omega-Fire ?"),
                 _("Oui : 4.4 → « Gérer les modèles ». Les 11 modèles livrés sont un point de départ "
                   "enregistré dans var/runtime/jail_presets.json : chacun peut être retiré, et vous "
                   "pouvez ajouter les vôtres.")),
        FaqEntry(f2b, _("J'ai supprimé un jail en 4.5 et il est revenu, ou 4.5 refuse de le supprimer."),
                 _("Depuis la 3.5, 4.5 retrouve le fichier d'un jail par le nom de sa section. Un jail installé "
                   "par omega-jail est supprimé avec son filtre, après un avertissement : omega-jail le "
                   "recréera à sa prochaine installation (« omega-jail --apply »). Un jail défini dans "
                   "jail.local / jail.conf, ou dans un fichier qui définit aussi d'autres jails, n'est "
                   "jamais supprimé : le message explique comment le désactiver ou retirer sa section à "
                   "la main.")),
        FaqEntry(logs, _("Les logs de mon instance omega-serv n'apparaissent pas dans la Bibliothèque (5.1)."),
                 _("Les instances sont détectées par leur service systemd (omega-serv*.service) et par "
                   "le registre d'instances d'omega-serv. Une instance lancée à la main n'est pas vue : "
                   "épinglez ses journaux avec « Épingler un chemin ». Un journal retiré à la main n'est "
                   "plus réimporté automatiquement ; « Importer omega-serv » les réimporte tous.")),
        FaqEntry(logs, _("Pourquoi seul lnav accepte-t-il plusieurs logs à la fois ?"),
                 _("Les lecteurs Simple et Classique suivent un seul fichier. lnav fusionne plusieurs "
                   "journaux en une seule vue chronologique : c'est le lecteur des favoris qui combinent "
                   "plusieurs logs (5.2). Un favori de plusieurs logs avec un autre lecteur est refusé.")),
        FaqEntry(logs, _("Comment retirer des logs les IPs trouvées par le Top N, sans les recopier ?"),
                 _("En 5.4, après l'analyse, « Exporter » enregistre le classement (JSON, TXT ou HTML). "
                   "En 5.5, « Charger depuis un export » liste les exports d'IPs : choisissez le fichier, "
                   "cochez les IPs, puis confirmez. Le récapitulatif donne le nombre de lignes retirées "
                   "par IP. Plusieurs IPs peuvent aussi être saisies, séparées par des virgules.")),
        FaqEntry(logs, _("L'import SSH (Sources distantes) échoue sans demander de mot de passe."),
                 _("C'est voulu : la copie se fait par scp en mode non interactif, par clé ou agent SSH, "
                   "pour ne jamais bloquer l'interface sur une invite. Indiquez le chemin de la clé "
                   "privée dans la source, ou chargez-la dans votre agent. La copie n'est pas suivie en "
                   "direct : relancez « Récupérer maintenant » pour la mettre à jour.")),
        FaqEntry(logs, _("Où sont passés nginx, apache et auth.log dans les fichiers épinglés ?"),
                 _("Depuis la version 3.5, plus aucun chemin système n'est épinglé d'office (ils "
                   "n'existent pas sur toutes les machines). « Gérer les épingles » → « Presets » "
                   "propose les chemins usuels réellement présents sur la machine, et les logs de la "
                   "Bibliothèque : cochez ceux à épingler.")),
        FaqEntry(exports, _("Où retrouver mes exports et comment les ouvrir ?"),
                 _("6.5 « Voir tous les exports » les liste tous (type, date, taille). « Ouvrir » affiche "
                   "un HTML dans votre navigateur, un JSON ou un TXT dans Omega-Fire. Le dossier se "
                   "choisit dans les Réglages (var/exports/ par défaut).")),
        FaqEntry(exports, _("Le rapport s'ouvre dans un autre navigateur que le mien."),
                 _("Omega-Fire ouvre le rapport avec votre navigateur web par défaut (celui déclaré pour "
                   "votre session, par exemple avec `xdg-settings set default-web-browser`). Si aucun "
                   "n'est déclaré, il utilise l'application associée aux fichiers .html, qui peut être "
                   "différente : changez-la dans les applications préférées de votre bureau.")),
        FaqEntry(exports, _("Le navigateur se referme tout seul quelques secondes après l'ouverture."),
                 _("Vérifiez la mémoire : un service comme earlyoom ferme le programme le plus gourmand "
                   "quand la mémoire et la swap sont presque pleines, et un navigateur qui démarre en est "
                   "souvent la cible (`journalctl | grep earlyoom`). Libérez de la mémoire, ou utilisez "
                   "un navigateur déjà ouvert : le rapport s'y ouvre dans un onglet.")),
        FaqEntry(exports, _("Rien ne s'ouvre quand je travaille en SSH."),
                 _("Sans session graphique, aucun navigateur ne peut s'ouvrir : Omega-Fire affiche le "
                   "chemin du fichier pour l'ouvrir depuis un poste avec navigateur. « Copier le "
                   "chemin » (6.5) le copie.")),
        FaqEntry(ui, _("Dans quelle langue sont écrits les exports ?"),
                 _("Les rapports, le guide d'aide et sa FAQ suivent le réglage « Langue des exports » "
                   "(par défaut : comme l'interface). Le journal applicatif et l'historique d'audit "
                   "restent en français.")),
        FaqEntry(ui, _("L'historique d'audit (7.3) montre d'anciens numéros du menu 5."),
                 _("Le menu 5 a été renuméroté en 3.5 (5.1 Bibliothèque, 5.2 Favoris, 5.3 Voir les "
                   "logs ; les anciens 5.2 à 5.8 sont devenus 5.4 à 5.10). Une entrée enregistrée avant, "
                   "ou par `--legacy-cli`, garde son numéro et son libellé d'origine.")),
        FaqEntry(ui, _("Quelles différences avec l'ancienne interface (--legacy-cli) ?"),
                 _("`--legacy-cli` reste l'interface de la version 3.0, en français : menu 5 d'origine "
                   "(sans Bibliothèque, Favoris ni lecteur Classique), sans 6.5, sans guide d'aide ni "
                   "presets. L'interface Textual est la version 3.5 complète.")),
    )
