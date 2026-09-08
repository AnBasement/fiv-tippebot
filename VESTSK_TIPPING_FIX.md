# Code Review & Improvement Recommendations

## High Priority Issues

### 1. Deprecated Dependency: `oauth2client`
**Location:** `cogs/sheets.py` (line 5)

**Issue:** `oauth2client` is deprecated and no longer maintained by Google. It should be replaced with `google-auth`.

**Recommendation:** 
- Replace `oauth2client` with `google-auth` and `google-auth-oauthlib`
- Update credential handling to use the new library
- Update `cogs/sheets.py` entirely
- This also affects `pyproject.toml` if using ruff with oauth2client

### 2. Outdated Dependencies
**Location:** `requirements.txt` and implicit versions

**Identified outdated packages:**
- `discord.py==2.3.2` → Should be 2.4.x or later (we're in 2026)
- `pytz==2023.3` → Should be latest 2024+ version
- `asynctest` → Deprecated (Python 3.8+), use `unittest.mock.AsyncMock` instead
- `gspread==5.7.2` → Should verify latest version
- `python-dotenv==1.0.0` → Should verify latest version
- `Flask==2.3.3` → Should verify latest version
- Missing `google-auth` and `google-auth-oauthlib` (for oauth2client replacement)

**Recommendation:** Update `requirements.txt` and test thoroughly with new versions.

---

## Medium Priority Issues

### 3. Missing State Persistence Error Handling
**Location:** `vestsk_tipping.py` (lines ~600-650, `_load_state()` and `_save_state()`)

**Issue:** State loading/saving methods exist but their implementation isn't shown in the review. If they use a file-based approach, they could fail silently on permission errors.

**Recommendation:**
- Ensure `_load_state()` handles missing state files gracefully
- Log state persistence operations for debugging
- Consider using a dedicated database or persistent store instead of files

### 4. Hardcoded Configuration Values
**Location:** Multiple files

**Issues:**
- `cogs/ppr.py` (line 52): Hardcoded player names in `_get_players()` method
- `cogs/sheets.py`: Hardcoded sheet names ("Fest i Vest", "Vestsk Tipping")
- `data/channel_ids.py`: Channel IDs hardcoded (though there's a comment about testing)
- `cogs/responses.py`: Emoji IDs hardcoded in response messages

**Recommendation:** Move configuration to environment variables or a config file:
```python
# Example for environment variables
PLAYERS = os.getenv("PLAYERS", "").split(",")
MAIN_SHEET_NAME = os.getenv("MAIN_SHEET_NAME", "Fest i Vest")
```

### 5. Type Hints Missing in Key Functions
**Location:** `vestsk_tipping.py`

**Issues:**
- `_process_previous_week()` context namespace creation could be better typed
- Several methods lack return type hints
- Dictionary type hints are sometimes incomplete (e.g., `dict` instead of `dict[str, Any]`)

**Recommendation:** Add comprehensive type hints throughout `vestsk_tipping.py` to improve code clarity and enable better IDE support.

### 6. Error Handling Too Broad
**Location:** Multiple files

**Examples:**
- `vestsk_tipping.py` (line 318): `except Exception as exc:` catches all exceptions
- `cogs/ppr.py`: Similar broad exception handling
- `cogs/fantasy_reminders.py`: Broad exception catches

**Recommendation:** Be more specific with exception types to avoid masking unexpected errors:
```python
except (asyncio.TimeoutError, aiohttp.ClientError) as exc:
```

---

## Low Priority Issues (Code Quality & Documentation)

### 7. Timezone Offset Quirk in `vestsk_tipping.py`
**Location:** `_season_window()` method (line 461)

**Issue:** The bot reports an unusual timezone offset (`+00:53` in logs), likely a DST or pytz formatting quirk. However, the bot's actual behavior is correct—it properly waits until Sept 9 00:00 when the season starts.

**Recommendation:** Low priority. Monitor for actual issues. If timezone handling causes problems later, investigate pytz handling or consider replacing with `zoneinfo` (Python 3.9+).

### 8. Magic Numbers & Hardcoded Values
**Location:** Various files

**Examples:**
- `vestsk_tipping.py` (line 43-44): `PROCESS_WEEKDAY = 1`, `PROCESS_HOUR = 20` (well-documented but still magic)
- `reminder_scheduler()`: `timedelta(minutes=60)` appears multiple times
- API timeout values (10 seconds) hardcoded in multiple places

**Recommendation:** Create constants at module level:
```python
API_TIMEOUT_SECONDS = 10
BET_CLOSE_BUFFER_MINUTES = 60
```

### 9. Inconsistent Documentation
**Location:** Various files

**Issues:**
- Some cogs have comprehensive docstrings, others are minimal
- `core/keep_alive.py` has no description of what "keep alive" means (Flask pinging)
- `_fetch_week_events()` lacks a docstring

**Recommendation:** Add docstrings to all public methods following the existing format.

### 10. Complex Function: `reminder_scheduler()`
**Location:** `vestsk_tipping.py` (line 227)

**Issue:** This is ~150+ lines with nested logic for Thursday and Sunday reminders. It's difficult to follow and maintain.

**Recommendation:** Break into separate methods:
```python
async def _check_thursday_reminder()
async def _check_sunday_reminder()
```

### 11. Unused/Redundant Code
**Location:** `core/utils/global_cooldown.py` (line 20-21)

**Issue:** Comment says "on_command_error is now handled centrally" but the decorator still exists. If it's genuinely needed, update the comment. If not, consider deprecating.

### 12. Test Coverage
**Location:** `tests/` folder

**Issues:**
- `conftest.py` mocks Google Sheets but doesn't test actual integration
- No tests for `vestsk_tipping.py` auto scheduler logic
- No tests for timezone handling in season window calculations

**Recommendation:** Add integration tests for:
- Season window edge cases (Sept 8, seasonal transitions)
- Auto-posting scheduler state management
- State persistence and recovery

### 13. Hardcoded Google Sheet Names
**Location:** Multiple files

**Examples:**
- `cogs/ppr.py` (line 40): `self.sheet = get_client().open("Fest i Vest")`
- `cogs/vestsk_tipping.py`: Likely has hardcoded sheet names

**Recommendation:** Move to environment variables:
```python
MAIN_SHEET = os.getenv("GOOGLE_SHEET_NAME", "Fest i Vest")
```

### 14. Missing `setup()` Function
**Location:** `cogs/vestsk_tipping.py`, `cogs/ppr.py`, `cogs/fantasy_reminders.py`

**Issue:** Discord.py 2.0+ requires a `setup()` function for cog loading. These cogs appear to use the old-style loading. Verify they have proper async setup functions:

```python
async def setup(bot: Bot) -> None:
    await bot.add_cog(VestskTipping(bot))
```

**Recommendation:** Verify all cogs follow the 2.0+ pattern.

---

## Deprecation Warnings

### 15. `oauth2client` Library
The entire Google Sheets authentication should migrate to `google-auth`:
```python
# Old (deprecated)
from oauth2client.service_account import ServiceAccountCredentials

# New
from google.oauth2.service_account import Credentials
```

---

## Summary of Quick Wins

1. Update `asynctest` to use `unittest.mock.AsyncMock` in tests
2. Add environment variable `GOOGLE_SHEETS_KEYFILE` (already exists, but could be documented better)
3. Add constants for magic numbers at top of modules
4. Add a few missing docstrings to public methods
5. Verify all cogs have proper `async def setup(bot)` functions

---

## Testing Recommendations

Before deploying with updated dependencies:
1. Run full test suite with new discord.py version
2. Test season window calculations for 2026 specifically
3. Test state persistence across bot restarts
4. Test auto-posting scheduler with mock ESPN API data
5. Test timezone handling in all reminder functions

---

## Configuration Checklist Before Season Start

- [ ] Verify `credentials.json` for Google API access
- [ ] Verify `ADMIN_IDS` environment variable is set correctly
- [ ] Verify `PREIK_KANAL` and `VESTSK_KANAL` are correct channel IDs
- [ ] Verify Google Sheets "Fest i Vest" exists and is shared with bot
- [ ] Verify Google Sheets "Vestsk Tipping" 2026 sheet exists
- [ ] Test `!kamper` command to ensure ESPN API access works
- [ ] Test `!eksporter` after setting bets to ensure Sheets export works
- [ ] Review logs for any timezone errors on Sept 8-9, 2026
