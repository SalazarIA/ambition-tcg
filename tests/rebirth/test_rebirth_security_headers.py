SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def test_security_headers_are_present_on_public_rebirth_surfaces(client):
    for path in [
        "/",
        "/rebirth",
        "/health",
        "/privacy",
        "/terms",
        "/data-deletion",
        "/manifest.webmanifest",
        "/service-worker.js",
    ]:
        response = client.get(path)

        assert response.status_code == 200
        for header, expected in SECURITY_HEADERS.items():
            assert response.headers[header] == expected

        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "script-src 'self' 'unsafe-inline'" in csp
        assert "style-src 'self' 'unsafe-inline'" in csp
        assert "img-src 'self' data:" in csp
        assert "manifest-src 'self'" in csp
        assert "worker-src 'self'" in csp
        assert "object-src 'none'" in csp
        assert "base-uri 'self'" in csp
        assert "form-action 'self'" in csp
        assert "frame-ancestors 'none'" in csp


def test_security_headers_are_preserved_on_error_responses(client):
    response = client.post("/privacy")

    assert response.status_code == 405
    for header, expected in SECURITY_HEADERS.items():
        assert response.headers[header] == expected
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_service_worker_declares_root_scope(client):
    response = client.get("/service-worker.js")

    assert response.status_code == 200
    assert response.headers["Service-Worker-Allowed"] == "/"
    assert response.headers["Cache-Control"] == "no-cache"
    assert "application/javascript" in response.content_type


def test_root_manifest_uses_manifest_content_type(client):
    response = client.get("/manifest.webmanifest")

    assert response.status_code == 200
    assert "application/manifest+json" in response.content_type
    assert response.get_json()["start_url"].startswith("/rebirth")
