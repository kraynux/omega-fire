<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
# Gestion des exceptions inter-couches — Omega-Fire

Ce document regroupe l’esprit général, la lecture pratique, les règles de base et le référentiel de traitement des exceptions inter-couches pour le projet **omega-fire**.
L’objectif est de garder des frontières nettes entre le domaine, l’application, l’infrastructure, l’interface et le câblage, tout en permettant une traduction explicite des erreurs quand elles traversent une couche ].

---

## 1. L’esprit

Dans une architecture propre, les exceptions ne sont pas un problème à supprimer, mais un phénomène à **localiser, classifier et traduire** au bon niveau.
Une erreur métier ne doit pas être confondue avec une panne technique, et une erreur technique ne doit pas remonter brute jusqu’à l’utilisateur sans contextualisation.

Le principe directeur est simple : chaque couche lève ses propres erreurs, et toute erreur qui franchit une frontière doit être traduite ou encapsulée.
Quand une erreur est attendue dans un workflow, il est souvent préférable de la modéliser par un résultat explicite plutôt que par une exception brute, surtout dans les cas de validation ou de mode dégradé.

---

## 2. Règles de base

- Le **domaine** lève des exceptions métier pures.
- L’**application** décide si l’erreur devient un échec de cas d’usage, un `Result` ou une exception de contexte.
- L’**infrastructure** capture les erreurs techniques et les encapsule avant de les remonter.
- L’**interface** transforme les erreurs applicatives en messages, statuts ou affichages compréhensibles.
- Le **câblage** (`app/`) ne fait que relier les couches, sans logique de traitement d’erreur métier.

Règle pratique : si une erreur peut être comprise localement, on la traite localement ; si elle franchit une frontière, on la traduit ; si elle représente un état prévu du système, on privilégie un `Result`.

---

## 3. Référentiel des couches

### Domaine

Le domaine contient les erreurs liées aux règles métier, aux invariants et aux validations intrinsèques des objets métier.
Exemples : IP invalide, politique impossible, règle firewall incohérente, état métier contradictoire.

Règle :
- ne jamais importer d’erreur d’infrastructure dans le domaine ;
- ne jamais utiliser le domaine pour signaler une panne de système ;
- ne lever que des erreurs qui expriment une réalité métier.

### Application

L’application orchestre les cas d’usage et gère les erreurs de scénario : validation d’entrée, capacité absente, backend indisponible, rollback impossible, exécution partielle.
C’est la couche la plus naturelle pour attraper les erreurs du domaine et les erreurs techniques encapsulées, puis décider de la réponse finale du cas d’usage.

Règle :
- vérifier la validité du request object ;
- retourner un échec structuré si l’entrée est invalide ;
- traduire les exceptions techniques en erreur applicative stable ;
- ne jamais appeler un backend concret directement si un port existe.

### Infrastructure

L’infrastructure parle au monde réel : commandes système, fichiers, services, SQLite, backend firewall, parsing de sortie, accès réseau .
Elle est autorisée à lever des erreurs techniques, mais elle doit les encapsuler ou les transformer avant de les transmettre vers le haut.

Règle :
- capturer les exceptions bas niveau ;
- enrichir le contexte si nécessaire ;
- ne pas propager brute une erreur de commande, de fichier ou de DB vers l’application ou l’interface.

### Interface

L’interface transforme les erreurs applicatives en expérience utilisateur lisible : message, couleur, état de menu, statut HTTP, code de sortie.
Elle ne doit pas réinterpréter le métier ; elle consomme une erreur déjà qualifiée par l’application.

Règle :
- afficher l’erreur finalisée ;
- convertir l’erreur en statut ou message adapté au canal ;
- ne pas décider seule de la sémantique métier.

### Core / Shared

`core/` peut contenir des exceptions transverses et structurantes, par exemple des erreurs liées au registre de capacités ou au modèle global.
`shared/` ne doit contenir que des exceptions réellement génériques, utilitaires et non métier.

Règle :
- le code partagé reste neutre ;
- une exception spécifique métier n’a pas sa place dans `shared/` ;
- un problème structurel commun à toute l’application peut vivre dans `core/`.

### Plugins

Les plugins doivent être considérés comme des extensions isolables.
Une erreur de plugin ne doit pas détruire le cœur applicatif : elle doit être détectée, signalée et, si possible, neutralisée par le manager de plugins ou le bootstrap.

