Legacy Disabled Tests
=====================

These tests belong to the pre-Rebirth Arena, Ascension, BE2, economy,
progression, shop, collection, deck builder, SocketIO and database product
surface.

Ambitionz Rebirth is now the only active runtime product. The standard test
suite is intentionally scoped to `tests/rebirth` through `pytest.ini`.

Do not make these tests pass by restoring retired APIs, routes, database
systems, SocketIO handlers or economy flows. If a retired behavior is migrated
into Rebirth later, add new Rebirth-native coverage under `tests/rebirth`.
