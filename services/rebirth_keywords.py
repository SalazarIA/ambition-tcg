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
# K3 Fortaleza — keywords de payoff defensivo (mudam o INCENTIVO de defender,
# não os números). THORNS pune agressão; ENTRENCH recompensa segurar a linha.
KEYWORD_THORNS = "THORNS"
KEYWORD_ENTRENCH = "ENTRENCH"
KEYWORD_SUNDER = "SUNDER"
# I5 — counter estrutural à Fortaleza: ignora metade da mitigação de Guarda do
# alvo (anti-muralha incondicional, complementar ao SUNDER condicional). Pune
# decks que dependem só de empilhar Guarda, sem nerfar EARTH contra o resto.
KEYWORD_SIEGE = "SIEGE"

ALL_KEYWORDS = (
    KEYWORD_RUSH,
    KEYWORD_BURST,
    KEYWORD_LIFESTEAL,
    KEYWORD_TAUNT,
    KEYWORD_SHIELD,
    KEYWORD_PIERCE,
    KEYWORD_REGEN,
    KEYWORD_EXECUTE,
    KEYWORD_THORNS,
    KEYWORD_ENTRENCH,
    KEYWORD_SUNDER,
    KEYWORD_SIEGE,
)

# Quanto THORNS reflete por golpe (fixo, como BURST=1 — previsível pro balance;
# pode virar opt-in por carta depois). ENTRENCH cresce 1 de Guarda por turno
# defendido (auto-limitado pelo ritmo curto da partida).
THORNS_REFLECT_AMOUNT = 2
ENTRENCH_GROWTH_AMOUNT = 1

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
    KEYWORD_THORNS:    ("Espinhos",   "Quem ataca esta carta sofre 2 de dano na Guarda."),
    KEYWORD_ENTRENCH:  ("Entrincheirar", "Se não atacou no turno anterior, ganha +1 de Guarda permanente."),
    KEYWORD_SUNDER:    ("Ruptura", "Com aliado de outra família, ganha +2 Ataque contra Provocar/Escudo e rompe Escudo."),
    KEYWORD_SIEGE:     ("Cerco", "Ignora metade da Guarda do alvo no cálculo de dano — perfura muralhas."),
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
    KEYWORD_THORNS:    "#6f8f4a",  # verde-musgo espinho
    KEYWORD_ENTRENCH:  "#9a8456",  # terra/pedra muralha
    KEYWORD_SUNDER:    "#b66cff",  # violeta de ruptura midrange
    KEYWORD_SIEGE:     "#d2691e",  # ocre-ferrugem de cerco
}

# Defaults por família — usado por _monster_card quando keywords não
# está sobrescrito pra carta específica.
FAMILY_DEFAULT_KEYWORDS = {
    # Keywords passivas/sutis por família (tier 2+ base).
    "FIRE":    [KEYWORD_RUSH],
    "WATER":   [KEYWORD_LIFESTEAL],
    "EARTH":   [KEYWORD_SHIELD],
    "SHADOW":  [KEYWORD_PIERCE],
    "ARCANO":  [],
    "OCULTO":  [],
}

# K3 re-centro do meta: keywords que a família carrega JÁ NO TIER 1 (identidade
# que não é recompensa de evolução). FIRE = "dano direto / queimadura" → carrega
# BURST (reach) em todos os tiers: é a tecnologia anti-sustain que faltava à
# agressão. Sem isso, controle EARTH+WATER out-healava o campo inteiro
# (round-robin ~0.79). Com BURST=2 em FIRE o eixo AGGRO↔CONTROLE re-centra
# (controle 0.81→0.65) mantendo o macro misto 50/50 e o casual saudável.
# Reverte o nerf v74 (que era do meta antigo, pré-dominância de controle).
FAMILY_TIER1_KEYWORDS = {
    "FIRE": [KEYWORD_BURST],
}

