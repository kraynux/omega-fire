<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
# Référentiel : hiérarchie d'exceptions pour Omega‑Fire

But : fournir une nomenclature stable et explicite pour les erreurs, faciliter la traduction inter‑couches et rendre les tests / logs plus clairs.

Remarque : n’utiliser ces classes que comme guide — adapte les noms si tu as déjà des conventions dans le projet.

---

## Arborescence proposée (nom de classe — fichier recommandé — rôle)

- Core exceptions (fichier : `src/omega_fire/core/exceptions.py`)
  - `OmegaFireError` (base de toutes les exceptions spécifiques au projet)
    - usage : racine commune pour attraper tout ce qui est lié à l’app.
  - `CapabilityRegistryError` (core/errors)
    - usage : problème structurel avec le registre (contradiction d’état, corruption).
  - `ConfigurationError`
    - usage : erreurs de configuration ou lecture `.env` invalide.

- Shared / Utilitaires (fichier : `src/omega_fire/shared/exceptions.py`)
  - `SharedError` (hérite de `OmegaFireError`)
  - `ValidationError` (pour utilitaires génériques)
    - usage : parsing non‑métier, validation utilitaire (date mal formée, parse JSON).
  - `ResourceNotFoundError`
    - usage : fichier attendu non trouvé dans utilitaires, ressource externe manquante.

- Domain (par sous‑domaine, ex : `src/omega_fire/domain/ip_blacklist/exceptions.py`, etc.)
  - `DomainError` (hérite de `OmegaFireError`)
    - usage : base pour erreurs métier.
  - `InvalidEntityError` (Domain)
    - usage : objet métier invalide (ex : IP mal formée, CIDR invalide).
  - `PolicyConflictError`
    - usage : tentative d’appliquer une politique incompatible (ex : maintenance vs monitoring).
  - `DomainInvariantViolation`
    - usage : invariant métier violé.

- Application (fichier : `src/omega_fire/application/exceptions.py`)
  - `ApplicationError` (hérite de `OmegaFireError`)
    - usage : base pour erreurs liées aux cas d’usage / pipeline.
  - `UseCaseExecutionError`
    - usage : erreur générale d’exécution d’un cas d’usage qui n’est ni strictement métier ni strictement technique.
  - `CapabilityUnavailableError`
    - usage : tentative d’utiliser une capacité marquée `MISSING` ou `DISQUALIFIED`.
  - `PermissionDeniedError`
    - usage : utilisateur ou contexte sans droit d’exécution.
  - `PartialExecutionError`
    - usage : exécution partielle acceptée (mode dégradé), inclut détails des sous‑étapes échouées.
  - `RollbackError`
    - usage : rollback échoué après une étape partiellement accomplie.

- Infrastructure (par adaptateur, ex : `src/omega_fire/infrastructure/backends/nftables/exceptions.py`)
  - `InfrastructureError` (hérite de `OmegaFireError`)
    - usage : base des erreurs techniques.
  - `CommandExecutionError`
    - usage : sortie non nulle d’une commande shell (ex : `nft`, `iptables-save`, `fail2ban-client`), inclure stdout/stderr dans le contexte.
  - `ServiceUnavailableError`
    - usage : daemon inaccessible (ex : fail2ban daemon down, systemd refusant l’action).
  - `StorageError`
    - usage : erreur d’I/O, corruption SQLite, verrous bloquants.
  - `ParseError`
    - usage : impossibilité de parser la sortie d’un binaire (ex : parser nft/iptables).
  - `AdapterConfigurationError`
    - usage : configuration d’adapter invalide ou manquante.

- Interfaces (fichier : `src/omega_fire/interfaces/exceptions.py`)
  - `InterfaceError` (hérite de `OmegaFireError`)
  - `UserInputError`
    - usage : saisie invalide, validation prompt.
  - `RenderError`
    - usage : échec du rendu (Rich/TUI) ou problème d’affichage.

- Plugins (fichier : `src/omega_fire/plugins/exceptions.py`)
  - `PluginError` (hérite de `OmegaFireError`)
  - `PluginLoadError`
    - usage : erreur pendant la découverte ou l’import d’un plugin.
  - `PluginActivationError`
    - usage : échec d’initialisation ou de cycle de vie.

---

## Principes de conception et bonnes pratiques

