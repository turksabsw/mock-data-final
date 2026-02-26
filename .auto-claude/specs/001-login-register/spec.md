# Specification: VISE OS — VFS Global Register & Login Bot

## Overview

VISE OS is a greenfield Python automation bot that performs automated account registration and login on the VFS Global visa portal for Turkey-origin applicants. The bot uses Camoufox (a Firefox fork with C++-level anti-detect capabilities) via the Juggler protocol (NOT CDP) to evade anti-bot detection systems including Cloudflare Turnstile. The system supports multiple VFS countries with per-country configuration, cross-platform execution (macOS, Windows, Linux), fingerprint OS rotation, human-like interaction patterns, and automated OTP/email verification via Mailcow IMAP. The MVP targets low-protection countries (`aut`, `hrv`, `che`) before scaling to high-traffic routes like `ita` and `nld`.

## Workflow Type

**Type**: feature

**Rationale**: This is a brand-new greenfield project requiring full implementation of a complete automation system from scratch — project skeleton, configuration management, browser automation, form filling, OTP reading, CAPTCHA handling, CLI interface, and test suite. No existing code to modify.

## Task Scope

### Services Involved
- **vise-os-bot** (primary) — Python CLI application performing browser automation via Camoufox
- **Mailcow IMAP** (integration) — External mail server at `mail.atonota.com` for OTP/verification email retrieval
- **CapSolver API** (integration, optional) — External CAPTCHA solving service for Turnstile/reCAPTCHA/hCaptcha

### This Task Will:
- [ ] Create the complete project skeleton with all directories and configuration files
- [ ] Implement cross-platform detection (`platform_config.py`) with fingerprint OS rotation
- [ ] Implement country configuration management (`country_manager.py`) with per-country selectors
- [ ] Implement shared utilities (`utils.py`) — logging, screenshots, human-like typing, element finding with fallback selectors
- [ ] Implement Camoufox browser management (`browser.py`) with anti-detect configuration
- [ ] Implement Mailcow IMAP OTP reader (`otp_reader.py`) for email verification
- [ ] Implement CAPTCHA solver skeleton (`captcha_solver.py`) with CapSolver API integration
- [ ] Implement the registration flow (`register.py`) — country-agnostic, config-driven
- [ ] Implement the login flow (`login.py`) — with OTP integration
- [ ] Implement CLI entry point (`main.py`) with argparse for register/login/test actions
- [ ] Implement unit and E2E test suites
- [ ] Create `.env` template, `.gitignore`, and `config/countries.json`

### Out of Scope:
- Non-VFS providers (Auslandsportal for `deu`, TLScontact for `fra`/`gbr`) — require separate adapters
- Live selector discovery for each country (requires manual browser reconnaissance)
- n8n workflow automation setup (Mailcow integration is IMAP-only for now)
- Proxy procurement and rotation strategy (bot supports proxy config, but sourcing is external)
- VFS appointment booking (this scope covers registration and login only)
- Web dashboard or GUI (CLI-only for MVP)

## Service Context

### VISE OS Bot (Primary)

**Tech Stack:**
- Language: Python 3.11+
- Browser Engine: Camoufox (Firefox fork, C++ anti-detect)
- Protocol: Juggler (NOT CDP)
- Automation: Playwright API accessed via Camoufox wrapper
- Config: python-dotenv for environment variables
- Mail: imap-tools for Mailcow IMAP OTP retrieval (NOT raw imaplib — imap-tools provides higher-level API with query builder, parsed messages, and IDLE support)
- Key directories: `src/`, `config/`, `tests/`, `debug/`

**Entry Point:** `main.py`

**How to Run:**
```bash
# Install dependencies (ALL required packages)
pip install -U camoufox[geoip] python-dotenv imap-tools capsolver

# Download Camoufox browser binary (REQUIRED — nothing works without this)
camoufox fetch

# Linux servers: install Xvfb
# sudo apt install -y xvfb libgtk-3-0 libx11-xcb1 libasound2

# Run the bot
python main.py register --country aut
python main.py login --country aut
python main.py test --country aut
```

**Port:** N/A (CLI application, no server)

### Mailcow IMAP (Integration)

**Tech Stack:**
- Protocol: IMAP over SSL
- Host: `mail.atonota.com`
- Port: 993
- Purpose: Retrieve OTP codes and verification links from VFS registration emails

## Files to Create

Since this is a greenfield project, all files must be created from scratch.

