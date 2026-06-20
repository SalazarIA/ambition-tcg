from copy import deepcopy
from enum import Enum
import hashlib
import secrets

from services.rebirth_domain import CARD_SET_VERSION, ENGINE_VERSION, REDUCER_VERSION, RULESET_VERSION
from services.rebirth_contracts import FIELD_SLOT_COUNT, PHASE_CHOOSE
from services.rebirth_cards import BOT_DECK, PLAYER_DECK, build_deck
from services.rebirth_bot import choose_personality, difficulty_payload, personality_payload
from services.rebirth_events import append_event, append_snapshot, ensure_event_contract


STARTING_HP = 30
# Bot HP no primeiro duelo: encurta a partida em ~40% sem alterar regras de
# mana/curva, mantendo a noção de "partida real" mas com janela de vitória
# muito mais visível para o jogador novo.
FIRST_DUEL_BOT_HP = 18
HAND_SIZE = 5
REDUCER_INLINE_RUNTIME_MODES = {"replay", "audit", "network_sync", "pvp_sync"}


class TurnPhase(Enum):
    DRAW_PHASE = "DRAW_PHASE"
    MAIN_PHASE = "MAIN_PHASE"
    COMBAT_PHASE = "COMBAT_PHASE"
    END_PHASE = "END_PHASE"


class RebirthStateError(ValueError):
    pass


def _match_id(seed=None):
    # When no seed is supplied we MUST NOT collapse every match onto the same
    # id. Pre-fix, seed=None hashed the literal "rebirth-default-seed", so all
    # guest matches shared id rebirth-963745ae6ffc — concurrent guests
    # overwrote each other in MATCH_STORE and choose_personality always picked
    # the same profile. Generate fresh entropy instead.
    source = secrets.token_hex(16) if seed is None else str(seed)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]
    return f"rebirth-{digest}"


def create_player(name, owner, card_ids=None, starting_hp=STARTING_HP):
    starting_hp = max(1, int(starting_hp or STARTING_HP))
    return {
        "name": name,
        "hp": starting_hp,
        "max_hp": starting_hp,
        "energy": 2,
        "max_energy": 2,
        "deck": build_deck(owner, card_ids=card_ids),
        "hand": [],
        "battlefield": [],
        "field": [None for _ in range(FIELD_SLOT_COUNT)],
        "discard": [],
        "played_card": None,
        "traps": [],
        "statuses": {},
        "wounded": False,
    }


def field_slots(side):
    raw_slots = side.get("field")
    raw_slots = raw_slots if isinstance(raw_slots, list) else []
    seen = set()
    compact = []
    for source in (side.get("battlefield", []), raw_slots):
        for card in source or []:
            if not card:
                continue
            key = card.get("instance_id") or card.get("id") or id(card)
            if key in seen:
                continue
            seen.add(key)
            compact.append(card)

    slots = [None for _ in range(FIELD_SLOT_COUNT)]
    # Respect a valid occupied position; cards without placement metadata take
    # the first open position within the authoritative three-slot field.
    for card in compact[:FIELD_SLOT_COUNT]:
        card["exhausted"] = bool(card.get("exhausted", False))
        card["has_attacked"] = bool(card.get("has_attacked", False))
        # A recorded attack always consumes its action, even when the mirrored
        # action-lock flag is absent from stored state.
        card["has_acted"] = bool(card.get("has_acted", card["has_attacked"]))
        card["just_summoned"] = bool(card.get("just_summoned", False))
        raw = card.get("field_slot")
        index = int(raw) if isinstance(raw, int) or (isinstance(raw, str) and raw.isdigit()) else None
        if index is None or not (0 <= index < FIELD_SLOT_COUNT) or slots[index] is not None:
            index = next((i for i, slot in enumerate(slots) if slot is None), None)
        if index is None:
            break
        slots[index] = card
        card["field_slot"] = index
        card["slot"] = index + 1
    side["field"] = slots
    return slots


def compact_battlefield(side):
    side["battlefield"] = [card for card in field_slots(side) if card]
    return side["battlefield"]


def draw_card(player):
    if not player["deck"]:
        return None
    card = player["deck"].pop(0)
    player["hand"].append(card)
    return card


def draw_to_hand_size(player, hand_size=HAND_SIZE):
    drawn = []
    while len(player["hand"]) < hand_size:
        card = draw_card(player)
        if not card:
            break
        drawn.append(card)
    return drawn


