# Codebase Concerns

**Analysis Date:** 2026-03-29

## Technical Debt

### Monolithic File Complexity

**Issue:** Several core files have grown to extreme sizes, making maintenance and debugging difficult.

- `run_agent.py` - 8,283 lines
- `cli.py` - 7,602 lines
- `gateway/run.py` - 5,924 lines
- `hermes_cli/main.py` - 4,381 lines
- `hermes_cli/setup.py` - 3,592 lines

**Impact:** Hard to navigate, understand, and test. High risk of introducing bugs when modifying these files.

**Recommendation:** Consider extracting distinct responsibilities into separate modules (e.g., provider handling, tool orchestration, message processing).

---

### Deprecated Configuration Variables

**Issue:** Some environment variables are deprecated but still accepted for backward compatibility.

**Files:** `hermes_cli/config.py` (lines 953-969)

```python
"HERMES_TOOL_PROGRESS": {
    "description": "(deprecated) Use display.tool_progress in config.yaml instead",
},
"HERMES_TOOL_PROGRESS_MODE": {
    "description": "(deprecated) Use display.tool_progress in config.yaml instead",
},
```

**Impact:** Users may configure using deprecated variables without knowing they're deprecated.

**Recommendation:** Remove deprecated vars or add clear deprecation warnings at startup.

---

### Broad Exception Handling

**Issue:** 2,252 instances of `except Exception:` and `except:` patterns throughout the codebase.

**Examples:**
- `run_agent.py` - multiple broad exception handlers
- `tools/web_tools.py` - line 431: `except RuntimeError:` followed by `except Exception:`
- `tools/terminal_tool.py` - multiple bare `except:` clauses

**Impact:** Errors are silently swallowed, making debugging difficult. Specific error conditions are not properly surfaced.

**Recommendation:** Use specific exception types and propagate meaningful errors.

---

### Empty Return Values

**Issue:** 863+ functions return empty containers (`{}`, `[]`, `None`) instead of proper error objects.

**Example locations:**
- `toolsets.py` - lines 412, 415, 429, 576
- `tools/web_tools.py` - line 67 returns `{}`
- `tools/website_policy.py` - lines 55, 58, 78, 81 return `None` or `[]`

**Impact:** Callers cannot distinguish between "not available", "failed", and "success with empty result".

**Recommendation:** Use typed results or raise exceptions for failure cases.

---

## Known Bugs / Unresolved Issues

### OpenAI SDK Event Loop Workaround

**File:** `agent/auxiliary_client.py` (lines 1230-1249)

**Issue:** The OpenAI SDK's `AsyncHttpxClientWrapper.__del__` method raises `RuntimeError("Event loop is closed")` when the CLI exits. The current workaround neuters the `__del__` method:

```python
AsyncHttpxClientWrapper.__del__ = lambda self: None  # type: ignore[assignment]
```

**Impact:** This is a fragile workaround that could break with SDK updates. The OpenAI SDK itself marks this as a TODO.

**Recommendation:** Monitor OpenAI SDK releases for proper async runtime support.

---

### Nous Portal Provider Preference Disabled

**File:** `run_agent.py` (line 4740)

**Issue:** TODO comment indicates provider preferences are disabled for Nous Portal:

```python
# TODO: Nous Portal will add transparent proxy support — re-enable
# for _is_nous when their backend is updated.
```

**Impact:** Users using Nous Portal cannot use provider preferences (only, ignore, order, sort).

**Recommendation:** Re-enable when Nous Portal backend is updated.

---

### Matrix Media Download Deprecated Path

**File:** `gateway/platforms/matrix.py` (line 977)

**Issue:** Uses deprecated `/_matrix/media/v3/download/` path instead of `/_matrix/client/v1/media/download/`.

**Impact:** May stop working when Matrix servers deprecate the old path.

---

## Security Considerations

### Environment Variable Secret Handling

**Issue:** 1,048 instances of `os.getenv()` and `os.environ.get()` throughout the codebase, many handling sensitive data.

