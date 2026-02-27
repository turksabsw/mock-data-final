"""
VISE OS — Unit Tests for Country Configuration Management

Tests for:
- UlkeYonetici: Country loading, validation, URL building, selector loading
- GENEL_VFS_SELECTOR_SABLONU: Default selector template structure
"""

import json
import os
import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def temiz_env(monkeypatch):
    """Clear VFS env vars before each test to prevent .env leakage."""
    monkeypatch.delenv("VFS_ORIGIN", raising=False)
    monkeypatch.delenv("VFS_LANGUAGE", raising=False)


# ---------------------------------------------------------------------------
# UlkeYonetici — Country Loading Tests
# ---------------------------------------------------------------------------

class TestUlkeYoneticiYukleme:
    """Tests for UlkeYonetici initialization and country loading."""

    def test_basarili_yukleme(self):
        """UlkeYonetici must initialize successfully from countries.json."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        assert uy is not None

    def test_aktif_vfs_8_ulke(self):
        """aktif_vfs_ulkeleri() must return exactly 8 active VFS countries."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        aktif = uy.aktif_vfs_ulkeleri()
        assert len(aktif) == 8, (
            f"Expected 8 active VFS countries, got {len(aktif)}: {aktif}"
        )

    def test_aktif_vfs_ulke_kodlari_dogru(self):
        """Active VFS countries must be aut, bel, che, cze, hrv, irl, ita, nld."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        aktif = uy.aktif_vfs_ulkeleri()
        beklenen = ["aut", "bel", "che", "cze", "hrv", "irl", "ita", "nld"]
        assert aktif == beklenen, (
            f"Expected {beklenen}, got {aktif}"
        )

    def test_aktif_vfs_ulkeler_sirali(self):
        """aktif_vfs_ulkeleri() must return country codes in sorted order."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        aktif = uy.aktif_vfs_ulkeleri()
        assert aktif == sorted(aktif), "Active VFS countries must be sorted"

    def test_tum_ulkeler_11_ulke(self):
        """tum_ulkeler() must return all 11 countries (8 active + 3 excluded)."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        tum = uy.tum_ulkeler()
        assert len(tum) == 11, (
            f"Expected 11 total countries, got {len(tum)}"
        )

    def test_tum_ulkeler_dict_doner(self):
        """tum_ulkeler() must return a dict."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        tum = uy.tum_ulkeler()
        assert isinstance(tum, dict)

    def test_mvp_ulkeleri_dogru(self):
        """mvp_ulkeleri() must return aut, che, hrv."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        mvp = uy.mvp_ulkeleri()
        assert mvp == ["aut", "che", "hrv"], (
            f"Expected MVP countries ['aut', 'che', 'hrv'], got {mvp}"
        )

    def test_ulke_al_gecerli_vfs_gerekli_anahtarlar(self):
        """ulke_al('aut') must return config with all required keys."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        ulke = uy.ulke_al("aut")

        gerekli = {
            "ad", "ad_en", "kod", "provider", "aktif", "oncelik",
            "koruma_seviyesi", "mvp", "captcha_tipi", "otp_zorunlu", "notlar"
        }
        assert gerekli.issubset(set(ulke.keys())), (
            f"Missing keys: {gerekli - set(ulke.keys())}"
        )

    def test_ulke_al_aut_provider_vfs(self):
        """Austria (aut) must have provider='vfs'."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        ulke = uy.ulke_al("aut")
        assert ulke["provider"] == "vfs"

    def test_ulke_al_aut_aktif(self):
        """Austria (aut) must be active."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        ulke = uy.ulke_al("aut")
        assert ulke["aktif"] is True

    def test_ulke_al_tum_aktif_ulkeler_basarili(self):
        """ulke_al() must succeed for all 8 active VFS countries."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        for kod in ["aut", "bel", "che", "cze", "hrv", "irl", "ita", "nld"]:
            ulke = uy.ulke_al(kod)
            assert ulke["provider"] == "vfs", (
                f"{kod}: provider must be 'vfs', got '{ulke['provider']}'"
            )
            assert ulke["aktif"] is True, (
                f"{kod}: must be active"
            )


# ---------------------------------------------------------------------------
# UlkeYonetici — Validation & Error Handling Tests
# ---------------------------------------------------------------------------

class TestUlkeYoneticiDogrulama:
    """Tests for UlkeYonetici country validation and error handling."""

    def test_bilinmeyen_ulke_kodu_hata(self):
        """Unknown country code must raise ValueError."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        with pytest.raises(ValueError, match="Bilinmeyen ulke kodu"):
            uy.ulke_al("xxx")

    def test_bilinmeyen_ulke_gecerli_kodlar_mesajda(self):
        """ValueError for unknown code must list valid codes in error message."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        with pytest.raises(ValueError, match="Gecerli kodlar"):
            uy.ulke_al("xyz")

    def test_deu_vfs_degil_auslandsportal(self):
        """Germany (deu) must raise ValueError mentioning 'auslandsportal'."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        with pytest.raises(ValueError, match="auslandsportal"):
            uy.ulke_al("deu")

    def test_fra_vfs_degil_tlscontact(self):
        """France (fra) must raise ValueError mentioning 'tlscontact'."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        with pytest.raises(ValueError, match="tlscontact"):
            uy.ulke_al("fra")

    def test_gbr_vfs_degil_tlscontact(self):
        """UK (gbr) must raise ValueError mentioning 'tlscontact'."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        with pytest.raises(ValueError, match="tlscontact"):
            uy.ulke_al("gbr")

    def test_non_vfs_hata_mesaji_provider_icerir(self):
        """Non-VFS country error must include provider name."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        with pytest.raises(ValueError, match="VFS degil"):
            uy.ulke_al("deu")

    def test_ulke_kodu_buyuk_harf_normalize(self):
        """Country code should be case-insensitive (uppercase input accepted)."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        ulke = uy.ulke_al("AUT")
        assert ulke["kod"] == "aut"

    def test_ulke_kodu_bosluk_strip(self):
        """Country code with leading/trailing whitespace should be stripped."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        ulke = uy.ulke_al("  aut  ")
        assert ulke["kod"] == "aut"

    def test_ulke_kodu_karisik_harf_normalize(self):
        """Country code with mixed case should be normalized."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        ulke = uy.ulke_al("Aut")
        assert ulke["kod"] == "aut"


