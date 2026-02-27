"""
VISE OS — Country Configuration Management

Loads per-country configs from config/countries.json, builds VFS URLs,
validates country codes, and loads per-country CSS selectors with
fallback to the default GENEL_VFS_SELECTOR_SABLONU template.
"""

import json
import os
import warnings


# --- Default VFS Selector Template ---
# Used as fallback when no country-specific selector file has content.
# Each page has form fields with 3-tier selectors: primary, fallback_1, fallback_2.
# Real selectors will be populated per-country after live site reconnaissance.
GENEL_VFS_SELECTOR_SABLONU = {
    "register": {
        "first_name": {
            "primary": "input[id='firstName']",
            "fallback_1": "input[name='firstName']",
            "fallback_2": "input[data-testid='firstName']",
            "ai_hint": "First name text input on registration form"
        },
        "last_name": {
            "primary": "input[id='lastName']",
            "fallback_1": "input[name='lastName']",
            "fallback_2": "input[data-testid='lastName']",
            "ai_hint": "Last name text input on registration form"
        },
        "email": {
            "primary": "input[id='email']",
            "fallback_1": "input[name='email']",
            "fallback_2": "input[type='email']",
            "ai_hint": "Email address input on registration form"
        },
        "password": {
            "primary": "input[id='password']",
            "fallback_1": "input[name='password']",
            "fallback_2": "input[type='password']:first-of-type",
            "ai_hint": "Password input on registration form"
        },
        "password_confirm": {
            "primary": "input[id='confirmPassword']",
            "fallback_1": "input[name='confirmPassword']",
            "fallback_2": "input[type='password']:last-of-type",
            "ai_hint": "Password confirmation input on registration form"
        },
        "terms_checkbox": {
            "primary": "input[id='termsAndConditions']",
            "fallback_1": "input[name='termsAndConditions']",
            "fallback_2": "input[type='checkbox']",
            "ai_hint": "Terms and conditions checkbox on registration form"
        },
        "submit_button": {
            "primary": "button[type='submit']",
            "fallback_1": "button.btn-primary",
            "fallback_2": "button:has-text('Submit'), button:has-text('Register')",
            "ai_hint": "Submit/Register button on registration form"
        }
    },
    "login": {
        "email": {
            "primary": "input[id='email']",
            "fallback_1": "input[name='email']",
            "fallback_2": "input[type='email']",
            "ai_hint": "Email address input on login form"
        },
        "password": {
            "primary": "input[id='password']",
            "fallback_1": "input[name='password']",
            "fallback_2": "input[type='password']",
            "ai_hint": "Password input on login form"
        },
        "submit_button": {
            "primary": "button[type='submit']",
            "fallback_1": "button.btn-primary",
            "fallback_2": "button:has-text('Sign In'), button:has-text('Login')",
            "ai_hint": "Sign In/Login button on login form"
        },
        "otp_field": {
            "primary": "input[id='otp']",
            "fallback_1": "input[name='otp']",
            "fallback_2": "input[data-testid='otp'], input[placeholder*='OTP']",
            "ai_hint": "OTP/verification code input field"
        }
    }
}


# Path to config directory relative to project root
_PROJE_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_DIR = os.path.join(_PROJE_KOK, "config")
_COUNTRIES_JSON = os.path.join(_CONFIG_DIR, "countries.json")
_SELECTORS_DIR = os.path.join(_CONFIG_DIR, "selectors")


