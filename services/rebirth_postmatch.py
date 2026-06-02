def _hp(side):
    return int((side or {}).get("hp", 0) or 0)


def _card_name(card, fallback):
    return str((card or {}).get("name") or fallback)


def post_match_recap(state):
    """Build a short player-facing explanation for a finished match."""
    state = state or {}
    if not state.get("is_finished"):
        return None

    winner = state.get("winner")
    player_hp = _hp(state.get("player"))
    bot_hp = _hp(state.get("bot"))
    turn = int(state.get("turn", 0) or 0)
    result = state.get("result") or {}
    last_clash = state.get("last_clash") or {}
    damage = result.get("damage") or {}
    hero_damage = result.get("hero_damage") or {}
    player_card = _card_name(last_clash.get("player_card"), "sua unidade")
    bot_card = _card_name(last_clash.get("bot_card"), "a unidade do bot")

    won = winner == "player"
    title = "Por que você venceu" if won else "Por que você perdeu" if winner == "bot" else "Como a partida terminou"
    bullets = []

    if won:
        bullets.append(f"Você derrubou o bot para {bot_hp} HP no turno {turn}.")
        if player_hp <= 8:
            bullets.append(f"Foi uma vitória apertada: você terminou com {player_hp} HP.")
        elif player_hp >= 18:
            bullets.append(f"Sua linha preservou HP: você terminou com {player_hp} HP.")
    elif winner == "bot":
        bullets.append(f"O bot zerou seu HP no turno {turn}.")
        if bot_hp <= 8:
            bullets.append(f"A partida estava próxima: o bot terminou com {bot_hp} HP.")
        else:
            bullets.append(f"O bot manteve {bot_hp} HP e controlou o ritmo da mesa.")
    else:
        bullets.append(f"A partida encerrou no turno {turn} sem vencedor claro.")

    if last_clash:
        bullets.append(f"A última troca colocou {player_card} contra {bot_card}.")

    bot_damage = int(damage.get("bot", 0) or 0) + int(hero_damage.get("bot", 0) or 0)
    player_damage = int(damage.get("player", 0) or 0) + int(hero_damage.get("player", 0) or 0)
    if bot_damage > player_damage:
        bullets.append(f"Você causou mais dano no fechamento ({bot_damage} contra {player_damage}).")
    elif player_damage > bot_damage:
        bullets.append(f"O bot causou mais dano no fechamento ({player_damage} contra {bot_damage}).")

    ability_events = result.get("ability_events") or []
    if ability_events:
        bullets.append(f"Efeito decisivo: {ability_events[-1]}")

    next_step = (
        "Abra um booster ou ajuste o deck para repetir a linha vencedora."
        if won
        else "Priorize campo antes de dano direto e guarde mana para responder pressão."
        if winner == "bot"
        else "Jogue outra partida para validar o deck com uma amostra melhor."
    )

    return {
        "title": title,
        "outcome": winner or "draw",
        "turn": turn,
        "bullets": bullets[:4],
        "next_step": next_step,
    }
