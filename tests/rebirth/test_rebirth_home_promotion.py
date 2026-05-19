def test_home_promotes_rebirth_first(client):
    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Ambitionz Rebirth" in body
    assert "One card. One decision. One clash." in body
    assert 'href="/rebirth"' in body
    assert "Play Rebirth Prototype" in body
    assert "Single cockpit" in body


def test_home_does_not_make_ascension_primary_cta(client):
    body = client.get("/").get_data(as_text=True)
    hero_start = body.index('id="rebirth-home-hero"')
    hero_end = body.index("rb-home-preview", hero_start)
    hero = body[hero_start:hero_end]

    assert "Play Rebirth Prototype" in hero
    assert "Play Ascension Duel" not in hero
    assert 'href="/training"' not in hero