**Files with sensitive env var access:**
- `tools/terminal_tool.py` - lines 333, 1031-1077: `SUDO_PASSWORD`, `MODAL_TOKEN_ID`, session tokens
- `tools/send_message_tool.py` - lines 592-629: `EMAIL_PASSWORD`, `EMAIL_SMTP_HOST`, `TWILIO_ACCOUNT_SID`
- `tools/tirith_security.py` - line 209: `GITHUB_TOKEN`
- `tools/transcription_tools.py` - lines 121, 142, 205: API keys for STT providers

**Impact:** Secrets may be logged, exposed in error messages, or cached in memory.

**Recommendation:** 
- Audit all environment variable access for secret exposure
- Ensure secrets are redacted from logs and error messages
- Consider using a secrets manager instead of environment variables

---

### Sudo Password Caching

**File:** `tools/terminal_tool.py` (lines 95-96, 333)

**Issue:** Sudo password is cached in a global variable `_cached_sudo_password` for the session:

```python
_cached_sudo_password: str = ""
```

**Impact:** Password remains in memory for the duration of the CLI session.

**Recommendation:** Clear password after each use or use more secure authentication methods.

---

### Skills Secret Capture

**File:** `tools/skills_tool.py` (lines 106-117, 280-298)

**Issue:** Skills can define `collect_secrets` which prompts users for sensitive information:

```python
collect_secrets: List[Dict[str, Any]] = []
```

**Impact:** Users may unknowingly provide secrets that get stored or transmitted.

**Recommendation:** Clear warning when secrets are being collected; ensure proper encryption at rest.

---

## Performance Concerns

### Large File Processing

**Files:**
- `tools/web_tools.py` - 1,843 lines
- `tools/mcp_tool.py` - 1,895 lines
- `tools/browser_tool.py` - 1,955 lines

**Issue:** These files handle complex operations (web extraction, MCP protocol, browser automation) and may have performance bottlenecks.

**Impact:** Slow response times for tool operations.

---

### Context Compression Overhead

**File:** `trajectory_compressor.py` (1,499 lines)

**Issue:** Trajectory compression runs after every agent turn when approaching context limits, requiring LLM calls for summarization.

**Impact:** Adds latency and token costs during long conversations.

---

### Skills Hub Search Rate Limiting

**File:** `tools/skills_hub.py` (line 413)

**Issue:** Code mentions rate limiting concerns in search:

```python
avoid per-directory rate limiting that causes silent subdirectory
```

**Impact:** Frequent searches may hit rate limits and fail silently.

---

## Scalability Limitations

### GitHub API Rate Limits

**File:** `hermes_cli/doctor.py` (line 696)

**Issue:** Without `GITHUB_TOKEN`, rate limit is 60 requests/hour:

```python
check_warn("No GITHUB_TOKEN", f"(60 req/hr rate limit — set in {_DHH}/.env for better rates)")
```

**Impact:** Skills Hub and ClawHub operations may fail with frequent use.

---

### SQLite Session Storage

**File:** `gateway/session.py` (lines 482, 518, 737)

**Issue:** Session storage falls back to JSONL if SQLite is unavailable:

```python
print(f"[gateway] Warning: SQLite session store unavailable, falling back to JSONL: {e}")
```

**Impact:** Less performant for high-volume message processing; no FTS5 search.

---

### MCP Server Sampling Rate Limit

**File:** `tools/mcp_tool.py` (lines 354-355, 563-570)

**Issue:** MCP servers have a sliding-window rate limiter (default 60 requests/minute):

```python
def _check_rate_limit(self) -> bool:
    """Sliding-window rate limiter.  Returns True if request is allowed."""
```

**Impact:** High-frequency MCP tool usage may be throttled.

---

## Configuration Pitfalls

### Complex Configuration Loading

**Files:**
- `hermes_cli/config.py` - 2,081 lines
- `hermes_cli/auth.py` - 2,356 lines
- `gateway/config.py` - multiple config loaders

**Issue:** Multiple configuration systems (YAML, environment variables, CLI flags) with different precedence rules.

**Impact:** Users may be confused about which config takes precedence. Debugging configuration issues is difficult.

---

### Environment Variable Precedence

**Issue:** Some settings can be configured via both config.yaml AND environment variables, but the precedence is not always clear.

