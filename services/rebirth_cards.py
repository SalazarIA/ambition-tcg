from copy import deepcopy

from services.rebirth_keywords import default_keywords_for


CARD_IMAGE_TEMPLATE = "static/img/cards/baralho/{card_number}.webp"
CARD_TYPES = {"MONSTER", "SPELL", "TRAP"}
MONSTER_FAMILIES = ("FIRE", "WATER", "EARTH", "SHADOW")
STARTER_DECK_SIZE = 30
MONSTER_DECK_MIN = 18
MONSTER_DECK_MAX = 22
TURN_ONE_TEST_CARD_IDS = {"card_001", "card_002", "card_021", "card_041", "card_061"}


FAMILY_CONFIGS = {
    "FIRE": {
        "element": "Fogo",
        "role": "Dano direto / queimadura",
        "palette": ["#ff5b35", "#ffb347", "#2a0f0b"],
        "base_start": 1,
        "evolved_start": 11,
        "base_names": [
            "Cinder Lynx",
            "Ashen Brawler",
            "Blazewing Adept",
            "Coalheart Runner",
            "Flareblade Cub",
            "Scorchscale Imp",
            "Emberhorn Raider",
            "Sunstoke Duelist",
            "Pyrebound Hound",
            "Volcanic Herald",
        ],
        "evolved_names": [
            "Cinder Lynx Alpha",
            "Ashen Brawler Rex",
            "Blazewing Tyrant",
            "Coalheart Champion",
            "Flareblade Matriarch",
            "Scorchscale Infernal",
            "Emberhorn Warlord",
            "Sunstoke Archon",
            "Pyrebound Cerberus",
            "Volcanic Avatar",
        ],
        "abilities": [
            ("fire_direct", "Faísca Direta", "Causa pressão adicional quando vence o combate."),
            ("fire_burn", "Marca Ardente", "Aplica queimadura após vencer o combate."),
            ("fire_surge", "Surto de Calor", "Ganha ataque nos primeiros combates."),
            ("fire_execute", "Execução de Cinzas", "Pune alvos feridos."),
        ],
    },
    "WATER": {
        "element": "Água",
        "role": "Cura / purificação",
        "palette": ["#37c7ff", "#b8fff6", "#092033"],
        "base_start": 21,
        "evolved_start": 31,
        "base_names": [
            "Mistcall Tactician",
            "Riverglass Medic",
            "Tidepool Acolyte",
            "Pearlfin Guard",
            "Rainspire Oracle",
            "Coldstream Sentry",
            "Brineveil Seer",
            "Moonwell Keeper",
            "Foamfang Skirmisher",
            "Riptide Maven",
        ],
        "evolved_names": [
            "Mistcall Strategist",
            "Riverglass Saint",
            "Tidepool Hierophant",
            "Pearlfin Bastion",
            "Rainspire Prophet",
            "Coldstream Paladin",
            "Brineveil Highseer",
            "Moonwell Archkeeper",
            "Foamfang Tempest",
            "Riptide Grandmaster",
        ],
        "abilities": [
            ("water_heal", "Maré Curativa", "Recupera PV após a pressão do combate."),
            ("water_cleanse", "Corrente Purificadora", "Remove um efeito nocivo após o combate."),
            ("water_tide", "Maré Crescente", "Melhora o ataque em combate após o segundo turno."),
            ("water_guard", "Guarda Fluida", "Reduz o dano recebido em combate."),
        ],
    },
    "EARTH": {
        "element": "Terra",
        "role": "Escudo / defesa",
        "palette": ["#8bd05f", "#f0e2a0", "#17220d"],
        "base_start": 41,
        "evolved_start": 51,
        "base_names": [
            "Stonehide Recruit",
            "Rootwall Tender",
            "Amberplate Cub",
            "Granite Pactbearer",
            "Mossback Brute",
            "Bramblehorn Knight",
            "Quartzroot Sentinel",
            "Ironbark Veteran",
            "Terrashield Monk",
            "Boulderwake Colossus",
        ],
        "evolved_names": [
            "Stonehide Bulwark",
            "Rootwall Ancient",
            "Amberplate Titan",
            "Granite Pactlord",
            "Mossback Behemoth",
            "Bramblehorn Paragon",
            "Quartzroot Citadel",
            "Ironbark Warden",
            "Terrashield Ascetic",
            "Boulderwake Primordial",
        ],
        "abilities": [
            ("earth_shield", "Florescer do Escudo", "Adiciona um escudo persistente após o combate."),
            ("earth_fortify", "Fortificar", "Transforma guarda em valor extra de combate."),
            ("earth_counter", "Contra-Golpe de Pedra", "Contra-ataca inimigos de baixo ataque."),
            ("earth_bulwark", "Baluarte", "Reduz fortemente o dano recebido em combate."),
        ],
    },
    "SHADOW": {
        "element": "Sombra",
        "role": "Efeitos persistentes / roubo de vida",
        "palette": ["#9b5cff", "#221437", "#f2d9ff"],
        "base_start": 61,
        "evolved_start": 71,
        "base_names": [
            "Duskwisp Thief",
            "Hollowmark Stalker",
            "Nightchain Adept",
            "Graveveil Duelist",
            "Umbral Lurker",
            "Voidkiss Assassin",
            "Cryptsong Reaper",
            "Shadeglass Scout",
            "Blackthorn Revenant",
            "Eclipse Herald",
        ],
        "evolved_names": [
            "Duskwisp Shade",
            "Hollowmark Predator",
            "Nightchain Archmage",
            "Graveveil Champion",
            "Umbral Horror",
            "Voidkiss Executioner",
            "Cryptsong Harvester",
            "Shadeglass Phantom",
            "Blackthorn Lich",
            "Eclipse Avatar",
        ],
        "abilities": [
            ("shadow_lifesteal", "Roubo de Vida", "Cura seu controlador após causar dano."),
            ("shadow_decay", "Deterioração", "Aplica deterioração persistente ao alvo."),
            ("shadow_mark", "Marca da Ferida", "Vence empates contra inimigos feridos."),
            ("shadow_drain", "Drenagem de Alma", "Rouba PV através da pilha de efeitos."),
        ],
    },
}


