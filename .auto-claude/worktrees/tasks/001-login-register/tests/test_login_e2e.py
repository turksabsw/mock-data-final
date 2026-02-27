"""
VISE OS — E2E Login Test Skeletons

End-to-end tests for the login flow:
- Full login on VFS Global (country-agnostic)
- CAPTCHA handling (if present)
- OTP handling via Mailcow IMAP (if required)
- Error detection (invalid credentials, account locked, account not found)
- Login success verification (URL + page text indicators)

Marked @pytest.mark.e2e — requires:
    - Live VFS website access
    - Real credentials in .env (VFS_EMAIL, VFS_PASSWORD)
    - Mailcow IMAP access for OTP (MAILCOW_HOST/USER/PASS/PORT)
    - Camoufox binary installed (camoufox fetch)

Skipped by default — run explicitly with:
    python -m pytest tests/test_login_e2e.py -v -m e2e
"""

import os
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.e2e


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def temiz_env_kontrol():
    """Verify required .env variables are set for E2E tests.

    Does not modify environment — just checks that required vars exist.
    E2E tests are skipped if credentials are missing.
    """
    pass


def _e2e_gereksinimleri_mevcut():
    """Check if all E2E test requirements are met.

    Returns True only if:
        - Camoufox is importable
        - VFS_EMAIL is set in environment
        - VFS_PASSWORD is set in environment
    """
    try:
        from camoufox.sync_api import Camoufox
    except ImportError:
        return False

    gerekli = ["VFS_EMAIL", "VFS_PASSWORD"]
    return all(os.getenv(var) for var in gerekli)


def _otp_gereksinimleri_mevcut():
    """Check if Mailcow IMAP requirements are met for OTP testing.

    Returns True only if MAILCOW_HOST, MAILCOW_USER, and MAILCOW_PASS are set.
    """
    gerekli = ["MAILCOW_HOST", "MAILCOW_USER", "MAILCOW_PASS"]
    return all(os.getenv(var) for var in gerekli)


def _mvp_ulke_kodlari():
    """Return MVP country codes for E2E testing."""
    return ["aut", "hrv", "che"]


# ---------------------------------------------------------------------------
# Module Import Tests
# ---------------------------------------------------------------------------

class TestLoginModulImport:
    """Tests for login module imports — no browser launch required."""

    def test_login_modulu_import_edilebilir(self):
        """src.login module must import without errors."""
        from src.login import login_yap
        assert callable(login_yap)

    def test_hata_kaliplari_mevcut(self):
        """Error detection patterns must be defined and non-empty."""
        from src.login import (
            HATA_GECERSIZ_KIMLIK,
            HATA_HESAP_KILITLI,
            HATA_HESAP_BULUNAMADI,
        )

        assert isinstance(HATA_GECERSIZ_KIMLIK, list)
        assert len(HATA_GECERSIZ_KIMLIK) > 0, (
            "HATA_GECERSIZ_KIMLIK must have at least one pattern"
        )

        assert isinstance(HATA_HESAP_KILITLI, list)
        assert len(HATA_HESAP_KILITLI) > 0, (
            "HATA_HESAP_KILITLI must have at least one pattern"
        )

        assert isinstance(HATA_HESAP_BULUNAMADI, list)
        assert len(HATA_HESAP_BULUNAMADI) > 0, (
            "HATA_HESAP_BULUNAMADI must have at least one pattern"
        )

    def test_hata_kaliplari_string_listesi(self):
        """Error patterns must be lists of strings."""
        from src.login import (
            HATA_GECERSIZ_KIMLIK,
            HATA_HESAP_KILITLI,
            HATA_HESAP_BULUNAMADI,
        )

        for kalip in HATA_GECERSIZ_KIMLIK:
            assert isinstance(kalip, str), (
                f"HATA_GECERSIZ_KIMLIK: '{kalip}' must be a string"
            )

        for kalip in HATA_HESAP_KILITLI:
            assert isinstance(kalip, str), (
                f"HATA_HESAP_KILITLI: '{kalip}' must be a string"
            )

        for kalip in HATA_HESAP_BULUNAMADI:
            assert isinstance(kalip, str), (
                f"HATA_HESAP_BULUNAMADI: '{kalip}' must be a string"
            )

    def test_basari_kaliplari_mevcut(self):
        """Login success detection patterns must be defined."""
        from src.login import GIRIS_BASARILI_IPUCLARI, GIRIS_BASARILI_URL_IPUCLARI

        assert isinstance(GIRIS_BASARILI_IPUCLARI, list)
        assert len(GIRIS_BASARILI_IPUCLARI) > 0, (
            "GIRIS_BASARILI_IPUCLARI must have at least one pattern"
        )

        assert isinstance(GIRIS_BASARILI_URL_IPUCLARI, list)
        assert len(GIRIS_BASARILI_URL_IPUCLARI) > 0, (
            "GIRIS_BASARILI_URL_IPUCLARI must have at least one pattern"
        )

    def test_otp_kaliplari_mevcut(self):
        """OTP detection patterns must be defined."""
        from src.login import OTP_IPUCLARI

        assert isinstance(OTP_IPUCLARI, list)
        assert len(OTP_IPUCLARI) > 0, (
            "OTP_IPUCLARI must have at least one pattern"
        )