class UlkeYonetici:
    """Country configuration manager for VFS Global automation.

    Loads country configs from config/countries.json, validates country codes,
    builds VFS URLs, and loads per-country CSS selectors with fallback to
    the default GENEL_VFS_SELECTOR_SABLONU template.

    Usage:
        uy = UlkeYonetici()
        url = uy.url_olustur("aut", "register")
        selectors = uy.selectors_yukle("aut")
    """

    def __init__(self):
        """Initialize UlkeYonetici by loading countries.json config."""
        self._config = self._config_yukle()
        self._meta = self._config.get("_meta", {})
        self._ulkeler = self._config.get("ulkeler", {})

    def _config_yukle(self):
        """Load and parse config/countries.json.

        Returns:
            dict: Parsed countries configuration.

        Raises:
            FileNotFoundError: If countries.json does not exist.
            json.JSONDecodeError: If countries.json contains invalid JSON.
        """
        with open(_COUNTRIES_JSON, "r", encoding="utf-8") as f:
            return json.load(f)

    def ulke_al(self, ulke_kodu: str) -> dict:
        """Get validated country config for an active VFS country.

        Args:
            ulke_kodu: ISO 3166-1 alpha-3 country code (e.g., "aut", "hrv")

        Returns:
            dict: Country configuration with keys: ad, ad_en, kod, provider,
                  aktif, oncelik, koruma_seviyesi, mvp, captcha_tipi,
                  otp_zorunlu, notlar

        Raises:
            ValueError: If country code is unknown, not active, or not VFS provider.
        """
        ulke_kodu = ulke_kodu.lower().strip()

        if ulke_kodu not in self._ulkeler:
            raise ValueError(
                f"Bilinmeyen ulke kodu: '{ulke_kodu}'. "
                f"Gecerli kodlar: {', '.join(sorted(self._ulkeler.keys()))}"
            )

        ulke = self._ulkeler[ulke_kodu]

        if ulke["provider"] != "vfs":
            raise ValueError(
                f"{ulke['ad']} ({ulke_kodu}) VFS degil -> {ulke['provider']}. "
                f"Bu ulke icin ayri adapter gerekli."
            )

        if not ulke["aktif"]:
            raise ValueError(
                f"{ulke['ad']} ({ulke_kodu}) aktif degil. "
                f"Not: {ulke.get('notlar', 'Bilgi yok')}"
            )

        return ulke

    def url_olustur(self, ulke_kodu: str, sayfa: str) -> str:
        """Build VFS Global URL for a given country and page.

        Uses the URL template from countries.json _meta section with
        default origin (tur) and language (en), overridable via .env.

        Args:
            ulke_kodu: ISO 3166-1 alpha-3 country code (e.g., "aut")
            sayfa: Page name — "register" or "login"

        Returns:
            str: Full VFS URL (e.g., "https://visa.vfsglobal.com/tur/en/aut/register")

        Raises:
            ValueError: If country code is invalid or not active VFS.
        """
        # Validate the country first
        self.ulke_al(ulke_kodu)

        # Get origin and language from env or defaults
        origin = os.getenv("VFS_ORIGIN", self._meta.get("varsayilan_origin", "tur"))
        language = os.getenv("VFS_LANGUAGE", self._meta.get("varsayilan_dil", "en"))

        # Build URL from template
        url_sablonu = self._meta.get(
            "url_sablonu",
            "https://visa.vfsglobal.com/{origin}/{language}/{country_code}/{page}"
        )

        return url_sablonu.format(
            origin=origin,
            language=language,
            country_code=ulke_kodu.lower().strip(),
            page=sayfa.lower().strip()
        )

    def aktif_vfs_ulkeleri(self) -> list:
        """Get list of all active VFS country codes.

        Returns:
            list: Sorted list of active VFS country codes
                  (e.g., ["aut", "bel", "che", "cze", "hrv", "irl", "ita", "nld"])
        """
        return sorted([
            kod for kod, ulke in self._ulkeler.items()
            if ulke.get("aktif") and ulke.get("provider") == "vfs"
        ])

    def selectors_yukle(self, ulke_kodu: str) -> dict:
        """Load CSS selectors for a country, falling back to default template.

        Attempts to load from config/selectors/vfs_{ulke_kodu}.json first.
        If the file doesn't exist or only contains _meta (no page selectors),
        falls back to GENEL_VFS_SELECTOR_SABLONU.

        Args:
            ulke_kodu: ISO 3166-1 alpha-3 country code (e.g., "aut")

        Returns:
            dict: Selector configuration with page keys ("register", "login"),
                  each containing field selectors with 3-tier fallback
                  (primary, fallback_1, fallback_2).
        """
        ulke_kodu = ulke_kodu.lower().strip()
        dosya_yolu = os.path.join(_SELECTORS_DIR, f"vfs_{ulke_kodu}.json")

        if os.path.exists(dosya_yolu):
            try:
                with open(dosya_yolu, "r", encoding="utf-8") as f:
                    veri = json.load(f)

                # Check if file has actual page selectors (not just _meta)
                sayfa_anahtarlari = [k for k in veri.keys() if k != "_meta"]
                if sayfa_anahtarlari:
                    return veri
            except (json.JSONDecodeError, IOError) as e:
                warnings.warn(
                    f"Selector dosyasi okunamadi ({dosya_yolu}): {e} "
                    f"— varsayilan sablona dusulecek"
                )

        # Fallback to default template
        return GENEL_VFS_SELECTOR_SABLONU

    def tum_ulkeler(self) -> dict:
        """Get all country configurations (active and inactive).

        Returns:
            dict: All country entries from countries.json.
        """
        return self._ulkeler

    def mvp_ulkeleri(self) -> list:
        """Get list of MVP candidate country codes.

        Returns:
            list: Sorted list of MVP country codes (e.g., ["aut", "che", "hrv"])
        """
        return sorted([
            kod for kod, ulke in self._ulkeler.items()
            if ulke.get("mvp") and ulke.get("aktif") and ulke.get("provider") == "vfs"
        ])
