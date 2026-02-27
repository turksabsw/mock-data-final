"""
VISE OS — Camoufox Browser Health Check Tests

Integration tests that verify Camoufox browser can:
- Launch in non-persistent mode
- Open and navigate to a page
- Close cleanly without errors

Marked @pytest.mark.integration — requires Camoufox binary (camoufox fetch).
Skipped automatically if Camoufox binary is not available.
"""

import os
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def temiz_env(monkeypatch, tmp_path):
    """Set safe temp dirs for PROFILE_DIR and DEBUG_DIR to avoid polluting real dirs."""
    monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "profile"))
    monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))


def _camoufox_mevcut_mu():
    """Check if Camoufox binary is available for testing."""
    try:
        from camoufox.sync_api import Camoufox
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Browser Configuration Tests (unit-level, no browser launch)
# ---------------------------------------------------------------------------

class TestBrowserConfigSaglik:
    """Tests for browser module configuration — no actual browser launch."""

    def test_browser_modulu_import_edilebilir(self):
        """src.browser module must import without errors."""
        from src.browser import (
            tarayici_baslat,
            tarayici_baslat_test,
            sayfa_git,
            tarayici_kapat,
            tarayici_kapat_test,
            cf_clearance_kontrol,
            proxy_yapilandir,
        )
        assert callable(tarayici_baslat)
        assert callable(tarayici_baslat_test)
        assert callable(sayfa_git)
        assert callable(tarayici_kapat)
        assert callable(tarayici_kapat_test)
        assert callable(cf_clearance_kontrol)
        assert callable(proxy_yapilandir)

    def test_proxy_yapilandir_none_varsayilan(self, monkeypatch):
        """proxy_yapilandir() must return None when PROXY_SERVER is not set."""
        monkeypatch.delenv("PROXY_SERVER", raising=False)

        from src.browser import proxy_yapilandir
        sonuc = proxy_yapilandir()

        assert sonuc is None, "proxy_yapilandir() must return None without PROXY_SERVER"

    def test_proxy_yapilandir_server_var(self, monkeypatch):
        """proxy_yapilandir() must return dict when PROXY_SERVER is set."""
        monkeypatch.setenv("PROXY_SERVER", "http://test-proxy:8080")
        monkeypatch.setenv("PROXY_USERNAME", "testuser")
        monkeypatch.setenv("PROXY_PASSWORD", "testpass")

        from src.browser import proxy_yapilandir
        sonuc = proxy_yapilandir()

        assert isinstance(sonuc, dict)
        assert sonuc["server"] == "http://test-proxy:8080"
        assert sonuc["username"] == "testuser"
        assert sonuc["password"] == "testpass"

    def test_proxy_yapilandir_sadece_server(self, monkeypatch):
        """proxy_yapilandir() must work with only PROXY_SERVER (no auth)."""
        monkeypatch.setenv("PROXY_SERVER", "http://simple-proxy:3128")
        monkeypatch.delenv("PROXY_USERNAME", raising=False)
        monkeypatch.delenv("PROXY_PASSWORD", raising=False)

        from src.browser import proxy_yapilandir
        sonuc = proxy_yapilandir()

        assert isinstance(sonuc, dict)
        assert sonuc["server"] == "http://simple-proxy:3128"
        assert "username" not in sonuc
        assert "password" not in sonuc

    def test_camoufox_config_zorunlu_parametreler(self):
        """camoufox_config_olustur() must include all mandatory anti-detect flags."""
        from src.platform_config import camoufox_config_olustur
        config = camoufox_config_olustur("aut")

        assert config["humanize"] is True, "humanize must be True"
        assert config["disable_coop"] is True, "disable_coop must be True"
        assert config["geoip"] is True, "geoip must be True"
        assert config["persistent_context"] is True, "persistent_context must be True"

    def test_camoufox_config_headless_asla_true(self):
        """Camoufox config headless must never be Python True."""
        from src.platform_config import camoufox_config_olustur
        config = camoufox_config_olustur("aut")

        assert config["headless"] in (False, "virtual"), (
            f"headless must be False or 'virtual', got: {config['headless']}"
        )

    def test_camoufox_config_os_gecerli(self):
        """Camoufox config os must be a valid fingerprint OS."""
        from src.platform_config import camoufox_config_olustur
        config = camoufox_config_olustur("aut")

        assert config["os"] in {"windows", "macos", "linux"}, (
            f"os must be windows/macos/linux, got: {config['os']}"
        )

    def test_camoufox_config_user_data_dir_mevcut(self):
        """Camoufox config must have user_data_dir for persistent context."""
        from src.platform_config import camoufox_config_olustur
        config = camoufox_config_olustur("aut")

        assert "user_data_dir" in config
        assert isinstance(config["user_data_dir"], str)
        assert len(config["user_data_dir"]) > 0


