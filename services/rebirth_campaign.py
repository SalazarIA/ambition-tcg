"""Deterministic campaign definitions for the Rebirth single-player path."""

from copy import deepcopy

from services.rebirth_cards import BOT_DECK, get_card


CAMPAIGN_VERSION = "rebirth_campaign_v1"


def _prioritized_bot_deck(*card_ids):
    deck = list(BOT_DECK)
    front = []
    for card_id in card_ids:
        if card_id in deck:
            deck.remove(card_id)
            front.append(card_id)
    return front + deck


def _presentation(title, tone, accent, fx="pulse", intensity="normal"):
    return {
        "title": title,
        "tone": tone,
        "accent": accent,
        "fx": fx,
        "intensity": intensity,
    }


def _node(
    node_id,
    order,
    name,
    intro,
    profile,
    bot_hp,
    xp,
    unlock,
    deck,
    *,
    modifiers=None,
    presentation=None,
    loss_tip,
    key_card_id,
):
    return {
        "id": node_id,
        "order": order,
        "name": name,
        "intro": intro,
        "bot_profile_id": profile,
        "bot_hp": bot_hp,
        "player_hp": 30,
        "reward": {"xp": xp},
        "unlock": unlock,
        "bot_deck_override": _prioritized_bot_deck(*deck),
        "modifiers": deepcopy(modifiers or []),
        "presentation": deepcopy(presentation or {}),
        "loss_tip": loss_tip,
        "key_card": {
            "id": key_card_id,
            "name": get_card(key_card_id)["name"],
        },
    }


_CAMPAIGN_NODES = (
    _node(
        "node_01_acolyte", 1, "Acolito da Brasa",
        "Uma chama jovem guarda o primeiro portal. Venca para seguir.",
        "novice", 18, 60, None, ("card_001", "card_021", "card_041"),
        presentation=_presentation("O Primeiro Portal", "fire", "#e6ad4b", "ember"),
        loss_tip="Construa um monstro antes de buscar dano direto; o Acolito deixa janelas abertas.",
        key_card_id="card_001",
    ),
    _node(
        "node_02_guardian", 2, "Guardiao de Pedra",
        "A passagem estreita sob uma muralha que sabe responder.",
        "defensive", 26, 90, "node_01_acolyte", ("card_044", "card_043", "card_042"),
        modifiers=[{"id": "opening_shield", "side": "bot", "amount": 2, "turns": 2}],
        presentation=_presentation("Muralha Desperta", "earth", "#8bc86c", "stone"),
        loss_tip="Force o escudo primeiro; guarde seu maior atacante para depois da quebra.",
        key_card_id="card_044",
    ),
    _node(
        "node_03_pyrelord", 3, "Pyrelord",
        "O senhor das cinzas exige uma vitoria sem hesitacao.",
        "aggressive", 34, 140, "node_02_guardian", ("card_004", "card_003", "card_001"),
        modifiers=[{"id": "extra_draw_turn_1", "side": "bot", "amount": 1}],
        presentation=_presentation("Senhor das Cinzas", "fire", "#ff6138", "inferno", "heavy"),
        loss_tip="Pyrelord vence corridas longas; troque cedo e nao deixe seus PV virarem combustivel.",
        key_card_id="card_004",
    ),
    _node(
        "node_04_stone_sentinel", 4, "Sentinela de Pedra",
        "Um colosso antigo fecha a trilha com runas de resistencia.",
        "defensive", 36, 165, "node_03_pyrelord", ("card_046", "card_044", "card_043", "card_042"),
        modifiers=[{"id": "opening_shield", "side": "bot", "amount": 3, "turns": 2}],
        presentation=_presentation("A Sentinela", "earth", "#98ce72", "stone", "heavy"),
        loss_tip="Magias que quebram escudo valem mais que dano pequeno contra a Sentinela.",
        key_card_id="card_046",
    ),
    _node(
        "node_05_tide_witch", 5, "Bruxa da Mare",
        "As aguas sobem a cada decisao lenta; a bruxa joga com folego infinito.",
        "opportunist", 37, 185, "node_04_stone_sentinel", ("card_024", "card_023", "card_022", "card_021"),
        modifiers=[{"id": "extra_draw_turn_1", "side": "bot", "amount": 1}],
        presentation=_presentation("Maré sem Lua", "water", "#44d8ff", "tide"),
        loss_tip="Concentre dano em uma janela: curas sucessivas punem ataques espalhados.",
        key_card_id="card_024",
    ),
    _node(
        "node_06_crimson_executioner", 6, "Carrasco Rubro",
        "O machado ja esta levantado. Cada turno entregue vira uma sentenca.",
        "aggressive", 39, 210, "node_05_tide_witch", ("card_004", "card_003", "card_002", "card_001"),
        modifiers=[{"id": "opening_mana", "side": "bot", "amount": 1}],
        presentation=_presentation("Sentenca Rubra", "fire", "#ff463f", "inferno", "heavy"),
        loss_tip="Defenda o primeiro pico; o Carrasco e mais vulneravel depois de gastar sua abertura.",
        key_card_id="card_004",
    ),
    _node(
        "node_07_eclipse_parasite", 7, "Parasita do Eclipse",
        "A sombra nao ataca so o corpo: ela aprende com suas feridas.",
        "opportunist", 41, 235, "node_06_crimson_executioner", ("card_065", "card_064", "card_063", "card_061"),
        modifiers=[
            {"id": "extra_draw_turn_1", "side": "bot", "amount": 1},
            {"id": "energy_ramp", "side": "bot", "amount": 1},
        ],
        presentation=_presentation("Eclipse Vivo", "shadow", "#aa6cff", "void", "heavy"),
        loss_tip="Limpe deterioracao quando puder e evite trocas que alimentem roubo de vida.",
        key_card_id="card_065",
    ),
    _node(
        "node_08_abyssal_golem", 8, "Golem Abissal",
        "Pedra e vazio se fundiram numa fortaleza que marcha.",
        "defensive", 44, 265, "node_07_eclipse_parasite", ("card_046", "card_045", "card_044", "card_043"),
        modifiers=[
            {"id": "opening_shield", "side": "bot", "amount": 5, "turns": 2},
            {"id": "extra_draw_turn_1", "side": "bot", "amount": 1},
            {"id": "energy_ramp", "side": "bot", "amount": 1},
        ],
        presentation=_presentation("Fortaleza Abissal", "earth", "#71bd85", "stone", "heavy"),
        loss_tip="Nao desperdice ataque no escudo inicial; monte campo e derrube tudo em cadeia.",
        key_card_id="card_046",
    ),
    _node(
        "node_09_herald", 9, "O Arauto",
        "Ele anuncia a queda antes de ela acontecer, carregado de todas as marés.",
        "opportunist", 46, 300, "node_08_abyssal_golem", ("card_065", "card_004", "card_024", "card_044"),
        modifiers=[
            {"id": "extra_draw_turn_1", "side": "bot", "amount": 2},
            {"id": "opening_mana", "side": "bot", "amount": 1},
            {"id": "energy_ramp", "side": "bot", "amount": 1},
        ],
        presentation=_presentation("A Ultima Profecia", "shadow", "#d493ff", "void", "heavy"),
        loss_tip="O Arauto abre com opcoes demais; priorize sobrevivencia ate a mao dele estreitar.",
        key_card_id="card_065",
    ),
    _node(
        "node_10_gray_king", 10, "Rei Cinzento",
        "No trono frio, fogo, pedra e sombra obedecem a uma unica coroa.",
        "aggressive", 50, 400, "node_09_herald", ("card_004", "card_065", "card_046", "card_024"),
        modifiers=[
            {"id": "opening_shield", "side": "bot", "amount": 4, "turns": 2},
            {"id": "extra_draw_turn_1", "side": "bot", "amount": 2},
            {"id": "opening_mana", "side": "bot", "amount": 1},
            {"id": "energy_ramp", "side": "bot", "amount": 2},
        ],
        presentation=_presentation("Rei Cinzento", "royal", "#f0c56b", "crown", "heavy"),
        loss_tip="Quebre a coroa em fases: sobreviva a abertura, remova o escudo e so entao acelere o dano.",
        key_card_id="card_004",
    ),
)


