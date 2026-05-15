# Tests

Three layers, each catching a different class of bug:

| Layer | Where | Catches |
|---|---|---|
| **Unit** | `tests/unit/` | Pure functions, i18n integrity, callback_data limits, webapp JSON contract |
| **DB integration** | `tests/integration/test_db.py` | Schema drift, broken upserts, stats math, JSON serialization |
| **Handler integration** | `tests/integration/test_handlers.py` | Full callback → DB → response flow; FSM transitions; regression tests for past bugs |

## Running

### Unit tests only (no setup required)

```bash
pip install -r requirements-dev.txt
pytest tests/unit
```

Always runs in CI and locally — fast, no Postgres needed.

### Full suite (requires Postgres)

You need a Postgres available with a database where `schema.sql` can be applied. Test runs `TRUNCATE … CASCADE` between tests, so use a dedicated test DB — **not** your dev/prod DB.

```bash
# spin up a local Postgres in Docker (one time)
docker run -d --name psybot-test-db \
  -e POSTGRES_USER=psybot -e POSTGRES_PASSWORD=psybot -e POSTGRES_DB=psybot_test \
  -p 5433:5432 postgres:16

export TEST_DATABASE_URL=postgresql://psybot:psybot@localhost:5433/psybot_test
pytest
```

If `TEST_DATABASE_URL` is unset, integration tests are auto-skipped.

### Specific tests

```bash
pytest tests/integration/test_db.py::test_subscription_record_does_NOT_have_timezone_column -v
```

## CI

`.github/workflows/tests.yml` spins up Postgres as a service and runs the full suite on every push and PR.

## Adding a new test

- **New i18n key** → already covered: `test_all_keys_exist_in_both_languages` fails if missing in one lang.
- **New DB function** → add to `test_db.py`. Always cover the happy path + at least one edge case (missing row, idempotency).
- **New handler** → add a smoke test to `test_handlers.py` that wires a `make_callback` / `make_message` + real `pool` + real `fsm` and checks that:
  - the handler doesn't raise
  - `.answer()` / `.edit_text()` is awaited
  - DB state is what you expect
- **New WebApp message format** → update `test_webapp_payloads.py` to pin the contract.

## Why this catches the bugs we've actually hit

- The `KeyError: 'timezone'` bug — `test_start_session_uses_user_timezone_not_subscription` and `test_cb_hist_action_uses_user_timezone_not_subscription` would have failed before the fix
- Schema column moves — `test_subscription_record_does_NOT_have_timezone_column` is an explicit regression guard
- "Delete confirmation shown even with no record" — `test_cb_hist_day_delete_with_no_record_shows_fallback`
- callback_data over 64 bytes — `test_keyboards.py` walks every KB and asserts length
- i18n key drift — `test_all_keys_exist_in_both_languages`
