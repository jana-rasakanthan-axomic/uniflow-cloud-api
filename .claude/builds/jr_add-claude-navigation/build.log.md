# Build Log: EP01-T06 Long-Poll Signaling Channel

**Branch:** `jr_add-claude-navigation`
**Session ID:** 2026-03-25-initial
**Build Start:** 2026-03-25 00:00

## Scope

Implementing long-poll signaling channel per ADR-0001 for uniflow-cloud-api.

### Components
1. CommandRepository - Atomic command fetch/mark (pop_pending)
2. SignalingService - Poll event management (hold_poll, dispatch_command)
3. Edge Router - GET /poll endpoint
4. Config - Add poll_timeout_seconds
5. Shutdown handler - Close all connections

### Build Order (Layer-by-Layer TDD)
1. Repository Layer - CommandRepository
2. Service Layer - SignalingService poll methods
3. API Layer - GET /poll endpoint
4. Config/Main - Settings & shutdown handler

---

## TDD Log

### Layer 1: Repository - CommandRepository

**WRITE_TESTS** (2026-03-25 00:00)
- Created `tests/test_command_repository.py`
- Tests: pop_pending returns oldest, returns None when empty, filters by agent_id, ignores EXPIRED

**CONFIRM_RED** (2026-03-25 00:05)
- Tests fail: `ModuleNotFoundError: No module named 'app.repositories.command_repository'`
- Status: RED confirmed ✓

**WRITE_IMPL** (2026-03-25 00:10)
- Created `app/repositories/command_repository.py`
- Implemented `pop_pending(db, agent_id)` - SELECT + UPDATE pattern

**CONFIRM_GREEN** (2026-03-25 00:15)
- All 5 tests pass
- Status: GREEN confirmed ✓

**VERIFY** (2026-03-25 00:20)
- Linter: 4 issues auto-fixed (datetime.UTC, import sorting)
- Tests still pass after fixes
- Status: VERIFIED ✓

---

### Layer 2: Service - SignalingService Poll Methods

**WRITE_TESTS** (2026-03-25 00:25)
- Created `tests/test_signaling_service_poll.py`
- Tests: hold_poll timeout, immediate return, dispatch wake, event cleanup, active agents, close_all

**CONFIRM_RED** (2026-03-25 00:30)
- All 9 tests fail: `AttributeError: 'SignalingService' object has no attribute 'hold_poll'`
- Status: RED confirmed ✓

**WRITE_IMPL** (2026-03-25 00:35)
- Extended `app/services/signaling_service.py`
- Added: hold_poll, dispatch_command, get_active_poll_agents, close_all_connections
- Added internal state: _poll_events dict, _events_lock

**CONFIRM_GREEN** (2026-03-25 00:40)
- All 9 tests pass
- Status: GREEN confirmed ✓

**VERIFY** (2026-03-25 00:45)
- Linter: 1 issue auto-fixed (asyncio.TimeoutError → TimeoutError)
- Tests still pass after fixes
- Status: VERIFIED ✓

---

### Layer 3: API - GET /poll Endpoint

**WRITE_TESTS** (2026-03-25 00:50)
- Created `tests/test_edge_poll_endpoint.py`
- Tests: returns none on timeout, returns command, validates agent_id, calls hold_poll

**CONFIRM_RED** (2026-03-25 00:55)
- Tests fail: `TypeError: poll() got an unexpected keyword argument 'agent_id'`
- Status: RED confirmed ✓

**WRITE_IMPL** (2026-03-25 01:00)
- Replaced placeholder `GET /poll` in `app/api/routers/edge.py`
- Added agent_id validation, SignalingService call, command/timeout responses
- Added `poll_timeout_seconds: int = 55` to `app/config.py`

**CONFIRM_GREEN** (2026-03-25 01:05)
- All 4 tests pass
- Status: GREEN confirmed ✓

**VERIFY** (2026-03-25 01:10)
- Linter: Added B008 ignore for FastAPI dependency injection pattern
- Tests still pass
- Status: VERIFIED ✓

---

### Layer 4: Config/Main - Shutdown Handler

**WRITE_TESTS** (2026-03-25 01:15)
- Created `tests/test_app_shutdown.py`
- Test: shutdown handler calls SignalingService.close_all_connections

**CONFIRM_RED** (2026-03-25 01:20)
- Test fails: `AttributeError: <module 'app.main'> does not have the attribute 'SignalingService'`
- Status: RED confirmed ✓

**WRITE_IMPL** (2026-03-25 01:25)
- Added lifespan context manager to `app/main.py`
- Calls `SignalingService().close_all_connections()` on shutdown

**CONFIRM_GREEN** (2026-03-25 01:30)
- Test passes
- Status: GREEN confirmed ✓

**VERIFY** (2026-03-25 01:35)
- Linter: 1 issue auto-fixed (import sorting)
- Test still passes
- Status: VERIFIED ✓

---

## Build Complete

**End Time:** 2026-03-25 01:40
**Total Duration:** ~1h 40m

### Summary Table

| Layer | Component | Files Created/Modified | Tests | Status |
|-------|-----------|----------------------|-------|--------|
| Repository | CommandRepository | `app/repositories/command_repository.py` | 5 | ✓ PASS |
| Service | SignalingService | `app/services/signaling_service.py` | 9 | ✓ PASS |
| API | GET /poll | `app/api/routers/edge.py` | 4 | ✓ PASS |
| Config/Main | Shutdown handler | `app/main.py`, `app/config.py` | 1 | ✓ PASS |

**Total Tests:** 19 passing

### Files Created
- `app/repositories/command_repository.py`
- `tests/test_command_repository.py`
- `tests/test_signaling_service_poll.py`
- `tests/test_edge_poll_endpoint.py`
- `tests/test_app_shutdown.py`

### Files Modified
- `app/services/signaling_service.py` - Added poll methods
- `app/api/routers/edge.py` - Implemented GET /poll endpoint
- `app/config.py` - Added poll_timeout_seconds
- `app/main.py` - Added lifespan shutdown handler
- `app/exceptions/__init__.py` - Added placeholder exceptions
- `pyproject.toml` - Added B008 ignore for FastAPI

### Design Decisions
1. Used asyncio.Event for poll wake signaling (not channels/queues)
2. Short timeout (0.1s) in tests instead of 55s
3. Module-level SignalingService instances (not singleton pattern)
4. Simple SELECT + UPDATE for pop_pending (defer FOR UPDATE SKIP LOCKED optimization)
5. Lifespan context manager (modern FastAPI pattern, not @app.on_event)

### Plan Alignment
All components from EP01-T06 scope implemented:
- ✓ CommandRepository with pop_pending
- ✓ SignalingService with hold_poll, dispatch_command, get_active_poll_agents, close_all_connections
- ✓ GET /poll endpoint with auth and agent_id validation
- ✓ Config setting poll_timeout_seconds
- ✓ Shutdown handler to close connections