| File | Purpose | Priority |
|------|---------|----------|
| `.env` | Environment variables (credentials, proxy, paths) | Step 1 |
| `.env.example` | Template showing required env vars (safe to commit) | Step 1 |
| `.gitignore` | Exclude `.env`, `debug/`, `__pycache__/`, profile dirs | Step 1 |
| `requirements.txt` | Python dependencies (see exact content below) | Step 1 |
| `config/countries.json` | All VFS country configurations | Step 1 |
| `config/proxy_list.json` | Proxy server list (placeholder) | Step 1 |
| `config/selectors/` | Per-country selector JSON files (empty placeholders) | Step 1 |
| `src/__init__.py` | Package init | Step 2 |
| `src/platform_config.py` | Cross-platform detection + fingerprint OS rotation | Step 2 |
| `src/country_manager.py` | Country config loader + URL builder + selector loader | Step 3 |
| `src/utils.py` | Logging, screenshots, human-like behavior, element finder | Step 4 |
| `src/browser.py` | Camoufox launch, page navigation, session management | Step 5 |
| `src/otp_reader.py` | Mailcow IMAP connection, OTP extraction, link extraction | Step 6 |
| `src/captcha_solver.py` | Turnstile/reCAPTCHA/hCaptcha skeletons + CapSolver API | Step 7 |
| `src/register.py` | Registration flow — country-agnostic, config-driven | Step 8 |
| `src/login.py` | Login flow — with OTP integration | Step 9 |
| `main.py` | CLI entry point with argparse | Step 10 |
| `tests/__init__.py` | Test package init | Step 11 |
| `tests/test_platform_detection.py` | Unit tests for platform detection + fingerprint OS rotation | Step 11 |
| `tests/test_country_manager.py` | Unit tests for UlkeYonetici (country loading, URL building, selectors) | Step 11 |
| `tests/test_camoufox_health.py` | Camoufox browser health check | Step 11 |
| `tests/test_register_e2e.py` | E2E registration test | Step 11 |
| `tests/test_login_e2e.py` | E2E login test | Step 11 |

### requirements.txt Content

```
camoufox[geoip]>=0.4.11
python-dotenv>=1.0.0
capsolver>=1.0.7
imap-tools>=1.7.0
```

**Note:** `playwright` and `browserforge` are auto-installed as Camoufox dependencies — do NOT list them separately.

## Patterns to Follow

Since this is a greenfield project, patterns are defined by the master prompt specification. All code MUST follow these patterns exactly.

### Pattern 1: Cross-Platform Detection

```python
import platform, os, random

def platform_ayarlari_al():
    """Detect runtime OS, set platform-specific paths and headless mode."""
    sistem = platform.system()  # "Darwin", "Windows", "Linux"

    ayarlar = {
        "sistem": sistem,
        "headless": False,
        "profile_dir": "",
        "debug_dir": "",
        "xvfb_gerekli": False,
    }

    if sistem == "Darwin":
        ayarlar["headless"] = False
        ayarlar["profile_dir"] = os.path.expanduser(
            "~/Library/Application Support/VISE-OS/vfs-profile"
        )
        ayarlar["debug_dir"] = os.path.expanduser("~/vise-os-bot/debug")
    elif sistem == "Windows":
        ayarlar["headless"] = False
        ayarlar["profile_dir"] = os.path.join(
            os.environ.get("APPDATA", "C:\\Users\\Default\\AppData\\Roaming"),
            "VISE-OS", "vfs-profile"
        )
        ayarlar["debug_dir"] = os.path.join(
            os.environ.get("USERPROFILE", "C:\\Users\\Default"),
            "vise-os-bot", "debug"
        )
    elif sistem == "Linux":
        ayarlar["headless"] = "virtual"  # Xvfb required
        ayarlar["xvfb_gerekli"] = True
        ayarlar["profile_dir"] = os.path.expanduser("~/.config/vise-os/vfs-profile")
        ayarlar["debug_dir"] = os.path.expanduser("~/vise-os-bot/debug")

    # .env overrides — check BEFORE using defaults
    env_profile = os.getenv("PROFILE_DIR")
    env_debug = os.getenv("DEBUG_DIR")
    if env_profile:
        ayarlar["profile_dir"] = env_profile
    if env_debug:
        ayarlar["debug_dir"] = env_debug

    os.makedirs(ayarlar["profile_dir"], exist_ok=True)
    os.makedirs(ayarlar["debug_dir"], exist_ok=True)

    return ayarlar
```

**Key Points:**
- Runtime OS vs fingerprint OS are TWO SEPARATE concepts — never conflate them
- Linux always uses `headless="virtual"` (Xvfb), never `headless=True`
- macOS/Windows use `headless=False`
- `.env` overrides for `PROFILE_DIR` and `DEBUG_DIR` are checked first — if set, they override platform defaults
- `load_dotenv()` must be called before `platform_ayarlari_al()` for `.env` overrides to work

