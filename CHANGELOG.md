<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->

# Changelog

Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

Omega-Fire administre le pare-feu et Fail2Ban d'une machine en production : les changements
qui touchent aux **règles, aux bans ou aux services** sont toujours signalés explicitement,
même mineurs. Les changements de textes affichés sont signalés aussi : ils doivent être
reportés dans les 16 traductions (interface et README).

## version 3.5.0 : 2026-10-29

> **Traductions** : tous les textes ajoutés ou modifiés par la version 3.5 (point 1 à la FAQ,
> 342 textes) sont traduits dans les 16 langues — 2 689 messages par catalogue, aucun manquant
> ni approximatif. README ×17 à jour (2026-10-28) : sections 1, 3, 4, 5, 6, 7, nouvelle section
> « 10. Aide », parcours, navigation, `--legacy-cli`, sécurité, tests, limites.

### Ajouté

- **Interface en 17 langues** : français (langue source), anglais, espagnol, portugais
  (Brésil), italien, allemand, néerlandais, polonais, russe, chinois, vietnamien, thaï,
  indonésien, japonais, coréen, hindi, arabe — 2 351 phrases par langue, toutes validées.
  Choix dans les Réglages (« Langue / Language », libellé jamais traduit) : seule l'interface
  redémarre, les règles du pare-feu, Fail2Ban et les services ne sont pas touchés. Choix
  ponctuel : `OMEGA_FIRE_LANG=en ./omega-fire.sh` (conservé à travers `sudo` par le lanceur).
  Langue indisponible ou catalogue illisible : français, avec un message, jamais d'erreur au
  démarrage.
- Console texte Linux (TTY) : les langues dont l'écriture manque aux polices console
  (vietnamien, chinois, thaï, japonais, coréen, hindi, arabe) s'affichent en anglais pour la
  session, sans changer le réglage.
- Arabe affiché de droite à gauche dans le terminal ; hindi aligné (largeur des voyelles
  devanagari). Les deux correctifs viennent d'omega-serv et sont désormais partagés par
  omega-lib.
- **Langue des exports** (Réglages, « Comme l'interface » par défaut) : les 8 exports HTML et
  TXT de l'interface (audit, Fail2Ban, état système, règles, jail, blacklist, conntrack,
  statistiques 7 et 30 jours) peuvent sortir dans une autre langue que l'interface, sans
  redémarrage. Les rapports HTML annoncent leur langue et leur sens d'écriture (`lang`, `dir`) ;
  en arabe, la page s'affiche de droite à gauche.
- Réglages : dossiers d'exports et de captures d'écran modifiables (vide = dossier par défaut),
  et boutons « Vider les exports » / « Vider les captures » avec confirmation montrant le chemin
  exact. Le vidage refuse les dossiers système et personnels, la racine du projet et ses
  parents, ne suit pas les liens, tourne sans figer l'interface et signale ce qu'il n'a pas pu
  supprimer.
- README disponible en 17 langues (barre de langues en tête, section « Langues de
  l'interface ») ; les README traduits sont rangés dans `docs/translation/<code>/`.

- **3.2 « Nettoyer et resynchroniser la base (pare-feu non modifié) »** : remet la table des
  règles d'accord avec ce que le noyau contient vraiment, sans jamais flusher. Aperçu d'abord
  (à garder, doublons, règles absentes du noyau, backend absent de la machine, règles du noyau
  à importer), puis confirmation ; la base `omega.db` est sauvegardée avant dans
  `var/backups/db/`. Un backend dont la lecture échoue n'est jamais touché. Seule la base
  change : aucune règle n'est ajoutée ni retirée du pare-feu.

- **Règles d'autres outils signalées** (3.3, 3.2) : une règle posée par UFW, Tailscale, Docker,
  Fail2Ban, firewalld, libvirt… affiche le nom de son outil dans la colonne « Origine » au lieu
  de « SYSTEME », et 3.3 indique combien de règles appartiennent à d'autres outils. 3.2 refuse de
  les supprimer (elles se gèrent avec leur outil) et ne les propose plus comme « règles
  jumelles ».

- **Garde-fou avant de vider iptables / ip6tables** quand d'autres outils (UFW, Tailscale,
  Docker…) y ont des règles. Sur ces backends, appliquer un profil (3.4) ou vider (3.5) efface
  toute la table filter (`iptables -F`), règles des autres outils comprises. L'utilisateur
  décide, en le sachant : le message indique le nombre de règles par outil et par backend.
  - 3.4 et 3.5 « vider tous les backends » : choix entre « Tous les backends — efface ces
    règles », « Seulement nftables — garde ces règles » et « Annuler » ;
  - 3.5 « vider un backend » et « remettre les politiques à ACCEPT » : la confirmation détaille
    les règles concernées et l'effet (UFW compte sur INPUT en DROP).
  La touche `a` ouvre l'aide de l'action depuis la fenêtre de confirmation. Sur nftables, rien
  ne change : Omega-Fire n'y vide que sa propre table.
