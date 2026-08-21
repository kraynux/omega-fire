<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
# Charte d’architecture

Omega-Fire est structuré selon une architecture en couches inspirée de Clean Architecture et du modèle Ports & Adapters. Les dépendances de code pointent toujours vers l’intérieur : le domaine et les cas d’usage ne dépendent jamais des détails d’interface, de stockage, de rendu ou d’exécution système.

L’objectif de cette architecture est de préserver un cœur métier stable, testable et indépendant des outils concrets comme nft, iptables, fail2ban-client, systemd, Rich ou SQLite.

## Règle de dépendance

La règle centrale du projet est la suivante : **aucune couche interne ne doit connaître une couche plus externe**. Une dépendance existe dès qu’un module importe, référence ou appelle directement un élément d’une autre couche, ce qui signifie que les violations peuvent apparaître même sans couplage “visible” dans l’exécution.

### Règles applicables :

- `domain/` ne dépend d’aucune autre couche.
- `application/` peut dépendre de `domain/` et des contrats internes comme `ports/` et `core/`, mais jamais d’une implémentation concrète.
- `infrastructure/` peut dépendre des couches internes nécessaires pour implémenter les contrats, mais aucune couche interne ne dépend d’elle.
- `interfaces/` dépend de `application/` pour exécuter les cas d’usage et afficher leurs résultats, sans appeler directement les backends concrets.
- `app/` assemble les composants et démarre l’application, sans contenir de logique métier.

## Responsabilités

Chaque couche a une responsabilité unique :

- `core/` définit les concepts transverses : capacités, statuts, résultats, exceptions globales, registre.
- `domain/` porte la logique métier par sous-domaine : blacklist, règles, fail2ban, logs, rapports, monitoring.
- `application/` orchestre les cas d’usage : commandes, requêtes, pipeline, guards, hooks, DTO.
- `ports/` définit les contrats attendus par le cœur applicatif.
- `infrastructure/` implémente les accès concrets au système, aux fichiers, à SQLite, aux exporteurs et aux backends.
- `interfaces/` gère l’interaction utilisateur CLI/TUI et le rendu Rich.
- `shared/` contient uniquement des utilitaires transverses non métier.
- `plugins/` permet l’extension dynamique du système sans modifier le cœur.

## Règles projet

Les règles suivantes sont obligatoires :

- Aucun module de `domain/` ne doit importer un module de `application/`, `interfaces/` ou `infrastructure/`.
- Aucun module de `application/` ne doit importer un adapter concret depuis `infrastructure/backends/`, `infrastructure/storage/` ou `infrastructure/exporters/`.
- Toute interaction réelle avec le système passe par `infrastructure/` via un contrat défini dans `ports/`.
- Toute décision de rendu utilisateur passe par `interfaces/`, jamais par `domain/` ou `infrastructure/`.
- `shared/` ne doit pas devenir un dossier fourre-tout ; si un code exprime une règle métier, il doit vivre dans `domain/` ou `application/`.

## Règles fonctionnelles

### Pour les capacités :

- la détection technique est réalisée dans `infrastructure/probe/`;
- la consolidation vit dans `core/capability_registry.py`;
- l’autorisation d’exécution est décidée par les guards dans `application/pipeline/guards/`;
- le grisage ou l’activation d’un menu est projeté par `interfaces/cli/tree_builder.py`.

### Pour les exports :

- `domain/reports/` construit le contenu logique;
- `infrastructure/exporters/` écrit le format concret JSON, TXT ou HTML;
- `interfaces/cli/` propose à l’utilisateur le format, le chemin et les options.

### Pour le pipeline :

- `application/pipeline/` orchestre les étapes, guards, hooks et rollback;
- les actions réelles sont effectuées à travers des ports implémentés par `infrastructure/`;
- aucune commande système ne doit être appelée directement depuis un cas d’usage sans passer par un port.

## Critères de validation

Avant d’ajouter un fichier, il faut pouvoir répondre clairement à ces questions :

- Est-ce une règle métier ? Alors il va dans `domain/`.
- Est-ce un scénario applicatif ou un workflow ? Alors il va dans `application/`.
- Est-ce un contrat attendu par le cœur ? Alors il va dans `ports/`.
- Est-ce une implémentation concrète ou un accès système ? Alors il va dans `infrastructure/`.
- Est-ce du rendu, de la navigation ou de l’interaction utilisateur ? Alors il va dans `interfaces/`.
- Est-ce du câblage et du démarrage ? Alors il va dans `app/`.

## Discipline d’évolution

Toute nouvelle fonctionnalité doit d’abord être pensée en termes de capacité métier, cas d’usage, contrat, puis implémentation. On évite d’introduire directement un nouvel appel système, un nouveau format ou un nouveau backend sans l’inscrire d’abord dans cette chaîne de responsabilités.

Une violation ponctuelle peut parfois sembler pratique à court terme, mais elle fragilise immédiatement la testabilité, le mode dégradé et le mécanisme de grisage. La cohérence d’Omega-Fire repose donc moins sur le nombre de modules que sur le respect strict des frontières entre couches.