### Pattern 2: Fingerprint OS Rotation

```python
def parmak_izi_os_sec():
    """Select fingerprint OS with weighted random based on Turkish user distribution."""
    return random.choices(
        population=["windows", "macos", "linux"],
        weights=[75, 17, 8],
        k=1
    )[0]
```

**Key Points:**
- Weights mirror Turkey desktop OS distribution: Windows 75%, macOS 17%, Linux 8%
- Called fresh for EVERY browser session — never use a static/fixed `os` parameter
- This is the OS shown to VFS, not the runtime OS

### Pattern 3: Camoufox Configuration

**IMPORTANT:** For persistent context (cookie/session persistence), use `NewBrowser` with `sync_playwright()` — this is the documented approach per Camoufox docs. The `Camoufox()` context manager is for non-persistent sessions.

```python
from camoufox.sync_api import Camoufox, NewBrowser  # Sync API
from playwright.sync_api import sync_playwright
import os

def camoufox_config_olustur(ulke_kodu: str = "aut", proxy: dict = None):
    """Platform-agnostik, ülke-agnostik Camoufox konfigürasyonu üret."""
    p = platform_ayarlari_al()

    config = {
        "headless": p["headless"],        # From platform detection
        "humanize": True,                  # MANDATORY — human-like cursor
        "os": parmak_izi_os_sec(),        # Random fingerprint per session
        "geoip": True,                     # Auto timezone/locale from proxy IP
        "disable_coop": True,              # MANDATORY — Cloudflare Turnstile iframe access
        "persistent_context": True,        # Cookie persistence (cf_clearance reuse)
        "user_data_dir": os.path.join(     # Per-country isolated profile
            p["profile_dir"], ulke_kodu
        ),
    }

    if proxy:
        config["proxy"] = proxy

    return config

# --- Usage: Persistent context (PREFERRED — preserves cookies/cf_clearance) ---
def tarayici_baslat(ulke_kodu: str, proxy: dict = None):
    """Launch Camoufox with persistent context for cookie reuse."""
    config = camoufox_config_olustur(ulke_kodu, proxy)
    pw = sync_playwright().start()
    context = NewBrowser(pw, **config)
    page = context.new_page()
    return pw, context, page

# --- Usage: Non-persistent (for testing/quick sessions) ---
# with Camoufox(headless=False, humanize=True, os=parmak_izi_os_sec(),
#               geoip=True, disable_coop=True) as browser:
#     page = browser.new_page()
```

**Key Points:**
- **Persistent context MUST use `NewBrowser`** — `Camoufox()` context manager is for non-persistent use
- `disable_coop=True` is MANDATORY for Cloudflare Turnstile iframe interaction
- `persistent_context=True` REQUIRES `user_data_dir` — will crash without it
- `humanize=True` adds ~1.5s human-like cursor movement — MANDATORY (can also pass float like `humanize=2.0` for longer duration)
- Never import Playwright directly for browser launch — always go through Camoufox wrapper (`NewBrowser` or `Camoufox`)
- Juggler protocol is used automatically by Camoufox (not CDP)
- Remember to call `context.close()` and `pw.stop()` in cleanup/finally blocks

### Pattern 4: Tiered Selector Fallback

```python
def element_bul(page, ulke_kodu, sayfa, alan_adi, timeout=15000):
    """Find element using tiered fallback selectors from country config."""
    selectors = uy.selectors_yukle(ulke_kodu)
    sel = selectors.get(sayfa, {}).get(alan_adi, {})

    for kademe in ["primary", "fallback_1", "fallback_2"]:
        try:
            element = page.wait_for_selector(sel[kademe], timeout=timeout // 3)
            if element:
                log(f"[SELECTOR] {alan_adi} -> {kademe} found")
                return element
        except:
            log(f"[SELECTOR] {alan_adi} -> {kademe} failed...")

    screenshot_al(page, f"selector_not_found_{alan_adi}")
    raise Exception(f"Element not found: {ulke_kodu}/{sayfa}/{alan_adi}")
```

**Key Points:**
- NEVER hardcode selectors — always read from `config/selectors/vfs_{country}.json`
- Three-tier fallback: `primary` -> `fallback_1` -> `fallback_2`
- Each tier gets `timeout/3` to try
- Screenshot on failure for debugging
- General template `GENEL_VFS_SELECTOR_SABLONU` used when no country-specific file exists

### Pattern 5: Human-Like Behavior

