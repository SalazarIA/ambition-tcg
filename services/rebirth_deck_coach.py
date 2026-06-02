from collections import Counter

from services.rebirth_cards import catalog_payload


def _catalog_index():
    return {card["id"]: card for card in catalog_payload()}


def _counts(collection_counts=None, loadout_card_ids=None):
    counts = Counter(collection_counts or {})
    if not counts:
        counts.update(loadout_card_ids or [])
    return counts


def deck_suggestions(profile=None, collection_counts=None, loadout_card_ids=None, booster_cards=None, last_match=None):
    """Return small, actionable deck-edit suggestions for closed beta."""
    profile = profile or {}
    catalog = _catalog_index()
    counts = _counts(collection_counts=collection_counts, loadout_card_ids=loadout_card_ids)
    loadout = [catalog[card_id] for card_id in (loadout_card_ids or []) if card_id in catalog]
    booster_cards = booster_cards or []
    suggestions = []

    families = Counter(card.get("family") for card in loadout if card.get("family"))
    if loadout:
        main_family, main_count = families.most_common(1)[0] if families else ("FIRE", 0)
        support_count = sum(1 for card in loadout if str(card.get("type")).upper() in {"SPELL", "TRAP"})
        duplicate_pairs = sum(1 for amount in Counter(card["id"] for card in loadout).values() if amount >= 2)
        if duplicate_pairs < 4:
            suggestions.append(
                {
                    "title": "Aumente pares de evolução",
                    "copy": "Seu deck tem poucos pares. Duplicatas tornam a primeira evolução mais frequente.",
                    "action": "Troque cartas soltas por uma segunda cópia de monstros que você já usa.",
                }
            )
        if support_count < 7:
            suggestions.append(
                {
                    "title": "Inclua mais respostas",
                    "copy": "Magias e armadilhas evitam turnos mortos quando o campo está cheio.",
                    "action": "Suba para 7 a 10 cartas de suporte no deck de 30.",
                }
            )
        suggestions.append(
            {
                "title": f"Consolide {main_family}",
                "copy": f"{main_count} cartas do seu deck já compartilham essa família.",
                "action": "Teste duas partidas mantendo a família dominante antes de mudar tudo.",
            }
        )

    new_cards = [card for card in booster_cards if card.get("id") in catalog]
    if new_cards:
        best = sorted(
            new_cards,
            key=lambda card: (
                str(card.get("rarity") or "") == "LEGENDARY",
                int(card.get("tier", 1) or 1),
                int(card.get("attack", 0) or 0) + int(card.get("guard", 0) or 0),
            ),
            reverse=True,
        )[0]
        suggestions.insert(
            0,
            {
                "title": f"Teste {best['name']}",
                "copy": "Foi a carta mais promissora do booster recém-aberto.",
                "action": "Substitua uma carta da mesma família ou uma carta sem par no deck.",
            },
        )

    losses = int(profile.get("losses", 0) or 0)
    wins = int(profile.get("wins", 0) or 0)
    if losses > wins:
        suggestions.append(
            {
                "title": "Mais defesa no próximo teste",
                "copy": "Seu histórico atual tem mais derrotas que vitórias.",
                "action": "Priorize cartas com Guarda alta, cura ou escudo por duas partidas.",
            }
        )

    if not suggestions:
        suggestions.append(
            {
                "title": "Deck pronto para amostra maior",
                "copy": "Nenhum ajuste óbvio apareceu agora.",
                "action": "Jogue três partidas e reavalie com o recap pós-match.",
            }
        )

    return suggestions[:4]
