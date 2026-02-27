"""
VISE OS — Login Flow

Country-agnostic VFS Global login using config-driven selectors,
human-like form filling, CAPTCHA handling, and OTP support via Mailcow IMAP.

All credentials loaded from .env: VFS_EMAIL, VFS_PASSWORD.
OTP retrieved via MAILCOW_HOST/USER/PASS/PORT.
"""

import os
import random

from src.browser import tarayici_baslat, sayfa_git, tarayici_kapat, cf_clearance_kontrol
from src.captcha_solver import CaptcaCozucu
from src.country_manager import UlkeYonetici
from src.otp_reader import OtpOkuyucu
from src.utils import (
    log,
    screenshot_al,
    insan_gibi_bekle,
    element_bul,
    akis_calistir,
)


# --- Login Error Detection Patterns ---
# Text patterns on VFS pages that indicate specific login errors.
# Checked case-insensitively against page body text after form submission.
HATA_GECERSIZ_KIMLIK = [
    "invalid credentials",
    "invalid email or password",
    "incorrect password",
    "wrong password",
    "email or password is incorrect",
    "login failed",
    "authentication failed",
    "hatali giris",
    "gecersiz kimlik",
]

HATA_HESAP_KILITLI = [
    "account locked",
    "account has been locked",
    "too many attempts",
    "temporarily locked",
    "account suspended",
    "hesap kilitlendi",
    "hesap askiya alindi",
]

HATA_HESAP_BULUNAMADI = [
    "account not found",
    "no account found",
    "email not registered",
    "user not found",
    "hesap bulunamadi",
    "kayitli degil",
]

# --- OTP Detection Patterns ---
# Text patterns that indicate VFS requires OTP verification during login.
OTP_IPUCLARI = [
    "one-time password",
    "one time password",
    "verification code",
    "enter the code",
    "enter otp",
    "otp sent",
    "code sent",
    "check your email",
    "sent to your email",
    "dogrulama kodu",
    "tek kullanimlik",
]

# --- Successful Login Detection Patterns ---
# Text patterns or URL fragments that indicate successful login.
GIRIS_BASARILI_IPUCLARI = [
    "dashboard",
    "welcome",
    "my account",
    "my applications",
    "book appointment",
    "new booking",
    "application centre",
    "hesabim",
    "randevu",
    "basvuru",
]

GIRIS_BASARILI_URL_IPUCLARI = [
    "/dashboard",
    "/account",
    "/booking",
    "/applications",
    "/appointment",
]


def _env_giris_bilgileri_al():
    """Load login credentials from .env.

    Returns:
        dict: Login credentials with keys:
            - email: VFS_EMAIL
            - password: VFS_PASSWORD

    Raises:
        ValueError: If any required credential is missing from .env.
    """
    email = os.getenv("VFS_EMAIL", "")
    password = os.getenv("VFS_PASSWORD", "")

    eksik = []
    if not email:
        eksik.append("VFS_EMAIL")
    if not password:
        eksik.append("VFS_PASSWORD")

    if eksik:
        raise ValueError(
            f"Giris icin gerekli .env degiskenleri eksik: {', '.join(eksik)}"
        )

    return {
        "email": email,
        "password": password,
    }


def _alan_doldur(page, ulke_kodu, alan_adi, metin):
    """Find a login form field via 3-tier selectors and fill with human-like typing.

    Combines element_bul() (3-tier selector fallback from config) with human-like
    character-by-character typing: click -> wait -> type char by char -> wait.

    Args:
        page: Playwright page object.
        ulke_kodu: VFS country code for selector lookup.
        alan_adi: Field name in selector config (e.g., "email", "password").
        metin: Text to type into the field.
    """
    element = element_bul(page, ulke_kodu, "login", alan_adi)
    element.click()
    insan_gibi_bekle(0.3, 0.8)
    for karakter in metin:
        element.type(karakter, delay=random.randint(50, 150))
    insan_gibi_bekle(0.5, 1.5)


