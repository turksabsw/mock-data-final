#!/usr/bin/env python3
"""Find Dial Code Dropdown Selector"""
from camoufox.sync_api import Camoufox
import time
print("[*] Camoufox başlatılıyor...")
with Camoufox(headless=False, humanize=True) as browser:
    page = browser.new_page()
    page.goto("https://visa.vfsglobal.com/tur/en/aut/register")
    time.sleep(5)
    # Cookie modal kapat
    try:
        page.evaluate("() => document.getElementById('onetrust-consent-sdk')?.remove()")
        time.sleep(2)
    except:
        pass
    # Mobil numara input'u çevresini analiz et
    result = page.evaluate("""
        () => {
            const mobile = document.getElementById('mat-input-3');
            if (!mobile) return 'Mobile input not found';
            const parent = mobile.closest('.input-group, .form-group, .mat-form-field');
            const buttons = parent ? Array.from(parent.querySelectorAll('button')) : [];
            const dropdowns = parent ? Array.from(parent.querySelectorAll('[role="button"], .dropdown-toggle')) : [];
            return {
                parent_class: parent?.className || 'N/A',
                buttons: buttons.map(b => ({
                    id: b.id || 'N/A',
                    class: b.className,
                    text: b.textContent.trim().substring(0,30)
                })),
                dropdowns: dropdowns.map(d => ({
                    tag: d.tagName,
                    id: d.id || 'N/A',
                    class: d.className,
                    text: d.textContent.trim().substring(0,30)
                }))
            };
        }
    """)
    print("\n" + "="*70)
    print("ANALIZ SONUCU:")
    print("="*70)
    import json
    print(json.dumps(result, indent=2))
    print("\n[*] 30 saniye bekle - F12 ile manuel incele!")
    print("[*] Mobil numara input'unun SOLUNDAKI dropdown'ı bul!")
    time.sleep(30)