# ---------------------------------------------------------------------------
# Profile Lock Detection Tests (unit-level)
# ---------------------------------------------------------------------------

class TestProfilKilidiKontrol:
    """Tests for _profil_kilidi_kontrol() — profile lock file detection."""

    def test_olmayan_dizin_kullanilabilir(self):
        """Non-existent directory should be reported as available."""
        from src.browser import _profil_kilidi_kontrol
        sonuc = _profil_kilidi_kontrol("/tmp/nonexistent_dir_xyz_123")
        assert sonuc is True

    def test_bos_dizin_kullanilabilir(self, tmp_path):
        """Empty directory should be reported as available."""
        from src.browser import _profil_kilidi_kontrol
        bos_dizin = tmp_path / "bos_profil"
        bos_dizin.mkdir()
        sonuc = _profil_kilidi_kontrol(str(bos_dizin))
        assert sonuc is True

    def test_kilitli_dizin_tespit_edilir(self, tmp_path):
        """Directory with lock file should be reported as locked."""
        from src.browser import _profil_kilidi_kontrol
        kilitli_dizin = tmp_path / "kilitli_profil"
        kilitli_dizin.mkdir()
        (kilitli_dizin / "lock").touch()
        sonuc = _profil_kilidi_kontrol(str(kilitli_dizin))
        assert sonuc is False

    def test_parent_lock_tespit_edilir(self, tmp_path):
        """Directory with parent.lock should be reported as locked."""
        from src.browser import _profil_kilidi_kontrol
        kilitli_dizin = tmp_path / "parent_lock_profil"
        kilitli_dizin.mkdir()
        (kilitli_dizin / "parent.lock").touch()
        sonuc = _profil_kilidi_kontrol(str(kilitli_dizin))
        assert sonuc is False


# ---------------------------------------------------------------------------
# Xvfb Check Tests (unit-level)
# ---------------------------------------------------------------------------

class TestXvfbKontrol:
    """Tests for _xvfb_kontrol() — Xvfb availability check."""

    @patch("src.browser.platform_ayarlari_al")
    def test_xvfb_gereksiz_true_doner(self, mock_platform):
        """On platforms where Xvfb is not needed, must return True."""
        mock_platform.return_value = {
            "sistem": "Darwin",
            "headless": False,
            "profile_dir": "/tmp/profile",
            "debug_dir": "/tmp/debug",
            "xvfb_gerekli": False,
        }

        from src.browser import _xvfb_kontrol
        sonuc = _xvfb_kontrol()
        assert sonuc is True


# ---------------------------------------------------------------------------
# Browser Close Safety Tests (unit-level, mocked)
# ---------------------------------------------------------------------------

