"""
VISE OS — Unit Tests for Platform Detection & Fingerprint OS Rotation

Tests for:
- platform_ayarlari_al(): Cross-platform OS detection, paths, headless mode
- parmak_izi_os_sec(): Weighted fingerprint OS rotation
- camoufox_config_olustur(): Camoufox configuration builder
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from collections import Counter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def temiz_env(monkeypatch):
    """Clear PROFILE_DIR and DEBUG_DIR env vars before each test."""
    monkeypatch.delenv("PROFILE_DIR", raising=False)
    monkeypatch.delenv("DEBUG_DIR", raising=False)


# ---------------------------------------------------------------------------
# platform_ayarlari_al() Tests
# ---------------------------------------------------------------------------

class TestPlatformAyarlariAl:
    """Tests for platform_ayarlari_al() — cross-platform OS detection."""

    def test_donus_degeri_gerekli_anahtarlari_icerir(self, tmp_path, monkeypatch):
        """Return dict must contain all required keys."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import platform_ayarlari_al
        sonuc = platform_ayarlari_al()

        gerekli_anahtarlar = {"sistem", "headless", "profile_dir", "debug_dir", "xvfb_gerekli"}
        assert gerekli_anahtarlar == set(sonuc.keys()), (
            f"Missing keys: {gerekli_anahtarlar - set(sonuc.keys())}"
        )

    def test_sistem_string_doner(self, tmp_path, monkeypatch):
        """sistem value must be a non-empty string."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import platform_ayarlari_al
        sonuc = platform_ayarlari_al()

        assert isinstance(sonuc["sistem"], str)
        assert len(sonuc["sistem"]) > 0

    # --- Linux ---

    @patch("src.platform_config.platform.system", return_value="Linux")
    def test_linux_headless_virtual(self, mock_system, tmp_path, monkeypatch):
        """Linux must use headless='virtual' (Xvfb), NOT True."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import platform_ayarlari_al
        sonuc = platform_ayarlari_al()

        assert sonuc["headless"] == "virtual", (
            "Linux must use headless='virtual' for Xvfb, never headless=True"
        )

    @patch("src.platform_config.platform.system", return_value="Linux")
    def test_linux_xvfb_gerekli(self, mock_system, tmp_path, monkeypatch):
        """Linux must require Xvfb."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import platform_ayarlari_al
        sonuc = platform_ayarlari_al()

        assert sonuc["xvfb_gerekli"] is True

    @patch("src.platform_config.platform.system", return_value="Linux")
    def test_linux_varsayilan_dizinler(self, mock_system, tmp_path, monkeypatch):
        """Linux default paths when no .env override."""
        # Do NOT set PROFILE_DIR/DEBUG_DIR — let platform defaults apply
        # But mock makedirs to prevent actual directory creation
        monkeypatch.delenv("PROFILE_DIR", raising=False)
        monkeypatch.delenv("DEBUG_DIR", raising=False)

        with patch("src.platform_config.os.makedirs"):
            from src.platform_config import platform_ayarlari_al
            sonuc = platform_ayarlari_al()

        assert ".config/vise-os/vfs-profile" in sonuc["profile_dir"]
        assert "vise-os-bot/debug" in sonuc["debug_dir"]

    # --- macOS (Darwin) ---

    @patch("src.platform_config.platform.system", return_value="Darwin")
    def test_macos_headless_false(self, mock_system, tmp_path, monkeypatch):
        """macOS must use headless=False."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import platform_ayarlari_al
        sonuc = platform_ayarlari_al()

        assert sonuc["headless"] is False

    @patch("src.platform_config.platform.system", return_value="Darwin")
    def test_macos_xvfb_gereksiz(self, mock_system, tmp_path, monkeypatch):
        """macOS must NOT require Xvfb."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import platform_ayarlari_al
        sonuc = platform_ayarlari_al()

        assert sonuc["xvfb_gerekli"] is False

    @patch("src.platform_config.platform.system", return_value="Darwin")
    def test_macos_varsayilan_dizinler(self, mock_system, tmp_path, monkeypatch):
        """macOS default paths when no .env override."""
        monkeypatch.delenv("PROFILE_DIR", raising=False)
        monkeypatch.delenv("DEBUG_DIR", raising=False)

        with patch("src.platform_config.os.makedirs"):
            from src.platform_config import platform_ayarlari_al
            sonuc = platform_ayarlari_al()

        assert "Library/Application Support/VISE-OS/vfs-profile" in sonuc["profile_dir"]
        assert "vise-os-bot/debug" in sonuc["debug_dir"]

    # --- Windows ---

    @patch("src.platform_config.platform.system", return_value="Windows")
    def test_windows_headless_false(self, mock_system, tmp_path, monkeypatch):
        """Windows must use headless=False."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import platform_ayarlari_al
        sonuc = platform_ayarlari_al()

        assert sonuc["headless"] is False

    @patch("src.platform_config.platform.system", return_value="Windows")
    def test_windows_xvfb_gereksiz(self, mock_system, tmp_path, monkeypatch):
        """Windows must NOT require Xvfb."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import platform_ayarlari_al
        sonuc = platform_ayarlari_al()

        assert sonuc["xvfb_gerekli"] is False

    @patch("src.platform_config.platform.system", return_value="Windows")
    def test_windows_appdata_profil_dizini(self, mock_system, tmp_path, monkeypatch):
        """Windows uses APPDATA-based profile directory."""
        monkeypatch.delenv("PROFILE_DIR", raising=False)
        monkeypatch.delenv("DEBUG_DIR", raising=False)
        monkeypatch.setenv("APPDATA", str(tmp_path / "AppData" / "Roaming"))
        monkeypatch.setenv("USERPROFILE", str(tmp_path / "Users" / "Test"))

        with patch("src.platform_config.os.makedirs"):
            from src.platform_config import platform_ayarlari_al
            sonuc = platform_ayarlari_al()

        assert "VISE-OS" in sonuc["profile_dir"]
        assert "vfs-profile" in sonuc["profile_dir"]

    # --- .env Overrides ---

    def test_env_profile_dir_override(self, tmp_path, monkeypatch):
        """PROFILE_DIR env var overrides platform default."""
        ozel_profil = str(tmp_path / "ozel-profil")
        monkeypatch.setenv("PROFILE_DIR", ozel_profil)
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import platform_ayarlari_al
        sonuc = platform_ayarlari_al()

        assert sonuc["profile_dir"] == ozel_profil

    def test_env_debug_dir_override(self, tmp_path, monkeypatch):
        """DEBUG_DIR env var overrides platform default."""
        ozel_debug = str(tmp_path / "ozel-debug")
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", ozel_debug)

        from src.platform_config import platform_ayarlari_al
        sonuc = platform_ayarlari_al()

        assert sonuc["debug_dir"] == ozel_debug

    def test_dizinler_olusturulur(self, tmp_path, monkeypatch):
        """platform_ayarlari_al() must create profile and debug directories."""
        profil = str(tmp_path / "yeni-profil")
        debug = str(tmp_path / "yeni-debug")
        monkeypatch.setenv("PROFILE_DIR", profil)
        monkeypatch.setenv("DEBUG_DIR", debug)

        from src.platform_config import platform_ayarlari_al
        platform_ayarlari_al()

        assert os.path.isdir(profil), "profile_dir must be created"
        assert os.path.isdir(debug), "debug_dir must be created"


# ---------------------------------------------------------------------------
# parmak_izi_os_sec() Tests
# ---------------------------------------------------------------------------

class TestParmakIziOsSec:
    """Tests for parmak_izi_os_sec() — fingerprint OS rotation."""

    def test_gecerli_os_doner(self):
        """Must return one of 'windows', 'macos', 'linux'."""
        from src.platform_config import parmak_izi_os_sec

        gecerli_degerler = {"windows", "macos", "linux"}
        sonuc = parmak_izi_os_sec()

        assert sonuc in gecerli_degerler, (
            f"parmak_izi_os_sec() returned '{sonuc}', expected one of {gecerli_degerler}"
        )

    def test_string_doner(self):
        """Must return a string type."""
        from src.platform_config import parmak_izi_os_sec

        sonuc = parmak_izi_os_sec()
        assert isinstance(sonuc, str)

    def test_100_cagri_hepsi_gecerli(self):
        """100 consecutive calls must all return valid OS values."""
        from src.platform_config import parmak_izi_os_sec

        gecerli_degerler = {"windows", "macos", "linux"}
        for i in range(100):
            sonuc = parmak_izi_os_sec()
            assert sonuc in gecerli_degerler, (
                f"Call #{i+1}: '{sonuc}' is not a valid fingerprint OS"
            )

    def test_dagilim_agirlikli_1000_cagri(self):
        """Distribution over 1000 calls should roughly match 75/17/8 weights.

        Uses wide tolerance bands (+-15%) to avoid flaky tests while still
        catching completely broken weight distributions.
        """
        from src.platform_config import parmak_izi_os_sec

        sayac = Counter()
        toplam = 1000
        for _ in range(toplam):
            sayac[parmak_izi_os_sec()] += 1

        windows_oran = sayac["windows"] / toplam * 100
        macos_oran = sayac["macos"] / toplam * 100
        linux_oran = sayac["linux"] / toplam * 100

        # Windows: expected 75%, accept 55-95%
        assert 55 <= windows_oran <= 95, (
            f"Windows: {windows_oran:.1f}% — expected ~75% (tolerance 55-95%)"
        )
        # macOS: expected 17%, accept 5-35%
        assert 5 <= macos_oran <= 35, (
            f"macOS: {macos_oran:.1f}% — expected ~17% (tolerance 5-35%)"
        )
        # Linux: expected 8%, accept 1-25%
        assert 1 <= linux_oran <= 25, (
            f"Linux: {linux_oran:.1f}% — expected ~8% (tolerance 1-25%)"
        )

    def test_tum_osler_uretilir(self):
        """Over 500 calls, all three OS values should appear at least once."""
        from src.platform_config import parmak_izi_os_sec

        sonuclar = set()
        for _ in range(500):
            sonuclar.add(parmak_izi_os_sec())
            if len(sonuclar) == 3:
                break

        assert sonuclar == {"windows", "macos", "linux"}, (
            f"Expected all 3 OS values in 500 calls, got: {sonuclar}"
        )


# ---------------------------------------------------------------------------
# camoufox_config_olustur() Tests
# ---------------------------------------------------------------------------

class TestCamoufoxConfigOlustur:
    """Tests for camoufox_config_olustur() — Camoufox configuration builder."""

    def test_zorunlu_anahtarlar_mevcut(self, tmp_path, monkeypatch):
        """Config must contain all mandatory keys."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import camoufox_config_olustur
        config = camoufox_config_olustur("aut")

        zorunlu = {
            "headless", "humanize", "os", "geoip",
            "disable_coop", "persistent_context", "user_data_dir"
        }
        assert zorunlu.issubset(set(config.keys())), (
            f"Missing mandatory keys: {zorunlu - set(config.keys())}"
        )

    def test_humanize_true(self, tmp_path, monkeypatch):
        """humanize MUST be True — human-like cursor movement is mandatory."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import camoufox_config_olustur
        config = camoufox_config_olustur("aut")

        assert config["humanize"] is True, "humanize must be True (mandatory)"

    def test_disable_coop_true(self, tmp_path, monkeypatch):
        """disable_coop MUST be True — required for Cloudflare Turnstile iframe."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import camoufox_config_olustur
        config = camoufox_config_olustur("aut")

        assert config["disable_coop"] is True, (
            "disable_coop must be True (mandatory for Turnstile iframe access)"
        )

    def test_geoip_true(self, tmp_path, monkeypatch):
        """geoip MUST be True — auto timezone/locale from proxy IP."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import camoufox_config_olustur
        config = camoufox_config_olustur("aut")

        assert config["geoip"] is True, "geoip must be True"

    def test_persistent_context_true(self, tmp_path, monkeypatch):
        """persistent_context MUST be True — cookie persistence for cf_clearance."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import camoufox_config_olustur
        config = camoufox_config_olustur("aut")

        assert config["persistent_context"] is True, (
            "persistent_context must be True for cookie persistence"
        )

    def test_os_gecerli_parmak_izi(self, tmp_path, monkeypatch):
        """os field must be a valid fingerprint OS from parmak_izi_os_sec()."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import camoufox_config_olustur
        config = camoufox_config_olustur("aut")

        assert config["os"] in {"windows", "macos", "linux"}, (
            f"os='{config['os']}' is not a valid fingerprint OS"
        )

    def test_user_data_dir_ulke_kodu_icerir(self, tmp_path, monkeypatch):
        """user_data_dir must include the country code for per-country isolation."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import camoufox_config_olustur
        config = camoufox_config_olustur("aut")

        assert config["user_data_dir"].endswith("aut"), (
            f"user_data_dir must end with country code 'aut', got: {config['user_data_dir']}"
        )

    def test_farkli_ulke_kodlari_farkli_dizinler(self, tmp_path, monkeypatch):
        """Different country codes must produce different user_data_dir paths."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import camoufox_config_olustur
        config_aut = camoufox_config_olustur("aut")
        config_hrv = camoufox_config_olustur("hrv")

        assert config_aut["user_data_dir"] != config_hrv["user_data_dir"], (
            "Different countries must have different user_data_dir paths"
        )

    def test_proxy_olmadan_proxy_anahtari_yok(self, tmp_path, monkeypatch):
        """When no proxy is passed, config should NOT contain 'proxy' key."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import camoufox_config_olustur
        config = camoufox_config_olustur("aut")

        assert "proxy" not in config, (
            "Config must NOT contain 'proxy' key when no proxy is passed"
        )

    def test_proxy_ile_proxy_anahtari_var(self, tmp_path, monkeypatch):
        """When proxy is passed, config must contain the proxy configuration."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        proxy = {
            "server": "http://proxy.example.com:8080",
            "username": "user",
            "password": "pass"
        }

        from src.platform_config import camoufox_config_olustur
        config = camoufox_config_olustur("aut", proxy=proxy)

        assert "proxy" in config, "Config must contain 'proxy' key when proxy is passed"
        assert config["proxy"] == proxy, "Proxy config must match the input proxy dict"

    def test_varsayilan_ulke_kodu_aut(self, tmp_path, monkeypatch):
        """Default country code should be 'aut'."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import camoufox_config_olustur
        config = camoufox_config_olustur()

        assert config["user_data_dir"].endswith("aut"), (
            f"Default country should be 'aut', user_data_dir: {config['user_data_dir']}"
        )

    def test_headless_platform_ile_eslesiyor(self, tmp_path, monkeypatch):
        """headless value must come from platform_ayarlari_al()."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import platform_ayarlari_al, camoufox_config_olustur
        platform = platform_ayarlari_al()
        config = camoufox_config_olustur("aut")

        assert config["headless"] == platform["headless"], (
            "Camoufox headless must match platform detection headless value"
        )

    def test_headless_asla_true_degil(self, tmp_path, monkeypatch):
        """headless must NEVER be Python True — only False or 'virtual'."""
        monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.platform_config import camoufox_config_olustur
        config = camoufox_config_olustur("aut")

        assert config["headless"] is not True or config["headless"] is False, (
            "headless must be False or 'virtual', never True"
        )
        # More explicit: must be either False or the string "virtual"
        assert config["headless"] in (False, "virtual"), (
            f"headless='{config['headless']}' is invalid. Must be False or 'virtual'"
        )