- Aide : nouvelle entrée 3.5 (Gestion des tables) ; 3.2, 3.3, 3.4 et 7.2 détaillent les
  conséquences (règles d'autres outils, nettoyage de la base, vidage iptables, restauration
  limitée aux règles recréables à l'identique).

- **Gestion des logs (menu 5) au niveau d'omega-log et d'omega-serv** :
  - **5.1 Bibliothèque** : import des logs. Automatique pour les instances omega-serv détectées
    (service systemd `omega-serv*.service` et registre d'instances : `access.log`, `error.log`,
    `waf-alerts.log` d'omega-waf, `active-defense-enriched.jsonl`) ; épinglage d'un chemin à la
    main ; **sources distantes SSH** (copie par `scp` dans `var/log/remote/`, clé ou agent SSH,
    jamais de mot de passe). Un journal omega-serv retiré à la main n'est plus réimporté
    automatiquement. La Bibliothèque alimente 5.2 et 5.3.
  - **5.2 Favoris** : combiner des logs, les enregistrer sous un nom avec un lecteur, les lancer
    directement. Plusieurs logs : lnav seul (refus explicite d'un autre lecteur).
  - **5.3 Voir les logs** : un log, lecteur au choix — **Simple** (tableau de bord temps réel de
    8.5), **Classique** (nouveau : dernières lignes lues depuis la fin du fichier, puis suivi en
    direct, rotation comprise), **lnav** (8.6).

- **5.4 → 5.5 sans recopier les IPs** :
  - 5.4 Analyser les IPs : bouton **Exporter** après l'analyse (JSON, TXT ou HTML avec thème,
    même mécanisme que 6.1), fichier `top-ips_<date>` dans le dossier d'exports ;
  - 5.5 Supprimer une IP des logs : **plusieurs IPs** à la fois (séparées par des virgules) et
    **« Charger depuis un export »** — choix d'un export d'IPs (Top N de 5.4 en premier, puis
    blacklist 6.1 et jails 4.8), puis des IPs à cocher. La confirmation donne le nombre de
    lignes retirées par IP et les IPs absentes du fichier. Une IP ne correspond plus à une IP
    plus longue (`1.2.3.4` ne touche ni `11.2.3.4` ni `1.2.3.45`).
- **6.5 Voir tous les exports** : tous les fichiers exportés au même endroit (dossier d'exports
  et exports de blacklist de 6.1), avec type, date et taille ; ouvrir, copier le chemin,
  supprimer (après confirmation). Un rapport HTML s'ouvre **dans le navigateur web par défaut
  de l'utilisateur**, même si les fichiers `.html` sont associés à une autre application (repli
  sur xdg-open s'il n'a pas déclaré de navigateur) : Omega-Fire tourne en root, le navigateur
  est donc lancé au nom de l'utilisateur qui a fait sudo, dans sa session graphique ; si le fichier ne lui est pas
  lisible, une copie lui appartenant est ouverte. Sans session graphique (SSH, serveur), le
  chemin est affiché. JSON et TXT se lisent dans Omega-Fire (lecteur Classique de 5.3).
- **Guide d'aide centralisé** (menu 10 « AIDE », comme dans omega-serv) : toutes les fiches
  d'aide déjà rédigées — vue d'ensemble de chaque section, chaque action, accueil, raccourcis
  clavier, réglages — réunies dans un seul parcours, dans l'ordre des menus. Chaque fiche ouvre
  ses fiches liées (« Voir 5.2 »…). **Export HTML de tout le guide** (sommaire cliquable, thème
  au choix) dans le dossier d'exports, visible en 6.5. La touche `a` reste l'aide de l'écran
  courant ; l'aide générique propose « Guide d'aide complet ». Une seule source : une fiche
  modifiée l'est partout (touche `a`, guide, export).
- **FAQ** (bouton FAQ du guide, comme dans omega-serv) : 20 questions réelles rencontrées en
  3.5, par thème — règles et pare-feu (base désynchronisée, règles d'UFW, vidage iptables,
  politiques, tables iptables-nft), sauvegarde et restauration, Fail2ban, logs (omega-serv,
  lnav, Top N → 5.5, SSH, presets), exports et navigateur (navigateur par défaut, fermeture
  par manque de mémoire, SSH), interface (langue des exports, anciens numéros, `--legacy-cli`).
  Incluse dans l'export HTML du guide, ou exportable seule.
- **Convergence avec la suite omega** (point 7) :
  - registre des capacités (1.1, tableau de bord, exports 1.7 / 6.3) : nouvelle catégorie
    **« Suite omega »** — **omega-serv** (instances détectées, en service ; « dégradé » si aucune
    ne tourne), **omega-waf** (extra `magnet` activé dans une instance), **omega-jail** (jails
    installés dans `/etc/fail2ban/jail.d`) ;
  - Bibliothèque 5.1 : les journaux d'omega-waf sont importés aux chemins de l'extra `magnet`,
    même hors de `var/log/` ;
  - 4.1 : nouvelle colonne **Origine** (Omega-Fire, omega-jail, `jail.local` / `jail.conf`,
    autre) ;
  - 4.4 : rappel qu'omega-jail installe en une commande les jails adaptés à omega-serv et
    omega-waf, quand omega-serv est détecté sans omega-jail.
- **Presets à cocher** pour les épingles (« Gérer les épingles » → **Presets**) : chemins usuels
  (logs système, serveurs web, blocklists d'Omega-Fire, logs de la Bibliothèque 5.1), seulement
  ceux présents sur la machine et pas encore épinglés. La liste des logs système n'est plus
  qu'une liste de presets ; seules les blocklists d'Omega-Fire restent épinglées d'office.

### Modifié

- **Version affichée** : « version 3.5 » dans le splash, le header (« OMEGA-FIRE version 3.5 »)
  et le tableau de bord (« Version Omega-Fire : 3.5 », au lieu de « v3.0 »). Une seule constante,
  `OMEGA_FIRE_VERSION` (`core/constants.py`) ; `APP_VERSION` (métadonnées des snapshots) inchangée.
  L'ancienne interface (`--legacy-cli`) garde son en-tête « v3.0 ». Nouveau texte « version
  {version} » traduit ×16 ; README : rien à reporter.

- La langue de contrôle « x-test » n'est plus proposée dans les Réglages (toujours accessible
  par `OMEGA_FIRE_LANG=x-test` pour vérifier les traductions).
- Menu principal : le menu 1 devient **« CAPACITÉS & DIAGNOSTICS »** (au lieu de « ÉTAT DES
  CAPACITÉS & DIAGNOSTICS »), même icône ; titre de la section, aide et `--legacy-cli` alignés.
- Menu principal : nouveau bouton **« 10. AIDE »**, dans la même colonne que les autres ; il
  ouvre le guide d'aide (voir « Ajouté »). Fiches d'aide : « Conséquences » et « À savoir »
  s'affichent accentués.

- Messages de l'application réécrits en français accentué (environ 350 messages étaient en
  anglais, 2 000 mots sans accents). Les textes relus par le code (sorties de `nft`, `iptables`,
  `fail2ban-client`, motifs cherchés dans les journaux, configuration de jail écrite sur disque,
  commentaires posés sur les règles et les bans) sont restés **strictement identiques**.