# audit #6: ability_name de spell/trap vinha cru em inglês ("DrawTwoCards")
# e vazava na coleção/arena. Este mapa dá um nome de habilidade localizado
# (display-only; ability_key segue sendo a chave funcional).
SPELL_TRAP_ABILITY_PT = {
    "DrawTwoCards": "Recarga Arcana",
    "CleanseAll": "Purificação Total",
    "DestroyShield": "Quebra-Escudo",
    "Fireball": "Bola de Fogo",
    "HealingRain": "Chuva Curativa",
    "Fortify": "Fortificar",
    "BurningEdict": "Édito Flamejante",
    "ShadowDrain": "Dreno Sombrio",
    "StoneSkin": "Pele de Pedra",
    "TidalRenewal": "Renovação das Marés",
    "BurnAttacker": "Queimar Atacante",
    "CleanseAmbush": "Emboscada Purificadora",
    "DrainCounter": "Contra-Dreno",
    "EmergencyShield": "Escudo de Emergência",
    "FreezeStrike": "Golpe Congelante",
    "GuardBreakTrap": "Rompe-Guarda",
    "NegateAttack": "Anular Ataque",
    "ReflectDamage": "Refletir Dano",
    "SecondWind": "Segundo Fôlego",
    "StunRune": "Runa Atordoante",
}


def _localized_ability_name(action):
    return SPELL_TRAP_ABILITY_PT.get(action) or str(action)


