# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Firewall preset policies.

Pure domain definitions of predefined firewall profiles (menu 3.4).
A preset describes WHAT a policy allows/blocks in business terms
(chains, actions, protocols, ports) — never HOW it is expressed in
nftables or iptables syntax. Backend adapters translate a FirewallPreset
into their own command language.

No external dependencies beyond domain/rules/models.py.
"""
from dataclasses import dataclass, field
from typing import Optional

from omega_fire.domain.rules.models import RuleAction, RuleChain, RuleProtocol


@dataclass(frozen=True)
class ChainPolicy:
    """Default (base) policy for a chain when a preset is active.

    Example: chain=INPUT, default_action=DROP means "block everything
    on INPUT unless an explicit PresetRule below allows it".
    """
    chain: RuleChain
    default_action: RuleAction


@dataclass(frozen=True)
class PresetRule:
    """A single allow/block rule within a preset.

    Special-purpose flags (loopback_only, match_established) express
    intents that don't map to a simple protocol/port match, and are
    translated by each backend adapter into its own idiom (e.g.
    "iifname lo" in nftables, "-i lo" in iptables; "ct state
    established,related" vs "-m state --state ESTABLISHED,RELATED").

    A rule with multiple ports (ports=[22, 80, 443]) is translated by
    each backend adapter into one independent firewall rule PER PORT,
    never a single grouped rule (nft port set '{ }' or iptables
    '-m multiport'). This keeps every applied port individually
    manageable afterwards (menu 3.2 delete, menu 7.2 restore) — a
    grouped rule can only be removed or restored as a whole.
    """
    chain: RuleChain
    action: RuleAction
    protocol: Optional[RuleProtocol] = None
    ports: Optional[list[int]] = None  # multiple ports (e.g. [22, 80, 443])
    source_cidr: Optional[str] = None
    dest_cidr: Optional[str] = None
    loopback_only: bool = False
    match_established: bool = False


@dataclass(frozen=True)
class FirewallPreset:
    """A complete predefined firewall profile."""
    key: str
    name: str
    description: str
    policy_label: str
    chain_policies: list[ChainPolicy] = field(default_factory=list)
    rules: list[PresetRule] = field(default_factory=list)


PRESETS: dict[str, FirewallPreset] = {
    "1": FirewallPreset(
        key="1",
        name="Moyenne",
        description="Profil Web/SSH standard : SSH (22), HTTP (80), HTTPS (443) autorisés.",
        policy_label="DROP (Restreint)",
        chain_policies=[
            ChainPolicy(chain=RuleChain.INPUT, default_action=RuleAction.DROP),
            ChainPolicy(chain=RuleChain.OUTPUT, default_action=RuleAction.ACCEPT),
        ],
        rules=[
            PresetRule(chain=RuleChain.INPUT, action=RuleAction.ACCEPT, loopback_only=True),
            PresetRule(chain=RuleChain.INPUT, action=RuleAction.ACCEPT, match_established=True),
            PresetRule(
                chain=RuleChain.INPUT,
                action=RuleAction.ACCEPT,
                protocol=RuleProtocol.TCP,
                ports=[22, 80, 443],
            ),
        ],
    ),
    "2": FirewallPreset(
        key="2",
        name="Moyenne (Contrôle Distant)",
        description="Profil Web/SSH standard + accès de secours : SSH (22), HTTP (80), "
                     "HTTPS (443), VNC (5900, 5901), RDP (3389).",
        policy_label="DROP (Restreint)",
        chain_policies=[
            ChainPolicy(chain=RuleChain.INPUT, default_action=RuleAction.DROP),
            ChainPolicy(chain=RuleChain.OUTPUT, default_action=RuleAction.ACCEPT),
        ],
        rules=[
            PresetRule(chain=RuleChain.INPUT, action=RuleAction.ACCEPT, loopback_only=True),
            PresetRule(chain=RuleChain.INPUT, action=RuleAction.ACCEPT, match_established=True),
            PresetRule(
                chain=RuleChain.INPUT,
                action=RuleAction.ACCEPT,
                protocol=RuleProtocol.TCP,
                ports=[22, 80, 443, 5900, 5901, 3389],
            ),
        ],
    ),
    "3": FirewallPreset(
        key="3",
        name="Strict",
        description="Sécurité maximale : Tout est bloqué sauf connexions établies.",
        policy_label="DROP Strict",
        chain_policies=[
            ChainPolicy(chain=RuleChain.INPUT, default_action=RuleAction.DROP),
            ChainPolicy(chain=RuleChain.FORWARD, default_action=RuleAction.DROP),
        ],
        rules=[
            PresetRule(chain=RuleChain.INPUT, action=RuleAction.ACCEPT, loopback_only=True),
            PresetRule(chain=RuleChain.INPUT, action=RuleAction.ACCEPT, match_established=True),
        ],
    ),
    "4": FirewallPreset(
        key="4",
        name="Local (Isolation)",
        description="Isole la machine d'Internet. Autorise uniquement le trafic Local/LAN.",
        policy_label="DROP (Internet)",
        chain_policies=[
            ChainPolicy(chain=RuleChain.INPUT, default_action=RuleAction.DROP),
            ChainPolicy(chain=RuleChain.OUTPUT, default_action=RuleAction.DROP),
        ],
        rules=[
            PresetRule(chain=RuleChain.INPUT, action=RuleAction.ACCEPT, loopback_only=True),
            PresetRule(chain=RuleChain.OUTPUT, action=RuleAction.ACCEPT, loopback_only=True),
            # Réseaux privés RFC 1918 : couvre toutes les configurations LAN
            # possibles, pas seulement une sous-classe arbitraire.
            PresetRule(chain=RuleChain.INPUT, action=RuleAction.ACCEPT, source_cidr="10.0.0.0/8"),
            PresetRule(chain=RuleChain.INPUT, action=RuleAction.ACCEPT, source_cidr="172.16.0.0/12"),
            PresetRule(chain=RuleChain.INPUT, action=RuleAction.ACCEPT, source_cidr="192.168.0.0/16"),
            PresetRule(chain=RuleChain.OUTPUT, action=RuleAction.ACCEPT, dest_cidr="10.0.0.0/8"),
            PresetRule(chain=RuleChain.OUTPUT, action=RuleAction.ACCEPT, dest_cidr="172.16.0.0/12"),
            PresetRule(chain=RuleChain.OUTPUT, action=RuleAction.ACCEPT, dest_cidr="192.168.0.0/16"),
        ],
    ),
    "5": FirewallPreset(
        key="5",
        name="Paranoia",
        description="Isolation absolue : Blocage total entrant, sortant, LAN, Internet et Loopback.",
        policy_label="DROP Total",
        chain_policies=[
            ChainPolicy(chain=RuleChain.INPUT, default_action=RuleAction.DROP),
            ChainPolicy(chain=RuleChain.OUTPUT, default_action=RuleAction.DROP),
            ChainPolicy(chain=RuleChain.FORWARD, default_action=RuleAction.DROP),
        ],
        rules=[],
    ),
    "6": FirewallPreset(
        key="6",
        name="Monitoring",
        description="Autorise Ping/ICMP et métriques de supervision.",
        policy_label="DROP (Supervision)",
        chain_policies=[
            ChainPolicy(chain=RuleChain.INPUT, default_action=RuleAction.DROP),
        ],
        rules=[
            PresetRule(chain=RuleChain.INPUT, action=RuleAction.ACCEPT, protocol=RuleProtocol.ICMP),
            PresetRule(
                chain=RuleChain.INPUT,
                action=RuleAction.ACCEPT,
                protocol=RuleProtocol.TCP,
                ports=[9100],
            ),
        ],
    ),
    "7": FirewallPreset(
        key="7",
        name="Maintenance",
        description="Ouverture totale temporaire pour interventions techniques.",
        policy_label="ACCEPT",
        chain_policies=[
            ChainPolicy(chain=RuleChain.INPUT, default_action=RuleAction.ACCEPT),
            ChainPolicy(chain=RuleChain.OUTPUT, default_action=RuleAction.ACCEPT),
            ChainPolicy(chain=RuleChain.FORWARD, default_action=RuleAction.ACCEPT),
        ],
        rules=[],
    ),
    "8": FirewallPreset(
        key="8",
        name="Server Web & FTP",
        description="Serveur Web + FTP : SSH (22), HTTP (80), HTTPS (443), FTP contrôle (21) "
                     "et plage passive restreinte (30000-30009). Configurer le démon FTP "
                     "(pasv_min_port/pasv_max_port) pour correspondre à cette plage.",
        policy_label="DROP (Restreint)",
        chain_policies=[
            ChainPolicy(chain=RuleChain.INPUT, default_action=RuleAction.DROP),
            ChainPolicy(chain=RuleChain.OUTPUT, default_action=RuleAction.ACCEPT),
        ],
        rules=[
            PresetRule(chain=RuleChain.INPUT, action=RuleAction.ACCEPT, loopback_only=True),
            PresetRule(chain=RuleChain.INPUT, action=RuleAction.ACCEPT, match_established=True),
            PresetRule(
                chain=RuleChain.INPUT,
                action=RuleAction.ACCEPT,
                protocol=RuleProtocol.TCP,
                ports=[22, 80, 443],
            ),
            # FTP séparé dans sa propre règle pour la lisibilité : port de
            # contrôle (21) + plage passive volontairement réduite à 10
            # ports fixes plutôt qu'une vraie plage nft/iptables — chaque
            # port devient une règle indépendante (voir PresetRule
            # docstring), une plage complète (ex. 30000-31000) produirait
            # des centaines de règles distinctes.
            PresetRule(
                chain=RuleChain.INPUT,
                action=RuleAction.ACCEPT,
                protocol=RuleProtocol.TCP,
                ports=[21] + list(range(30000, 30010)),
            ),
        ],
    ),
    "9": FirewallPreset(
        key="9",
        name="Multi-server (Reverse Proxy / Docker)",
        description="Reverse proxy et services conteneurisés : SSH (22), HTTP (80), "
                     "HTTPS (443), et ports d'exposition courants (8000, 8080, 8443).",
        policy_label="DROP (Restreint)",
        chain_policies=[
            ChainPolicy(chain=RuleChain.INPUT, default_action=RuleAction.DROP),
            ChainPolicy(chain=RuleChain.OUTPUT, default_action=RuleAction.ACCEPT),
        ],
        rules=[
            PresetRule(chain=RuleChain.INPUT, action=RuleAction.ACCEPT, loopback_only=True),
            PresetRule(chain=RuleChain.INPUT, action=RuleAction.ACCEPT, match_established=True),
            PresetRule(
                chain=RuleChain.INPUT,
                action=RuleAction.ACCEPT,
                protocol=RuleProtocol.TCP,
                ports=[22, 80, 443, 8000, 8080, 8443],
            ),
        ],
    ),
}


def get_preset(key: str) -> Optional[FirewallPreset]:
    """Get a preset by its menu key ("1" through "9").

    Args:
        key: Preset key as selected in menu 3.4

    Returns:
        FirewallPreset if found, None otherwise
    """
    return PRESETS.get(key)


def list_presets() -> list[FirewallPreset]:
    """Get all presets in a stable, ordered list.

    Sorted numerically (key=int) rather than lexicographically: plain
    string sort would place "10" right after "1" and before "2", which
    silently breaks menu ordering the moment a two-digit key exists.

    Returns:
        List of FirewallPreset, ordered by key (numeric)
    """
    return [PRESETS[k] for k in sorted(PRESETS.keys(), key=int)]


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les 9 profils firewall prédéfinis (menu 3.4) en langage métier
#   pur : politiques par défaut des chaînes, règles d'autorisation/blocage
#   (protocole, ports, source/destination), sans aucune syntaxe nft/iptables.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : qu'est-ce que le profil "Strict" autorise,
#   indépendamment de la façon dont nftables ou iptables l'exprime
# - Aucune dépendance externe hormis domain/rules/models.py (enums)
# - Testable sans aucun backend réel
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas de commande nft/iptables, pas de subprocess
# ❌ Pas d'import depuis infrastructure/, application/, interfaces/
# ❌ Pas de logique d'exécution (juste la structure de données)
# Points clés :
# - ChainPolicy : politique par défaut d'une chaîne (ex: INPUT -> DROP)
# - PresetRule : une règle d'autorisation/blocage au sein d'un profil
#   - loopback_only : intention "autoriser le loopback", traduite par
#     chaque adapter dans son propre idiome (iifname lo / -i lo)
#   - match_established : intention "connexions établies/liées", traduite
#     en "ct state established,related" (nft) ou "-m state --state
#     ESTABLISHED,RELATED" (iptables)
#   - ports : liste de ports (ex: [22, 80, 443]), chaque port devient UNE
#     règle nft/iptables indépendante côté adapter (jamais un set nft
#     groupé ni un -m multiport) — voir docstring de PresetRule
# - FirewallPreset : profil complet (métadonnées + politiques + règles)
# - PRESETS : dictionnaire des 9 profils, clés "1" à "9" (numérotation
#   fixée volontairement le 10/08/2026 — voir liste ci-dessous, ne pas
#   réordonner sans raison documentée dans docs/decisions/)
#     1 Moyenne | 2 Moyenne (Contrôle Distant) | 3 Strict |
#     4 Local (Isolation) | 5 Paranoia | 6 Monitoring | 7 Maintenance |
#     8 Server Web & FTP | 9 Multi-server (Reverse Proxy / Docker)
# - get_preset(key) / list_presets() : accès en lecture, tri numérique
#   (key=int) — pas lexicographique, cassant dès une clé à 2 chiffres
# Comment il sera utilisé (aperçu) :
# - infrastructure/backends/nftables/adapter.py : apply_preset() traduit un
#   FirewallPreset en commandes nft
# - infrastructure/backends/iptables/adapter.py : apply_preset() traduit un
#   FirewallPreset en commandes iptables
# - application/commands/apply_preset.py orchestre la sélection + snapshot
#   + application via l'adapter du backend choisi
# - interfaces/cli/actions.py (menu 3.4) affiche list_presets() pour le choix
#---------------------------------------------------------------------->