```python
import random, time

def insan_gibi_bekle(min_sn=1.0, max_sn=3.0):
    time.sleep(random.uniform(min_sn, max_sn))

def insan_gibi_yaz(page, selector, metin):
    element = page.locator(selector)
    element.click()
    insan_gibi_bekle(0.3, 0.8)
    for karakter in metin:
        element.type(karakter, delay=random.randint(50, 150))
    insan_gibi_bekle(0.5, 1.5)
```

**Key Points:**
- NEVER use `time.sleep(N)` with a fixed value — always `random.uniform(min, max)`
- Always `.click()` before typing into a field
- Character-by-character typing with random 50-150ms delay between keystrokes
- Add random wait before and after typing

### Pattern 6: Debug-First Error Handling

```python
def akis_calistir(adim_adi, fonksiyon, page, *args, **kwargs):
    try:
        log(f"[{adim_adi}] Starting...")
        sonuc = fonksiyon(page, *args, **kwargs)
        log(f"[{adim_adi}] OK")
        return sonuc
    except TimeoutError:
        log(f"[{adim_adi}] TIMEOUT")
        screenshot_al(page, f"{adim_adi}_timeout")
        raise
    except Exception as e:
        log(f"[{adim_adi}] ERROR: {type(e).__name__}: {e}")
        screenshot_al(page, f"{adim_adi}_error")
        raise
```

**Key Points:**
- EVERY critical step must have log + screenshot on failure
- NEVER swallow errors with empty `except: pass`
- Always re-raise after logging — failures must propagate
- "Where did it break?" must always be answerable from debug output

### Pattern 7: Logging Standard

```python
import datetime, os

def log(mesaj):
    zaman = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    satir = f"[{zaman}] {mesaj}"
    print(satir)
    with open(os.path.join(LOG_DIR, f"vise_{datetime.date.today()}.log"), "a", encoding="utf-8") as f:
        f.write(satir + "\n")
```

**Key Points:**
- Millisecond precision timestamps
- Dual output: console + daily log file
- Log directory from `platform_ayarlari_al()["debug_dir"]`
- UTF-8 encoding for Turkish characters

## Requirements

### Functional Requirements

1. **Cross-Platform Runtime Detection**
   - Description: Auto-detect macOS/Windows/Linux and configure paths, headless mode, and Xvfb requirement accordingly
   - Acceptance: `platform_ayarlari_al()` returns correct config on all three OS types; Linux returns `headless="virtual"`, others return `headless=False`

2. **Fingerprint OS Rotation**
   - Description: Randomly select a fingerprint OS (Windows 75%, macOS 17%, Linux 8%) for each browser session to show to VFS
   - Acceptance: `parmak_izi_os_sec()` produces weighted random distribution matching Turkish user demographics

3. **Country Configuration Management**
   - Description: Load per-country config from `config/countries.json`, generate VFS URLs, validate country codes, load per-country selectors
   - Acceptance: `UlkeYonetici` correctly loads 8 active VFS countries, rejects `deu`/`fra`/`gbr`, builds correct URLs

4. **Camoufox Browser Management**
   - Description: Launch Camoufox with anti-detect config (Juggler, humanize, disable_coop, geoip, persistent_context, per-country profile)
   - Acceptance: Browser launches without detection on bot-check sites; `cf_clearance` cookie persists across sessions

5. **Tiered Selector Element Finding**
   - Description: Find page elements using 3-tier fallback selectors (primary -> fallback_1 -> fallback_2) loaded from config
   - Acceptance: Elements found with first available selector; screenshot captured on total failure

6. **Human-Like Form Interaction**
   - Description: Fill forms with click-before-type, character-by-character random-delay typing, random waits between actions
   - Acceptance: Form filling takes realistic human-like time (not instant); no detectable automation patterns

7. **Registration Flow**
   - Description: Navigate to VFS register page, fill first name, last name, email, password, confirm password, accept terms, submit — all config-driven per country
   - Acceptance: Successfully registers a new account on MVP country (`aut`, `hrv`, or `che`); handles CAPTCHA if present; handles email verification if required

8. **Login Flow**
   - Description: Navigate to VFS login page, fill email + password, handle OTP if required, submit — all config-driven per country
   - Acceptance: Successfully logs into an existing VFS account; OTP retrieved from Mailcow within 30 seconds

9. **OTP Email Reader**
   - Description: Connect to Mailcow IMAP via `imap-tools` library (NOT raw imaplib), search for VFS verification emails, extract OTP code or verification link
   - Acceptance: OTP extracted within 30 seconds of email arrival; handles both numeric OTP codes and verification links
   - Implementation note: Use `imap-tools` `MailBox` with `IDLE mode` (`mailbox.idle.wait(timeout=60)`) for real-time push notifications instead of naive polling — reduces latency from 5-30s to near-instant