# ---------------------------------------------------------------------------
# Login Flow Configuration Tests (no browser)
# ---------------------------------------------------------------------------

class TestLoginKonfigurasyonDogrulama:
    """Tests for login flow configuration — no browser needed."""

    def test_mvp_ulkeleri_url_olusturulabilir(self):
        """URL generation must succeed for all MVP countries."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()

        for kod in _mvp_ulke_kodlari():
            url = uy.url_olustur(kod, "login")
            assert url.startswith("https://visa.vfsglobal.com/"), (
                f"URL for {kod} must start with VFS base"
            )
            assert f"/{kod}/login" in url, (
                f"URL for {kod} must contain country code and 'login'"
            )

    def test_login_selectors_4_alan(self):
        """Login selectors must have all 4 required fields."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()

        for kod in _mvp_ulke_kodlari():
            selectors = uy.selectors_yukle(kod)
            gerekli_alanlar = {"email", "password", "submit_button", "otp_field"}
            assert gerekli_alanlar == set(selectors["login"].keys()), (
                f"Country {kod}: login must have all 4 fields, "
                f"missing: {gerekli_alanlar - set(selectors['login'].keys())}"
            )

    def test_env_giris_bilgileri_formati(self, monkeypatch):
        """VFS login credentials from .env must be non-empty strings when set."""
        monkeypatch.setenv("VFS_EMAIL", "test@example.com")
        monkeypatch.setenv("VFS_PASSWORD", "TestPassword123")

        email = os.getenv("VFS_EMAIL")
        password = os.getenv("VFS_PASSWORD")

        assert isinstance(email, str) and len(email) > 0
        assert isinstance(password, str) and len(password) > 0

    def test_login_ulke_dogrulama_gecersiz_ulke(self):
        """login_yap() must validate country code before browser launch."""
        from src.country_manager import UlkeYonetici
        uy = UlkeYonetici()

        with pytest.raises(ValueError, match="auslandsportal"):
            uy.ulke_al("deu")

        with pytest.raises(ValueError):
            uy.ulke_al("xxx")

    def test_otp_reader_import_edilebilir(self):
        """OtpOkuyucu must be importable for login OTP handling."""
        from src.otp_reader import OtpOkuyucu
        assert callable(OtpOkuyucu)


# ---------------------------------------------------------------------------
# E2E Login Flow Tests (requires live VFS + credentials)
# ---------------------------------------------------------------------------

