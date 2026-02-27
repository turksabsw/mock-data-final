"""
VISE OS — CAPTCHA Solver

Detects CAPTCHA type (Turnstile/reCAPTCHA/hCaptcha) on VFS pages, attempts
Turnstile bypass via frame_locator() click (requires disable_coop=True), and
falls back to CapSolver API (SDK primary + raw HTTP fallback).

CapSolver API key loaded from .env: CAPSOLVER_API_KEY.
Country-specific CAPTCHA type from config/countries.json captcha_tipi field.
"""

import json
import os
import re

import requests

from src.utils import log, screenshot_al, insan_gibi_bekle
from src.country_manager import UlkeYonetici


# --- CAPTCHA Type Constants ---
CAPTCHA_TURNSTILE = "turnstile"
CAPTCHA_RECAPTCHA = "recaptcha"
CAPTCHA_HCAPTCHA = "hcaptcha"
CAPTCHA_YOK = None  # No CAPTCHA detected

# --- CapSolver API Endpoints ---
CAPSOLVER_CREATE_TASK_URL = "https://api.capsolver.com/createTask"
CAPSOLVER_GET_RESULT_URL = "https://api.capsolver.com/getTaskResult"

# --- CapSolver Task Types ---
CAPSOLVER_TASK_TYPES = {
    CAPTCHA_TURNSTILE: "AntiTurnstileTaskProxyLess",
    CAPTCHA_RECAPTCHA: "ReCaptchaV2TaskProxyLess",
    CAPTCHA_HCAPTCHA: "HCaptchaTaskProxyLess",
}

# --- Turnstile iframe detection selectors ---
TURNSTILE_IFRAME_SELECTORS = [
    "iframe[src*='challenges.cloudflare.com']",
    "iframe[src*='turnstile']",
    "iframe[title*='Cloudflare']",
    "#cf-turnstile iframe",
    ".cf-turnstile iframe",
    "[data-turnstile-callback] iframe",
]

# --- reCAPTCHA detection selectors ---
RECAPTCHA_SELECTORS = [
    "iframe[src*='google.com/recaptcha']",
    "iframe[src*='recaptcha']",
    ".g-recaptcha",
    "[data-sitekey][class*='recaptcha']",
]

# --- hCaptcha detection selectors ---
HCAPTCHA_SELECTORS = [
    "iframe[src*='hcaptcha.com']",
    ".h-captcha",
    "[data-sitekey][class*='hcaptcha']",
]

# --- Site key extraction selectors ---
SITEKEY_SELECTORS = {
    CAPTCHA_TURNSTILE: [
        "#cf-turnstile[data-sitekey]",
        ".cf-turnstile[data-sitekey]",
        "[data-turnstile-callback][data-sitekey]",
        "div[data-sitekey]",
    ],
    CAPTCHA_RECAPTCHA: [
        ".g-recaptcha[data-sitekey]",
        "[data-sitekey][class*='recaptcha']",
        "div[data-sitekey]",
    ],
    CAPTCHA_HCAPTCHA: [
        ".h-captcha[data-sitekey]",
        "[data-sitekey][class*='hcaptcha']",
        "div[data-sitekey]",
    ],
}

# Singleton UlkeYonetici for country config lookup
_ulke_yonetici = None


def _ulke_yonetici_al():
    """Lazy-load singleton UlkeYonetici instance.

    Returns:
        UlkeYonetici: Shared country manager instance.
    """
    global _ulke_yonetici
    if _ulke_yonetici is None:
        _ulke_yonetici = UlkeYonetici()
    return _ulke_yonetici