10. **CAPTCHA Solver (Skeleton)**
    - Description: Detect CAPTCHA type (Turnstile/reCAPTCHA/hCaptcha), attempt Turnstile bypass via `frame_locator()`, fall back to CapSolver API
    - Acceptance: Turnstile checkbox click works with `disable_coop=True`; CapSolver integration skeleton functional
    - Implementation note: Use `capsolver` SDK as primary, but also implement raw `requests`-based API fallback (`POST https://api.capsolver.com/createTask` + `getTaskResult`) since SDK is from July 2023 and may lack latest features. For Turnstile, use `AntiTurnstileTaskProxyLess` task type. Extract `websiteKey` from Turnstile iframe's `data-sitekey` attribute.

11. **CLI Entry Point**
    - Description: `main.py` with argparse supporting `register`, `login`, `test` actions and `--country` flag
    - Acceptance: `python main.py register -c aut` executes registration flow; `python main.py test -c aut` runs register then login

12. **Debug Infrastructure**
    - Description: Every action logs with timestamps, every failure captures screenshots, daily log files, cross-platform debug directories
    - Acceptance: After any run, `debug/logs/` has timestamped log file, `debug/screenshots/` has relevant PNGs

### Non-Functional Requirements

1. **Anti-Detection**: Bot must not trigger Cloudflare or VFS anti-bot systems. Juggler protocol via Camoufox, no CDP, no JS webdriver patches.
2. **Cross-Platform**: Must work identically on macOS, Windows, and Linux (with Xvfb on Linux servers).
3. **OTP Timing**: Full OTP pipeline (email arrival -> extraction -> form fill) must complete under 30 seconds (OTP validity: 60-90s).
4. **Config-Driven**: No hardcoded selectors, URLs, country codes, or platform paths. Everything from config files or `.env`.
5. **Resilient**: Every error logged + screenshot. No silent failures. Graceful degradation where possible.

### Edge Cases

1. **Selector Not Found** — All three tiers fail: capture screenshot, log `ai_hint` from selector config, raise descriptive exception
2. **OTP Timeout** — Email doesn't arrive within 60 seconds: retry IMAP check 3 times with 10s intervals, then fail with screenshot
3. **Cloudflare Challenge Loop** — Repeated Turnstile challenges: check if `cf_clearance` cookie exists, retry with new fingerprint OS, log challenge count
4. **Country Not Active** — User passes inactive or non-VFS country code: raise clear `ValueError` with provider info
5. **Network Timeout** — Page load timeout: capture HAR + screenshot, retry once with fresh browser session
6. **Email Already Registered** — VFS returns "email exists" error: detect error message on page, log, and exit without retrying
7. **Password Policy Rejection** — VFS rejects password: detect validation error, log requirements, exit with clear message
8. **Proxy Failure** — Proxy connection fails: log error, attempt without proxy if configured, or fail clearly
9. **Profile Directory Locked** — `user_data_dir` locked by another process: detect lock, wait or use alternative profile
10. **Linux Without Xvfb** — Xvfb not installed on Linux server: detect absence before browser launch, provide installation instruction in error message

## Implementation Notes

### DO
- Follow the exact file structure specified: `src/`, `config/`, `tests/`, `debug/`
- Use Turkish naming convention for all functions and variables as specified in the master prompt (e.g., `platform_ayarlari_al`, `ulke_al`, `insan_gibi_yaz`)
- Load ALL sensitive values from `.env` via `python-dotenv` — `load_dotenv()` then `os.getenv()`
- Use `platform_ayarlari_al()` for ALL path construction — never hardcode OS-specific paths
- Use `UlkeYonetici.url_olustur()` for ALL VFS URL generation
- Use `parmak_izi_os_sec()` for EVERY browser session — never fix the OS fingerprint
- Implement `element_bul()` with 3-tier fallback for ALL form interactions
- Add `insan_gibi_bekle()` between EVERY form interaction step
- Use character-by-character typing via `insan_gibi_yaz()` for ALL text inputs
- Capture screenshot + log at EVERY error boundary
- Use `NewBrowser` from `camoufox.sync_api` with `sync_playwright()` for persistent context sessions
- Use `Camoufox` context manager (sync API: `with Camoufox(**config) as browser:`) for non-persistent test sessions only
- Set `disable_coop=True` for Cloudflare Turnstile iframe access
- Set `persistent_context=True` + `user_data_dir` for cookie persistence (requires `NewBrowser` pattern)
- Use `page.frame_locator()` to interact with Turnstile iframes