# ---------------------------------------------------------------------------
# url_olustur() — VFS URL Builder Tests
# ---------------------------------------------------------------------------

class TestUrlOlustur:
    """Tests for url_olustur() — VFS URL builder."""

    def test_aut_register_url(self):
        """url_olustur('aut', 'register') must return correct VFS URL."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        url = uy.url_olustur("aut", "register")
        assert url == "https://visa.vfsglobal.com/tur/en/aut/register"

    def test_aut_login_url(self):
        """url_olustur('aut', 'login') must return correct VFS URL."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        url = uy.url_olustur("aut", "login")
        assert url == "https://visa.vfsglobal.com/tur/en/aut/login"

    def test_hrv_register_url(self):
        """url_olustur('hrv', 'register') must return correct VFS URL."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        url = uy.url_olustur("hrv", "register")
        assert url == "https://visa.vfsglobal.com/tur/en/hrv/register"

    def test_che_login_url(self):
        """url_olustur('che', 'login') must return correct VFS URL."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        url = uy.url_olustur("che", "login")
        assert url == "https://visa.vfsglobal.com/tur/en/che/login"

    def test_url_https_ile_baslar(self):
        """All generated URLs must start with https://."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        url = uy.url_olustur("aut", "register")
        assert url.startswith("https://"), (
            f"URL must start with https://, got: {url}"
        )

    def test_url_vfsglobal_domain(self):
        """All generated URLs must use visa.vfsglobal.com domain."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        url = uy.url_olustur("aut", "register")
        assert "visa.vfsglobal.com" in url

    def test_gecersiz_ulke_url_hata(self):
        """url_olustur() with unknown country must raise ValueError."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        with pytest.raises(ValueError):
            uy.url_olustur("xxx", "register")

    def test_non_vfs_ulke_url_hata(self):
        """url_olustur() with non-VFS country must raise ValueError."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        with pytest.raises(ValueError):
            uy.url_olustur("deu", "register")

    def test_env_origin_override(self, monkeypatch):
        """VFS_ORIGIN env var overrides default origin (tur) in URL."""
        monkeypatch.setenv("VFS_ORIGIN", "deu")

        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        url = uy.url_olustur("aut", "register")
        assert url == "https://visa.vfsglobal.com/deu/en/aut/register", (
            f"VFS_ORIGIN override not applied, got: {url}"
        )

    def test_env_language_override(self, monkeypatch):
        """VFS_LANGUAGE env var overrides default language (en) in URL."""
        monkeypatch.setenv("VFS_LANGUAGE", "tr")

        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        url = uy.url_olustur("aut", "register")
        assert url == "https://visa.vfsglobal.com/tur/tr/aut/register", (
            f"VFS_LANGUAGE override not applied, got: {url}"
        )

    def test_tum_aktif_ulkeler_url_basarili(self):
        """url_olustur() must work for all 8 active VFS countries."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        for kod in ["aut", "bel", "che", "cze", "hrv", "irl", "ita", "nld"]:
            url = uy.url_olustur(kod, "register")
            assert kod in url, f"Country code '{kod}' not found in URL: {url}"
            assert url.startswith("https://visa.vfsglobal.com/"), (
                f"URL must start with VFS base, got: {url}"
            )

    def test_url_ulke_kodu_kucuk_harf(self):
        """URL must contain lowercase country code even if input is uppercase."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        url = uy.url_olustur("AUT", "register")
        assert "/aut/" in url, (
            f"URL must contain lowercase country code, got: {url}"
        )

    def test_url_sayfa_kucuk_harf(self):
        """URL must contain lowercase page name even if input has mixed case."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        url = uy.url_olustur("aut", "Register")
        assert url.endswith("/register"), (
            f"URL must end with lowercase page name, got: {url}"
        )


# ---------------------------------------------------------------------------
# selectors_yukle() — CSS Selector Loading Tests
# ---------------------------------------------------------------------------

class TestSelectorsYukle:
    """Tests for selectors_yukle() — CSS selector loading with fallback."""

    def test_bos_selector_dosyasi_fallback(self):
        """When selector file only has _meta, must fall back to GENEL_VFS_SELECTOR_SABLONU."""
        from src.country_manager import UlkeYonetici, GENEL_VFS_SELECTOR_SABLONU
        uy = UlkeYonetici()
        selectors = uy.selectors_yukle("aut")
        assert selectors == GENEL_VFS_SELECTOR_SABLONU

    def test_fallback_tum_aktif_ulkeler_icin(self):
        """All 8 active VFS countries with placeholder files must fall back to default."""
        from src.country_manager import UlkeYonetici, GENEL_VFS_SELECTOR_SABLONU
        uy = UlkeYonetici()
        for kod in ["aut", "bel", "che", "cze", "hrv", "irl", "ita", "nld"]:
            selectors = uy.selectors_yukle(kod)
            assert selectors == GENEL_VFS_SELECTOR_SABLONU, (
                f"Country '{kod}' should fall back to default template"
            )

    def test_fallback_register_sayfa_mevcut(self):
        """Fallback selectors must have 'register' page."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        selectors = uy.selectors_yukle("aut")
        assert "register" in selectors

    def test_fallback_login_sayfa_mevcut(self):
        """Fallback selectors must have 'login' page."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        selectors = uy.selectors_yukle("aut")
        assert "login" in selectors

    def test_fallback_register_7_alan(self):
        """Fallback register selectors must have all 7 required fields."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        selectors = uy.selectors_yukle("aut")
        beklenen_alanlar = {
            "first_name", "last_name", "email", "password",
            "password_confirm", "terms_checkbox", "submit_button"
        }
        assert beklenen_alanlar == set(selectors["register"].keys()), (
            f"Expected fields: {beklenen_alanlar}, "
            f"got: {set(selectors['register'].keys())}"
        )

    def test_fallback_login_4_alan(self):
        """Fallback login selectors must have all 4 required fields."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        selectors = uy.selectors_yukle("aut")
        beklenen_alanlar = {"email", "password", "submit_button", "otp_field"}
        assert beklenen_alanlar == set(selectors["login"].keys()), (
            f"Expected fields: {beklenen_alanlar}, "
            f"got: {set(selectors['login'].keys())}"
        )

    def test_uc_tier_selector_yapisi(self):
        """Each selector field must have primary, fallback_1, fallback_2 tiers."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        selectors = uy.selectors_yukle("aut")

        for sayfa in ["register", "login"]:
            for alan, deger in selectors[sayfa].items():
                assert "primary" in deger, (
                    f"{sayfa}/{alan} missing 'primary' tier"
                )
                assert "fallback_1" in deger, (
                    f"{sayfa}/{alan} missing 'fallback_1' tier"
                )
                assert "fallback_2" in deger, (
                    f"{sayfa}/{alan} missing 'fallback_2' tier"
                )

    def test_selector_degerleri_bos_degil_string(self):
        """All selector tier values must be non-empty strings."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()
        selectors = uy.selectors_yukle("aut")

        for sayfa in ["register", "login"]:
            for alan, deger in selectors[sayfa].items():
                for tier in ["primary", "fallback_1", "fallback_2"]:
                    assert isinstance(deger[tier], str), (
                        f"{sayfa}/{alan}/{tier} must be a string"
                    )
                    assert len(deger[tier]) > 0, (
                        f"{sayfa}/{alan}/{tier} must not be empty"
                    )

    def test_ulke_spesifik_selector_dosyasi_yuklenir(self, tmp_path):
        """When selector file has page content, it must be used instead of fallback."""
        from src.country_manager import UlkeYonetici

        ozel_selectors = {
            "_meta": {"ulke_kodu": "test"},
            "register": {
                "email": {
                    "primary": "#custom-email",
                    "fallback_1": ".custom-email",
                    "fallback_2": "input.email"
                }
            }
        }

        uy = UlkeYonetici()
        with patch("src.country_manager._SELECTORS_DIR", str(tmp_path)):
            selector_dosya = os.path.join(str(tmp_path), "vfs_ozel.json")
            with open(selector_dosya, "w", encoding="utf-8") as f:
                json.dump(ozel_selectors, f)

            selectors = uy.selectors_yukle("ozel")
            assert "register" in selectors
            assert selectors["register"]["email"]["primary"] == "#custom-email"

    def test_olmayan_dosya_fallback(self):
        """When no selector file exists at all, must fall back to default template."""
        from src.country_manager import UlkeYonetici, GENEL_VFS_SELECTOR_SABLONU
        uy = UlkeYonetici()

        with patch("src.country_manager._SELECTORS_DIR", "/tmp/nonexistent_dir_xyz"):
            selectors = uy.selectors_yukle("bilinmeyen")
            assert selectors == GENEL_VFS_SELECTOR_SABLONU

    def test_bozuk_json_fallback(self, tmp_path):
        """When selector file contains invalid JSON, must fall back to default template."""
        from src.country_manager import UlkeYonetici, GENEL_VFS_SELECTOR_SABLONU
        uy = UlkeYonetici()

        with patch("src.country_manager._SELECTORS_DIR", str(tmp_path)):
            bozuk_dosya = os.path.join(str(tmp_path), "vfs_bozuk.json")
            with open(bozuk_dosya, "w") as f:
                f.write("{ invalid json !!!")

            selectors = uy.selectors_yukle("bozuk")
            assert selectors == GENEL_VFS_SELECTOR_SABLONU


# ---------------------------------------------------------------------------
# GENEL_VFS_SELECTOR_SABLONU — Default Template Structure Tests
# ---------------------------------------------------------------------------

class TestGenelVfsSelectorSablonu:
    """Tests for GENEL_VFS_SELECTOR_SABLONU — default selector template."""

    def test_register_ve_login_sayfalari(self):
        """Template must have exactly 'register' and 'login' pages."""
        from src.country_manager import GENEL_VFS_SELECTOR_SABLONU
        assert set(GENEL_VFS_SELECTOR_SABLONU.keys()) == {"register", "login"}

    def test_register_7_alan(self):
        """Register page must have exactly 7 fields."""
        from src.country_manager import GENEL_VFS_SELECTOR_SABLONU
        assert len(GENEL_VFS_SELECTOR_SABLONU["register"]) == 7

    def test_login_4_alan(self):
        """Login page must have exactly 4 fields."""
        from src.country_manager import GENEL_VFS_SELECTOR_SABLONU
        assert len(GENEL_VFS_SELECTOR_SABLONU["login"]) == 4

    def test_ai_hint_tum_alanlarda_mevcut(self):
        """Each selector field must have an ai_hint for debugging."""
        from src.country_manager import GENEL_VFS_SELECTOR_SABLONU
        for sayfa in ["register", "login"]:
            for alan, deger in GENEL_VFS_SELECTOR_SABLONU[sayfa].items():
                assert "ai_hint" in deger, (
                    f"{sayfa}/{alan} missing 'ai_hint' for debugging"
                )
                assert isinstance(deger["ai_hint"], str), (
                    f"{sayfa}/{alan}/ai_hint must be a string"
                )
                assert len(deger["ai_hint"]) > 0, (
                    f"{sayfa}/{alan}/ai_hint must not be empty"
                )

    def test_sablon_dict_tipi(self):
        """Template must be a dictionary."""
        from src.country_manager import GENEL_VFS_SELECTOR_SABLONU
        assert isinstance(GENEL_VFS_SELECTOR_SABLONU, dict)

    def test_register_submit_button_mevcut(self):
        """Register page must have a submit_button selector."""
        from src.country_manager import GENEL_VFS_SELECTOR_SABLONU
        assert "submit_button" in GENEL_VFS_SELECTOR_SABLONU["register"]

    def test_login_otp_field_mevcut(self):
        """Login page must have an otp_field selector for OTP input."""
        from src.country_manager import GENEL_VFS_SELECTOR_SABLONU
        assert "otp_field" in GENEL_VFS_SELECTOR_SABLONU["login"]
