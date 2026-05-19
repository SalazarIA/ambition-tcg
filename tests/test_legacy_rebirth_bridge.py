LEGACY_ROUTES = [
    "/training",
    "/training-legacy",
    "/arena",
    "/collection",
    "/deck-builder",
    "/shop",
    "/roadmap",
]


def test_legacy_routes_show_rebirth_bridge_when_available(client):
    for path in LEGACY_ROUTES:
        response = client.get(path)
        if response.status_code == 404:
            continue
        if response.status_code in {302, 401, 403}:
            assert response.status_code in {302, 401, 403}
            continue

        body = response.get_data(as_text=True)
        assert response.status_code == 200, f"{path} returned {response.status_code}"
        assert "Rebirth" in body, f"{path} missing Rebirth migration copy"
        assert "/rebirth" in body, f"{path} missing Rebirth link"


def test_rebirth_route_does_not_import_legacy_arena_runtime(client):
    body = client.get("/rebirth").get_data(as_text=True)

    assert "az48" not in body
    assert "arena_clean_v48" not in body
    assert "socket.io" not in body.lower()