def shuffle_deck(player, *, seed, owner, salt=""):
    """Embaralha o deck inteiro de forma deterministica a partir da seed.

    Todo deck (padrao ou loadout custom) passa por aqui ANTES da compra
    inicial — a ordem do loadout nunca pode ser a ordem de compra, senao a
    partida vira um script conhecido e exploravel.
    """
    source = str(seed or "rebirth")
    side = str(owner or player.get("name") or "side")
    extra = str(salt or "")
    player["deck"] = sorted(
        player.get("deck") or [],
        key=lambda card: hashlib.sha256(
            f"{source}|{side}|{extra}|{card.get('instance_id')}|{card.get('id')}".encode("utf-8")
        ).hexdigest(),
    )
    return player


def shuffle_deck_tail(player, *, seed, owner):
    # Compat: alguns chamadores antigos embaralham apos a compra inicial.
    return shuffle_deck(player, seed=seed, owner=owner, salt="tail")


PLAYABLE_OPENER_MAX_COST = 2


def ensure_playable_opening_hand(player):
    """Garante ao menos um monstro de custo <=2 na mao inicial.

    Com o shuffle real a mao pode abrir sem jogada de turno 1; trocamos a
    carta mais cara da mao pelo primeiro monstro barato do deck (ambos por
    ordem deterministica) para preservar o contrato de abertura jogavel.
    """
    hand = player.get("hand") or []
    deck = player.get("deck") or []
    if any(
        str(card.get("type") or card.get("card_type")) == "MONSTER"
        and int(card.get("cost", 99) or 99) <= PLAYABLE_OPENER_MAX_COST
        for card in hand
    ):
        return player
    swap_in_index = next(
        (
            index
            for index, card in enumerate(deck)
            if str(card.get("type") or card.get("card_type")) == "MONSTER"
            and int(card.get("cost", 99) or 99) <= PLAYABLE_OPENER_MAX_COST
        ),
        None,
    )
    if swap_in_index is None or not hand:
        return player
    swap_out_index = max(
        range(len(hand)),
        key=lambda index: (int(hand[index].get("cost", 0) or 0), index),
    )
    swap_in = deck.pop(swap_in_index)
    swap_out = hand[swap_out_index]
    hand[swap_out_index] = swap_in
    deck.insert(swap_in_index, swap_out)
    return player


def normalize_campaign_modifiers(modifiers):
    # opening_* = one-shot opening advantage. energy_ramp = SUSTAINED tempo:
    # a permanent max_energy bump so the bot keeps out-curving every turn, not
    # just turn 1. Audit #3: campaign was only inflating HP (longer bar, same
    # threat); sustained pressure is what makes late nodes actually hard
    # against a competent player without rewriting the bot AI.
    supported = {"opening_shield", "extra_draw_turn_1", "opening_mana", "energy_ramp"}
    normalized = []
    for raw in modifiers or []:
        modifier = raw if isinstance(raw, dict) else {"id": raw}
        modifier_id = str(modifier.get("id") or "").strip()
        if modifier_id not in supported:
            continue
        side = "player" if modifier.get("side") == "player" else "bot"
        amount = max(1, min(5, int(modifier.get("amount", 1) or 1)))
        item = {"id": modifier_id, "side": side, "amount": amount}
        if modifier_id == "opening_shield":
            item["turns"] = max(1, min(3, int(modifier.get("turns", 2) or 2)))
        normalized.append(item)
    return normalized


def apply_campaign_opening_modifiers(player, bot, modifiers):
    for modifier in modifiers:
        side = player if modifier["side"] == "player" else bot
        amount = modifier["amount"]
        if modifier["id"] == "opening_shield":
            side.setdefault("statuses", {})["shield"] = {
                "potency": amount,
                "turns": modifier["turns"],
            }
        elif modifier["id"] == "extra_draw_turn_1":
            for _ in range(amount):
                draw_card(side)
        elif modifier["id"] == "opening_mana":
            side["energy"] = int(side.get("energy", 0) or 0) + amount
            side["max_energy"] = int(side.get("max_energy", 0) or 0) + amount
        elif modifier["id"] == "energy_ramp":
            # Permanent tempo edge: lift both current and cap so the side keeps
            # affording bigger plays for the whole match.
            side["energy"] = int(side.get("energy", 0) or 0) + amount
            side["max_energy"] = int(side.get("max_energy", 0) or 0) + amount
            side["energy_ramp_bonus"] = int(side.get("energy_ramp_bonus", 0) or 0) + amount