- Historique d'audit : les titres d'action restent enregistrés en français ; ils s'affichent
  dans la langue active (écran 7.3, export d'audit 6.3, dernières actions des rapports 8.3 et
  8.4), avec le libellé actuel du menu. La même action enregistrée sous deux libellés est
  comptée une seule fois dans le résumé de l'audit.
- Journal applicatif (`app.log`) et historique d'audit : toujours écrits en français, quelle que
  soit la langue de l'interface.
- L'ancienne interface (`--legacy-cli`) reste en français.

- 8.5 Live Tail et 8.6 lnav : plus d'épingles par défaut codées en dur (nginx, apache,
  lighttpd, caddy, journal d'audit) ; les logs se déclarent dans la Bibliothèque 5.1 ou
  s'épinglent à la main. Les épingles personnelles et l'historique sont conservés.
- **Menu 5 renuméroté** : 5.1 Bibliothèque, 5.2 Favoris, 5.3 Voir les logs ; les anciens 5.2 à
  5.8 deviennent 5.4 à 5.10. L'ancien 5.1 (Live Tail) et l'ancien 5.9 (lnav), qui ouvraient les
  mêmes écrans que 8.5 et 8.6, sont retirés du menu 5 ; 8.5 et 8.6 sont inchangés. Aide de la
  section 5, de 8.5 et de 8.6 mise à jour.