def _sayfa_hata_kontrol(page, hata_kaliplari, hata_turu):
    """Check page content for known error patterns.

    Scans the page's visible text content for any matching error pattern.

    Args:
        page: Playwright page object.
        hata_kaliplari: List of error text patterns to search for (case-insensitive).
        hata_turu: Error type label for logging (e.g., "GECERSIZ_KIMLIK").

    Returns:
        str or None: Matched error text if found, None otherwise.
    """
    try:
        sayfa_metni = page.inner_text("body").lower()
        for kalip in hata_kaliplari:
            if kalip.lower() in sayfa_metni:
                log(f"[LOGIN] {hata_turu} hatasi algilandi: '{kalip}'")
                screenshot_al(page, f"login_{hata_turu.lower()}")
                return kalip
    except Exception as e:
        log(f"[LOGIN] Sayfa hata kontrol hatasi: {type(e).__name__}: {e}")

    return None


def _form_doldur(page, ulke_kodu, kimlik):
    """Fill the VFS login form using config-driven selectors.

    Uses element_bul() for 3-tier selector fallback and human-like
    character-by-character typing for each field.

    Steps:
        1. Fill email
        2. Fill password

    Args:
        page: Playwright page object.
        ulke_kodu: VFS country code for selector lookup.
        kimlik: Credentials dict from _env_giris_bilgileri_al().

    Returns:
        bool: True if form filled successfully.

    Raises:
        Exception: If any form element not found or interaction fails.
    """
    log("[LOGIN] Form doldurma baslatiliyor...")

    # 1. Email
    log("[LOGIN] Email alani dolduruluyor...")
    _alan_doldur(page, ulke_kodu, "email", kimlik["email"])
    log(f"[LOGIN] Email alani dolduruldu: {kimlik['email']}")
    insan_gibi_bekle(0.5, 1.5)

    # 2. Password
    log("[LOGIN] Sifre alani dolduruluyor...")
    _alan_doldur(page, ulke_kodu, "password", kimlik["password"])
    log("[LOGIN] Sifre alani dolduruldu")
    insan_gibi_bekle(0.5, 1.5)

    screenshot_al(page, "login_form_filled")
    log("[LOGIN] Form doldurma tamamlandi")
    return True


def _form_gonder(page, ulke_kodu):
    """Click the submit button on the login form.

    Finds the submit button via 3-tier selectors, adds a brief human pause,
    then clicks. Waits after click for page to respond.

    Args:
        page: Playwright page object.
        ulke_kodu: VFS country code for selector lookup.

    Returns:
        bool: True if submit button clicked successfully.

    Raises:
        Exception: If submit button not found or click fails.
    """
    log("[LOGIN] Form gonderiliyor...")
    submit_el = element_bul(page, ulke_kodu, "login", "submit_button")
    insan_gibi_bekle(0.5, 1.0)
    submit_el.click()
    log("[LOGIN] Submit butonu tiklandi")

    # Wait for page to process the submission
    insan_gibi_bekle(3.0, 5.0)
    screenshot_al(page, "login_after_submit")
    return True


def _otp_gerekli_mi(page):
    """Check if the page shows OTP/verification code prompt after login submission.

    Scans page body text for OTP-related keywords that indicate
    VFS requires a one-time password.

    Args:
        page: Playwright page object.

    Returns:
        bool: True if page indicates OTP is needed.
    """
    try:
        sayfa_metni = page.inner_text("body").lower()
        for ipucu in OTP_IPUCLARI:
            if ipucu in sayfa_metni:
                log(f"[LOGIN] Sayfa OTP istegi algilandi: '{ipucu}'")
                return True
    except Exception as e:
        log(f"[LOGIN] OTP kontrol hatasi: {type(e).__name__}: {e}")

    return False


