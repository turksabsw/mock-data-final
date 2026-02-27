#!/usr/bin/env python3
"""
VISE OS — VFS Global Register & Login Bot

CLI entry point with argparse supporting register, login, and test actions.
Uses Camoufox (Firefox fork) via Juggler protocol for anti-bot evasion.
All credentials and configuration from .env and config/ JSON files.

Usage:
    python main.py register --country aut
    python main.py login --country aut
    python main.py test --country aut
"""

import argparse
import os
import sys

from dotenv import load_dotenv


# --- Load environment variables BEFORE any src imports ---
# This ensures .env overrides are available for platform_ayarlari_al()
# and all other modules that read os.getenv() at import time.
load_dotenv()


from src.platform_config import platform_ayarlari_al
from src.country_manager import UlkeYonetici
from src.utils import log


# --- Version ---
SURUM = "0.1.0"


def _cli_olustur():
    """Create and configure the argparse CLI parser.

    Returns:
        argparse.ArgumentParser: Configured parser with register/login/test
        actions and --country flag.
    """
    parser = argparse.ArgumentParser(
        prog="vise-os",
        description="VISE OS — VFS Global Register & Login Bot",
        epilog=(
            "Examples:\n"
            "  python main.py register --country aut\n"
            "  python main.py login -c hrv\n"
            "  python main.py test -c che\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "aksiyon",
        choices=["register", "login", "test"],
        help="Action to perform: register (new account), login (existing account), test (register then login)",
    )

    parser.add_argument(
        "--country", "-c",
        dest="ulke_kodu",
        default=os.getenv("VFS_DEFAULT_COUNTRY", "aut"),
        help="Target country code (e.g., aut, hrv, che). Default: VFS_DEFAULT_COUNTRY from .env or 'aut'",
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"VISE OS v{SURUM}",
    )

    return parser


def _sistem_bilgisi_logla(platform_ayarlari, ulke_kodu, aksiyon):
    """Log system information at startup for debugging.

    Args:
        platform_ayarlari: Dict from platform_ayarlari_al().
        ulke_kodu: Target country code.
        aksiyon: Action being performed (register/login/test).
    """
    log("=" * 60)
    log(f"VISE OS v{SURUM} — Baslatiyor")
    log("=" * 60)
    log(f"[SISTEM] Aksiyon: {aksiyon}")
    log(f"[SISTEM] Ulke: {ulke_kodu}")
    log(f"[SISTEM] Platform: {platform_ayarlari['sistem']}")
    log(f"[SISTEM] Headless: {platform_ayarlari['headless']}")
    log(f"[SISTEM] Xvfb Gerekli: {platform_ayarlari['xvfb_gerekli']}")
    log(f"[SISTEM] Profil Dizini: {platform_ayarlari['profile_dir']}")
    log(f"[SISTEM] Debug Dizini: {platform_ayarlari['debug_dir']}")
    log("=" * 60)


def _ulke_dogrula(ulke_kodu):
    """Validate country code using UlkeYonetici.

    Args:
        ulke_kodu: Target country code to validate.

    Returns:
        dict: Country configuration from countries.json.

    Raises:
        SystemExit: If country code is invalid or not VFS provider.
    """
    try:
        uy = UlkeYonetici()
        ulke_bilgi = uy.ulke_al(ulke_kodu)
        log(f"[ULKE] {ulke_bilgi['ad_en']} ({ulke_kodu}) — Provider: {ulke_bilgi['provider']}")
        return ulke_bilgi
    except ValueError as e:
        log(f"[HATA] Gecersiz ulke kodu: {e}")
        print(f"\nHata: {e}", file=sys.stderr)
        sys.exit(1)


def _register_calistir(ulke_kodu):
    """Execute the registration flow for the given country.

    Args:
        ulke_kodu: Target country code.

    Returns:
        bool: True if registration succeeded, False otherwise.
    """
    from src.register import register_yap

    log(f"[KAYIT] Register akisi baslatiliyor — {ulke_kodu}")
    try:
        register_yap(ulke_kodu)
        log(f"[KAYIT] Register akisi tamamlandi — {ulke_kodu}")
        return True
    except Exception as e:
        log(f"[KAYIT] Register akisi basarisiz — {type(e).__name__}: {e}")
        return False


def _login_calistir(ulke_kodu):
    """Execute the login flow for the given country.

    Args:
        ulke_kodu: Target country code.

    Returns:
        bool: True if login succeeded, False otherwise.
    """
    from src.login import login_yap

    log(f"[GIRIS] Login akisi baslatiliyor — {ulke_kodu}")
    try:
        login_yap(ulke_kodu)
        log(f"[GIRIS] Login akisi tamamlandi — {ulke_kodu}")
        return True
    except Exception as e:
        log(f"[GIRIS] Login akisi basarisiz — {type(e).__name__}: {e}")
        return False


def _test_calistir(ulke_kodu):
    """Execute register then login sequentially for the given country.

    This is the full end-to-end test flow: creates a new account and then
    logs into it immediately after.

    Args:
        ulke_kodu: Target country code.

    Returns:
        bool: True if both register and login succeeded, False otherwise.
    """
    log(f"[TEST] Test akisi baslatiliyor — {ulke_kodu} (register + login)")

    # Step 1: Register
    register_basarili = _register_calistir(ulke_kodu)
    if not register_basarili:
        log("[TEST] Register basarisiz — login atlanacak")
        return False

    # Step 2: Login
    login_basarili = _login_calistir(ulke_kodu)
    if not login_basarili:
        log("[TEST] Login basarisiz")
        return False

    log(f"[TEST] Test akisi tamamlandi — {ulke_kodu} (register + login basarili)")
    return True


def main():
    """Main entry point — parse CLI args and dispatch to appropriate flow."""
    parser = _cli_olustur()
    args = parser.parse_args()

    # Get platform config (already initialized by utils import, but we need it for logging)
    platform_ayarlari = platform_ayarlari_al()

    # Validate country code
    _ulke_dogrula(args.ulke_kodu)

    # Log system information
    _sistem_bilgisi_logla(platform_ayarlari, args.ulke_kodu, args.aksiyon)

    # Dispatch to action
    basarili = False

    if args.aksiyon == "register":
        basarili = _register_calistir(args.ulke_kodu)
    elif args.aksiyon == "login":
        basarili = _login_calistir(args.ulke_kodu)
    elif args.aksiyon == "test":
        basarili = _test_calistir(args.ulke_kodu)

    # Final status
    if basarili:
        log(f"[SONUC] {args.aksiyon} — BASARILI")
        sys.exit(0)
    else:
        log(f"[SONUC] {args.aksiyon} — BASARISIZ")
        sys.exit(1)


if __name__ == "__main__":
    main()
