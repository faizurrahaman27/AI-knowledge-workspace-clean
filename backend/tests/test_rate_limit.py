def test_rate_limit_blocks_after_threshold(client, monkeypatch):
    from src.core import rate_limit as rl

    monkeypatch.setattr(rl.settings, "RATE_LIMIT_PER_MINUTE", 3)

    statuses = []
    for _ in range(5):
        r = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "whatever123"},
        )
        statuses.append(r.status_code)

    assert 429 in statuses, f"Expected a 429 once the rate limit was exceeded, got {statuses}"
