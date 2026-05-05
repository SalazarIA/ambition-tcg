from game.cards import get_card_by_id
from models import CardStat, db


def played_cards_for_stats(player):
    cards = []

    cards.extend([card for card in player.get("graveyard", []) if card])

    for zone in ("field_m", "field_st"):
        card = player.get(zone)

        if card:
            cards.append(card)

    return cards


def update_card_stats_after_match(match, winner_key):
    for player_key in ("p1", "p2"):
        player = match.get(player_key, {})
        played_cards = played_cards_for_stats(player)

        if not played_cards:
            continue

        seen_card_ids = set()

        for card in played_cards:
            card_id = card.get("id")

            if not card_id:
                continue

            catalog_card = get_card_by_id(card_id) or card
            stat = CardStat.query.filter_by(card_id=card_id).first()

            if not stat:
                stat = CardStat(
                    card_id=card_id,
                    card_name=catalog_card.get("name", card.get("name", card_id)),
                    card_type=catalog_card.get("type", card.get("type", "Unknown")),
                    element=catalog_card.get("element", card.get("element", "Global")),
                    rarity=catalog_card.get("rarity", card.get("rarity", "Common")),
                )
                db.session.add(stat)

            stat.times_played = int(stat.times_played or 0) + 1

            if card_id not in seen_card_ids:
                stat.games_seen = int(stat.games_seen or 0) + 1
                seen_card_ids.add(card_id)

            if winner_key == "DRAW":
                stat.draws_when_played = int(stat.draws_when_played or 0) + 1
            elif winner_key == player_key:
                stat.wins_when_played = int(stat.wins_when_played or 0) + 1
            else:
                stat.losses_when_played = int(stat.losses_when_played or 0) + 1