- Historique d'audit : une ancienne entrée du menu 5 (ou une entrée écrite par `--legacy-cli`,
  qui garde l'ancienne numérotation) garde son numéro et son libellé, traduit ; elle n'est pas
  affichée sous le nouveau libellé de ce numéro.
- `--legacy-cli` : reste sur le menu 5 de la version 3.0 (pas de Bibliothèque, Favoris ni
  lecteur Classique) ; son aide du menu 5 suit désormais la numérotation de l'interface Textual.
- 3.5 Gestion des tables : le message « Divergence(s) de politique entre backends » devient
  « Politiques différentes selon les backends ». Il donne l'effet réel (un paquet doit être
  accepté par chaque backend, le plus strict l'emporte : « nftables ACCEPT · iptables DROP →
  en pratique DROP »), puis pour chaque politique DROP sa cause et son remède : outil qui l'a
  posée (UFW…, rien à faire), profil Omega-Fire actif, politique orpheline sans aucune règle
  (seul cas en jaune : tout est bloqué sur ce backend), politique DROP avec des règles sans
  profil. Même texte dans `--legacy-cli` (en français). Aide 3.5 complétée.

### Corrigé

- **Tableau de bord (8.1)** : alerte « omega-jail-… : configuré (jail.d) mais non chargé » alors
  que les jails étaient actifs (constaté sur craftdark). L'alerte comparait les noms de
  fichiers de `jail.d` aux jails chargés : fausse pour chaque jail d'omega-jail, pour un fichier
  qui définit plusieurs jails et pour un jail volontairement désactivé. Elle compare maintenant
  les jails activés (`enabled = true`, dernier réglage gagnant) aux jails chargés.
- Écrans non centrés : 1.6 Rechercher dans les diagnostics était collé à gauche (tableau des
  résultats en pleine largeur) ; 5.6, 5.7 et 5.8 basculaient à gauche dès que leur tableau
  apparaissait. Formulaire de 1.6 dans un bloc centré, tableaux de 5.6 à 5.8 à la largeur du
  formulaire.
