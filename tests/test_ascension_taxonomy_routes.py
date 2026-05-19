from pathlib import Path

from services.ascension_cards import build_ascension_starter_deck, get_card_by_id
from services.ascension_taxonomy import ascension_deck_summary, ascension_type_label, enrich_ascension_card


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_ascension_taxonomy_maps_legacy_internally():
    assert ascension_type_label("Monster") == "Champion"
    assert ascension_type_label("Spell") == "Technique"
    assert ascension_type_label("Trap") == "Scheme"


def test_ascension_card_enrichment_and_deck_summary():
    card = enrich_ascension_card(get_card_by_id("ember_vowbound"), owned_ids={"ember_vowbound"})
    summary = ascension_deck_summary(build_ascension_starter_deck(seed="taxonomy"))

    assert card["type_label"] == "Champion"
    assert card["role"] in {"Pressure Champion", "Anchor Champion", "Balanced Champion"}
    assert summary["total"] == 30
    assert summary["counts"]["champion"] >= 10
    assert summary["posture"] in {"Pressure-led", "Control-led", "Momentum-led", "Balanced"}


def test_new_public_ascension_pages_do_not_expose_legacy_primary_labels(client):
    for path in ["/", "/roadmap", "/training", "/collection-ascension", "/deck-builder-ascension"]:
        response = client.get(path)
        body = response.get_data(as_text=True).lower()

        assert response.status_code == 200
        assert "monster" not in body
        assert "spell" not in body
        assert "trap" not in body
        assert "lane" not in body


def test_ascension_collection_and_deck_routes_render_new_taxonomy(client):
    collection = client.get("/collection-ascension")
    deck = client.get("/deck-builder-ascension")

    assert collection.status_code == 200
    assert "Ascension Collection" in collection.get_data(as_text=True)
    assert "Champion" in collection.get_data(as_text=True)
    assert "Technique" in collection.get_data(as_text=True)
    assert deck.status_code == 200
    assert "Ascension Deck" in deck.get_data(as_text=True)
    assert "pressure" in deck.get_data(as_text=True)


def test_public_home_ctas_use_ascension_routes():
    homepage = (PROJECT_ROOT / "templates" / "index.html").read_text()

    assert "url_for('collection_ascension')" in homepage
    assert "url_for('deck_builder_ascension')" in homepage
    assert "url_for('rebirth')" in homepage
    assert "az-rebirth-bridge" in homepage
    assert "Legacy Arena" in homepage
