def test_balance_snapshot_tool_imports():
    import tools.balance_snapshot as balance_snapshot

    assert callable(balance_snapshot.main)