def create_match(
    seed=None,
    player_card_ids=None,
    player_name="Você",
    bot_profile_id=None,
    bot_difficulty_id=None,
    runtime_mode="singleplayer",
    apply_reducers_inline=None,
    first_duel=False,
    bot_card_ids=None,
    player_hp=None,
    bot_hp=None,
    campaign_version=None,
    campaign_node=None,
    campaign_attempt=None,
    campaign_modifiers=None,
    campaign_presentation=None,
    campaign_advice=None,
    shuffle=True,
):
    # Resolve the seed ONCE so match_id, game_seed and bot personality all
    # derive from the same entropy. With seed=None we mint a fresh seed so two
    # concurrent guests never collide and the bot profile actually varies.
    effective_seed = str(seed) if seed is not None else secrets.token_hex(16)
    match_id = _match_id(effective_seed)
    game_seed = effective_seed
    runtime_mode = str(runtime_mode or "singleplayer")
    if apply_reducers_inline is None:
        apply_reducers_inline = runtime_mode in REDUCER_INLINE_RUNTIME_MODES
    deck_ids = None
    if player_card_ids:
        deck_ids = list(player_card_ids)
    bot_deck_ids = list(bot_card_ids) if bot_card_ids else None
    player = create_player(player_name, "player", card_ids=deck_ids, starting_hp=player_hp or STARTING_HP)
    bot = create_player("Bot", "bot", card_ids=bot_deck_ids, starting_hp=bot_hp or STARTING_HP)
    # Shuffle SEMPRE no caminho real (API), antes da compra, para os dois
    # lados — deck custom nao-embaralhado era ordem de compra conhecida (bug
    # critico de TCG). shuffle=False existe apenas para harnesses de teste
    # roteirizados; nenhuma rota expõe esse flag.
    if shuffle:
        shuffle_deck(player, seed=game_seed, owner="player")
        shuffle_deck(bot, seed=game_seed, owner="bot")
    draw_to_hand_size(player)
    draw_to_hand_size(bot)
    if shuffle:
        ensure_playable_opening_hand(player)
        ensure_playable_opening_hand(bot)
    if first_duel and not campaign_node:
        # Reduz HP do bot apenas — o jogador continua com a barra cheia para a
        # sensação de "ainda no controle".
        bot["hp"] = FIRST_DUEL_BOT_HP
        bot["max_hp"] = FIRST_DUEL_BOT_HP
    bot_profile = personality_payload(bot_profile_id or choose_personality(seed=game_seed, match_id=match_id))
    bot_difficulty = difficulty_payload(bot_difficulty_id or ("easy" if first_duel else "normal"))
    modifiers = normalize_campaign_modifiers(campaign_modifiers) if campaign_node else []
    if modifiers:
        apply_campaign_opening_modifiers(player, bot, modifiers)

    initial = {
        "player_card_ids": list(deck_ids or PLAYER_DECK),
        "bot_card_ids": list(bot_deck_ids or BOT_DECK),
        "player_uses_default_deck": not bool(player_card_ids),
        "bot_uses_default_deck": not bool(bot_card_ids),
        "player_name": player_name,
        "bot_profile_id": bot_profile["id"],
        "bot_difficulty_id": bot_difficulty["id"],
        "first_duel": bool(first_duel),
        "shuffle": bool(shuffle),
    }
    if campaign_node:
        initial.update(
            {
                "player_hp": int(player["max_hp"]),
                "bot_hp": int(bot["max_hp"]),
                "campaign_version": str(campaign_version or ""),
                "campaign_node": str(campaign_node),
                "campaign_attempt": int(campaign_attempt or 1),
                "campaign_modifiers": deepcopy(modifiers),
                "campaign_presentation": deepcopy(campaign_presentation or {}),
                "campaign_advice": deepcopy(campaign_advice or {}),
            }
        )
    match = {
        "match_id": match_id,
        "architecture": "Ambitionz Rebirth",
        "engine_version": ENGINE_VERSION,
        "card_set_version": CARD_SET_VERSION,
        "ruleset_version": RULESET_VERSION,
        "reducer_version": REDUCER_VERSION,
        "_runtime_mode": runtime_mode,
        "_apply_reducers_inline": bool(apply_reducers_inline),
        "game_seed": game_seed,
        "seed": str(seed or ""),
        "first_duel": bool(first_duel),
        "initial": initial,
        "turn": 1,
        "phase": PHASE_CHOOSE,
        "turn_phase": TurnPhase.MAIN_PHASE.value,
        "player": player,
        "bot": bot,
        "bot_profile": bot_profile,
        "bot_difficulty": bot_difficulty,
        "last_clash": None,
        "result": None,
        "winner": None,
        "is_finished": False,
        "mulligan_used": False,
        "log": [
            "Turno 01   Duelo Rebirth iniciado.",
            "Turno 01   Escolha uma carta.",
        ],
        # O catalogo NAO vive dentro do match: sao ~200KB deep-copiados que
        # iam parar em cada snapshot persistido. O cliente usa /api/rebirth/catalog.
    }
    if campaign_node:
        match.update(
            {
                "campaign_version": str(campaign_version or ""),
                "campaign_node": str(campaign_node),
                "campaign_attempt": int(campaign_attempt or 1),
                "campaign_modifiers": deepcopy(modifiers),
                "campaign_presentation": deepcopy(campaign_presentation or {}),
                "campaign_advice": deepcopy(campaign_advice or {}),
            }
        )
    ensure_event_contract(match)
    started_payload = {
            "seed": str(seed or ""),
            "game_seed": game_seed,
            "engine_version": ENGINE_VERSION,
            "card_set_version": CARD_SET_VERSION,
            "player_name": player_name,
            "bot_profile_id": bot_profile["id"],
            "bot_difficulty_id": bot_difficulty["id"],
            "player_deck_count": len(player["deck"]) + len(player["hand"]),
            "bot_deck_count": len(bot["deck"]) + len(bot["hand"]),
        }
    if campaign_node:
        started_payload.update(
            {
                "campaign_version": match["campaign_version"],
                "campaign_node": match["campaign_node"],
                "campaign_attempt": match["campaign_attempt"],
                "campaign_modifiers": deepcopy(match["campaign_modifiers"]),
            }
        )
    append_event(
        match,
        "MATCH_STARTED",
        payload=started_payload,
        message="Duelo Rebirth iniciado.",
    )
    append_snapshot(match, "match_started")
    return match