SPELL_DEFINITIONS = [
    ("DrawTwoCards", "Recarga Arcana", "Compre duas cartas.", [{"type": "draw", "target": "self", "amount": 2}], 2),
    ("CleanseAll", "Purificação das Marés", "Remova todos os efeitos nocivos do seu lado.", [{"type": "cleanse", "target": "self", "mode": "all"}], 2),
    ("DestroyShield", "Hex do Quebra-Escudo", "Destrua o escudo do oponente.", [{"type": "destroy_shield", "target": "opponent"}], 1),
    ("Fireball", "Bola de Fogo da Arena", "Cause dano direto ao oponente.", [{"type": "damage", "target": "opponent", "amount": 3}], 2),
    ("HealingRain", "Chuva Curativa", "Recupere PV do seu lado.", [{"type": "heal", "target": "self", "amount": 4}], 2),
    ("Fortify", "Fortificação Rúnica", "Ganhe um escudo.", [{"type": "shield", "target": "self", "amount": 3, "turns": 2}], 1),
    ("BurningEdict", "Édito Ardente", "Aplique queimadura ao oponente.", [{"type": "status", "target": "opponent", "status": "burn", "potency": 1, "turns": 2}], 2),
    ("TidalRenewal", "Renovação das Marés", "Purifique e cure seu lado.", [{"type": "cleanse", "target": "self", "mode": "all"}, {"type": "heal", "target": "self", "amount": 2}], 3),
    ("StoneSkin", "Pele de Pedra", "Ganhe um escudo mais forte.", [{"type": "shield", "target": "self", "amount": 5, "turns": 1}], 3),
    ("ShadowDrain", "Drenagem Sombria", "Cause dano ao oponente e cure seu lado.", [{"type": "damage", "target": "opponent", "amount": 2}, {"type": "heal", "target": "self", "amount": 2}], 3),
]


TRAP_DEFINITIONS = [
    ("NegateAttack", "Sigilo Nulo", "Negue o próximo ataque em combate.", "opponent_attacks", "negate_attack", 2),
    ("ReflectDamage", "Espinhos Espelhados", "Reflita dano durante o combate.", "opponent_attacks", "reflect_damage", 2),
    ("BurnAttacker", "Laço de Cinzas", "Queime o atacante.", "opponent_attacks", "burn_attacker", 1),
    ("EmergencyShield", "Última Muralha", "Erga um escudo antes do dano de combate.", "owner_attacked", "shield_owner", 1),
    ("CleanseAmbush", "Reversão Pura", "Purifique efeitos antes do combate.", "owner_attacked", "cleanse_owner", 1),
    ("FreezeStrike", "Trava de Gelo", "Congele o atacante.", "opponent_attacks", "freeze_attacker", 2),
    ("DrainCounter", "Tributo Noturno", "Drene PV quando for atacado.", "owner_attacked", "drain_attacker", 2),
    ("GuardBreakTrap", "Linha de Falha", "Destrua escudos antes do combate.", "opponent_attacks", "destroy_shield", 1),
    ("SecondWind", "Fonte Oculta", "Cure-se sob pressão.", "owner_attacked", "heal_owner", 1),
    ("StunRune", "Runa Atordoante", "Reduza o poder de combate do atacante.", "opponent_attacks", "weaken_attacker", 2),
]


