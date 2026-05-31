"""K1: Sistema de keywords mecânicas pro Ambitionz Rebirth.

Keywords são modificadores táticos atomicos que cartas portam (lista de
strings em `card.keywords`). Diferente de `ability_key` (uma assinatura
narrativa única por carta), keywords são reutilizáveis e compõem:
uma mesma carta pode ter RUSH + LIFESTEAL, por exemplo.

Os hooks abaixo são chamados pelo engine nos momentos certos:

  • can_attack_this_turn(card, just_summoned)   → bool
       Decide se a carta pode atacar no turno em que foi invocada (RUSH).

  • on_summon(card, owner_side, state)          → list[event]
       Dispara ao invocar (BURST = dano direto, REGEN = heal inicial, etc).

  • modify_outgoing_damage(card, target, dmg)   → (new_dmg, pierce_amount)
       Modifica dano que A causa em B. PIERCE retorna excedente que vai
       direto pro HP do dono de B em vez de parar na guard.

  • modify_incoming_damage(card, dmg)           → (new_dmg, absorbed_event)
       Modifica dano que A recebe. SHIELD ignora 1ª hit, REGEN restaura X.

  • on_damage_dealt(card, owner_side, dmg, state) → list[event]
       Após causar dano. LIFESTEAL heal proporcional, BLEED stack, etc.

  • forces_target(card)                         → bool
       TAUNT: inimigo não pode ignorar essa carta. Engine valida target.

  • execute_threshold(card, target)             → int | None
       EXECUTE: insta-kill se target.guard + target.hp ≤ threshold.

Atribuição por família (default; cartas individuais podem sobrescrever):
  FIRE    → RUSH, BURST, EXECUTE              (agressivo, pressão imediata)
  WATER   → LIFESTEAL, REGEN                  (sustento, recuperação)
  EARTH   → TAUNT, SHIELD                     (defensivo, controle)
  SHADOW  → PIERCE, LIFESTEAL                 (corrosivo, perfurante)
  ARCANO  → BURST, PIERCE                     (alpha strike)
  OCULTO  → SHIELD, EXECUTE                   (preserva e finaliza)
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple


# Catálogo canônico — Engine usa estas constantes (case-sensitive).
KEYWORD_RUSH = "RUSH"
KEYWORD_BURST = "BURST"
KEYWORD_LIFESTEAL = "LIFESTEAL"
KEYWORD_TAUNT = "TAUNT"
KEYWORD_SHIELD = "SHIELD"
KEYWORD_PIERCE = "PIERCE"
KEYWORD_REGEN = "REGEN"
KEYWORD_EXECUTE = "EXECUTE"

ALL_KEYWORDS = (
    KEYWORD_RUSH,
    KEYWORD_BURST,
    KEYWORD_LIFESTEAL,
    KEYWORD_TAUNT,
    KEYWORD_SHIELD,
    KEYWORD_PIERCE,
    KEYWORD_REGEN,
    KEYWORD_EXECUTE,
)

# Descrições em pt-BR pra UI tooltip + listagem.
KEYWORD_LABELS = {
    KEYWORD_RUSH:      ("Investida",  "Pode atacar no turno em que é invocado."),
    KEYWORD_BURST:     ("Detonação",  "Causa 2 de dano direto ao oponente ao ser invocado."),
    KEYWORD_LIFESTEAL: ("Drenar",     "Recupera HP igual ao dano causado em combate."),
    KEYWORD_TAUNT:     ("Provocar",   "Inimigos devem atacar esta carta primeiro."),
    KEYWORD_SHIELD:    ("Escudo",     "Ignora a primeira instância de dano recebida."),
    KEYWORD_PIERCE:    ("Perfurar",   "Dano excedente sobre Guarda vai direto pro HP."),
    KEYWORD_REGEN:     ("Regenerar",  "Restaura 1 de Guarda no início do turno do dono."),
    KEYWORD_EXECUTE:   ("Executar",   "Mata instantaneamente alvos com Guarda ≤ 1."),
}

# Cor (CSS var --rb-gold/cyan/etc) usada pra colorir badge na UI.
KEYWORD_COLORS = {
    KEYWORD_RUSH:      "#ff6b3c",  # fogo vivo
    KEYWORD_BURST:     "#ffb22e",  # explosão
    KEYWORD_LIFESTEAL: "#7aa758",  # verde sustento
    KEYWORD_TAUNT:     "#c4a050",  # bronze taunt
    KEYWORD_SHIELD:    "#8aa6c8",  # azul aço
    KEYWORD_PIERCE:    "#c43030",  # vermelho perfuração
    KEYWORD_REGEN:     "#6ad29a",  # verde claro recuperação
    KEYWORD_EXECUTE:   "#a85cff",  # roxo execute
}

# Defaults por família — usado por _monster_card quando keywords não
# está sobrescrito pra carta específica.
FAMILY_DEFAULT_KEYWORDS = {
    "FIRE":    [KEYWORD_RUSH],
    "WATER":   [KEYWORD_LIFESTEAL],
    "EARTH":   [KEYWORD_TAUNT],
    "SHADOW":  [KEYWORD_PIERCE],
    "ARCANO":  [KEYWORD_BURST],
    "OCULTO":  [KEYWORD_SHIELD],
}

# Evolved cards (tier 2+) ganham 1 keyword extra agressiva.
# BURST removido do default FIRE+ARCANO após v71/v74 balance — dano direto
# automático em todos os evolved quebrava dominance ratio. BURST volta a
# ser opt-in por carta lendária específica (K2/K3). FIRE evolved fica
# apenas com RUSH; balance preservado.
FAMILY_EVOLVED_BONUS_KEYWORD = {
    "FIRE":    KEYWORD_EXECUTE,    # FIRE evoluído: RUSH + EXECUTE (finisher)
    "WATER":   KEYWORD_REGEN,      # WATER evoluído: LIFESTEAL + REGEN
    "EARTH":   KEYWORD_SHIELD,     # EARTH evoluído: TAUNT + SHIELD
    "SHADOW":  KEYWORD_LIFESTEAL,  # SHADOW evoluído: PIERCE + LIFESTEAL
    "ARCANO":  KEYWORD_PIERCE,
    "OCULTO":  KEYWORD_EXECUTE,
}


def default_keywords_for(family: str, *, tier: int = 1) -> List[str]:
    """Retorna a lista canônica de keywords pra uma carta da família
    em determinado tier. Caller pode sobrescrever totalmente."""
    base = list(FAMILY_DEFAULT_KEYWORDS.get(family, []))
    if tier >= 2:
        bonus = FAMILY_EVOLVED_BONUS_KEYWORD.get(family)
        if bonus and bonus not in base:
            base.append(bonus)
    return base


# ─────────────────────────────────────────────────────────────────────
# Engine hooks — funções puras consultadas pelo combat resolution.
# Todas retornam estruturas serializáveis (sem mutar state).
# ─────────────────────────────────────────────────────────────────────

def has_keyword(card: Optional[Dict[str, Any]], keyword: str) -> bool:
    if not card:
        return False
    return keyword in (card.get("keywords") or [])


def can_attack_this_turn(card: Dict[str, Any], *, just_summoned: bool) -> bool:
    """RUSH: ignora summoning sickness."""
    if not just_summoned:
        return True
    return has_keyword(card, KEYWORD_RUSH)


def on_summon_burst(card: Dict[str, Any]) -> int:
    """BURST: dano direto ao oponente ao invocar.

    Calibrado em 1 após v74 balance tests apontarem que valores ≥2
    quebram o teto de dominance ratio (>0.7). Pode subir após sinergias
    K2 trazerem counter-play.
    """
    return 1 if has_keyword(card, KEYWORD_BURST) else 0


def lifesteal_heal_amount(card: Dict[str, Any], damage_dealt: int) -> int:
    """LIFESTEAL: heal proporcional ao dano causado."""
    if not has_keyword(card, KEYWORD_LIFESTEAL):
        return 0
    return max(0, int(damage_dealt or 0))


def pierce_overflow(card: Dict[str, Any], damage: int, target_guard: int) -> int:
    """PIERCE: excedente de dano sobre guard escapa pro HP."""
    if not has_keyword(card, KEYWORD_PIERCE):
        return 0
    overflow = int(damage or 0) - int(target_guard or 0)
    return max(0, overflow)


def has_taunt_on_side(cards: List[Dict[str, Any]]) -> bool:
    """TAUNT: existe alguma carta com taunt no lado defensor?"""
    return any(has_keyword(c, KEYWORD_TAUNT) for c in (cards or []))


def forces_target(card: Dict[str, Any]) -> bool:
    return has_keyword(card, KEYWORD_TAUNT)


def shield_absorbs(card: Dict[str, Any]) -> bool:
    """SHIELD: primeira hit ignorada. Chamador deve setar flag
    `shield_consumed` na carta após usar."""
    if not has_keyword(card, KEYWORD_SHIELD):
        return False
    return not bool(card.get("shield_consumed"))


def regen_amount(card: Dict[str, Any]) -> int:
    """REGEN: Guarda restaurada no início do turno do dono."""
    return 1 if has_keyword(card, KEYWORD_REGEN) else 0


def execute_kills(card: Dict[str, Any], target: Optional[Dict[str, Any]]) -> bool:
    """EXECUTE: insta-kill se target.guard ≤ 1."""
    if not target or not has_keyword(card, KEYWORD_EXECUTE):
        return False
    return int(target.get("guard", 99) or 99) <= 1