def set_turn_phase(match, phase):
    phase_value = phase.value if isinstance(phase, TurnPhase) else str(phase or "")
    if phase_value not in {item.value for item in TurnPhase}:
        raise RebirthStateError(f"Fase de turno inválida: {phase_value}")
    match["turn_phase"] = phase_value
    return match


def current_turn_phase(match):
    return str(match.get("turn_phase") or TurnPhase.MAIN_PHASE.value)


def is_main_phase(match):
    return current_turn_phase(match) == TurnPhase.MAIN_PHASE.value


def remove_from_hand(player, *, card_instance_id=None, card_id=None):
    for index, card in enumerate(player["hand"]):
        if card_instance_id and card["instance_id"] == card_instance_id:
            return player["hand"].pop(index)
        if not card_instance_id and card_id and card["id"] == card_id:
            return player["hand"].pop(index)
    raise RebirthStateError("A carta não está na mão.")


def add_to_discard(player, card):
    if card:
        player["discard"].append(deepcopy(card))


def available_evolutions(player):
    grouped = {}
    for card in player["hand"]:
        if not card.get("evolution_id"):
            continue
        grouped.setdefault(card["id"], []).append(card)

    evolutions = []
    for card_id, cards in grouped.items():
        if len(cards) >= 2:
            first = cards[0]
            evolutions.append(
                {
                    "card_id": card_id,
                    "name": first["name"],
                    "count": len(cards),
                    "evolution_id": first["evolution_id"],
                }
            )
    return evolutions


def clear_played_cards(match):
    match["player"]["played_card"] = None
    match["bot"]["played_card"] = None


def side_payload(side, *, reveal_hand=True):
    field = deepcopy(field_slots(side))
    battlefield = deepcopy(compact_battlefield(side))
    payload = {
        "name": side["name"],
        "hp": side["hp"],
        "max_hp": side.get("max_hp", STARTING_HP),
        "energy": int(side.get("energy", 0) or 0),
        "max_energy": int(side.get("max_energy", 0) or 0),
        "deck_count": len(side["deck"]),
        "discard_count": len(side["discard"]),
        "played_card": deepcopy(side.get("played_card")),
        "battlefield": battlefield,
        "field": field,
        "trap_count": len(side.get("traps", [])),
        "wounded": bool(side.get("wounded")),
        "statuses": deepcopy(side.get("statuses", {})),
    }
    if reveal_hand:
        payload["hand"] = deepcopy(side["hand"])
        payload["traps"] = deepcopy(side.get("traps", []))
    else:
        payload["hand_count"] = len(side["hand"])
        payload["traps"] = [
            {"face_down": True, "armed": bool(trap.get("armed", True)), "slot": trap.get("slot")}
            for trap in side.get("traps", [])
        ]
    return payload


def public_state(match):
    from services.rebirth_serializers import public_state as serialize_public_state

    return serialize_public_state(match)