LEGENDARY_DEFINITIONS = [
    {
        "id": "legend_infernus_core",
        "name": "Infernus Core",
        "family": "FIRE",
        "element": "Fogo",
        "cost": 4,
        "attack": 6,
        "guard": 5,
        "keywords": ["RUSH", "BURST"],
        "ability_key": "infernus_core",
        "ability_name": "Núcleo Infernus",
        "ability_text": "Ao sobreviver ao combate, consome 1 mana para receber +2 ATK permanente.",
        "heuristic_vector": {
            "scaling_potential": 9,
            "survivability": 5,
            "trigger_threat": 8,
            "board_tempo": 8,
            "value_persistence": 8,
            "future_resource_swing": 4,
        },
        "art": "/static/assets/rebirth/cards/embermaw-alpha-art.webp",
        "palette": ["#ff5b35", "#ffcf6b", "#2a0f0b"],
    },
    {
        "id": "legend_aegis_sentinel",
        "name": "Aegis Sentinel",
        "family": "EARTH",
        "element": "Terra",
        "cost": 4,
        "attack": 4,
        "guard": 7,
        "keywords": ["TAUNT", "SHIELD"],
        "ability_key": "aegis_sentinel",
        "ability_name": "Sentinela Aegis",
        "ability_text": "No fim do turno, se não agiu, recebe +2 GRD temporário até o próximo dano resolvido.",
        "heuristic_vector": {
            "scaling_potential": 3,
            "survivability": 9,
            "trigger_threat": 7,
            "board_tempo": 7,
            "value_persistence": 8,
            "future_resource_swing": 2,
        },
        "art": "/static/assets/rebirth/cards/ironbastion-art.webp",
        "palette": ["#8bd05f", "#f0e2a0", "#17220d"],
    },
    {
        "id": "legend_shadow_reaper",
        "name": "Shadow Reaper",
        "family": "SHADOW",
        "element": "Sombra",
        "cost": 4,
        "attack": 5,
        "guard": 5,
        "keywords": ["PIERCE", "EXECUTE"],
        "ability_key": "shadow_reaper",
        "ability_name": "Ceifador Sombrio",
        "ability_text": "Ao ser invocado, exaure por 1 turno a criatura inimiga de maior ATK.",
        "heuristic_vector": {
            "scaling_potential": 2,
            "survivability": 5,
            "trigger_threat": 9,
            "board_tempo": 8,
            "value_persistence": 6,
            "future_resource_swing": 7,
        },
        "art": "/static/assets/rebirth/cards/voidstalker-art.webp",
        "palette": ["#9b5cff", "#221437", "#f2d9ff"],
    },
]


def _image_path(card_id):
    return CARD_IMAGE_TEMPLATE.format(card_number=int(card_id.rsplit("_", 1)[-1]))


def _art_payload(card_id, family, palette):
    return {
        "art": _image_path(card_id),
        "art_key": f"rebirth.card.{card_id}.v1",
        "art_version": "v1",
        "art_status": "optimized_webp_path",
        "art_finish": "tcg_card_frame",
        "palette": list(palette),
        "silhouette": f"{family.lower()}_sigil",
    }


def _monster_cost(attack, guard, is_evolved):
    """Mana cost scales with the card's stat total so the energy ramp is meaningful.

    Energy ramps from 1 to 10 (one per turn), and stat totals fall in 7..15. The
    bands below produce a Hearthstone-style curve where cheap cards swarm early
    turns and the strongest bodies need the ramp.
    """
    total = int(attack) + int(guard)
    if total <= 8:
        cost = 1
    elif total <= 11:
        cost = 2
    elif total <= 13:
        cost = 3
    else:
        cost = 4
    if is_evolved:
        cost += 1
    return cost


def _heuristic_vector(*, attack, guard, tier=1, scaling=0, trigger=0, persistence=0, resource=0):
    return {
        "scaling_potential": max(0, min(10, int(scaling or 0))),
        "survivability": max(0, min(10, int(guard or 0))),
        "trigger_threat": max(0, min(10, int(trigger or 0))),
        "board_tempo": max(0, min(10, int(attack or 0) + int(tier or 1))),
        "value_persistence": max(0, min(10, int(persistence or 0) + int(tier or 1))),
        "future_resource_swing": max(0, min(10, int(resource or 0))),
    }


def _monster_card(card_number, *, family, name, tier, slot):
    config = FAMILY_CONFIGS[family]
    card_id = f"card_{card_number:03d}"
    evolved_number = config["evolved_start"] + slot
    is_evolved = tier > 1
    ability_key, ability_name, ability_text = config["abilities"][slot % len(config["abilities"])]
    attack_curve = [4, 5, 5, 6, 6, 7, 7, 8, 8, 9]
    guard_curve = [3, 3, 4, 2, 4, 3, 5, 2, 4, 5]
    attack = attack_curve[slot] + (1 if is_evolved else 0)
    guard = guard_curve[slot] + (1 if is_evolved else 0)
    rarity = "UNCOMMON" if is_evolved else "COMMON"
    card = {
        "id": card_id,
        "name": name,
        "type": "MONSTER",
        "card_type": "MONSTER",
        "family": family,
        "role": config["role"],
        "tier": tier,
        "rarity": rarity,
        "cost": _monster_cost(attack, guard, is_evolved),
        "attack": attack,
        "power": attack,
        "guard": guard,
        "element": config["element"],
        "evolution_id": None if is_evolved else f"card_{evolved_number:03d}",
        "ability_key": ability_key,
        "ability_name": ability_name,
        "ability_text": ability_text,
        # K1: keywords mecânicas por família. Tier ≥ 2 ganha keyword bônus.
        "keywords": default_keywords_for(family, tier=tier),
        "flavor": f"{name} conduz a linhagem de {config['element'].lower()} à arena viva.",
        "status_affinity": family.lower(),
        "heuristic_vector": _heuristic_vector(
            attack=attack,
            guard=guard,
            tier=tier,
            scaling=2 if "Surto" in ability_name or "Crescente" in ability_name else 0,
            trigger=2 + (2 if is_evolved else 0),
            persistence=1 if family in {"EARTH", "SHADOW"} else 0,
        ),
    }
    card.update(_art_payload(card_id, family, config["palette"]))
    return card