class CaptcaCozucu:
    """CAPTCHA solver for VFS Global pages.

    Supports:
        - Cloudflare Turnstile bypass via frame_locator() checkbox click
        - CapSolver API integration (SDK primary + raw HTTP fallback)
        - CAPTCHA type detection (Turnstile, reCAPTCHA, hCaptcha)
        - Token injection into page response fields

    Usage:
        cozucu = CaptcaCozucu()
        captcha_tipi = cozucu.captcha_tipi_algila(page)
        if captcha_tipi == CAPTCHA_TURNSTILE:
            basarili = cozucu.turnstile_bypass(page)
            if not basarili:
                token = cozucu.capsolver_coz(page, site_key, CAPTCHA_TURNSTILE)
                cozucu.token_enjekte_et(page, token, CAPTCHA_TURNSTILE)
    """

    # Maximum wait time for CapSolver task result (seconds)
    CAPSOLVER_MAX_BEKLEME = 120

    # Poll interval for CapSolver task result (seconds)
    CAPSOLVER_POLL_ARALIK_MIN = 3.0
    CAPSOLVER_POLL_ARALIK_MAX = 6.0

    def __init__(self):
        """Initialize CAPTCHA solver with CapSolver API key from .env.

        Reads CAPSOLVER_API_KEY from environment. Logs a warning if not set
        (Turnstile bypass can still work without it, but API fallback won't).
        """
        self._api_key = os.getenv("CAPSOLVER_API_KEY", "")
        self._sdk_mevcut = False

        if not self._api_key:
            log("[CAPTCHA] UYARI: CAPSOLVER_API_KEY .env'de tanimli degil — "
                "yalnizca frame bypass denenecek")

        # Try to import CapSolver SDK
        try:
            import capsolver
            self._sdk_mevcut = True
            log("[CAPTCHA] CapSolver SDK mevcut")
        except ImportError:
            log("[CAPTCHA] CapSolver SDK bulunamadi — raw HTTP API kullanilacak")

    def captcha_tipi_algila(self, page, ulke_kodu=None):
        """Detect CAPTCHA type present on the current page.

        Detection order:
            1. Check country config for known captcha_tipi
            2. Scan page DOM for Turnstile iframes/elements
            3. Scan page DOM for reCAPTCHA iframes/elements
            4. Scan page DOM for hCaptcha iframes/elements

        Args:
            page: Playwright page object.
            ulke_kodu: Optional country code to check config-based type first.

        Returns:
            str or None: CAPTCHA type constant (CAPTCHA_TURNSTILE, CAPTCHA_RECAPTCHA,
                         CAPTCHA_HCAPTCHA) or None if no CAPTCHA detected.
        """
        log("[CAPTCHA] CAPTCHA tipi algilama baslatiliyor...")

        # 1. Check country config first (if known from reconnaissance)
        if ulke_kodu:
            try:
                uy = _ulke_yonetici_al()
                ulke = uy.ulke_al(ulke_kodu)
                config_tipi = ulke.get("captcha_tipi")
                if config_tipi:
                    log(f"[CAPTCHA] Config'den bilinen tip: {config_tipi} "
                        f"(ulke={ulke_kodu})")
                    return config_tipi
            except ValueError as e:
                log(f"[CAPTCHA] Ulke config okunamadi: {e}")

        # 2. Scan for Turnstile
        for selector in TURNSTILE_IFRAME_SELECTORS:
            try:
                element = page.locator(selector)
                if element.count() > 0:
                    log(f"[CAPTCHA] Turnstile algilandi: {selector}")
                    return CAPTCHA_TURNSTILE
            except Exception:
                continue

        # 3. Scan for reCAPTCHA
        for selector in RECAPTCHA_SELECTORS:
            try:
                element = page.locator(selector)
                if element.count() > 0:
                    log(f"[CAPTCHA] reCAPTCHA algilandi: {selector}")
                    return CAPTCHA_RECAPTCHA
            except Exception:
                continue

        # 4. Scan for hCaptcha
        for selector in HCAPTCHA_SELECTORS:
            try:
                element = page.locator(selector)
                if element.count() > 0:
                    log(f"[CAPTCHA] hCaptcha algilandi: {selector}")
                    return CAPTCHA_HCAPTCHA
            except Exception:
                continue

        log("[CAPTCHA] Sayfada CAPTCHA algilanamadi")
        return CAPTCHA_YOK

    def site_key_cikart(self, page, captcha_tipi):
        """Extract the site key (data-sitekey) for a detected CAPTCHA.

        Tries multiple selectors based on CAPTCHA type to find the element
        with a data-sitekey attribute.

        Args:
            page: Playwright page object.
            captcha_tipi: CAPTCHA type constant (from captcha_tipi_algila).

        Returns:
            str or None: Extracted site key string, or None if not found.
        """
        log(f"[CAPTCHA] Site key cikariliyor: tip={captcha_tipi}")

        selectors = SITEKEY_SELECTORS.get(captcha_tipi, [])

        for selector in selectors:
            try:
                element = page.locator(selector)
                if element.count() > 0:
                    sitekey = element.first.get_attribute("data-sitekey")
                    if sitekey:
                        log(f"[CAPTCHA] Site key bulundu: {sitekey[:16]}... "
                            f"(selector={selector})")
                        return sitekey
            except Exception as e:
                log(f"[CAPTCHA] Site key arama hatasi ({selector}): "
                    f"{type(e).__name__}: {e}")
                continue

        # Fallback: try generic data-sitekey search across all elements
        try:
            element = page.locator("[data-sitekey]")
            if element.count() > 0:
                sitekey = element.first.get_attribute("data-sitekey")
                if sitekey:
                    log(f"[CAPTCHA] Site key generic fallback bulundu: "
                        f"{sitekey[:16]}...")
                    return sitekey
        except Exception as e:
            log(f"[CAPTCHA] Generic site key arama hatasi: "
                f"{type(e).__name__}: {e}")

        log("[CAPTCHA] Site key bulunamadi")
        screenshot_al(page, "captcha_sitekey_not_found")
        return None

    def turnstile_bypass(self, page, max_deneme=3):
        """Attempt Cloudflare Turnstile bypass via frame_locator() checkbox click.

        Uses Playwright's frame_locator() to access the Turnstile iframe
        (requires disable_coop=True in Camoufox config) and clicks the
        verification checkbox.

        Args:
            page: Playwright page object.
            max_deneme: Maximum click attempts (default: 3).

        Returns:
            bool: True if bypass appears successful, False if failed.
        """
        log(f"[CAPTCHA] Turnstile bypass deneniyor (max_deneme={max_deneme})...")

        for deneme in range(1, max_deneme + 1):
            log(f"[CAPTCHA] Turnstile bypass deneme {deneme}/{max_deneme}")

            # Try each Turnstile iframe selector
            for iframe_selector in TURNSTILE_IFRAME_SELECTORS:
                try:
                    frame = page.frame_locator(iframe_selector)

                    # Try clicking the Turnstile checkbox inside the iframe
                    checkbox_selectors = [
                        "input[type='checkbox']",
                        "#challenge-stage input",
                        "label.cb-lb",
                        ".mark",
                        "[role='checkbox']",
                    ]

                    for cb_selector in checkbox_selectors:
                        try:
                            checkbox = frame.locator(cb_selector)
                            if checkbox.count() > 0:
                                checkbox.first.click(timeout=5000)
                                log(f"[CAPTCHA] Turnstile checkbox tiklandi: "
                                    f"iframe={iframe_selector}, cb={cb_selector}")

                                # Wait for Turnstile to process
                                insan_gibi_bekle(2.0, 4.0)

                                # Check if solved (look for success indicator)
                                if self._turnstile_cozuldu_mu(page):
                                    log("[CAPTCHA] Turnstile bypass BASARILI")
                                    screenshot_al(page, "turnstile_bypass_ok")
                                    return True

                                log("[CAPTCHA] Turnstile tiklandi ama henuz "
                                    "cozulmedi, devam ediliyor...")
                        except Exception:
                            continue

                except Exception as e:
                    log(f"[CAPTCHA] Turnstile iframe erisim hatasi "
                        f"({iframe_selector}): {type(e).__name__}: {e}")
                    continue

            # Wait between retries
            if deneme < max_deneme:
                log("[CAPTCHA] Turnstile retry oncesi bekleniyor...")
                insan_gibi_bekle(2.0, 4.0)

        log("[CAPTCHA] Turnstile bypass BASARISIZ — tum denemeler tukendi")
        screenshot_al(page, "turnstile_bypass_failed")
        return False

    def _turnstile_cozuldu_mu(self, page):
        """Check if Turnstile challenge has been solved.

        Looks for common success indicators:
            - cf-turnstile response input with value
            - Turnstile success callback data attributes
            - Hidden input with cf-turnstile-response name

        Args:
            page: Playwright page object.

        Returns:
            bool: True if Turnstile appears solved.
        """
        basari_selectors = [
            "input[name='cf-turnstile-response'][value]",
            "[data-turnstile-response]:not([data-turnstile-response=''])",
            "input[name='cf-turnstile-response']",
        ]

        for selector in basari_selectors:
            try:
                element = page.locator(selector)
                if element.count() > 0:
                    deger = element.first.get_attribute("value")
                    if deger and len(deger) > 10:
                        log(f"[CAPTCHA] Turnstile response bulundu: "
                            f"{len(deger)} karakter")
                        return True
            except Exception:
                continue

        return False

    def capsolver_coz(self, page, site_key, captcha_tipi):
        """Solve CAPTCHA using CapSolver API (SDK primary + raw HTTP fallback).

        Sends a task creation request to CapSolver with the appropriate task
        type for the detected CAPTCHA, then polls for the result.

        IMPORTANT: For Turnstile, same IP/TLS fingerprint/headers/User-Agent
        must be maintained during solving — any mismatch invalidates the token.

        Args:
            page: Playwright page object (for URL and screenshot on failure).
            site_key: CAPTCHA site key extracted from data-sitekey attribute.
            captcha_tipi: CAPTCHA type constant (CAPTCHA_TURNSTILE, etc.).

        Returns:
            str or None: Solved CAPTCHA token, or None if solving failed.

        Raises:
            ValueError: If API key is not configured.
        """
        if not self._api_key:
            log("[CAPTCHA] HATA: CAPSOLVER_API_KEY gerekli ama tanimli degil")
            raise ValueError(
                "CAPSOLVER_API_KEY .env'de tanimli degil — "
                "CapSolver API kullanimi icin gerekli"
            )

        page_url = page.url
        task_type = CAPSOLVER_TASK_TYPES.get(captcha_tipi)

        if not task_type:
            log(f"[CAPTCHA] HATA: Bilinmeyen CAPTCHA tipi: {captcha_tipi}")
            screenshot_al(page, "capsolver_unknown_type")
            return None

        log(f"[CAPTCHA] CapSolver ile cozuluyor: tip={captcha_tipi}, "
            f"task_type={task_type}, site_key={site_key[:16]}...")

        # Try SDK first, then raw HTTP fallback
        if self._sdk_mevcut:
            token = self._capsolver_sdk_coz(page_url, site_key, task_type)
            if token:
                return token
            log("[CAPTCHA] SDK basarisiz, raw HTTP API deneniyor...")

        token = self._capsolver_http_coz(page_url, site_key, task_type)

        if token:
            log(f"[CAPTCHA] CapSolver token alindi: {len(token)} karakter")
        else:
            log("[CAPTCHA] CapSolver cozum BASARISIZ")
            screenshot_al(page, "capsolver_failed")

        return token

    def _capsolver_sdk_coz(self, page_url, site_key, task_type):
        """Solve CAPTCHA using CapSolver Python SDK.

        Args:
            page_url: Current page URL.
            site_key: CAPTCHA site key.
            task_type: CapSolver task type string.

        Returns:
            str or None: Solved token, or None on failure.
        """
        log(f"[CAPTCHA] CapSolver SDK ile cozuluyor: task_type={task_type}")

        try:
            import capsolver

            capsolver.api_key = self._api_key

            task_params = {
                "type": task_type,
                "websiteURL": page_url,
                "websiteKey": site_key,
            }

            solution = capsolver.solve(task_params)

            if solution and isinstance(solution, dict):
                token = solution.get("token") or solution.get("gRecaptchaResponse")
                if token:
                    log(f"[CAPTCHA] SDK cozum basarili: {len(token)} karakter token")
                    return token
                log(f"[CAPTCHA] SDK cevap aldi ama token yok: "
                    f"{list(solution.keys())}")
            else:
                log(f"[CAPTCHA] SDK beklenmeyen cevap: {type(solution)}")

        except ImportError:
            log("[CAPTCHA] CapSolver SDK import hatasi")
        except Exception as e:
            log(f"[CAPTCHA] SDK hatasi: {type(e).__name__}: {e}")

        return None

    def _capsolver_http_coz(self, page_url, site_key, task_type):
        """Solve CAPTCHA using raw HTTP API (fallback when SDK fails/unavailable).

        Two-step process:
            1. POST /createTask — submit solving request
            2. GET /getTaskResult — poll until solution ready or timeout

        Args:
            page_url: Current page URL.
            site_key: CAPTCHA site key.
            task_type: CapSolver task type string.

        Returns:
            str or None: Solved token, or None on failure.
        """
        log(f"[CAPTCHA] CapSolver HTTP API ile cozuluyor: task_type={task_type}")

        # Step 1: Create task
        task_id = self._capsolver_task_olustur(page_url, site_key, task_type)
        if not task_id:
            return None

        # Step 2: Poll for result
        return self._capsolver_sonuc_bekle(task_id)

    def _capsolver_task_olustur(self, page_url, site_key, task_type):
        """Create a CapSolver task via raw HTTP POST.

        Args:
            page_url: Current page URL.
            site_key: CAPTCHA site key.
            task_type: CapSolver task type string.

        Returns:
            str or None: Task ID if created successfully, None on failure.
        """
        log("[CAPTCHA] CapSolver task olusturuluyor...")

        payload = {
            "clientKey": self._api_key,
            "task": {
                "type": task_type,
                "websiteURL": page_url,
                "websiteKey": site_key,
            }
        }

        try:
            response = requests.post(
                CAPSOLVER_CREATE_TASK_URL,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            error_id = data.get("errorId", 0)

            if error_id != 0:
                error_code = data.get("errorCode", "unknown")
                error_desc = data.get("errorDescription", "")
                log(f"[CAPTCHA] CapSolver task hatasi: "
                    f"code={error_code}, desc={error_desc}")
                return None

            task_id = data.get("taskId")
            if task_id:
                log(f"[CAPTCHA] CapSolver task olusturuldu: taskId={task_id}")
                return task_id

            log(f"[CAPTCHA] CapSolver cevabinda taskId yok: {data}")
            return None

        except requests.exceptions.Timeout:
            log("[CAPTCHA] CapSolver createTask timeout (30s)")
            return None
        except requests.exceptions.RequestException as e:
            log(f"[CAPTCHA] CapSolver HTTP hatasi: {type(e).__name__}: {e}")
            return None
        except (json.JSONDecodeError, ValueError) as e:
            log(f"[CAPTCHA] CapSolver cevap parse hatasi: "
                f"{type(e).__name__}: {e}")
            return None

    def _capsolver_sonuc_bekle(self, task_id):
        """Poll CapSolver for task result until ready or timeout.

        Uses human-like random intervals between polls.

        Args:
            task_id: CapSolver task ID from createTask response.

        Returns:
            str or None: Solved token, or None if timeout/error.
        """
        log(f"[CAPTCHA] CapSolver sonucu bekleniyor: taskId={task_id}")

        toplam_bekleme = 0

        while toplam_bekleme < self.CAPSOLVER_MAX_BEKLEME:
            # Random poll interval (human-like, not fixed)
            insan_gibi_bekle(
                self.CAPSOLVER_POLL_ARALIK_MIN,
                self.CAPSOLVER_POLL_ARALIK_MAX
            )
            toplam_bekleme += (
                self.CAPSOLVER_POLL_ARALIK_MIN + self.CAPSOLVER_POLL_ARALIK_MAX
            ) / 2

            try:
                payload = {
                    "clientKey": self._api_key,
                    "taskId": task_id,
                }

                response = requests.post(
                    CAPSOLVER_GET_RESULT_URL,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()

                data = response.json()
                error_id = data.get("errorId", 0)

                if error_id != 0:
                    error_code = data.get("errorCode", "unknown")
                    error_desc = data.get("errorDescription", "")
                    log(f"[CAPTCHA] CapSolver sonuc hatasi: "
                        f"code={error_code}, desc={error_desc}")
                    return None

                status = data.get("status", "")

                if status == "ready":
                    solution = data.get("solution", {})
                    token = (
                        solution.get("token")
                        or solution.get("gRecaptchaResponse")
                    )
                    if token:
                        log(f"[CAPTCHA] CapSolver cozuldu: "
                            f"{len(token)} karakter token "
                            f"(bekleme={toplam_bekleme:.1f}s)")
                        return token
                    log(f"[CAPTCHA] CapSolver ready ama token yok: "
                        f"{list(solution.keys())}")
                    return None

                elif status == "processing":
                    log(f"[CAPTCHA] CapSolver isleniyor... "
                        f"({toplam_bekleme:.1f}s/{self.CAPSOLVER_MAX_BEKLEME}s)")
                else:
                    log(f"[CAPTCHA] CapSolver beklenmeyen durum: {status}")

            except requests.exceptions.Timeout:
                log("[CAPTCHA] CapSolver getTaskResult timeout (30s)")
            except requests.exceptions.RequestException as e:
                log(f"[CAPTCHA] CapSolver poll hatasi: "
                    f"{type(e).__name__}: {e}")
            except (json.JSONDecodeError, ValueError) as e:
                log(f"[CAPTCHA] CapSolver sonuc parse hatasi: "
                    f"{type(e).__name__}: {e}")

        log(f"[CAPTCHA] CapSolver timeout: {self.CAPSOLVER_MAX_BEKLEME}s icerisinde "
            f"cozulemedi (taskId={task_id})")
        return None

    def token_enjekte_et(self, page, token, captcha_tipi):
        """Inject solved CAPTCHA token into the page's response field.

        Sets the token value in the appropriate hidden input or callback
        function based on CAPTCHA type.

        Args:
            page: Playwright page object.
            token: Solved CAPTCHA token string.
            captcha_tipi: CAPTCHA type constant.

        Returns:
            bool: True if injection appears successful.
        """
        log(f"[CAPTCHA] Token enjekte ediliyor: tip={captcha_tipi}, "
            f"token_uzunluk={len(token)}")

        try:
            if captcha_tipi == CAPTCHA_TURNSTILE:
                return self._turnstile_token_enjekte(page, token)
            elif captcha_tipi == CAPTCHA_RECAPTCHA:
                return self._recaptcha_token_enjekte(page, token)
            elif captcha_tipi == CAPTCHA_HCAPTCHA:
                return self._hcaptcha_token_enjekte(page, token)
            else:
                log(f"[CAPTCHA] Bilinmeyen tip icin enjeksiyon desteklenmiyor: "
                    f"{captcha_tipi}")
                return False
        except Exception as e:
            log(f"[CAPTCHA] Token enjeksiyon hatasi: {type(e).__name__}: {e}")
            screenshot_al(page, "token_injection_error")
            return False

    def _turnstile_token_enjekte(self, page, token):
        """Inject Turnstile token into cf-turnstile-response input.

        Args:
            page: Playwright page object.
            token: Solved Turnstile token.

        Returns:
            bool: True if injection successful.
        """
        response_selectors = [
            "input[name='cf-turnstile-response']",
            "[name='cf-turnstile-response']",
        ]

        for selector in response_selectors:
            try:
                element = page.locator(selector)
                if element.count() > 0:
                    page.evaluate(
                        f"document.querySelector(\"{selector}\").value = "
                        f"\"{token}\";"
                    )
                    log(f"[CAPTCHA] Turnstile token enjekte edildi: {selector}")
                    return True
            except Exception as e:
                log(f"[CAPTCHA] Turnstile enjeksiyon hatasi ({selector}): "
                    f"{type(e).__name__}: {e}")
                continue

        # Fallback: try to call Turnstile callback directly
        try:
            page.evaluate(
                f"""
                (function() {{
                    var inputs = document.querySelectorAll(
                        'input[name*="turnstile"]'
                    );
                    for (var i = 0; i < inputs.length; i++) {{
                        inputs[i].value = "{token}";
                    }}
                    if (window.turnstileCallback) {{
                        window.turnstileCallback("{token}");
                    }}
                }})();
                """
            )
            log("[CAPTCHA] Turnstile token fallback enjeksiyon denendi")
            return True
        except Exception as e:
            log(f"[CAPTCHA] Turnstile fallback enjeksiyon hatasi: "
                f"{type(e).__name__}: {e}")
            return False

    def _recaptcha_token_enjekte(self, page, token):
        """Inject reCAPTCHA token into g-recaptcha-response textarea.

        Args:
            page: Playwright page object.
            token: Solved reCAPTCHA token.

        Returns:
            bool: True if injection successful.
        """
        try:
            page.evaluate(
                f"""
                (function() {{
                    var textarea = document.getElementById(
                        'g-recaptcha-response'
                    );
                    if (textarea) {{
                        textarea.style.display = 'block';
                        textarea.value = "{token}";
                        textarea.style.display = 'none';
                    }}
                    if (typeof ___grecaptcha_cfg !== 'undefined') {{
                        Object.keys(___grecaptcha_cfg.clients).forEach(
                            function(key) {{
                                var client = ___grecaptcha_cfg.clients[key];
                                if (client && client.K && client.K.callback) {{
                                    client.K.callback("{token}");
                                }}
                            }}
                        );
                    }}
                }})();
                """
            )
            log("[CAPTCHA] reCAPTCHA token enjekte edildi")
            return True
        except Exception as e:
            log(f"[CAPTCHA] reCAPTCHA enjeksiyon hatasi: "
                f"{type(e).__name__}: {e}")
            return False

    def _hcaptcha_token_enjekte(self, page, token):
        """Inject hCaptcha token into response fields.

        Args:
            page: Playwright page object.
            token: Solved hCaptcha token.

        Returns:
            bool: True if injection successful.
        """
        try:
            page.evaluate(
                f"""
                (function() {{
                    var textareas = document.querySelectorAll(
                        '[name="h-captcha-response"], '
                        + '[name="g-recaptcha-response"]'
                    );
                    for (var i = 0; i < textareas.length; i++) {{
                        textareas[i].value = "{token}";
                    }}
                    if (window.hcaptcha) {{
                        window.hcaptcha.execute();
                    }}
                }})();
                """
            )
            log("[CAPTCHA] hCaptcha token enjekte edildi")
            return True
        except Exception as e:
            log(f"[CAPTCHA] hCaptcha enjeksiyon hatasi: "
                f"{type(e).__name__}: {e}")
            return False

    def captcha_coz(self, page, ulke_kodu=None):
        """High-level CAPTCHA solving orchestrator.

        Full pipeline:
            1. Detect CAPTCHA type
            2. If Turnstile: try frame_locator() bypass first
            3. If bypass fails or other type: extract site key + use CapSolver
            4. Inject solved token into page

        Args:
            page: Playwright page object.
            ulke_kodu: Optional country code for config-based detection.

        Returns:
            bool: True if CAPTCHA solved successfully, False otherwise.
        """
        log(f"[CAPTCHA] CAPTCHA cozme akisi baslatiliyor (ulke={ulke_kodu})")

        # Step 1: Detect CAPTCHA type
        captcha_tipi = self.captcha_tipi_algila(page, ulke_kodu)

        if captcha_tipi is None:
            log("[CAPTCHA] CAPTCHA yok — devam ediliyor")
            return True

        screenshot_al(page, f"captcha_detected_{captcha_tipi}")

        # Step 2: Try Turnstile bypass via frame click
        if captcha_tipi == CAPTCHA_TURNSTILE:
            bypass_basarili = self.turnstile_bypass(page)
            if bypass_basarili:
                return True
            log("[CAPTCHA] Turnstile bypass basarisiz, CapSolver deneniyor...")

        # Step 3: Extract site key for CapSolver
        site_key = self.site_key_cikart(page, captcha_tipi)
        if not site_key:
            log("[CAPTCHA] Site key bulunamadi — CAPTCHA cozulemiyor")
            screenshot_al(page, "captcha_no_sitekey")
            return False

        # Step 4: Solve via CapSolver API
        try:
            token = self.capsolver_coz(page, site_key, captcha_tipi)
        except ValueError as e:
            log(f"[CAPTCHA] CapSolver kullanimi mumkun degil: {e}")
            return False

        if not token:
            log("[CAPTCHA] CapSolver token alinamadi")
            return False

        # Step 5: Inject token into page
        basarili = self.token_enjekte_et(page, token, captcha_tipi)

        if basarili:
            log("[CAPTCHA] CAPTCHA basariyla cozuldu ve enjekte edildi")
            insan_gibi_bekle(1.0, 2.0)
        else:
            log("[CAPTCHA] Token enjeksiyonu basarisiz")
            screenshot_al(page, "captcha_injection_failed")

        return basarili