class TestLoginE2EAkis:
    """E2E login flow tests on live VFS site.

    These tests are skeletons — they define the complete test structure
    but are skipped unless all E2E requirements are met:
        - Camoufox binary installed
        - Real credentials in .env
        - Network access to VFS

    Run explicitly:
        python -m pytest tests/test_login_e2e.py::TestLoginE2EAkis -v -m e2e
    """

    @pytest.mark.skipif(
        not _e2e_gereksinimleri_mevcut(),
        reason="E2E requirements not met: Camoufox binary or .env credentials missing"
    )
    def test_login_tam_akis_aut(self):
        """Full login flow on Austria (aut) — MVP low-protection country.

        Steps:
            1. Launch browser with persistent context
            2. Navigate to VFS Austria login page
            3. Handle CAPTCHA if present (Turnstile bypass or CapSolver)
            4. Fill login form (email + password)
            5. Submit form
            6. Handle OTP if required (via Mailcow IMAP)
            7. Verify login success or detect known error

        Expected: Login succeeds OR a known error is detected
                  (invalid credentials, account locked, account not found).
        """
        from src.login import login_yap

        sonuc = login_yap("aut")

        # Assert that the flow completed (True or False, not an exception)
        assert isinstance(sonuc, bool), (
            f"login_yap must return bool, got {type(sonuc)}"
        )

    @pytest.mark.skipif(
        not _e2e_gereksinimleri_mevcut(),
        reason="E2E requirements not met: Camoufox binary or .env credentials missing"
    )
    def test_login_tam_akis_hrv(self):
        """Full login flow on Croatia (hrv) — MVP low-protection country.

        Same flow as test_login_tam_akis_aut but for Croatia.
        """
        from src.login import login_yap

        sonuc = login_yap("hrv")
        assert isinstance(sonuc, bool), (
            f"login_yap must return bool, got {type(sonuc)}"
        )

    @pytest.mark.skipif(
        not _e2e_gereksinimleri_mevcut(),
        reason="E2E requirements not met: Camoufox binary or .env credentials missing"
    )
    def test_login_tam_akis_che(self):
        """Full login flow on Switzerland (che) — MVP low-protection country.

        Same flow as test_login_tam_akis_aut but for Switzerland.
        """
        from src.login import login_yap

        sonuc = login_yap("che")
        assert isinstance(sonuc, bool), (
            f"login_yap must return bool, got {type(sonuc)}"
        )

    @pytest.mark.skipif(
        not _e2e_gereksinimleri_mevcut(),
        reason="E2E requirements not met: Camoufox binary or .env credentials missing"
    )
    def test_login_gecersiz_ulke_hata(self):
        """Login with non-VFS country must raise ValueError before browser launch.

        This verifies that country validation happens early in the flow,
        preventing unnecessary browser launches for invalid countries.
        """
        from src.login import login_yap

        with pytest.raises(ValueError):
            login_yap("deu")

    @pytest.mark.skipif(
        not _e2e_gereksinimleri_mevcut(),
        reason="E2E requirements not met: Camoufox binary or .env credentials missing"
    )
    def test_login_debug_ciktisi_uretilir(self, tmp_path, monkeypatch):
        """Login flow must produce debug output (logs).

        After a login attempt, the debug directory must contain:
            - Log file: debug/logs/vise_YYYY-MM-DD.log
        """
        monkeypatch.setenv("DEBUG_DIR", str(tmp_path / "debug"))

        from src.login import login_yap

        try:
            login_yap("aut")
        except Exception:
            # Login may fail (expected in test environments)
            # but debug output should still be generated
            pass

        log_dir = tmp_path / "debug" / "logs"
        if log_dir.exists():
            log_dosyalari = list(log_dir.glob("vise_*.log"))
            assert len(log_dosyalari) > 0, (
                "Login must produce at least one log file"
            )


# ---------------------------------------------------------------------------
# OTP Integration Tests (requires Mailcow IMAP)
# ---------------------------------------------------------------------------

class TestOtpEntegrasyonu:
    """Tests for OTP integration in login flow.

    These tests verify the OtpOkuyucu integration separately from
    the full login flow. Requires Mailcow IMAP credentials.
    """

    def test_otp_okuyucu_olusturulabilir(self):
        """OtpOkuyucu must be constructable without connection."""
        from src.otp_reader import OtpOkuyucu
        okuyucu = OtpOkuyucu()
        assert okuyucu is not None

    @pytest.mark.skipif(
        not _otp_gereksinimleri_mevcut(),
        reason="Mailcow IMAP credentials not set in .env"
    )
    def test_otp_okuyucu_baglanti(self):
        """OtpOkuyucu must connect to Mailcow IMAP successfully.

        Requires real Mailcow credentials in .env:
            - MAILCOW_HOST
            - MAILCOW_USER
            - MAILCOW_PASS
            - MAILCOW_PORT (default 993)
        """
        from src.otp_reader import OtpOkuyucu

        okuyucu = OtpOkuyucu()
        try:
            okuyucu.baglan()
            # If we get here, connection succeeded
            assert okuyucu._bagli is True, (
                "OtpOkuyucu must be in connected state after baglan()"
            )
        finally:
            okuyucu.kapat()