def _spell_card(offset, definition):
    action, name, text, stack_effects, cost = definition
    card_number = 81 + offset
    card_id = f"card_{card_number:03d}"
    card = {
        "id": card_id,
        "name": name,
        "type": "SPELL",
        "card_type": "SPELL",
        "family": "SPELL",
        "role": "Efeito instantâneo de pilha",
        "tier": 1,
        "rarity": "UNCOMMON",
        # O custo da definição é honrado — antes um min(2, cost) silencioso
        # transformava magias de custo 3 em custo 2 e desmentia a curva.
        "cost": max(0, int(cost)),
        "attack": 0,
        "power": 0,
        "guard": 0,
        "element": "Arcano",
        "evolution_id": None,
        "ability_key": f"spell_{action.lower()}",
        "ability_name": _localized_ability_name(action),
        "ability_text": text,
        "flavor": f"{name} altera a pilha antes do próximo clash.",
        "action": action,
        "stack_effects": deepcopy(stack_effects),
        "heuristic_vector": _heuristic_vector(attack=0, guard=0, trigger=2, resource=1),
    }
    card.update(_art_payload(card_id, "spell", ["#f9e27d", "#2f245f", "#ffffff"]))
    return card


def _trap_card(offset, definition):
    action, name, text, trigger, trap_effect, cost = definition
    card_number = 91 + offset
    card_id = f"card_{card_number:03d}"
    card = {
        "id": card_id,
        "name": name,
        "type": "TRAP",
        "card_type": "TRAP",
        "family": "TRAP",
        "role": "Gatilho oculto de combate",
        "tier": 1,
        "rarity": "UNCOMMON",
        "cost": max(0, int(cost)),
        "attack": 0,
        "power": 0,
        "guard": 0,
        "element": "Oculto",
        "evolution_id": None,
        "ability_key": f"trap_{action.lower()}",
        "ability_name": _localized_ability_name(action),
        "ability_text": text,
        "flavor": f"{name} aguarda virada para baixo até a fase de combate.",
        "action": action,
        "face_down": True,
        "trigger_phase": "COMBAT_PHASE",
        "trigger": trigger,
        "trap_effect": trap_effect,
        "heuristic_vector": _heuristic_vector(attack=0, guard=0, trigger=3, persistence=1),
    }
    card.update(_art_payload(card_id, "trap", ["#ff4f8b", "#181022", "#ffc6df"]))
    return card


def _legendary_card(definition):
    card = {
        "id": definition["id"],
        "name": definition["name"],
        "type": "MONSTER",
        "card_type": "MONSTER",
        "family": definition["family"],
        "role": "Lendária determinística de gatilho passivo",
        "tier": 3,
        "rarity": "LEGENDARY",
        "cost": definition["cost"],
        "attack": definition["attack"],
        "power": definition["attack"],
        "guard": definition["guard"],
        "element": definition["element"],
        "evolution_id": None,
        "keywords": list(definition.get("keywords") or []),
        "ability_key": definition["ability_key"],
        "ability_name": definition["ability_name"],
        "ability_text": definition["ability_text"],
        "flavor": f"{definition['name']} sela um contrato lendário no barramento de eventos.",
        "status_affinity": definition["family"].lower(),
        "legendary": True,
        "heuristic_vector": deepcopy(definition["heuristic_vector"]),
        "art": definition["art"],
        "art_key": f"rebirth.card.{definition['id']}.v1",
        "art_version": "v1",
        "art_status": "rebirth_legendary_contract",
        "art_finish": "tcg_card_frame",
        "palette": list(definition["palette"]),
        "silhouette": f"{definition['family'].lower()}_legendary_sigil",
    }
    return card


