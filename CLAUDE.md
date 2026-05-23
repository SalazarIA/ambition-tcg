# Ambitionz TCG — Claude operating rules

## Autonomy

The owner of this repo has authorized Claude to act on any front of this
project without asking for confirmation, until the game reaches a fully
playable state.

This includes:
- Editing any file in the tree (services, routes, templates, static assets, tests, docs).
- Committing to feature branches and to `main`.
- Pushing to `origin` (including `origin/main`, which triggers Render deploy via `render.yaml`).
- Installing/removing dependencies, updating `requirements.txt` / `requirements-dev.txt` / `package.json`.
- Running migrations, schema changes, and refactors that touch multiple modules at once.
- Deleting dead code, stale branches, and obsolete docs.

What is still off-limits without an explicit ask:
- Destructive history rewrites on shared branches (`git reset --hard origin/main`, force-push to `main`, deleting remote branches, rewriting published commits).
- Anything that touches secrets, `.env*` files, or production credentials.
- Spending money (paid APIs, paid services, infra upgrades).
- Disabling tests or pre-commit hooks (`--no-verify`) to make a red build green.

The bar drops once the game is playable end-to-end; revisit this section then.

## Project conventions (observed, not invented)

- `pytest.ini` opts e2e + `requires_postgres` out of the default run. Fast suite must stay green after every change.
- Service worker (`pwa.js`) is real and active in production; tests must block it explicitly when driving the browser.
- `services/rebirth_persistence.py` market handlers wrap `SQLAlchemyError` as `RebirthPersistenceError(code="database_write_failed")` — that mapping is part of the test contract.
- `_monster_cost` in `services/rebirth_cards.py` is the canonical mana-curve formula; catalog generators and tests both pin to it.
- Render auto-deploys from `main` per `render.yaml`. Don't push half-finished work to `main` even with autonomy — use a feature branch and fast-forward when ready.

## Communication

- Portuguese (pt-BR) is the working language with the owner.
- Skip end-of-turn praise / preamble; report what changed and what's next.
