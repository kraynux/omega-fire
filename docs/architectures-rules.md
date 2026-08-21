<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
# Référentiel de règles — Omega-Fire

Ce document sert de support de conception, de rappel opérationnel et de base de revue pour le projet **omega-fire**.  
La règle directrice est la suivante : les dépendances de code pointent vers l’intérieur, et les couches internes ne connaissent jamais les détails des couches externes.

## 1. Règles de structure

- `src/omega_fire/` contient uniquement le code Python importable.
- `var/` reste à la racine du projet, jamais dans `src/`, car il contient le runtime, les caches, les exports et les backups.
- `docs/` contient les documents de référence, les décisions d’architecture et les guides d’usage.
- `tests/` reflète les couches et les cas d’usage du projet.
- `app/` ne sert qu’au démarrage, au câblage et au cycle de vie.

## 2. Règles de dépendance

- `domain/` ne dépend d’aucune couche externe.
- `application/` dépend de `domain/` et des contrats, jamais des implémentations concrètes.
- `infrastructure/` implémente les contrats et parle au système réel.
- `interfaces/` appelle `application/` et affiche les résultats, sans logique métier.
- `shared/` reste limité aux utilitaires réellement transverses.
- `plugins/` étend le système sans casser le cœur.
- Les dépendances de code pointent toujours vers l’intérieur.

## 3. Règles de responsabilité

- `core/` définit le vocabulaire commun : capacités, statuts, résultats, exceptions globales, constantes.
- `domain/` porte la logique métier du pare-feu, des règles, de fail2ban, des logs, des rapports et du monitoring.
- `application/` orchestre les cas d’usage, les workflows, les guards, les hooks et les DTO.
- `ports/` définit les contrats attendus par le cœur applicatif.
- `infrastructure/` fournit les adaptateurs concrets : probes, backends, stockage, exporteurs, logging, configuration.
- `interfaces/` gère l’expérience utilisateur : menu, arbre, rendu, navigation, prompts.
- `app/` assemble tout et ne décide rien du métier.

## 4. Règles de capacités

- La détection des capacités se fait dans `infrastructure/probe/`.
- Le registre central des capacités vit dans `core/capability_registry.py`.
- Le grisage et l’activation des actions se décident via `application/pipeline/guards/`.
- L’arbre de menu conditionnel se construit dans `interfaces/cli/tree_builder.py`.
- Une capacité absente, dégradée ou disqualifiée ne doit jamais être appelée comme si elle était disponible.
- Le registre de capacités est la source de vérité unique.

## 5. Règles d’exécution

- Toute action importante passe par `application/pipeline/`.
- Les guards vérifient la capacité, les permissions et les conditions d’exécution.
- Les hooks gèrent l’audit, les métriques et les notifications.
- Le pipeline peut autoriser un mode dégradé, un skip ou un rollback.
- Aucun appel système direct ne doit contourner les ports.

## 6. Règles d’exports

- `domain/reports/` construit le contenu logique du rapport.
- `infrastructure/exporters/` écrit le fichier dans le format demandé.
- `interfaces/cli/` demande à l’utilisateur le format et le chemin.
- Les templates HTML restent séparés du code Python.
- Les exports JSON, TXT et HTML doivent raconter la même réalité métier.

## 7. Règles de persistance

- Les fichiers temporaires, caches, backups et bases runtime restent dans `var/`.
- Les migrations doivent être versionnées.
- SQLite ne doit pas être mélangé au métier.
- Les chemins de runtime ne doivent pas être codés en dur dans la logique métier.
- La persistance doit rester remplaçable sans impact sur le domaine.

## 8. Règles de plugins

- `plugins/loader.py` découvre les extensions.
- `plugins/manager.py` gère leur cycle de vie.
- `plugins/builtin/` contient les extensions internes.
- `plugins/external/` reste réservé aux plugins tiers.
- Un plugin ne doit jamais imposer sa logique au domaine.
- L’extensibilité ne doit pas casser le cœur applicatif.

## 9. Règles de rendu

- `interfaces/cli/` ne prend pas de décision métier.
- Le rendu Rich affiche l’état, mais ne le fabrique pas.
- Le menu conditionnel est dérivé des capacités.
- Le grisage reflète un état, il ne le définit pas.
- L’interface traduit le métier en interaction, jamais l’inverse.

## 10. Règles d’exceptions

- Le domaine lève des exceptions métier.
- L’infrastructure lève des exceptions techniques puis les encapsule.
- L’application décide de la traduction, du fallback ou du skip.
- L’interface affiche des messages finalisés et compréhensibles.
- Une exception brute ne doit pas franchir une frontière sans transformation.
- Les erreurs attendues peuvent être modélisées par un résultat explicite plutôt que par une exception.

## 11. Règles de qualité

- Chaque nouvelle fonctionnalité doit être rangée dans la bonne couche avant de coder.
- Chaque changement doit respecter la séparation entre métier, orchestration, contrat, implémentation et rendu.
- Toute revue de PR doit vérifier les dépendances, la localisation du code et la cohérence du mode dégradé.
- Toute violation de frontière doit être considérée comme un défaut d’architecture.
- Une bonne PR rend l’ensemble plus clair, pas plus couplé.

## 12. Règles de lecture rapide

- Si c’est une règle métier, c’est `domain/`.
- Si c’est une orchestration, c’est `application/`.
- Si c’est un contrat, c’est `ports/`.
- Si c’est une implémentation concrète, c’est `infrastructure/`.
- Si c’est de l’UI, c’est `interfaces/`.
- Si c’est du câblage, c’est `app/`.
- Si c’est transversal mais non métier, c’est `shared/`.
- Si c’est une extension, c’est `plugins/`.

## 13. Règle finale

- Le cœur du projet doit rester compréhensible sans connaître la technologie précise utilisée dessous.
- Toute décision technique doit rester remplaçable.
- Toute évolution doit préserver la lisibilité des frontières.
- Toute exception inter-couches doit être traduite ou encapsulée.
- Tout ce qui casse ces règles doit être considéré comme un problème d’architecture.