### DON'T
- **DON'T** use `headless=True` — use `headless=False` (macOS/Windows) or `headless="virtual"` (Linux)
- **DON'T** use CDP protocol — Camoufox uses Juggler automatically
- **DON'T** use `time.sleep(N)` with fixed values — always `random.uniform(min, max)`
- **DON'T** use datacenter proxies — residential or mobile only
- **DON'T** write empty `except: pass` — log and screenshot every error
- **DON'T** hardcode selectors — read from `config/selectors/` with fallback to `GENEL_VFS_SELECTOR_SABLONU`
- **DON'T** fill form fields without `.click()` first and `insan_gibi_bekle()` between
- **DON'T** embed credentials in code — use `.env` exclusively
- **DON'T** add JS webdriver patches — Camoufox handles anti-detect at C++ level
- **DON'T** use a fixed `os` parameter — use `parmak_izi_os_sec()` for each session
- **DON'T** hardcode country codes or URLs — use `UlkeYonetici`
- **DON'T** hardcode platform paths — use `platform_ayarlari_al()`
- **DON'T** import Playwright directly for browser launch — use Camoufox wrapper (`NewBrowser` or `Camoufox`). Note: `from playwright.sync_api import sync_playwright` IS required for the `NewBrowser` persistent context pattern — this is the one allowed Playwright import.

## Implementation Order

The following order MUST be followed. Each step must be completed and verified before proceeding to the next.

| Step | File(s) | Description | Dependencies |
|------|---------|-------------|--------------|
| 1 | Project skeleton, `.env`, `.gitignore`, `requirements.txt`, `config/` | Create directory structure and all config files | None |
| 2 | `src/platform_config.py` | Cross-platform detection + fingerprint OS rotation + Camoufox config builder | Step 1 |
| 3 | `src/country_manager.py` | `UlkeYonetici` class + `GENEL_VFS_SELECTOR_SABLONU` | Step 1 (config/countries.json) |
| 4 | `src/utils.py` | Logging, screenshots, human-like behavior, element finder | Steps 2, 3 |
| 5 | `src/browser.py` | Camoufox launch + page navigation + session management | Steps 2, 3, 4 |
| 6 | `src/otp_reader.py` | Mailcow IMAP OTP reader | Step 4 (utils) |
| 7 | `src/captcha_solver.py` | CAPTCHA detection + Turnstile bypass + CapSolver skeleton | Steps 4, 5 |
| 8 | `src/register.py` | Registration flow — country-agnostic | Steps 3, 4, 5, 7 |
| 9 | `src/login.py` | Login flow — with OTP | Steps 3, 4, 5, 6, 7 |
| 10 | `main.py` | CLI entry point with argparse | Steps 2, 3, 8, 9 |
| 11 | `tests/` | Unit tests + E2E tests | All previous steps |

## Development Environment

### Prerequisites

```bash
# Python 3.11+
python3 --version

# Install all dependencies
pip install -U camoufox[geoip] python-dotenv imap-tools capsolver

# Download Camoufox browser binary (REQUIRED — nothing works without this)
camoufox fetch

# Linux only: install Xvfb and system libraries for virtual display
sudo apt install -y xvfb libgtk-3-0 libx11-xcb1 libasound2
```

### Project Setup

```bash
# Create project directory
mkdir -p vise-os-bot/{src,config/selectors,tests,debug/{screenshots,har,logs}}

# Create .env from template
cp .env.example .env
# Edit .env with real credentials
```

### Run Commands

```bash
# Register on Austria (MVP test)
python main.py register --country aut

# Login on Austria
python main.py login --country aut

# Full test (register + login)
python main.py test --country aut
```

### Required Environment Variables
- `VFS_ORIGIN`: Origin country code (default: `tur`)
- `VFS_LANGUAGE`: Language code (default: `en`)
- `VFS_DEFAULT_COUNTRY`: Default target country (default: `aut`)
- `VFS_EMAIL`: Registration/login email (e.g., `test001@atonota.com`)
- `VFS_PASSWORD`: Account password
- `VFS_FIRST_NAME`: First name for registration
- `VFS_LAST_NAME`: Last name for registration
- `MAILCOW_HOST`: IMAP server host (e.g., `mail.atonota.com`)
- `MAILCOW_USER`: IMAP username
- `MAILCOW_PASS`: IMAP password
- `MAILCOW_PORT`: IMAP port (default: `993`)
- `PROXY_SERVER`: Proxy URL (optional)
- `PROXY_USERNAME`: Proxy auth username (optional)
- `PROXY_PASSWORD`: Proxy auth password (optional)
- `CAPSOLVER_API_KEY`: CapSolver API key (optional)
- `PROFILE_DIR`: Override default profile directory (optional — platform auto-detects if empty)
- `DEBUG_DIR`: Override default debug directory (optional — platform auto-detects if empty)