---

## 4. Lecture pratique

### Cas 1 — erreur métier pure
Un objet métier invalide, une politique impossible ou une IP mal formée doivent lever une exception métier au niveau du domaine.
L’application peut la convertir en échec structuré du cas d’usage ou la faire remonter dans un format cohérent.

### Cas 2 — erreur technique
Un `nft` qui échoue, un fichier de log manquant ou une base SQLite indisponible relèvent de l’infrastructure.
Ces erreurs doivent être capturées, traduites et re-émises sous forme d’erreur stable, jamais laissées brutes jusqu’à l’interface.

### Cas 3 — erreur de validation
Une requête mal formée, un paramètre absent ou un filtre incohérent doivent être rejetés avant l’exécution du cas d’usage.
C’est le rôle des request objects et de la validation applicative.

### Cas 4 — erreur attendue de workflow
Un backend absent, une capacité disqualifiée ou un mode dégradé actif ne sont pas toujours des exceptions fatales.
Dans ces cas, un `Result` explicite ou un échec applicatif bien typé est souvent meilleur qu’une exception intrusive.

---

## 5. Tableau récapitulatif

| Couche émettrice | Type d’exception | Déclencheur typique | Couche qui traite | Traitement attendu | Destination possible |
|---|---|---|---|---|---|
| `domain/` | Exception métier | Règle invalide, invariant violé, politique incompatible | `application/` | Capturer, convertir en échec de cas d’usage ou en `Result` d’erreur  | Message métier, skip contrôlé, refus explicite |
| `application/` | Exception de cas d’usage | Backend absent, action interdite, pipeline non exécutable  | `interfaces/` | Traduire en affichage, code de sortie, état de menu ou mode dégradé | Menu grisé, erreur lisible, log applicatif |
| `infrastructure/` | Exception technique | Commande système échouée, fichier manquant, SQLite indisponible, service arrêté | `application/` | Encapsuler ou mapper vers une erreur stable du système métier | Backend indisponible, stockage non joignable |
| `interfaces/` | Erreur d’entrée ou de rendu | Saisie invalide, interaction impossible, rendu non disponible | `application/` | Rejouer, corriger, redemander ou transformer en erreur de validation d’usage | Prompt de correction, retour au menu |
| `core/` | Exception transverse | État impossible du registre, contradiction structurelle | `application/` et `interfaces/` | Traiter comme erreur structurante, souvent fatale pour l’opération courante | Arrêt contrôlé, rescan, alerte |
| `shared/` | Exception générique partagée | Erreur utilitaire commune non métier | Couche appelante immédiate | Gérer localement, ne pas propager sans contexte | Parsing, validation générique |
| `plugins/` | Erreur de chargement ou d’activation | Plugin invalide, dépendance manquante, cycle de vie cassé  | `app/` ou `application/` | Isoler le plugin, désactiver l’extension, conserver le système principal | Plugin ignoré, extension non chargée |

---

## 6. Règles de traduction

- Une exception métier ne doit jamais être confondue avec une panne technique.
- Une exception technique ne doit jamais remonter brute jusqu’à l’interface sans traduction.
- Un cas d’usage doit retourner une structure connue, même en cas d’échec, pour éviter les comportements implicites.
- Un échec attendu dans le flux de travail peut être représenté par un `Result` au lieu d’une exception .
- Toute couche ne capture que ce qu’elle sait interpréter ; le reste doit être recontextualisé ou encapsulé.

---

## 7. Règles opérationnelles pour omega-fire

- `domain/` lève des erreurs métier pures.
- `application/` valide les requêtes, orchestre les cas d’usage et transforme les erreurs en réponses cohérentes.
- `infrastructure/` encapsule les erreurs des backends, du système de fichiers et des services.
- `interfaces/` affiche des erreurs déjà qualifiées et ne décide pas du métier.
- `core/` et `shared/` restent des zones de soutien, pas des dépôts d’erreurs métier spécifiques.
- Le pipeline peut choisir entre arrêt, skip, dégradation ou rollback selon le type d’erreur.
---

## 8. Règle finale

Toute exception qui traverse une frontière doit le faire avec un sens clair, un type clair et un niveau de contexte suffisant.
Si l’erreur est attendue, on la modélise ; si elle est technique, on l’encapsule ; si elle est métier, on la garde dans le domaine ; si elle doit être affichée, on la traduit pour l’utilisateur.