# Evolved cards (tier 2+) ganham 1 keyword extra agressiva.
# BURST removido do default FIRE+ARCANO após v71/v74 balance — dano direto
# automático em todos os evolved quebrava dominance ratio. BURST volta a
# ser opt-in por carta lendária específica (K2/K3). FIRE evolved fica
# apenas com RUSH; balance preservado.
FAMILY_EVOLVED_BONUS_KEYWORD = {
    # Tier 2: ganhos sutis que não quebram balance.
    "FIRE":    None,               # FIRE evoluído mantém apenas RUSH
    "WATER":   KEYWORD_REGEN,      # WATER evoluído: LIFESTEAL + REGEN
    "EARTH":   None,               # EARTH evoluído mantém apenas SHIELD
    "SHADOW":  None,               # SHADOW evoluído mantém apenas PIERCE
    "ARCANO":  None,
    "OCULTO":  None,
}


def default_keywords_for(family: str, *, tier: int = 1) -> List[str]:
    """Retorna a lista canônica de keywords pra uma carta da família
    em determinado tier. Caller pode sobrescrever totalmente.

    Spread escasso por design: tier 1 é baseline limpo, EXCETO as keywords de
    identidade do tier 1 (FAMILY_TIER1_KEYWORDS — hoje só FIRE/BURST como reach).
    Tier 2+ acumula a keyword de família (evolução = upgrade mecânico real);
    TAUNT e EXECUTE seguem opt-in por carta específica/lendária.
    """
    tier1 = list(FAMILY_TIER1_KEYWORDS.get(family, []))
    if int(tier or 1) < 2:
        return tier1
    # Tier 1 keyword sobe pro tier 2+ (dedup preservando ordem) + base + bônus.
    base = list(dict.fromkeys(tier1 + list(FAMILY_DEFAULT_KEYWORDS.get(family, []))))
    bonus = FAMILY_EVOLVED_BONUS_KEYWORD.get(family)
    if bonus is not None and bonus not in base:
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

    K3 re-centro: subido de 1 → 2. O nerf v74 (que capava em 1) era do meta
    antigo; com controle EARTH+WATER dominando o campo por out-heal (~0.79), a
    agressão precisava de reach que furasse a cura. BURST=2 em FIRE re-centra o
    eixo AGGRO↔CONTROLE (0.81→0.65) com macro misto 50/50 e casual saudável
    (medido no lab; ver docs/REBIRTH_DEPTH_WAVES.md).
    """
    return 2 if has_keyword(card, KEYWORD_BURST) else 0


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


def thorns_reflect(card: Dict[str, Any]) -> int:
    """THORNS: dano refletido à Guarda de quem ataca esta carta.

    Pune agressão contra a muralha — atacar uma fortaleza custa caro mesmo
    quando o ataque vence o combate. Engine aplica à current_guard do atacante.
    """
    return THORNS_REFLECT_AMOUNT if has_keyword(card, KEYWORD_THORNS) else 0


def entrench_growth(card: Dict[str, Any]) -> int:
    """ENTRENCH: Guarda permanente ganha por segurar a linha (não atacar).

    Engine consulta no início do turno do dono e só aplica se a carta NÃO
    atacou no turno anterior (caller cuida do gate `has_attacked`).
    """
    return ENTRENCH_GROWTH_AMOUNT if has_keyword(card, KEYWORD_ENTRENCH) else 0


SUNDER_ATTACK_BONUS = 2


def sunder_active(
    card: Optional[Dict[str, Any]],
    owner_field: Optional[List[Dict[str, Any]]],
    defender: Optional[Dict[str, Any]],
) -> bool:
    """Ruptura: ferramenta midrange anti-muralha, condicionada a board misto."""
    if not card or not defender or not has_keyword(card, KEYWORD_SUNDER):
        return False
    if not (forces_target(defender) or shield_absorbs(defender)):
        return False
    family = str(card.get("family") or "").upper()
    return any(
        ally
        and ally.get("instance_id") != card.get("instance_id")
        and str(ally.get("family") or "").upper()
        and str(ally.get("family") or "").upper() != family
        for ally in (owner_field or [])
    )


def total_field_guard(owner_field: List[Dict[str, Any]], *, exclude_instance_id: Optional[str] = None) -> int:
    """Soma a Guarda atual do board do dono — base da win-condition de Fortaleza."""
    total = 0
    for c in (owner_field or []):
        if exclude_instance_id is not None and c.get("instance_id") == exclude_instance_id:
            continue
        total += max(0, int(c.get("current_guard", c.get("guard", 0)) or 0))
    return total


# ─────────────────────────────────────────────────────────────────────
# K2: Sinergias condicionais
# ─────────────────────────────────────────────────────────────────────
# Cartas podem ter um campo `synergy` opcional com a estrutura:
#
#   "synergy": {
#       "condition": "controls_family",  # ou "low_hp", "field_count", "tier_2"
#       "value": "FIRE",                 # parâmetro da condição
#       "effect": {"attack": 2, "guard": 1}  # bônus aplicado quando true
#   }
#
# Engine consulta synergy_active() + apply_synergy_bonus() em momentos chave.

def synergy_active(card: Dict[str, Any], owner_field: List[Dict[str, Any]],
                   owner_hp: int = 30) -> bool:
    """Avalia se a condição de sinergia da carta está satisfeita."""
    if not card:
        return False
    syn = card.get("synergy")
    if not isinstance(syn, dict):
        return False
    condition = str(syn.get("condition") or "")
    value = syn.get("value")
    if condition == "controls_family":
        # Conta cartas no campo do MESMO dono com mesmo family (exceto a própria).
        target_family = str(value or "").upper()
        return any(
            c.get("family") == target_family
            and c.get("instance_id") != card.get("instance_id")
            for c in (owner_field or [])
        )
    if condition == "low_hp":
        threshold = int(value or 10)
        return int(owner_hp or 0) <= threshold
    if condition == "high_hp":
        # Win-condition de inevitabilidade (WATER): com a vida alta que a cura
        # sustenta, fecha o jogo. Espelho do low_hp do atrito SHADOW.
        threshold = int(value or 24)
        return int(owner_hp or 0) >= threshold
    if condition == "field_count":
        threshold = int(value or 2)
        return len([c for c in (owner_field or []) if c.get("instance_id") != card.get("instance_id")]) >= threshold
    if condition == "tier_2":
        # Ativo se controla ao menos 1 carta tier ≥ 2.
        return any(int(c.get("tier", 1) or 1) >= 2 for c in (owner_field or []))
    if condition == "total_guard":
        # Win-condition de Fortaleza: a muralha contra-ataca quando a Guarda
        # somada do board atinge o limiar. Recompensa segurar a linha.
        threshold = int(value or 8)
        return total_field_guard(owner_field, exclude_instance_id=card.get("instance_id")) + \
            max(0, int(card.get("current_guard", card.get("guard", 0)) or 0)) >= threshold
    return False


def synergy_bonus(card: Dict[str, Any]) -> Dict[str, int]:
    """Retorna bônus declarado pela sinergia (zeros se não houver)."""
    if not card:
        return {"attack": 0, "guard": 0}
    syn = card.get("synergy") or {}
    effect = syn.get("effect") or {}
    return {
        "attack": int(effect.get("attack", 0) or 0),
        "guard": int(effect.get("guard", 0) or 0),
    }


def synergy_label(card: Dict[str, Any]) -> Optional[str]:
    """Texto pt-BR descrevendo a sinergia, pra UI tooltip."""
    syn = (card or {}).get("synergy")
    if not isinstance(syn, dict):
        return None
    condition = str(syn.get("condition") or "")
    value = syn.get("value")
    effect = syn.get("effect") or {}
    parts = []
    if effect.get("attack"):
        parts.append(f"+{effect['attack']} Ataque")
    if effect.get("guard"):
        parts.append(f"+{effect['guard']} Guarda")
    bonus = " e ".join(parts) or "bônus"
    if condition == "controls_family":
        return f"Se você controla outro {str(value or '').title()}: {bonus}."
    if condition == "low_hp":
        return f"Se seu HP ≤ {value}: {bonus}."
    if condition == "high_hp":
        return f"Se seu HP ≥ {value}: {bonus}."
    if condition == "field_count":
        return f"Se você tem {value}+ monstros: {bonus}."
    if condition == "tier_2":
        return f"Se controla aliado evoluído: {bonus}."
    if condition == "total_guard":
        return f"Se sua Guarda total ≥ {value}: {bonus}."
    return None