## Country Configuration

### Active VFS Countries

| Code | Country | Priority | Protection Level | MVP Candidate |
|------|---------|----------|------------------|---------------|
| `aut` | Austria | Medium | Low | Yes |
| `hrv` | Croatia | Low | Low | Yes |
| `che` | Switzerland | Medium | Low | Yes |
| `bel` | Belgium | Medium | TBD | No |
| `cze` | Czech Republic | Medium | TBD | No |
| `irl` | Ireland | Low | TBD | No |
| `ita` | Italy | High | High (aggressive Cloudflare) | No (deferred) |
| `nld` | Netherlands | High | High (aggressive Cloudflare) | No (deferred) |

### Excluded Countries (Not VFS)

| Code | Country | Provider | Notes |
|------|---------|----------|-------|
| `deu` | Germany | Auslandsportal | `digital.diplo.de` — separate adapter needed |
| `fra` | France | TLScontact | Separate adapter needed |
| `gbr` | UK | TLScontact | Separate adapter needed |

### URL Pattern
```
https://visa.vfsglobal.com/tur/en/{country_code}/{page}
```
Where `{page}` is `login` or `register`.

## Risk Assessment

### High Risk
1. **Cloudflare Turnstile Detection** — Even with Camoufox + `disable_coop`, aggressive Cloudflare on `ita`/`nld` may block. Mitigation: Start with low-protection MVP countries; use `persistent_context` for `cf_clearance` reuse.
2. **VFS Account Bans** — Account bans are PERMANENT. Mitigation: Use fresh accounts for each test run; never reuse banned accounts.
3. **Selector Changes** — VFS may update their DOM at any time. Mitigation: 3-tier fallback selectors; per-country config files; `ai_hint` for manual investigation.

### Medium Risk
4. **OTP Timing** — 60-90 second validity window is tight. Mitigation: Pipeline must complete OTP flow in under 30 seconds; IMAP polling starts before form submission.
5. **Per-Country Variations** — Each country may have different form fields, CAPTCHA types, OTP requirements. Mitigation: All values in per-country config; live recon needed before each country goes live.
6. **Camoufox Maintenance** — v0.4.11 (Jan 2025) has noted maintenance gap; Firefox v146 may have fingerprint inconsistencies. Mitigation: Pin version; test regularly; have fallback plan.

### Low Risk
7. **Cross-Platform Path Issues** — Windows vs Unix path separators. Mitigation: `os.path.join()` everywhere; `platform_ayarlari_al()` centralizes all paths.
8. **Proxy Failures** — Residential proxies can be unstable. Mitigation: Retry logic; optional proxy-free fallback for testing.

## Success Criteria

The task is complete when:

1. [ ] Project skeleton exists with all specified directories (`src/`, `config/`, `tests/`, `debug/`)
2. [ ] `config/countries.json` has all 11 country entries (8 active VFS + 3 excluded)
3. [ ] `.env.example` has all required environment variables documented
4. [ ] `src/platform_config.py` correctly detects macOS/Windows/Linux and returns proper configs
5. [ ] `src/country_manager.py` loads countries, builds URLs, validates codes, loads selectors
6. [ ] `src/utils.py` provides log, screenshot, human-like typing, and tiered element finding
7. [ ] `src/browser.py` launches Camoufox with full anti-detect config (humanize, disable_coop, geoip, persistent_context)
8. [ ] `src/otp_reader.py` connects to Mailcow IMAP and extracts OTP codes/verification links
9. [ ] `src/captcha_solver.py` has Turnstile bypass skeleton and CapSolver API integration skeleton
10. [ ] `src/register.py` executes full registration flow using config-driven selectors
11. [ ] `src/login.py` executes full login flow with OTP support
12. [ ] `main.py` CLI works: `python main.py register -c aut` / `login` / `test`
13. [ ] All unit tests pass (`test_platform_detection.py`, `test_camoufox_health.py`)
14. [ ] No hardcoded selectors, URLs, country codes, platform paths, or credentials anywhere in code
15. [ ] Every error path captures screenshot + log entry
16. [ ] No `headless=True`, no CDP, no `time.sleep(fixed)`, no empty `except: pass`

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests
| Test | File | What to Verify |
|------|------|----------------|
| Platform Detection (macOS) | `tests/test_platform_detection.py` | Returns `headless=False`, correct macOS paths, `xvfb_gerekli=False` |
| Platform Detection (Linux) | `tests/test_platform_detection.py` | Returns `headless="virtual"`, correct Linux paths, `xvfb_gerekli=True` |
| Platform Detection (Windows) | `tests/test_platform_detection.py` | Returns `headless=False`, APPDATA-based paths, `xvfb_gerekli=False` |
| Fingerprint OS Distribution | `tests/test_platform_detection.py` | `parmak_izi_os_sec()` returns only "windows"/"macos"/"linux"; weighted distribution roughly correct over 1000 runs |
| Camoufox Config Builder | `tests/test_platform_detection.py` | `camoufox_config_olustur()` returns all mandatory keys; `humanize=True`, `disable_coop=True`, `geoip=True`, `persistent_context=True` |
| Country Loader | `tests/test_country_manager.py` | `UlkeYonetici` loads all 8 active VFS countries; rejects `deu`, `fra`, `gbr` |
| URL Builder | `tests/test_country_manager.py` | `url_olustur("aut", "register")` returns `https://visa.vfsglobal.com/tur/en/aut/register` |
| Selector Loader | `tests/test_country_manager.py` | Falls back to `GENEL_VFS_SELECTOR_SABLONU` when no country-specific file exists |

