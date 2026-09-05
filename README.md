<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->

<div align="center">
  <img src="docs/assets/omega-fire.png" alt="Omega-Fire" width="256">
</div>

# 󰦝 OMEGA-FIRE

**Poste de gestion unifié de la sécurité réseau**

> Élaboré par **kraynux** pour **Omega-server** 
[https://kraynux.snake-mackarel.ts.net](https://kraynux.snake-mackarel.ts.net)

Page officiel : [OMEGA-FIRE](https://kraynux.snake-mackarel.ts.net/omega-fire/) &nbsp; Apercu : [Screenshots](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/)  

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)
[![Interface](https://img.shields.io/badge/Interface-Textual%20TUI-cyan.svg)](https://github.com/Textualize/textual)

🇫🇷 **Français** · 🇬🇧 [English](README.en.md) · 🇪🇸 [Español](README.es.md) · 🇷🇺 [Русский](README.ru.md) · 🇨🇳 [中文](README.zh.md)

---

**Omega-Fire** est une application TUI (Terminal User Interface) Python construite avec [Textual](https://github.com/Textualize/textual). Elle fournit depuis un terminal une interface unique pour administrer les pare-feux Linux, Fail2Ban, les adresses bannies, les règles réseau, les journaux et les statistiques système.

L'interface Textual est le mode de fonctionnement par défaut et navigue par menus, formulaires validés (tous les champs requis sont vérifiés avant de continuer) et écrans dédiés, avec thèmes, aide contextuelle et raccourcis clavier partagés avec le reste de la suite OMEGA (omega-check, omega-deep, omega-stress...). L'ancienne interface [Rich](https://github.com/Textualize/rich), séquentielle et pilotée par saisie de numéros, reste disponible via `--legacy-cli` (voir [Lancement](#lancement)).

Le projet est conçu selon les principes de la **Clean Architecture**, avec une séparation claire entre domaine métier, orchestration, infrastructure et interface utilisateur.

## Sommaire

- [Présentation](#présentation)
- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Configuration](#configuration)
- [Backends et compatibilité](#backends-et-compatibilité)
- [Persistance, logs et exports](#persistance-logs-et-exports)
- [Sécurité](#sécurité)
- [Tests et qualité](#tests-et-qualité)
- [État du projet](#état-du-projet)
- [Désinstallation](#désinstallation)
- [Licence](#licence)

---

## Présentation

Omega-Fire agit comme un **poste de pilotage local** pour la sécurité réseau. Il détecte automatiquement les composants présents sur la machine et adapte les menus aux capacités réellement disponibles.

### Objectifs

- Réunir nftables, iptables, ip6tables et Fail2Ban dans une interface cohérente.
- Faciliter l'observation et l'action sur les connexions, les bannissements et les événements système.
- Centraliser les exports, les sauvegardes, les audits et l'historique des opérations.
- Conserver une architecture testable et extensible.
- Fonctionner en mode dégradé lorsqu'un composant optionnel est absent.

### Ce que fait Omega-Fire

- Détecte les backends, services, noyau et outils disponibles.
- Administre nftables, iptables et ip6tables lorsque ces composants sont présents.
- Gère les IP bannies, seules ou par lots, avec import, export, synchronisation et flush.
- Crée, liste et supprime des règles avancées.
- Applique des politiques prédéfinies avec sauvegarde automatique préalable.
- Administre les jails Fail2Ban et leurs bannissements.
- Analyse les logs en direct ou sous forme de statistiques.
- Propose de la surveillance sous forme de monitoring.
- Utilise conntrack pour afficher les connexions actives lorsqu'il est disponible.
- Produit des exports JSON, TXT et HTML.
- Sauvegarde et restaure l'état complet dans des archives `.tar.gz`.
- Journalise les opérations dans un journal applicatif et un audit JSON structuré.
- Surveille les services et applications détectés : systemd, runit, OpenRC, Docker, serveurs, VNC, etc.

### Ce que le projet ne fait pas

- Il ne remplace pas nftables, iptables ou Fail2Ban.
- Il ne constitue pas un pare-feu autonome indépendant du système.
- Il ne fournit pas d'authentification multi-utilisateur.
- Il n'expose pas d'API réseau en fonctionnement normal.
- Il ne s'agit pas d'un dashboard web.
- Il ne protège pas directement une machine distante depuis une autre machine.
- Il n'installe par défaut aucun fichier en dehors de son propre dossier.
- Il ne garantit pas la disponibilité de tous les backends sur toutes les distributions.

---

## Fonctionnalités

### 1. Capacités et diagnostics

- Affichage du registre des capacités détectées.
- Consultation détaillée d'une capacité par identifiant.
- Re-scan manuel du système après installation d'un composant.
- Consultation des diagnostics récents.
- Consultation et recherche dans le journal applicatif.
- Export de l'état et des diagnostics en JSON, TXT ou HTML.

### 2. Gestion unifiée des IP

La blacklist unifiée permet de travailler avec nftables et iptables depuis un même écran.

- Bannissement d'une IP ou d'une liste d'IPs.
- Débannissement individuel ou par lots.
- Saisie directe ou import depuis un fichier.
- Liste par backend ou vue unifiée.
- Synchronisation entre les backends NFTables/IPTables.
- Export et réimport des listes.
- Nettoyage complet d'un ou plusieurs backends.
- Prise en charge IPv4 et IPv6.
- Gestion des fichiers de blocklist (`var/blocklist/`) et de leurs épingles directement depuis l'écran dédié.

### 3. Gestion des règles et politiques

- Assistant pas à pas pour créer une règle avancée.
- Liste des règles système et des règles créées par Omega-Fire.
- Suppression d'une règle par sélection.
- Nettoyage automatique des règles inactives dans la base de référence.
- Application de politiques prédéfinies.
- Sauvegarde automatique avant application d'une politique.
- Personnalisation, sauvegarde et restauration d'une politique.
- Identification de la politique active dans le menu de statut et le dashboard.
- Signalement des profils modifiés sous la forme `Profil + CUSTOM`.

### 4. Gestion Fail2Ban

- État détaillé des jails et de leurs paramètres.
- Nombre d'IPs bannies et informations de rate-limit.
- Recherche d'une IP dans les jails.
- Ban et unban individuels ou multiples.
- Transfert d'IPs entre jails, backends et fichiers.
- Création guidée d'un jail personnalisé.
- Modèles de jails prédéfinis.
- Suppression d'un jail.
- Vidage d'un jail ou purge générale.
- Export en JSON, TXT ou HTML.
- Vérification et audit de configuration.
- Contrôle du service : statut, démarrage, arrêt, redémarrage, activation et désactivation au démarrage.

### 5. Logs et maintenance

- Live Tail avec tableau de bord Omega-Fire.
- Affichage multi-fichiers avec épingles (sources favorites, persistées entre deux lancements).
- Intégration de `lnav` : sélection d'un ou plusieurs fichiers (numéros ou chemins manuels, séparés par des virgules), fusion automatique en une seule vue chronologique, encapsulé dans un header/footer Omega-Fire (voir [Navigation](#navigation)).
- Analyse des IPs les plus fréquentes avec Top N.
- Nettoyage ciblé d'une IP dans des fichiers LOG ou TXT.
- Rotation et sauvegardes immédiates ou automatisées.
- Restauration d'un backup.
- Purge selon ancienneté, quota, type ou sélection manuelle.
- Nettoyage avancé par dossier ou environnement.
- Statistiques sur 24 heures, 7 jours ou 30 jours.
- Analyse des événements, mouvements, quotas et IPs présentes dans les jails.

### 6. Exports et rapports

Formats disponibles :

- **JSON** : données structurées et réutilisables.
- **TXT** : format brut ou adapté à l'injection.
- **HTML** : rapport lisible et visuel.

Rapports disponibles :

- Blacklist complète.
- Ruleset structuré.
- Règles sélectionnées par provenance : système, Omega-Fire ou actives.
- Rapport d'audit complet.
- Statistiques Fail2Ban.
- État et diagnostics système.
- Rapports statistiques sur 7 ou 30 jours.

Thèmes HTML :

- `omega-base` — bleu nuit et cyan, thème par défaut.
- `omega-burn` — braise rouge-orangé.
- `omega-neon` — cyberpunk cyan et magenta.
- `light-basic` — clair et sobre.
- `light-alt` — papier crème et vert forêt.

### 7. Système et persistance

- Sauvegarde de l'état complet : règles, bans nftables, bans iptables et Fail2Ban.
- Création d'archives `.tar.gz` horodatées.
- Liste et restauration des snapshots.
- Historique des actions.
- Filtrage et purge de l'historique.
- Rechargement de configuration et re-scan sans redémarrage.

### 8. Monitoring et statistiques

- Dashboard temps réel avec rafraîchissement périodique (toutes les 2 secondes), sans blocage de l'interface pendant la collecte.
- Visualisation de la politique active.
- Connexions actives via conntrack.
- Trafic, événements, statistiques et logs serveur.
- Rapports consolidés sur 7 et 30 jours.
- Export HTML des snapshots et rapports.

### 9. Réglages

- Choix du thème actif parmi les dix thèmes `omega-*` partagés avec le reste de la suite (voir [Thèmes et terminaux](#thèmes-et-terminaux)), persisté entre deux lancements.
- Surcharge manuelle du profil de rendu (automatique, complet, standard, réduit ou mono seul), appliquée au prochain lancement.
- Accessible depuis le menu principal (`9. RÉGLAGES`) ou directement via la touche `s`.

---

## Architecture

```text
src/omega_fire/
├── app/              Bootstrap et conteneur d'injection de dépendances
├── core/             Capacités, énumérations et exceptions
├── domain/           Logique métier pure : règles, IPs, jails, logs
├── application/      Orchestration : commands et queries
├── infrastructure/   Backends, stockage, exports, logs et sondes système
├── ports/            Contrats Protocol/ABC
├── interfaces/       interfaces/tui/ (Textual, par défaut) + interfaces/cli/ (Rich, --legacy-cli)
├── plugins/          Extensions intégrées : nftables, iptables, Fail2Ban, conntrack
└── shared/           Parsing, réseau, formatage et utilitaires transverses
```

### Principes de conception

- `domain/` ne contient ni I/O ni dépendance vers l'infrastructure.
- `application/` orchestre les cas d'usage via le domaine et les ports — les écrans Textual et les actions de l'interface Rich appellent les mêmes commands/queries, la logique métier ne dépend d'aucune des deux interfaces.
- `infrastructure/` est la seule couche autorisée à appeler `nft`, `iptables`, `fail2ban-client` et les autres outils externes (subprocess, pty, fichiers).
- `interfaces/` ne doit pas appeler directement `subprocess`.
- `ports/` définit les contrats attendus par les adaptateurs.
- `core/` fournit le registre de capacités utilisé par les différentes couches.
- Les plugins permettent d'ajouter ou de faire évoluer les backends sans modifier le domaine métier.
- L'interface Textual (`interfaces/tui/`) s'appuie sur [`omega-lib`](https://github.com/) (dépendance partagée par toute la suite OMEGA : thème à 9 tokens, détection de terminal, contrats de port communs), non publiée sur PyPI — vendorée dans l'archive distribuable (`vendor/omega-lib/`, voir [Installation](#installation)).
- Tout appel potentiellement lent (backend firewall, `fail2ban-client`, disque) déclenché depuis un écran Textual s'exécute en tâche de fond (thread), jamais sur le thread principal de l'interface — un dashboard ou un formulaire reste réactif pendant l'opération plutôt que de figer toute l'application.

### Structure des données

Omega-Fire utilise SQLite via la bibliothèque standard `sqlite3`, sans ORM externe. Les principaux ensembles de données concernent les bans, règles, événements d'audit et snapshots.

Les migrations sont versionnées et appliquées automatiquement au démarrage.

---

## Prérequis

### Système

- Linux, en priorité Arch Linux et distributions compatibles.
- Python 3.10 ou supérieur.
- Privilèges root disponibles via `sudo`.
- Un gestionnaire de services : systemd, runit ou OpenRC.
- Au moins un backend firewall : nftables ou iptables.
- Un terminal d'au moins 80x24 (voir [Thèmes et terminaux](#thèmes-et-terminaux) pour le détail des profils de rendu selon la taille disponible).

### Dépendances Python

Les dépendances de production sont définies dans `requirements.txt` :

- `textual` — interface TUI par défaut.
- `omega-lib` — thème, détection de terminal et contrats partagés avec la suite OMEGA (non publiée sur PyPI, voir [Architecture](#architecture) et [Installation](#installation)).
- `rich` — rendu de l'interface `--legacy-cli` et de certains rapports.
- `psutil` — informations système (CPU, mémoire, réseau, processus) pour le dashboard et les diagnostics.
- `jinja2` — génération des exports HTML.
- `python-dotenv` — variables d'environnement.
- `pyte` — émulateur de terminal virtuel, pour l'encapsulation `lnav` (menus 5.9/8.6).

Les outils de qualité (`pytest`, `black`, `flake8`, `mypy`) sont listés en commentaire dans `requirements.txt` : décommentez-les ou installez-les séparément si vous contribuez au projet (voir [Tests et qualité](#tests-et-qualité)).

### Outils optionnels recommandés

L'application fonctionne en mode dégradé si ces outils sont absents :

- `fail2ban` — bannissement automatisé.
- `conntrack` ou `conntrack-tools` — connexions actives et statistiques réseau.
- `lnav` — analyse avancée et multi-fichiers des logs.

Sur Arch Linux et dérivés :

```bash
sudo pacman -S fail2ban conntrack-tools lnav
```

---

## Installation

L'archive officielle est fournie au format `.tar.gz`. Vérifiez son intégrité avant installation :

```bash
sha256sum omega-fire.tar.gz
```

> ⚠️ **Ces trois méthodes servent à une première installation.** Si `~/omega-fire` existe déjà (mise à jour d'une version précédente), utilisez la section [Mise à jour](#mise-à-jour) ci-dessous — ne relancez jamais ces commandes depuis l'intérieur d'un dossier `omega-fire` existant : `tar` tenterait de créer un `omega-fire/omega-fire/` imbriqué et échouerait avec des erreurs de permission si ce dossier appartient à root (fréquent si une extraction précédente a été faite par erreur avec `sudo tar`).

### Méthode 1 — script d'installation

```bash
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Vous semblez déjà être dans un dossier omega-fire — voir la section Mise à jour du README." >&2; exit 1; }
[ -d omega-fire ] && echo "ℹ️ Déjà extrait ici, étape ignorée." || tar -xzf omega-fire.tar.gz
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire existe déjà, déplacement ignoré." || mv omega-fire ~/
cd ~/omega-fire/
chmod +x install.sh
./install.sh
```

Lancement :

```bash
./omega-fire.sh
```

Si l'alias a été installé, ouvrez un nouveau terminal puis utilisez :

```bash
fire
```

### Méthode 2 — installation complète résiliente

Cette commande peut être relancée : elle ignore les étapes déjà réalisées.

```bash
([ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Vous semblez déjà être dans un dossier omega-fire — voir la section Mise à jour du README." >&2; exit 1; }; [ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire existe déjà, extraction ignorée." || (tar -xzf omega-fire.tar.gz && mv omega-fire ~/)) && cd ~/omega-fire/ && ([ -d .venv ] && echo "ℹ️ .venv existe déjà, étape ignorée." || python3 -m venv .venv) && source .venv/bin/activate && ([ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib || true) && pip install -r requirements.txt && chmod +x omega-fire.sh && mkdir -p var && (getent group omega-fire >/dev/null 2>&1 && echo "ℹ️ Groupe omega-fire déjà présent." || sudo groupadd omega-fire) && (groups "$USER" 2>/dev/null | grep -qw omega-fire && echo "ℹ️ $USER déjà membre du groupe omega-fire." || sudo usermod -aG omega-fire "$USER") && sudo chgrp -R omega-fire var && sudo chmod -R 2775 var && echo "✅ Omega-Fire installé. Lancez ./omega-fire.sh."
```

### Méthode 3 — installation détaillée

```bash
# 0. Vérifier qu'on ne relance pas depuis l'intérieur d'un omega-fire existant
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Vous semblez déjà être dans un dossier omega-fire — voir la section Mise à jour du README." >&2; exit 1; }

# 1. Extraire
[ -d omega-fire ] && echo "ℹ️ Déjà extrait ici, étape ignorée." || tar -xzf omega-fire.tar.gz

# 2. Déplacer dans le home
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire existe déjà, déplacement ignoré." || mv omega-fire ~/

# 3. Entrer dans le projet
cd ~/omega-fire/

# 4. Créer l'environnement virtuel
[ -d .venv ] && echo "ℹ️ .venv existe déjà, création ignorée." || python3 -m venv .venv

# 5. Installer les dépendances (omega-lib vendorée, si présente, avant requirements.txt)
source .venv/bin/activate
[ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib
pip install -r requirements.txt

# 6. Rendre le lanceur exécutable
chmod +x omega-fire.sh

# 7. Préparer var/ pour root et l'utilisateur courant
mkdir -p var
getent group omega-fire >/dev/null 2>&1 || sudo groupadd omega-fire
groups "$USER" 2>/dev/null | grep -qw omega-fire || sudo usermod -aG omega-fire "$USER"
sudo chgrp -R omega-fire var
sudo chmod -R 2775 var

# 8. Lancer
./omega-fire.sh
```

`vendor/omega-lib/` n'est présent que dans l'archive officielle (`build-release.sh` l'y intègre automatiquement, car omega-lib n'est pas publiée sur PyPI) ; en clone de développement, installez-la séparément depuis son propre dépôt (`pip install -e chemin/vers/omega-lib`).

Le groupe dédié et le bit `setgid` permettent à root et à l'utilisateur de partager les fichiers produits dans `var/` sans ouvrir les permissions à l'ensemble du système. Une nouvelle connexion ou `newgrp omega-fire` peut être nécessaire pour bénéficier immédiatement de l'appartenance au groupe.

### Mise à jour

Si `~/omega-fire` existe déjà (installation précédente), **ne relancez jamais les commandes d'installation depuis l'intérieur de ce dossier** : `tar` tenterait de créer un `omega-fire/omega-fire/` imbriqué et échouerait, généralement avec une cascade d'erreurs « Permission non accordée » si le dossier appartient à `root` (cas fréquent si une extraction précédente a été faite par erreur avec `sudo tar`).

Procédure recommandée, depuis n'importe quel dossier **autre que `~/omega-fire`** (typiquement `~` lui-même) :

```bash
# 1. Vérifier l'état et le propriétaire de l'installation existante
ls -ld ~/omega-fire

# 2. Mettre l'ancienne installation de côté plutôt que l'écraser
sudo mv ~/omega-fire ~/omega-fire.old-$(date +%Y%m%d)

# 3. Extraire la nouvelle archive directement dans le home
tar -xzf omega-fire.tar.gz -C ~/

# 4. Réinstaller (recrée le venv, réinstalle les dépendances, refait les permissions var/)
cd ~/omega-fire
chmod +x install.sh
./install.sh

# 5. Lancer
./omega-fire.sh
```

Une fois la nouvelle installation validée, l'ancien dossier `~/omega-fire.old-AAAAMMJJ` peut être supprimé (`sudo rm -rf ~/omega-fire.old-AAAAMMJJ`).

### Alias Bash ou Zsh

```bash
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.bashrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.bashrc
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.zshrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.zshrc
```

Rechargez ensuite le shell :

```bash
source ~/.bashrc 2>/dev/null || source ~/.zshrc
```

### Icônes et symboles Nerd Fonts

Si les icônes ne sont pas disponibles, installez les symboles Nerd Fonts :

```bash
mkdir -p ~/.local/share/fonts
curl -fLo /tmp/NerdFontsSymbolsOnly.zip \
  https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip
unzip -o /tmp/NerdFontsSymbolsOnly.zip -d ~/.local/share/fonts
fc-cache -fv
```

---

## Utilisation

### Lancement

```bash
cd ~/omega-fire
./omega-fire.sh

# ou simplement, si l'alias a été créé :
fire
```

Le lanceur :

1. Vérifie les privilèges root et relance via `sudo` si nécessaire.
2. Détecte `.venv`, `venv` ou Python système.
3. Configure `PYTHONPATH` vers `src/`.
4. Lance `python -m omega_fire` — l'interface **Textual**, par défaut.

Pour lancer l'ancienne interface Rich (saisie séquentielle de numéros) à la place :

```bash
./omega-fire.sh --legacy-cli
```

### Parcours général

1. Écran de démarrage (splash), puis avertissement si le terminal est trop petit.
2. Détection des capacités système (écran dédié, non bloquant).
3. Menu principal : 8 sections thématiques (1-8) plus les réglages (9).
4. Sélection d'une section, puis d'une action — chaque action ouvre un formulaire dont tous les champs requis sont validés avant de continuer.
5. Confirmation explicite avant toute opération sensible ou destructive (flush, purge, restauration...).
6. Exécution en tâche de fond pour les opérations lentes (l'interface reste utilisable pendant l'attente), puis retour au menu avec un résumé du résultat.

### Navigation

- Flèches haut/bas : déplacer le curseur dans une liste ou un menu.
- Tab / Maj+Tab : naviguer entre les champs d'un formulaire.
- Entrée : sélectionner ou valider.
- Cliquer une ligne d'un tableau : la sélectionner et pré-remplir les champs concernés (source à épingler, jail ciblé, etc.).
- `Échap` : revenir à l'écran précédent (demande confirmation de sortie depuis l'accueil).
- `a` : aide contextuelle — détaille l'action en cours, ou la totalité des actions de la section courante si aucun écran d'action n'est encore ouvert.
- `t` : passer au thème suivant, sans confirmation.
- `r` : redétecter la taille et la famille du terminal.
- `s` : ouvrir les réglages (thème, profil de rendu).
- `q` / `Ctrl+Q` : quitter, avec confirmation.

#### Particularités de l'écran lnav (5.9 / 8.6)

`lnav` est encapsulé dans un pseudo-terminal avec un header/footer Omega-Fire persistants autour de sa propre vue, pour éviter toute collision entre ses raccourcis natifs et ceux d'Omega-Fire :

- Flèches ↑↓ : naviguer dans les logs (raccourci natif `lnav`, transmis tel quel).
- Flèches ←→ : défiler horizontalement sur les lignes longues (raccourci natif `lnav`).
- `g` / `G` : aller au début / à la fin (raccourci natif `lnav`).
- `Ctrl+C` : marquer la ligne courante et la copier dans le presse-papier système (remplace la commande native de copie de `lnav`, qui peut se bloquer sur certains systèmes).
- `t` minuscule : thème suivant, propre à cette vue (le `T` majuscule reste le raccourci natif de `lnav` pour afficher le temps écoulé entre les lignes).
- `Ctrl+Q` : revenir à Omega-Fire (ferme `lnav` proprement, sans quitter l'application).

---

## Thèmes et terminaux

Dix thèmes `omega-*` sont partagés avec le reste de la suite OMEGA :

```text
omega-base       omega-dark       omega-light
omega-neon       omega-burn       omega-pink
omega-hack       omega-contrast   omega-mono
omega-minimal
```

- Basculez entre les thèmes avec `t`, ou choisissez-en un directement depuis les réglages (`s`).
- Le thème choisi est persisté et retrouvé au prochain lancement.
- Omega-Fire adapte automatiquement la complexité visuelle (bordures, splash, densité d'information) au terminal détecté via un **profil de rendu** : Complet, Standard, Réduit ou Mono (ASCII seul). Le profil peut être surchargé manuellement depuis les réglages.

| Taille minimale | Profil | Terminaux typiques |
|---|---|---|
| 120×32 ou plus | Complet | Ghostty, Alacritty, WezTerm, Kitty |
| 100×28 ou plus | Standard | Konsole, GNOME Terminal, Terminator, xfce4-terminal |
| 80×24 ou plus | Réduit | urxvt, xterm, SSH moderne |
| en dessous de 80×24 | Mono (ASCII seul) | Linux TTY, SSH ancien |

En dessous de 80×24, le lancement est refusé (taille minimale requise) ; redimensionnez le terminal puis relancez, ou utilisez `r` après redimensionnement si l'affichage ne s'est pas mis à jour automatiquement.

---

## Configuration

La configuration spécifique peut être ajustée dans :

```text
omega-fire/config/omega-fire.conf
```

Elle peut notamment définir :

- chemins des journaux ;
- serveurs et sources de monitoring ;
- backends disponibles ou chemins personnalisés ;
- environnements à analyser ;
- paramètres adaptés à une installation particulière.

La configuration est relue au redémarrage ou lors d'un re-scan manuel (menu 1.3 ou 7.4).

### Chemins internes et chemins système

Par défaut, Omega-Fire travaille dans son propre dossier :

```text
var/exports/       # dossier interne au projet
/var/exports/      # chemin absolu du système
```

Le `/` initial est donc significatif. Les imports et exports vers le système doivent être demandés explicitement par l'utilisateur.

---

## Backends et compatibilité

Omega-Fire détecte les composants et active uniquement les fonctionnalités utilisables.

| Composant | Rôle | Statut |
|---|---|---|
| nftables | Pare-feu IPv4/IPv6 moderne | Recommandé |
| iptables | Pare-feu IPv4 | Compatible |
| ip6tables | Pare-feu IPv6 avec iptables | Compatible si disponible |
| Fail2Ban | Jails et bannissements automatisés | Optionnel |
| conntrack | Connexions actives | Optionnel |
| lnav | Analyse avancée des logs | Optionnel |
| systemd, runit, OpenRC | Gestion des services | Détection automatique |
| Docker, VNC, serveurs | Applications et services détectés | Selon installation |

### IPv4 et IPv6

Les deux familles d'adresses sont prises en charge par les backends compatibles :

- nftables : IPv4 et IPv6 en dual stack ;
- iptables/ip6tables : selon les binaires disponibles ;
- Fail2Ban : selon la configuration du jail et du système.

Les formats IPv6 longs, compressés, locaux, mixtes, avec zéros et en notation CIDR sont traités par les composants concernés.

---

## Persistance, logs et exports

### Persistance

- SQLite via `sqlite3`.
- Tables relatives aux bans, règles, audits et snapshots.
- Migrations versionnées appliquées automatiquement.
- Archives d'état complet au format `.tar.gz`.
- Épingles (sources de logs favorites) et historique récent persistés en JSON (`var/runtime/`), survivent à un redémarrage.

### Journaux

- Journal texte applicatif : `var/logs/app.log`.
- Journal d'audit JSON structuré avec notamment `event_type`, `actor`, `action`, `result` et `details`.

### Exports

Les exports sont disponibles en JSON, TXT et HTML, avec plusieurs thèmes CSS pour les rapports HTML.

---

## Sécurité

Omega-Fire agit sur des composants critiques du système et doit être utilisé avec prudence.

- Le lancement requiert des privilèges root via `sudo`.
- Le flush, la purge générale et l'application d'une politique peuvent être destructifs.
- Une politique prédéfinie déclenche une sauvegarde automatique avant modification.
- Réalisez une sauvegarde manuelle avant chaque changement majeur.
- Vérifiez l'état réel du firewall, des jails et des connexions après chaque opération.
- Testez d'abord sur une machine ou une cible jetable.
- Utilisez les réseaux de documentation RFC 5737 pour les essais IPv4 : `192.0.2.0/24`, `198.51.100.0/24` et `203.0.113.0/24`.
- Vérifiez les exports et snapshots avant de les restaurer sur une machine de production.
- N'accordez pas de permissions plus larges que nécessaire au dossier `var/`.

---

## Tests et qualité

Le projet compte une suite historique de 152 tests unitaires, écrite avant la migration Textual : elle couvre le domaine métier, l'orchestration (`application/`), l'infrastructure et l'interface Rich (`interfaces/cli/`), mais **ne couvre pas encore `interfaces/tui/`** (l'interface Textual par défaut). Cette archive ne contient pas le dossier `tests/` : récupérez-le depuis votre dépôt de développement si besoin de l'exécuter.

```bash
source .venv/bin/activate
python -m unittest discover tests/unit -v
```

Comme l'architecture en couches sépare strictement le domaine métier de la présentation (`domain/`, `application/`, `ports/` en `Protocol`, voir [Architecture](#architecture)), cette suite reste valide sans changement malgré la migration : seule l'interface Textual, plus récente, n'a pas encore sa propre couverture dédiée.

Si vous contribuez au projet, installez les outils de qualité déclarés (en commentaire) dans `requirements.txt` :

```bash
pip install pytest pytest-cov black flake8 mypy
```

Outils disponibles une fois installés :

```bash
black .
flake8 .
mypy src/
pytest --cov
```

---

## État du projet

### Points opérationnels

- TUI Textual unifiée pour les principaux mécanismes de sécurité réseau, formulaires validés, thèmes et aide contextuelle partagés avec la suite OMEGA.
- Interface Rich historique conservée en repli (`--legacy-cli`).
- Détection automatique des capacités.
- Gestion des backends disponibles.
- Support IPv4/IPv6 selon les outils présents.
- Journalisation applicative et audit.
- Sauvegarde et restauration.
- Exports JSON, TXT et HTML.
- Dashboard et statistiques, rafraîchis en tâche de fond sans bloquer l'interface.
- Architecture en couches documentée.

### Limites connues

- La suite de tests (152) ne couvre pas encore l'interface Textual (`interfaces/tui/`), écrite après elle (voir [Tests et qualité](#tests-et-qualité)).
- Le mécanisme `ExecutionPlan`/`PipelineStep` reste partiellement conservé dans le projet.
- La disponibilité exacte des fonctionnalités dépend des binaires, services, permissions et configurations de la machine hôte.
- L'interface Rich historique (`--legacy-cli`) n'est plus l'axe de développement actif ; elle est conservée le temps de fiabiliser totalement l'interface Textual en conditions réelles.

---

## Désinstallation

Si les données sont restées dans le dossier du projet :

```bash
sudo rm -rf ~/omega-fire
```

Supprimez manuellement les fichiers exportés ailleurs, les éventuels alias `fire` ajoutés dans `~/.bashrc` ou `~/.zshrc`, ainsi que le groupe dédié si celui-ci n'est plus utilisé :

```bash
sudo groupdel omega-fire
```

N'exécutez cette dernière commande que si aucun autre fichier ou service ne dépend de ce groupe.

---

## Licence

Omega-Fire est distribué sous licence **MIT**. Consultez le fichier [`LICENSE`](LICENSE) pour le texte complet.

---

> **Omega-Fire — Observer, piloter, auditer, sécuriser.**
>
> Une interface TUI unifiée pour nftables, iptables, ip6tables, Fail2Ban, les logs et le monitoring réseau.
