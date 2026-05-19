def test_home_promotes_rebirth_first(client):
    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Ambitionz Rebirth" in body
    assert "One-card tactical duels built for cinematic 3D combat." in body
    assert 'href="/rebirth"' in body
    assert "Enter Rebirth" in body
    assert "Legacy Access" in body
    assert "View Legacy Arena" in body


def test_home_does_not_make_ascension_primary_cta(client):
    body = client.get("/").get_data(as_text=True)
    hero_start = body.index('id="ax-home-hero"')
    hero_end = body.index("ax-home-proof", hero_start)
    hero = body[hero_start:hero_end]

    assert "Enter Rebirth" in hero
    assert "Play Ascension Duel" not in hero
    assert 'href="/training"' not in hero