def _build_catalog_dict():
    cards = {}
    for family in MONSTER_FAMILIES:
        config = FAMILY_CONFIGS[family]
        for slot, name in enumerate(config["base_names"]):
            card = _monster_card(config["base_start"] + slot, family=family, name=name, tier=1, slot=slot)
            cards[card["id"]] = card
        for slot, name in enumerate(config["evolved_names"]):
            card = _monster_card(config["evolved_start"] + slot, family=family, name=name, tier=2, slot=slot)
            cards[card["id"]] = card
    for offset, definition in enumerate(SPELL_DEFINITIONS):
        card = _spell_card(offset, definition)
        cards[card["id"]] = card
    for offset, definition in enumerate(TRAP_DEFINITIONS):
        card = _trap_card(offset, definition)
        cards[card["id"]] = card
    expected = [f"card_{index:03d}" for index in range(1, 101)]
    if list(cards.keys()) != expected:
        raise RuntimeError("Rebirth catalog generation must produce card_001 through card_100 in order.")
    for definition in LEGENDARY_DEFINITIONS:
        card = _legendary_card(definition)
        cards[card["id"]] = card
    return cards


CARD_CATALOG_DICT = _build_catalog_dict()


# v96 balance overrides: ajustes cirúrgicos sobre o catálogo gerado, sem mexer
# em _monster_cost (que é o contrato canônico da curva de mana). Cada entrada
# documenta o porquê para auditoria e mantém a correção restrita ao PvE atual.
CARD_BALANCE_OVERRIDES = {
    # Tidepool Acolyte: water_tide escalava cedo demais por 2 mana.
    # +1 mana preserva a identidade de scaling sem virar escolha obrigatória.
    "card_023": {"cost": 3},
    # Scorchscale Imp: ATK 7 + burn ainda era obrigatório; ATK 6 mantém
    # pressão de fogo sem decidir a partida sozinho.
    "card_006": {"attack": 6, "power": 6, "cost": 3},
    # Cinder Lynx Alpha: o par tutorial gera esta evolução em 100% das runs.
    # Custo 4 preserva o payoff, mas tira o pico automático do early game.
    "card_011": {"cost": 4},
    # Granite Pactbearer: 6/2 com bulwark por 1 mana gerava tempo demais.
    "card_044": {"cost": 2},
    # Stonehide Recruit: era corpo defensivo sem impacto; +1 guarda o torna
    # opener real sem mexer no custo de entrada.
    "card_041": {"guard": 4},
    # Amberplate Cub: contra-golpe precisava de ataque suficiente para trocar.
    "card_043": {"attack": 6, "power": 6},
    # Evoluções correspondentes precisam continuar claramente acima da base.
    "card_053": {"attack": 7, "power": 7, "cost": 4},
    # Duskwisp Thief: lifesteal com 4 ATK raramente convertia em pressão.
    "card_061": {"attack": 5, "power": 5},
    "card_071": {"attack": 6, "power": 6},
    # Hollowmark Stalker: decay precisava ameaçar troca real para sair da mão.
    "card_062": {"attack": 6, "power": 6, "cost": 2},
    "card_072": {"attack": 7, "power": 7},
    # Bramblehorn Knight: earth_fortify deve ser utilitário, não finisher.
    # ATK 5 tira o pico que empurrava todos os bots acima de 60% WR.
    "card_046": {"attack": 5, "power": 5, "cost": 2},
    # Mossback Brute: 6/4 com earth_shield por 2 mana segura board demais.
    # +1 mana alinha à curva real do stat-total (10 → cost 3 na fórmula).
    "card_045": {"cost": 3},
    # NOTA (playtest 10k, 2026-06-15): card_084 "Bola de Fogo da Arena" aparecia
    # com WR 0.86 ("dominant"), mas nerfá-la (3 mana / 2 dano) mal moveu o WR
    # (0.82) e o macro seguiu 49/51 — é VIÉS DE SELEÇÃO (finalizador jogado em
    # posição vencedora), não poder. Nenhum override aplicado. Ver
    # docs/REBIRTH_PLAYTEST_FINDINGS.md.
}