- Héritage clair : chaque sous‑couche a une base (DomainError, ApplicationError, InfrastructureError) qui hérite de `OmegaFireError`. Cela permet d’attraper facilement toutes les exceptions applicatives ou projet‑wide sans confondre les types [lecture pratique].
- Exception ≠ résultat : modélise les échecs attendus (capacité manquante, action non autorisée) comme `Result` contrôlé quand c’est prévu ; réserve les exceptions aux cas anormaux ou inattendus [règles de base].
- Enrichir le contexte : quand infrastructure capture une erreur (p.ex. `CommandExecutionError`), fournis stdout/stderr, exit code, commande et chemin de travail; facilite le debug et la décision d’application [infrastructure → application].
- Chainer proprement : utiliser `raise NewError(...) from exc` pour préserver la trace originale lors de la traduction d’erreurs [règles de traduction].
- Petite sémantique : préférer des classes fines (ex : `CapabilityUnavailableError`) plutôt qu’un unique `ApplicationError` trop générique — cela aide la prise de décision dans les guards et le pipeline.
- Mapping explicite : toujours mapper une erreur technique à une erreur applicative nommée avant de la propager vers `interfaces/`. Exemple : `CommandExecutionError` → `CapabilityUnavailableError` ou `UseCaseExecutionError` avec raison.
- Logs & audit : loguer l’erreur brute (niveau DEBUG/ERROR selon criticité) dans l’infrastructure, et loguer l’erreur contextualisée (info + user message) au niveau application/hook audit.

---

## Exemples d’usage (séquences)

1. Exécution d’une commande nft qui échoue :
   - `nft` renvoie code ≠ 0 → `infrastructure.backends.nftables.CommandExecutionError` (contient stdout/stderr, cmd).
   - Adapter capture et traduit : `InfrastructureError` → `CapabilityUnavailableError` (application) ou `UseCaseExecutionError` selon le contexte.
   - Pipeline (`application`) décide : skip / mode dégradé / rollback ; déclenche hooks d’audit.
   - Interface affiche message lisible : "Backend nftables indisponible : action non effectuée".

2. Tentative de bannir une IP invalide :
   - Validation initiale dans `application` détecte IP mal formée → `InvalidRequest` ou `ValidationError` (application) ou propagation d`InvalidEntityError` du domaine.
   - Interface renvoie prompt d’erreur et ne lance pas le pipeline.

3. Plugin externe ne charge pas :
   - Import échoue → `plugins.PluginLoadError`.
   - Manager isole le plugin, le marque `disabled`, écrit log audit et poursuit le démarrage sans planter l’application.

---

## Emplacement des fichiers recommandés

- `src/omega_fire/core/exceptions.py` : `OmegaFireError`, `CapabilityRegistryError`, `ConfigurationError`.
- `src/omega_fire/shared/exceptions.py` : `SharedError`, `ValidationError`, `ResourceNotFoundError`.
- `src/omega_fire/domain/<subdomain>/exceptions.py` : `DomainError`, `InvalidEntityError`, `PolicyConflictError`, ...
- `src/omega_fire/application/exceptions.py` : `ApplicationError`, `UseCaseExecutionError`, `CapabilityUnavailableError`, `PermissionDeniedError`, `PartialExecutionError`, `RollbackError`.
- `src/omega_fire/infrastructure/.../exceptions.py` : `InfrastructureError`, `CommandExecutionError`, `ServiceUnavailableError`, `StorageError`, `ParseError`.
- `src/omega_fire/interfaces/exceptions.py` : `InterfaceError`, `UserInputError`, `RenderError`.
- `src/omega_fire/plugins/exceptions.py` : `PluginError`, `PluginLoadError`, `PluginActivationError`.

---

## Checklist rapide (pour la PR)

- [ ] Chaque exception ajoutée a une place logique dans la hiérarchie.
- [ ] Les exceptions techniques sont capturées dans `infrastructure/` et traduites avant remontée.
- [ ] Les erreurs attendues du flux sont modélisées par `Result` quand pertinent.
- [ ] Les exceptions incluent contexte utile (cmd, stdout, chemin, ID de transaction).
- [ ] Les traductions utilisent `raise ... from ...` pour préserver la trace.
- [ ] Les messages destinés à l’utilisateur sont produits uniquement par `application/` ou `interfaces/`.

---


