SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def test_security_headers_are_present_on_public_rebirth_surfaces(client):
    for path in ["/", "/rebirth", "/health", "/service-worker.js"]:
        response = client.get(path)

        assert response.status_code == 200
        for header, expected in SECURITY_HEADERS.items():
            assert response.headers[header] == expected

        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "script-src 'self' 'unsafe-inline'" in csp
        assert "style-src 'self' 'unsafe-inline'" in csp
        assert "img-src 'self' data:" in csp
        assert "frame-ancestors 'none'" in csp


def test_service_worker_declares_root_scope(client):
    response = client.get("/service-worker.js")

    assert response.status_code == 200
    assert response.headers["Service-Worker-Allowed"] == "/"
    assert response.headers["Cache-Control"] == "no-cache"
    assert "application/javascript" in response.content_type