class TestTarayiciKapatGuvenlik:
    """Tests for tarayici_kapat() and tarayici_kapat_test() — safe cleanup."""

    def test_tarayici_kapat_none_parametreler(self):
        """tarayici_kapat() must handle all None parameters without error."""
        from src.browser import tarayici_kapat
        # Should not raise any exception
        tarayici_kapat(pw=None, context=None, page=None)

    def test_tarayici_kapat_test_none_parametreler(self):
        """tarayici_kapat_test() must handle all None parameters without error."""
        from src.browser import tarayici_kapat_test
        # Should not raise any exception
        tarayici_kapat_test(camoufox_cm=None, browser=None, page=None)

    def test_tarayici_kapat_hata_yutulmaz(self):
        """tarayici_kapat() must log errors but not re-raise them."""
        from src.browser import tarayici_kapat

        mock_page = MagicMock()
        mock_page.close.side_effect = Exception("Page close error")

        mock_context = MagicMock()
        mock_pw = MagicMock()

        # Should not raise — errors are caught and logged
        tarayici_kapat(pw=mock_pw, context=mock_context, page=mock_page)

        # Context and pw should still be closed even if page.close() fails
        mock_context.close.assert_called_once()
        mock_pw.stop.assert_called_once()


# ---------------------------------------------------------------------------
# Camoufox Launch Integration Test (requires binary)
# ---------------------------------------------------------------------------

class TestCamoufoxBaslatma:
    """Integration tests for actual Camoufox browser launch.

    Requires camoufox binary to be installed (camoufox fetch).
    Skipped if binary is not available.
    """

    @pytest.mark.skipif(
        not _camoufox_mevcut_mu(),
        reason="Camoufox binary not installed (run: camoufox fetch)"
    )
    def test_tarayici_baslat_test_non_persistent(self):
        """Non-persistent browser launch, page open, and clean close.

        This is the core health check: can Camoufox actually launch,
        create a page, and close without errors?
        """
        from src.browser import tarayici_baslat_test, tarayici_kapat_test

        camoufox_cm = None
        browser = None
        page = None

        try:
            camoufox_cm, browser, page = tarayici_baslat_test()

            # Browser must be running
            assert browser is not None, "Browser instance must not be None"
            assert page is not None, "Page instance must not be None"

        finally:
            tarayici_kapat_test(
                camoufox_cm=camoufox_cm,
                browser=browser,
                page=page,
            )

    @pytest.mark.skipif(
        not _camoufox_mevcut_mu(),
        reason="Camoufox binary not installed (run: camoufox fetch)"
    )
    def test_tarayici_sayfa_acilir(self):
        """Browser must be able to navigate to a basic page.

        Uses a data: URL to avoid network dependency.
        """
        from src.browser import tarayici_baslat_test, tarayici_kapat_test

        camoufox_cm = None
        browser = None
        page = None

        try:
            camoufox_cm, browser, page = tarayici_baslat_test()

            # Navigate to a simple data URL (no network needed)
            page.goto("data:text/html,<h1>VISE OS Health Check</h1>")

            # Verify page content
            baslik = page.text_content("h1")
            assert baslik == "VISE OS Health Check", (
                f"Page content mismatch: expected 'VISE OS Health Check', got '{baslik}'"
            )

        finally:
            tarayici_kapat_test(
                camoufox_cm=camoufox_cm,
                browser=browser,
                page=page,
            )

    @pytest.mark.skipif(
        not _camoufox_mevcut_mu(),
        reason="Camoufox binary not installed (run: camoufox fetch)"
    )
    def test_tarayici_webdriver_gizli(self):
        """Browser must NOT expose navigator.webdriver = true.

        This is a basic anti-detect check. Camoufox should not reveal
        that automation is in use via the standard webdriver property.
        """
        from src.browser import tarayici_baslat_test, tarayici_kapat_test

        camoufox_cm = None
        browser = None
        page = None

        try:
            camoufox_cm, browser, page = tarayici_baslat_test()

            page.goto("data:text/html,<h1>Test</h1>")
            webdriver = page.evaluate("() => navigator.webdriver")

            # Camoufox should hide webdriver flag
            assert webdriver is not True, (
                "navigator.webdriver must NOT be true — Camoufox anti-detect failed"
            )

        finally:
            tarayici_kapat_test(
                camoufox_cm=camoufox_cm,
                browser=browser,
                page=page,
            )