- **4.5 Supprimer un jail** :
  - un jail installé par omega-jail (fichier `omega-jail-<nom>.conf`) n'était pas retrouvé : il
    était arrêté puis relancé par le rechargement de fail2ban, et apparaissait deux fois dans la
    liste (nom du fichier et vrai nom). Le fichier est maintenant retrouvé par la section du jail ;
    un jail d'omega-jail est supprimé avec son filtre après un avertissement (omega-jail le
    recréera à sa prochaine installation) ;
  - un jail défini dans `jail.local` / `jail.conf`, ou dans un fichier de `jail.d` qui définit
    aussi d'autres jails, n'est plus « supprimé » sans effet : rien n'est touché, le message
    explique comment le désactiver ou retirer sa section ;
  - **sécurité** : le filtre `filter.d/<nom>.conf` était supprimé dès qu'il existait — pour un jail
    nommé comme un filtre standard (`sshd`…), le filtre de fail2ban partait avec lui. Seul un
    filtre portant l'en-tête d'Omega-Fire ou d'Omega-Jail est désormais supprimé.
- Aide 8.6 : « [t] pour changer de thème » s'affichait sans le « [t] » (lu comme balisage) ; et
  aide 5.1 : `waf-alerts.log` est le journal du WAF natif d'omega-serv, pas d'omega-waf.
- **Rapport d'audit (6.3) et export d'état (1.7) dans une autre langue que l'interface** : les
  motifs des capacités (« Processus détecté sur le système », « Service actif et activé au
  démarrage : … ») restaient dans la langue de l'interface. Rédigés au scan, ils sont
  désormais recomposés dans la langue des exports, détails des sondes compris ; seul l'état
  brut renvoyé par le système (ex. « inactive » de systemctl) reste tel quel.
- Sauvegarde automatique avant une restauration de backup : le motif enregistré citait encore
  l'ancien numéro « (5.5) » ; il devient « (restauration d'un backup) », valable pour les deux
  interfaces.
- **Guide d'aide et FAQ exportés toujours en français** malgré la « Langue des exports »
  (allemand, portugais…). Ils suivent maintenant ce réglage, comme les autres exports. Les
  fiches d'aide et les titres de section étaient traduits une seule fois au démarrage, dans la
  langue de l'interface, et ne pouvaient plus être retraduits : ils sont désormais traduits à
  l'affichage (touche `a`, guide) ou à l'export. `--legacy-cli` les affiche en français, comme
  avant.
- Numéros de menu après la renumérotation du menu 5 : tous les renvois des textes affichés
  (aide, fiches, messages, « Voir aussi ») ont été vérifiés. Deux corrigés : une sauvegarde
  manuelle de 5.6 était enregistrée « (menu 5.4) », et la fiche de la section 5 disait ses
  fichiers épinglés « indépendants du menu 4.4 » alors qu'ils forment une seule liste,
  partagée par 2.2, 2.4, 2.7, 2.8, 4.3, 4.4, 5.4 à 5.6 et 6.1.
- **6.5 : Firefox se refermait 3 à 5 secondes après l'ouverture d'un export HTML.** La sortie
  d'erreur du navigateur était reliée à Omega-Fire par un tube. Une fois xdg-open terminé,
  ce tube était fermé au lancement de commande suivant (rafraîchissement du tableau de bord),
  et la première écriture de Firefox sur cette sortie le tuait. Les sorties du navigateur vont
  désormais vers `/dev/null` : il reste ouvert.
- **Fail2ban démarré mais « inactif » au tableau de bord** : après « Démarrer », « Stopper » ou
  « Redémarrer » le service (4.10, et `--legacy-cli`), le registre des capacités n'était mis à
  jour qu'au prochain re-scan (1.3) ou rechargement (7.4). Omega-Fire attend maintenant que le
  serveur Fail2ban réponde (ou ne réponde plus), 15 s au plus, puis re-scanne : le tableau de
  bord affiche l'état réel. Si Fail2ban met plus longtemps à répondre, le message invite à
  relancer 1.3. Statut du service : « ACTIVÉE », « démarré » et « redémarré » s'affichent
  accentués et traduits.