### Integration Tests
| Test | Services | What to Verify |
|------|----------|----------------|
| Camoufox Launch | browser.py + platform_config.py | Browser launches with correct config, opens a page, closes cleanly |
| IMAP Connection | otp_reader.py + Mailcow | Connects to IMAP, authenticates, searches inbox (requires real credentials) |
| Full Register Flow | register.py + browser.py + country_manager.py + utils.py | Navigates to VFS register page, fills form, submits (requires live VFS) |
| Full Login Flow | login.py + browser.py + otp_reader.py + utils.py | Navigates to VFS login page, fills credentials, handles OTP (requires live VFS) |

### End-to-End Tests
| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| Registration (aut) | 1. `python main.py register -c aut` 2. Bot opens VFS Austria register page 3. Fills form with .env credentials 4. Handles CAPTCHA if present 5. Submits 6. Handles email verification if required | New VFS account created; debug logs + screenshots captured at each step |
| Login (aut) | 1. `python main.py login -c aut` 2. Bot opens VFS Austria login page 3. Fills email + password 4. Handles OTP via Mailcow IMAP if required 5. Submits | Successful login to VFS account; session cookie persisted |
| Full Test (aut) | 1. `python main.py test -c aut` 2. Runs register then login sequentially | Both registration and login succeed end-to-end |
| Invalid Country | 1. `python main.py register -c deu` | Clear error: "Almanya VFS degil -> auslandsportal" |
| Missing .env | 1. Remove `.env` 2. `python main.py register -c aut` | Clear error about missing configuration |

### Code Quality Checks
| Check | How to Verify | Expected |
|-------|---------------|----------|
| No hardcoded selectors | `grep -r "data-testid\|input\[type=" src/ --include="*.py"` (excluding `country_manager.py` template) | Zero matches outside of the default selector template |
| No hardcoded `time.sleep` | `grep -r "time.sleep(" src/ --include="*.py"` | Zero matches (all should use `random.uniform`) |
| No `headless=True` | `grep -r "headless.*True" src/ --include="*.py"` | Zero matches |
| No empty except | `grep -r "except.*pass" src/ --include="*.py"` | Zero matches |
| No embedded credentials | `grep -r "atonota\|GucluSifre\|CAP-" src/ --include="*.py"` | Zero matches (all from `.env`) |
| All functions have logging | Manual review of `register.py`, `login.py`, `browser.py` | Every function starts with `log()` call and has try/except with `log()` + `screenshot_al()` |

### Debug Output Verification
| Check | Command | Expected |
|-------|---------|----------|
| Log file exists | `ls debug/logs/vise_*.log` | Daily log file with timestamped entries |
| Screenshots captured | `ls debug/screenshots/` | PNG files for each major step and any errors |
| Log format correct | Check log content | `[YYYY-MM-DD HH:MM:SS.mmm] [MODULE] message` format |

### QA Sign-off Requirements
- [ ] All unit tests pass
- [ ] All integration tests pass (where live services available)
- [ ] All E2E tests pass on at least one MVP country
- [ ] Code quality checks pass (no hardcoded values, no anti-patterns)
- [ ] Debug output verified (logs + screenshots generated correctly)
- [ ] No regressions in existing functionality (N/A — greenfield)
- [ ] Code follows established patterns (Turkish naming, 3-tier selectors, human-like behavior)
- [ ] No security vulnerabilities introduced (credentials in `.env` only, `.gitignore` excludes sensitive files)
- [ ] Cross-platform compatibility verified (at minimum, tested on the dev machine's OS)
- [ ] Bot not detected on bot-check sites (e.g., `bot.sannysoft.com`, `browserleaks.com`)
