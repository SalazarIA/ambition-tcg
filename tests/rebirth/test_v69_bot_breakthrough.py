"""v69: bot deve responder a Breakthrough threat na valoração de ataques."""

from services.rebirth_bot import (
    attack_utility_projection,
    breakthrough_potential,
    opponent_breakthrough_pressure,
    tactical_utility_matrix,
)


def make_card(**fields):
    base = {
        "id": fields.get("id", "fake"),
        "instance_id": fields.get("instance_id", fields.get("id", "fake")),
        "attack": 0,
        "power": 0,
        "guard": 0,
        "current_guard": fields.get("current_guard", fields.get("guard", 0)),
        "tier": 1,
        "ability_key": "",
        "field_slot": fields.get("field_slot", 0),
        "exhausted": False,
        "has_attacked": False,
        "has_acted": False,
        "owner_side": fields.get("owner_side", "player"),
    }
    base.update(fields)
    base.setdefault("power", base["attack"])
    base.setdefault("current_guard", base.get("guard", 0))
    return base


def test_v69_breakthrough_potential_caps_at_engine_ceiling():
    # Engine cap on Breakthrough is 2 hero damage per attack.
    bramble = make_card(id="card_046", attack=7, guard=3)
    assert breakthrough_potential(bramble, defender_guard_pool=0) == 2
    assert breakthrough_potential(bramble, defender_guard_pool=4) == 2  # 7-4=3 → capped
    assert breakthrough_potential(bramble, defender_guard_pool=7) == 0
    assert breakthrough_potential(bramble, defender_guard_pool=20) == 0
    assert breakthrough_potential(None, defender_guard_pool=0) == 0


def test_v69_opponent_breakthrough_pressure_pairs_attackers_with_blockers():
    # Player has 2 strong attackers; bot has only 1 small blocker.
    attacker_a = make_card(id="card_046", instance_id="a", attack=7)
    attacker_b = make_card(id="card_045", instance_id="b", attack=6)
    blocker = make_card(id="card_044", instance_id="x", attack=3, guard=4, current_guard=4, owner_side="bot")
    pressure = opponent_breakthrough_pressure([attacker_a, attacker_b], [blocker])
    # Strongest opponent (7) paired with blocker (guard 4) → overflow 3 → capped at 2.
    # Second opponent (6) faces empty pool → overflow 6 → capped at 2. Total = 4.
    assert pressure == 4


def test_v69_attack_utility_rewards_killing_breakthrough_threat():
    # Bot attacker is strong enough to kill the target one-shot.
    bot_attacker = make_card(id="bot_str", instance_id="bot1", attack=8, guard=4, current_guard=4, owner_side="bot")
    threat = make_card(id="card_046", instance_id="bram", attack=7, guard=3, current_guard=3)
    bench_blocker = make_card(id="bot_def", instance_id="bot2", attack=2, guard=1, current_guard=1, owner_side="bot")

    proj = attack_utility_projection(
        bot_attacker,
        threat,
        bot_battlefield=[bot_attacker, bench_blocker],
        player_battlefield=[threat],
        player_hp=30,
        turn=4,
    )

    assert proj["allowed"] is True
    assert proj["target_destroyed"] is True
    assert proj["breakthrough_pressure"] >= 2
    assert proj["reason"] == "neutralize_breakthrough"


def test_v69_attack_utility_penalizes_leaving_breakthrough_alive():
    # Bot attacker chips but cannot kill the Breakthrough threat in one swing,
    # and survives the counter — não é suicídio nem futuro-lethal, então a
    # razão deve ser explicitamente o threat deixado vivo.
    chipper = make_card(id="bot_chip", instance_id="bot1", attack=4, guard=6, current_guard=6, owner_side="bot")
    threat = make_card(id="card_046", instance_id="bram", attack=6, guard=5, current_guard=5)

    proj = attack_utility_projection(
        chipper,
        threat,
        bot_battlefield=[chipper],
        player_battlefield=[threat],
        player_hp=30,
        turn=4,
    )

    assert proj["target_destroyed"] is False
    assert proj["attacker_destroyed"] is False
    assert proj["breakthrough_pressure"] >= 1
    assert proj["reason"] == "leaves_breakthrough_alive"


def test_v69_matrix_prefers_threat_kill_over_smaller_target():
    # Two viable targets: small dummy (no threat) and big Bramblehorn (Breakthrough).
    strong_attacker = make_card(id="bot_str", instance_id="bot1", attack=8, guard=4, current_guard=4, owner_side="bot")
    dummy = make_card(id="card_010", instance_id="dummy", attack=2, guard=2, current_guard=2)
    threat = make_card(id="card_046", instance_id="bram", attack=7, guard=3, current_guard=3)

    rows = tactical_utility_matrix(
        [strong_attacker],
        [dummy, threat],
        player_hp=30,
        turn=4,
    )
    rows_by_target = {row["target_instance_id"]: row for row in rows}
    # Killing the Breakthrough threat should outrank killing a dummy.
    assert rows_by_target["bram"]["utility"] > rows_by_target["dummy"]["utility"]
