def test_home_promotes_rebirth_first(client):
    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Ambitionz Rebirth" in body
    assert "Duelos, coleção e mercado em uma mesa viva." in body
    assert 'href="/rebirth"' in body
    assert "Entrar na Arena" in body
    assert "Loja &amp; Mercado" in body
    assert "Ouro + Gemas" in body


def test_home_does_not_make_ascension_primary_cta(client):
    body = client.get("/").get_data(as_text=True)
    hero_start = body.index('id="rebirth-home-hero"')
    hero_end = body.index("rb-home-preview", hero_start)
    hero = body[hero_start:hero_end]

    assert "Entrar na Arena" in hero
    assert "Play Ascension Duel" not in hero
    assert 'href="/training"' not in hero
