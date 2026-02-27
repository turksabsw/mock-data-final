#!/usr/bin/env python3
"""Test if Camoufox is detected as a bot"""
from camoufox.sync_api import Camoufox
import time
print("[*] Bot detection testi başlatılıyor...")
print("[*] Şu siteleri test edeceğiz:")
print("  1. bot.sannysoft.com (Bot tespit)")
print("  2. pixelscan.net (Fingerprint analizi)")
print("  3. browserleaks.com/canvas (Canvas fingerprint)")
with Camoufox(headless=False, humanize=True, geoip=True) as browser:
    page = browser.new_page()
    # Test 1: Sannysoft
    print("\n[1] Sannysoft bot detection testi...")
    page.goto('https://bot.sannysoft.com')
    time.sleep(5)
    print("✅ Sayfa yüklendi - Tarayıcıda kontrol et!")
    print("   🟢 Yeşil kutular = İyi (tespit edilmedi)")
    print("   🔴 Kırmızı kutular = Kötü (bot tespit edildi)")
    input("\n[Enter] Sonraki teste geçmek için...")
    # Test 2: PixelScan
    print("\n[2] PixelScan fingerprint testi...")
    page.goto('https://pixelscan.net')
    time.sleep(5)
    print("✅ Sayfa yüklendi - 'Consistency Score' kontrol et!")
    print("   🟢 80%+ = Çok iyi")
    print("   🟡 60-80% = İyi")
    print("   🔴 <60% = Bot tespit edilebilir")
    input("\n[Enter] Sonraki teste geçmek için...")
    # Test 3: Canvas Fingerprint
    print("\n[3] Canvas fingerprint testi...")
    page.goto('https://browserleaks.com/canvas')
    time.sleep(5)
    print("✅ Sayfa yüklendi - Canvas hash kontrol et!")
    print("   Canvas hash her tarayıcıda farklı olmalı")
    input("\n[Enter] Tarayıcıyı kapatmak için...")
print("\n[*] Test tamamlandı!")
