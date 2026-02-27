# Gotchas & Pitfalls

Things to watch out for in this codebase.

## [2026-02-26 07:19]
MUST run 'camoufox fetch' after pip install to download browser binary — without this, Camoufox will not work at all

_Context: Camoufox installation - the browser binary is NOT included in the pip package_

## [2026-02-26 07:19]
CapSolver Turnstile solve requires keeping same IP, TLS fingerprint, headers, and User-Agent during solving phase — any mismatch invalidates the token

_Context: CAPTCHA solving integration with CapSolver AntiTurnstileTaskProxyLess_

## [2026-02-26 07:48]
python3 and python commands are blocked by the project's allowed-commands callback hook policy. Verification commands requiring Python must be run manually by the user or use alternative structural verification (grep/read).

_Context: Attempted to run verification: python3 -c "from src.platform_config import ..." — blocked by PreToolUse:Callback hook with message "Command 'python3' is not in the allowed commands for this project"_