- **Tableaux réduits à leur en-tête** dans les écrans qui défilent : les 11 modèles de jail
  livrés (4.4 → « Gérer les modèles ») n'apparaissaient pas, donc ne pouvaient pas être
  retirés. Ils étaient pourtant bien enregistrés et modifiables (`var/runtime/jail_presets.json`).
  Un balayage de tous les écrans, avec des données, a trouvé le même défaut dans la gestion des
  fichiers blocklist (fichiers et épingles), Conntrack, et les tableaux d'automatisations ou de
  règles de 5.6, 5.7 et 5.8. Ces tableaux reprennent leur hauteur naturelle. Dans les modèles
  de jail, le bouton Retour reste visible hors de la zone qui défile ; la gestion des fichiers
  blocklist s'ouvre de nouveau sur son titre.
- **Sécurité — restauration d'un état (7.2)**, sur une machine où un autre outil gère aussi le
  pare-feu (UFW…) :
  - les règles importées d'autres outils étaient **retirées du noyau** ; seules les règles créées
    par Omega-Fire le sont désormais ;
  - la politique par défaut d'INPUT, OUTPUT et FORWARD était remise à **ACCEPT** sur tous les
    backends, ce qui ouvrait une machine UFW (INPUT en DROP) ; elle n'est plus remise à ACCEPT
    que sur un backend où un profil 3.4 était actif ;
  - les règles étaient réappliquées **sans leurs critères** (`ct state`, interface, type ICMP,
    `limit`, chaîne UFW rangée dans INPUT) : `ct state established accept` devenait « tout
    accepter ». Un snapshot (7.1) note désormais si chaque règle peut être recréée à
    l'identique, et 7.2 ne réapplique que celles-là ; les autres restent telles quelles dans le
    noyau. Un snapshot plus ancien, qui ne porte pas cette information, ne touche plus à aucune
    règle (les IP bannies sont toujours ajoutées).
- 5.2 Analyser les IPs : formulaire collé à gauche (le tableau de résultats, en pleine
  largeur, annulait le centrage) et tableau de résultats réduit à une ligne ; il prend la
  largeur du formulaire et sa hauteur naturelle.
- 3.5 Gestion des tables : en 80×24, le tableau d'état des backends était réduit à sa ligne
  d'en-tête, et la barre d'actions défilait avec le contenu ; le tableau garde sa hauteur, la
  barre reste visible, l'écran s'ouvre sur son titre.
- 5.3 Voir les logs / 5.2 Favoris : les lecteurs Simple et lnav ouvraient la première épingle
  de 8.5 / 8.6 (ex. `/var/log/apache2/access.log`) au lieu du log choisi — la surbrillance
  automatique du tableau d'épingles remplaçait la sélection après l'ouverture.
- **lnav ne s'ouvrait plus** (8.6, et le lecteur lnav de 5.2 / 5.3) : retour au terminal de
  lancement, interface figée. Cause : le marquage des traductions avait ajouté `_()` dans une
  fonction qui utilisait aussi `_` comme variable jetable (`r, _, _ = select.select(...)`) ; le
  rendu lnav levait une erreur dès son bandeau, et l'interface ne reprenait pas après l'erreur.
  Corrigé ; la reprise de l'interface est désormais garantie même si le programme lancé échoue
  (mécanisme repris d'omega-serv / omega-log), et un test interdit ce piège partout dans le
  code. Depuis 5.2 / 5.3, lnav est lancé directement par le clic.
- **Règles comptées deux fois (nftables)** : les tables gérées par iptables-nft (`ip6 filter`,
  `ip nat`, `ip6 nat`, `ip mangle`…) étaient lues aussi comme règles nftables ; seule `ip filter`
  était exclue. Avec UFW, les règles ip6tables apparaissaient donc deux fois. Ces tables sont
  désormais reconnues par l'avertissement de nft lui-même. Lecture seule, aucun changement sur
  le pare-feu.

- Rapports statistiques 8.3 et 8.4 : le titre écrit dans l'historique d'audit dépendait de la
  langue de l'interface ; il est désormais toujours le titre source.
- Rapports HTML en arabe : en-têtes de tableau décalés par rapport aux cellules et axe des heures
  inversé (propriétés CSS logiques, axe des heures toujours de 00 à 23).
- Listes déroulantes sans valeur : l'invite « Select » de Textual, en anglais, est remplacée par
  « Sélectionner » (traduite).