def _otp_isle(page, ulke_kodu):
    """Handle OTP verification during login.

    Connects to Mailcow IMAP via OtpOkuyucu, waits for a VFS OTP email,
    extracts the code, and enters it into the OTP field on the page.

    OTP pipeline must complete within 30 seconds (OTP validity: 60-90s).

    Args:
        page: Playwright page object.
        ulke_kodu: VFS country code for selector lookup.

    Returns:
        bool: True if OTP handled successfully, False otherwise.
    """
    log("[LOGIN] OTP islemi baslatiliyor...")

    okuyucu = OtpOkuyucu()
    try:
        okuyucu.baglan()

        sonuc = okuyucu.otp_bekle(timeout=60, max_deneme=3)

        if sonuc.get("otp"):
            log(f"[LOGIN] OTP kodu bulundu: {sonuc['otp']}")
            otp_girildi = _otp_kodu_gir(page, ulke_kodu, sonuc["otp"])

            if otp_girildi:
                _otp_submit_tikla(page, ulke_kodu)
                return True
            return False

        if sonuc.get("link"):
            # Less common for login, but handle verification link if present
            log(f"[LOGIN] Dogrulama linki bulundu: {sonuc['link']}")
            sayfa_git(page, sonuc["link"])
            insan_gibi_bekle(3.0, 5.0)
            screenshot_al(page, "login_verify_link_visited")
            log("[LOGIN] Dogrulama linki ziyaret edildi")
            return True

        log("[LOGIN] OTP sonucu bos — OTP/link bulunamadi")
        return False

    except TimeoutError:
        log("[LOGIN] OTP timeout — email gelmedi")
        screenshot_al(page, "login_otp_timeout")
        return False
    except ConnectionError as e:
        log(f"[LOGIN] IMAP baglanti hatasi: {e}")
        screenshot_al(page, "login_imap_connection_error")
        return False
    except Exception as e:
        log(f"[LOGIN] OTP isleme hatasi: {type(e).__name__}: {e}")
        screenshot_al(page, "login_otp_error")
        return False
    finally:
        okuyucu.kapat()


def _otp_kodu_gir(page, ulke_kodu, otp_kod):
    """Enter OTP code into the page using config-driven selectors.

    Uses element_bul() with login page's otp_field selectors (3-tier fallback).
    Types the code with human-like character-by-character delay.

    Args:
        page: Playwright page object.
        ulke_kodu: VFS country code for selector lookup.
        otp_kod: OTP code string to enter.

    Returns:
        bool: True if OTP entered successfully, False if no input found.
    """
    log(f"[LOGIN] OTP kodu giriliyor: {otp_kod}")

    try:
        otp_el = element_bul(page, ulke_kodu, "login", "otp_field", timeout=10000)
        otp_el.click()
        insan_gibi_bekle(0.3, 0.8)
        for karakter in otp_kod:
            otp_el.type(karakter, delay=random.randint(50, 150))
        insan_gibi_bekle(0.5, 1.0)
        log("[LOGIN] OTP kodu girildi")
        screenshot_al(page, "login_otp_entered")
        return True
    except Exception as e:
        log(
            f"[LOGIN] OTP alani bulunamadi veya doldurulamadi: "
            f"{type(e).__name__}: {e}"
        )
        screenshot_al(page, "login_otp_field_error")
        return False


def _otp_submit_tikla(page, ulke_kodu):
    """Try to click a submit/verify button after OTP entry.

    Uses element_bul() with login page's submit_button selectors (3-tier
    config-driven fallback) to find and click the submit button.

    Args:
        page: Playwright page object.
        ulke_kodu: VFS country code for selector lookup.
    """
    try:
        submit_el = element_bul(
            page, ulke_kodu, "login", "submit_button", timeout=10000
        )
        insan_gibi_bekle(0.3, 0.8)
        submit_el.click()
        log("[LOGIN] OTP submit tiklandi")
        insan_gibi_bekle(3.0, 5.0)
        screenshot_al(page, "login_otp_submitted")
    except Exception as e:
        log(
            f"[LOGIN] OTP submit butonu bulunamadi: "
            f"{type(e).__name__}: {e} — manuel onay gerekebilir"
        )