**Example:** `HERMES_TOOL_PROGRESS` (deprecated) vs `display.tool_progress` in config.yaml.

---

### Platform-Specific Path Handling

**Files:**
- `tests/tools/test_modal_sandbox_fixes.py` - Windows path handling
- `tests/tools/test_windows_compat.py` - Windows compatibility tests

**Issue:** Path separators differ between Windows (`\`) and Unix (`/`), causing issues in cross-platform code.

**Impact:** Features may break on Windows (e.g., Modal sandbox paths, credential file paths).

---

### Terminal Environment Complexity

**File:** `tools/terminal_tool.py` (lines 455-524)

**Issue:** Multiple terminal backends (local, docker, singularity, modal, daytona, SSH) with complex configuration:

```python
env_type = os.getenv("TERMINAL_ENV", "local")
docker_cwd_source = os.getenv("TERMINAL_CWD") or os.getcwd()
mount_docker_cwd = os.getenv("TERMINAL_DOCKER_MOUNT_CWD_TO_WORKSPACE", "false").lower() in ("true", "1", "yes")
```

**Impact:** Users must understand multiple environment variables to configure different backends.

---

## Missing Features / Incomplete Implementations

### Skills Platform Filtering

**File:** `tools/skills_tool.py` (lines 100-102)

**Issue:** Platform mapping is incomplete:

```python
"macos": "darwin",
"linux": "linux",
"windows": "win32",
```

**Impact:** Skills may not filter correctly on all platforms.

---

### Voice Mode Platform Support

**File:** `tools/voice_mode.py`

**Issue:** Platform-specific audio playback implementations with fallback chains.

**Impact:** Voice features may not work on all platforms; multiple fallback paths indicate incomplete platform support.

---

## Test Coverage Gaps

### Integration Test Coverage

**Issue:** Many tool implementations lack comprehensive integration tests.

**Files with limited tests:**
- `tools/tirith_security.py` - security tool with limited test coverage
- `tools/mcp_tool.py` - complex MCP protocol with 1,895 lines but integration gaps
- `gateway/platforms/` - platform adapters may lack full integration testing

**Risk:** Platform-specific bugs may go unnoticed until production.

---

### Error Handling Test Coverage

**Issue:** Bare exception handlers make it difficult to test error recovery paths.

**Impact:** Error conditions are not properly tested, leading to unhandled edge cases in production.

---

## Platform-Specific Issues

### Windows-Specific Concerns

- Path handling in `terminal_tool.py` (line 477): `TERMINAL_CWD` may contain Windows-style paths
- Modal sandbox path replacement (tests show Windows path handling issues)
- Clipboard operations differ between Windows versions

### macOS-Specific Concerns

- `SSH_CLIENT`/`SSH_TTY`/`SSH_CONNECTION` detection in `tools/voice_mode.py` (line 59)
- Launchd plist generation for gateway service (tests reference macOS-specific code)

### Linux-Specific Concerns

- Multiple clipboard backends (WSL, Wayland, X11) - see `hermes_cli/clipboard.py`
- Systemd service management

---

## Deprecation Warnings

### Active Deprecations

| Variable | Location | Recommended Alternative |
|----------|----------|------------------------|
| `HERMES_TOOL_PROGRESS` | `hermes_cli/config.py:956` | `display.tool_progress` in config.yaml |
| `HERMES_TOOL_PROGRESS_MODE` | `hermes_cli/config.py:963` | `display.tool_progress` in config.yaml |
| Matrix v3 media path | `gateway/platforms/matrix.py:977` | Matrix v1 media path |

---

## Risk Summary

| Concern | Severity | Priority |
|---------|----------|----------|
| Monolithic file complexity | High | Refactor |
| Secret exposure via env vars | High | Audit & Fix |
| Deprecated config vars still accepted | Medium | Remove or warn |
| Broad exception handling | Medium | Specify exceptions |
| GitHub API rate limits | Medium | Document workaround |
| Platform-specific path issues | Medium | Fix Windows support |
| Event loop workaround | Low | Monitor SDK updates |

---

*Concerns audit: 2026-03-29*