for _card_id, _override in CARD_BALANCE_OVERRIDES.items():
    if _card_id in CARD_CATALOG_DICT:
        CARD_CATALOG_DICT[_card_id].update(_override)

# Keywords opt-in por carta: TAUNT/BURST/EXECUTE são fortes demais para spread
# de família — entram em corpos tier-2 escolhidos (+ lendárias, definidas acima).
CARD_KEYWORD_OVERRIDES = {
    "card_051": ["SHIELD", "TAUNT"],    # Stonehide Bulwark — muralha de linha de frente
    "card_059": ["SHIELD", "TAUNT"],    # Terrashield Ascetic — protetor tardio
    "card_016": ["RUSH", "BURST"],      # Scorchscale Infernal — entrada explosiva
    "card_076": ["PIERCE", "EXECUTE"],  # Voidkiss Executioner — o nome já era contrato
}

for _card_id, _keywords in CARD_KEYWORD_OVERRIDES.items():
    if _card_id in CARD_CATALOG_DICT:
        CARD_CATALOG_DICT[_card_id]["keywords"] = list(_keywords)

# Sinergias K2 (condicionais de board/HP) agora avaliadas pela engine no clash.
CARD_SYNERGY_OVERRIDES = {
    "card_003": {"condition": "controls_family", "value": "FIRE", "effect": {"attack": 1}},
    "card_007": {"condition": "low_hp", "value": 15, "effect": {"attack": 2}},
    "card_022": {"condition": "controls_family", "value": "WATER", "effect": {"guard": 1}},
    "card_026": {"condition": "field_count", "value": 2, "effect": {"attack": 1, "guard": 1}},
    "card_042": {"condition": "controls_family", "value": "EARTH", "effect": {"guard": 2}},
    "card_047": {"condition": "tier_2", "value": None, "effect": {"attack": 1, "guard": 1}},
    "card_063": {"condition": "controls_family", "value": "SHADOW", "effect": {"attack": 1}},
    "card_066": {"condition": "low_hp", "value": 12, "effect": {"attack": 2}},
}

from services.rebirth_keywords import synergy_label as _synergy_label  # noqa: E402

for _card_id, _synergy in CARD_SYNERGY_OVERRIDES.items():
    if _card_id in CARD_CATALOG_DICT:
        CARD_CATALOG_DICT[_card_id]["synergy"] = dict(_synergy)
        CARD_CATALOG_DICT[_card_id]["synergy_label"] = _synergy_label({"synergy": _synergy})

CARD_BY_ID = CARD_CATALOG_DICT
CARD_CATALOG = [deepcopy(card) for card in CARD_CATALOG_DICT.values()]
BASE_MONSTERS = [deepcopy(card) for card in CARD_CATALOG_DICT.values() if card["type"] == "MONSTER" and int(card["tier"]) == 1]
EVOLVED_MONSTERS = [deepcopy(card) for card in CARD_CATALOG_DICT.values() if card["type"] == "MONSTER" and int(card["tier"]) > 1]
SPELL_CARDS = [deepcopy(card) for card in CARD_CATALOG_DICT.values() if card["type"] == "SPELL"]
TRAP_CARDS = [deepcopy(card) for card in CARD_CATALOG_DICT.values() if card["type"] == "TRAP"]
LEGENDARY_CARDS = [deepcopy(card) for card in CARD_CATALOG_DICT.values() if card.get("rarity") == "LEGENDARY"]
CARD_ABILITY_KEYS = {card_id: card["ability_key"] for card_id, card in CARD_CATALOG_DICT.items()}