def all_nodes():
    return [deepcopy(node) for node in _CAMPAIGN_NODES]


def get_node(node_id):
    node_id = str(node_id or "").strip()
    for node in _CAMPAIGN_NODES:
        if node["id"] == node_id:
            return deepcopy(node)
    return None


def _node_progress(progress, node_id):
    return ((progress or {}).get("nodes") or {}).get(node_id) or {}


def is_unlocked(node_id, progress=None):
    node = get_node(node_id)
    if not node:
        return False
    prerequisite = node.get("unlock")
    return not prerequisite or bool(_node_progress(progress, prerequisite).get("completed_at"))


def next_available(progress=None):
    for node in _CAMPAIGN_NODES:
        completed = bool(_node_progress(progress, node["id"]).get("completed_at"))
        if not completed and is_unlocked(node["id"], progress):
            return deepcopy(node)
    return None


def _modifier_label(modifier):
    amount = int(modifier.get("amount", 1) or 1)
    if modifier["id"] == "opening_shield":
        return f"Escudo inicial +{amount}"
    if modifier["id"] == "extra_draw_turn_1":
        return f"Mão inicial +{amount}"
    if modifier["id"] == "opening_mana":
        return f"Mana inicial +{amount}"
    if modifier["id"] == "energy_ramp":
        return f"Tempo sustentado +{amount} mana/turno"
    return modifier["id"]


def campaign_payload(progress=None):
    progress = progress or {"campaign_version": CAMPAIGN_VERSION, "nodes": {}}
    nodes = []
    for node in _CAMPAIGN_NODES:
        recorded = _node_progress(progress, node["id"])
        completed = bool(recorded.get("completed_at"))
        unlocked = is_unlocked(node["id"], progress)
        nodes.append(
            {
                "id": node["id"],
                "order": node["order"],
                "name": node["name"],
                "intro": node["intro"],
                "bot_profile_id": node["bot_profile_id"],
                "bot_hp": node["bot_hp"],
                "player_hp": node["player_hp"],
                "reward": deepcopy(node["reward"]),
                "unlock": node["unlock"],
                "modifiers": deepcopy(node["modifiers"]),
                "modifier_labels": [_modifier_label(modifier) for modifier in node["modifiers"]],
                "presentation": deepcopy(node["presentation"]),
                "attempts": int(recorded.get("attempts", 0) or 0),
                "completed_at": recorded.get("completed_at"),
                "status": "completed" if completed else "available" if unlocked else "locked",
            }
        )
    next_node = next_available(progress)
    return {
        "version": CAMPAIGN_VERSION,
        "nodes": nodes,
        "next_available": next_node["id"] if next_node else None,
    }