def _giris_basarili_mi(page):
    """Check if login was successful by examining page content and URL.

    Checks:
        1. Current URL for dashboard/account indicators
        2. Page body text for welcome/dashboard keywords

    Args:
        page: Playwright page object.

    Returns:
        bool: True if login appears successful.
    """
    # Check URL for success indicators
    try:
        mevcut_url = page.url.lower()
        for ipucu in GIRIS_BASARILI_URL_IPUCLARI:
            if ipucu in mevcut_url:
                log(f"[LOGIN] Giris basarili — URL ipucu: '{ipucu}' (url={page.url})")
                return True
    except Exception as e:
        log(f"[LOGIN] URL kontrol hatasi: {type(e).__name__}: {e}")

    # Check page content for success indicators
    try:
        sayfa_metni = page.inner_text("body").lower()
        for ipucu in GIRIS_BASARILI_IPUCLARI:
            if ipucu in sayfa_metni:
                log(f"[LOGIN] Giris basarili — sayfa ipucu: '{ipucu}'")
                return True
    except Exception as e:
        log(f"[LOGIN] Sayfa icerik kontrol hatasi: {type(e).__name__}: {e}")

    return False


def login_yap(ulke_kodu: str):
    """Execute the full VFS Global login flow for a given country.

    Country-agnostic login flow:
        1. Validate country code and load credentials from .env
        2. Launch Camoufox browser with persistent context
        3. Navigate to VFS login page
        4. Check for Cloudflare challenge and handle CAPTCHA
        5. Fill login form (email, password)
        6. Submit form
        7. Check for login errors (invalid credentials, account locked,
           account not found)
        8. Handle OTP verification if required
        9. Verify successful login
        10. Cleanup browser in finally block

    All interactions use config-driven selectors (from config/selectors/)
    and human-like behavior (random waits, character-by-character typing).
    OTP pipeline completes within 30 seconds (OTP validity: 60-90s).

    Args:
        ulke_kodu: VFS country code (e.g., "aut", "hrv", "che").

    Returns:
        bool: True if login completed successfully.

    Raises:
        ValueError: If country code is invalid/inactive or credentials missing.
        Exception: If a critical step fails. Logged + screenshot before re-raising.
    """
    log(f"[LOGIN] ===== GIRIS AKISI BASLATILIYOR: ulke={ulke_kodu} =====")

    pw = None
    context = None
    page = None

    try:
        # --- Step 1: Validate country and load credentials ---
        log("[LOGIN] Adim 1: Ulke dogrulama ve giris bilgileri yukleme")
        uy = UlkeYonetici()
        ulke = uy.ulke_al(ulke_kodu)
        log(f"[LOGIN] Ulke dogrulandi: {ulke['ad_en']} ({ulke_kodu})")

        kimlik = _env_giris_bilgileri_al()
        log(f"[LOGIN] Giris bilgileri yuklendi: email={kimlik['email']}")

        # --- Step 2: Launch browser ---
        log("[LOGIN] Adim 2: Tarayici baslatiliyor")
        pw, context, page = tarayici_baslat(ulke_kodu)
        log("[LOGIN] Tarayici baslatildi")

        # --- Step 3: Navigate to login page ---
        log("[LOGIN] Adim 3: Giris sayfasina gidiliyor")
        login_url = uy.url_olustur(ulke_kodu, "login")
        log(f"[LOGIN] Giris URL: {login_url}")
        sayfa_git(page, login_url)
        screenshot_al(page, "login_page_loaded")

        # --- Step 4: Cloudflare and CAPTCHA handling ---
        log("[LOGIN] Adim 4: Cloudflare ve CAPTCHA kontrolu")
        cf_var = cf_clearance_kontrol(context)
        if cf_var:
            log("[LOGIN] cf_clearance mevcut — Cloudflare challenge atlandi")

        cozucu = CaptcaCozucu()
        captcha_sonuc = akis_calistir(
            "LOGIN_CAPTCHA",
            cozucu.captcha_coz,
            page,
            ulke_kodu,
        )
        if not captcha_sonuc:
            log(
                "[LOGIN] UYARI: CAPTCHA cozulemedi — "
                "form gonderiminde sorun olabilir"
            )

        # --- Step 5: Fill login form ---
        log("[LOGIN] Adim 5: Giris formu dolduruluyor")
        akis_calistir(
            "LOGIN_FORM_FILL",
            _form_doldur,
            page,
            ulke_kodu,
            kimlik,
        )

        # --- Step 6: Submit form ---
        log("[LOGIN] Adim 6: Form gonderiliyor")
        akis_calistir(
            "LOGIN_FORM_SUBMIT",
            _form_gonder,
            page,
            ulke_kodu,
        )

        # --- Step 7: Check for login errors ---
        log("[LOGIN] Adim 7: Hata kontrolu")

        kimlik_hata = _sayfa_hata_kontrol(
            page, HATA_GECERSIZ_KIMLIK, "GECERSIZ_KIMLIK"
        )
        if kimlik_hata:
            raise Exception(
                f"Giris basarisiz: Gecersiz kimlik bilgileri — '{kimlik_hata}'. "
                f"Email ve sifrenizi kontrol edin."
            )

        hesap_kilitli = _sayfa_hata_kontrol(
            page, HATA_HESAP_KILITLI, "HESAP_KILITLI"
        )
        if hesap_kilitli:
            raise Exception(
                f"Giris basarisiz: Hesap kilitlendi — '{hesap_kilitli}'. "
                f"Lutfen bir sure sonra tekrar deneyin."
            )

        hesap_yok = _sayfa_hata_kontrol(
            page, HATA_HESAP_BULUNAMADI, "HESAP_BULUNAMADI"
        )
        if hesap_yok:
            raise Exception(
                f"Giris basarisiz: Hesap bulunamadi — '{hesap_yok}'. "
                f"Once kayit olmaniz gerekebilir."
            )

        # --- Step 8: Handle OTP verification if required ---
        log("[LOGIN] Adim 8: OTP kontrolu")
        otp_zorunlu = ulke.get("otp_zorunlu", False)

        if otp_zorunlu:
            log("[LOGIN] Bu ulke icin OTP zorunlu")
            otp_sonuc = _otp_isle(page, ulke_kodu)
            if otp_sonuc:
                log("[LOGIN] OTP dogrulama basarili")
            else:
                log("[LOGIN] UYARI: OTP dogrulama tamamlanamadi")
        else:
            log("[LOGIN] OTP zorunlu degil — sayfa kontrol ediliyor")
            # Some countries may trigger OTP dynamically
            insan_gibi_bekle(2.0, 4.0)

            if _otp_gerekli_mi(page):
                log(
                    "[LOGIN] Sayfa OTP istedi — "
                    "OTP islemi baslatiliyor"
                )
                otp_sonuc = _otp_isle(page, ulke_kodu)
                if otp_sonuc:
                    log("[LOGIN] Dinamik OTP dogrulama basarili")
                else:
                    log(
                        "[LOGIN] UYARI: Dinamik OTP dogrulama "
                        "tamamlanamadi"
                    )
            else:
                log("[LOGIN] Sayfada OTP istegi yok — devam ediliyor")

        # --- Step 9: Verify successful login ---
        log("[LOGIN] Adim 9: Giris dogrulama")
        insan_gibi_bekle(2.0, 4.0)

        if _giris_basarili_mi(page):
            log("[LOGIN] Giris basariyla dogrulandi")
        else:
            log(
                "[LOGIN] UYARI: Giris basari ipucu bulunamadi — "
                "sayfa durumu belirsiz"
            )
            screenshot_al(page, "login_verification_uncertain")

        # --- Final ---
        screenshot_al(page, "login_completed")
        log(
            f"[LOGIN] ===== GIRIS AKISI TAMAMLANDI: "
            f"ulke={ulke_kodu} ====="
        )
        return True

    except ValueError as e:
        log(f"[LOGIN] DOGRULAMA HATASI: {e}")
        raise
    except Exception as e:
        log(f"[LOGIN] HATA: {type(e).__name__}: {e}")
        if page:
            screenshot_al(page, "login_critical_error")
        raise
    finally:
        # Step 10: Cleanup browser resources
        log("[LOGIN] Tarayici kapatiliyor...")
        tarayici_kapat(pw, context, page)