PLAYER_DECK = [
    # v97: preserve the tutorial opener pair while seeding more duplicate
    # families through the default deck so tier-2 cards appear beyond card_011.
    "card_001",
    "card_001",
    "card_002",
    "card_021",
    "card_041",
    "card_061",
    "card_061",
    "card_003",
    "card_022",
    "card_062",
    "card_062",
    "card_004",
    "card_023",
    "card_023",
    "card_043",
    "card_043",
    "card_005",
    "card_024",
    "card_044",
    "card_006",
    "card_083",
    "card_088",
    "card_085",
    "card_086",
    "card_090",
    "card_091",
    "card_092",
    "card_093",
    "card_094",
    "card_095",
]

BOT_DECK = [
    # v97: composição média com múltiplos pares tier-1; o bot continua sem
    # começar com evoluídas, mas o catálogo tier-2 entra no loop via fusão.
    "card_044",
    "card_044",
    "card_043",
    "card_043",
    "card_042",
    "card_061",
    "card_061",
    "card_021",
    "card_001",
    "card_001",
    "card_041",
    "card_041",
    "card_062",
    "card_062",
    "card_022",
    "card_002",
    "card_023",
    "card_003",
    "card_025",
    "card_004",
    "card_083",
    "card_082",
    "card_087",
    "card_088",
    "card_089",
    "card_096",
    "card_097",
    "card_098",
    "card_099",
    "card_100",
]


def card_type(card_or_id):
    card = get_card(card_or_id) if isinstance(card_or_id, str) else card_or_id
    explicit = str(card.get("type") or card.get("card_type") or "").upper()
    if explicit:
        return explicit
    if "attack" in card or "guard" in card:
        return "MONSTER"
    return ""


def is_monster(card_or_id):
    return card_type(card_or_id) == "MONSTER"


def is_spell(card_or_id):
    return card_type(card_or_id) == "SPELL"


def is_trap(card_or_id):
    return card_type(card_or_id) == "TRAP"


def cards_by_type(card_ids):
    counts = {"MONSTER": 0, "SPELL": 0, "TRAP": 0}
    for card_id in card_ids:
        ctype = card_type(card_id)
        if ctype not in counts:
            raise ValueError(f"{card_id} não é um tipo de carta Rebirth suportado.")
        counts[ctype] += 1
    return counts


def validate_deck_distribution(card_ids, *, deck_size=STARTER_DECK_SIZE):
    if not isinstance(card_ids, list):
        raise ValueError("Os identificadores de cartas do baralho devem ser uma lista.")
    if len(card_ids) != deck_size:
        raise ValueError(f"Rebirth deck requires exactly {deck_size} cards.")
    counts = cards_by_type(card_ids)
    if not MONSTER_DECK_MIN <= counts["MONSTER"] <= MONSTER_DECK_MAX:
        raise ValueError("Rebirth deck requires between 18 and 22 monsters.")
    if abs(counts["SPELL"] - counts["TRAP"]) > 1:
        raise ValueError("Magias e armadilhas do baralho Rebirth devem estar equilibradas.")
    return counts


def get_card(card_id):
    try:
        return deepcopy(CARD_CATALOG_DICT[str(card_id)])
    except KeyError as exc:
        raise ValueError(f"Unknown Rebirth card: {card_id}") from exc


def create_card_instance(card_id, owner, sequence):
    card = get_card(card_id)
    card["owner"] = owner
    card["sequence"] = int(sequence or 0)
    card["instance_id"] = f"{owner}-{int(sequence or 0):02d}-{card['id']}"
    card["status_effects"] = []
    return card


def build_deck(owner, card_ids=None):
    source_ids = list(card_ids or (BOT_DECK if owner == "bot" else PLAYER_DECK))
    return [create_card_instance(card_id, owner, index + 1) for index, card_id in enumerate(source_ids)]


def catalog_payload():
    return [get_card(card_id) for card_id in CARD_CATALOG_DICT]
