"""Disable collection for tests that target the retired pre-Rebirth product."""


def pytest_ignore_collect(collection_path, config):
    return collection_path.name.startswith("test_") and collection_path.name != "test_archive_notice.py"
