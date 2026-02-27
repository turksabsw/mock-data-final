#!/usr/bin/env python3
"""
VFS Selector Extraction Tool
Loads VFS registration page and extracts form element selectors
"""
from camoufox.sync_api import Camoufox
import json
import time
def extract_vfs_selectors():
    """Extract form selectors from VFS Austria registration page"""
    print("[*] Camoufox başlatılıyor...")
    with Camoufox(headless=False, humanize=True) as browser:
        page = browser.new_page()
        print("[*] VFS Austria kayıt sayfasına gidiliyor...")
        page.goto("https://visa.vfsglobal.com/tur/en/aut/register")
        print("[*] Sayfa yüklendi, 5 saniye bekleniyor...")
        time.sleep(5)
        # Cookie modal'ını kapat (varsa)
        try:
            page.click("button:has-text('Accept')", timeout=3000)
            print("[+] Cookie modal kapatıldı")
            time.sleep(2)
        except:
            print("[-] Cookie modal bulunamadı veya zaten kapalı")
        print("\n[*] Form elemanları analiz ediliyor...")
        # JavaScript ile tüm input ve button elemanlarını bul
        selectors = page.evaluate("""
            () => {
                const inputs = Array.from(document.querySelectorAll('input, button'));
                return inputs.map(el => ({
                    tag: el.tagName,
                    type: el.type || 'N/A',
                    name: el.name || 'N/A',
                    id: el.id || 'N/A',
                    placeholder: el.placeholder || 'N/A',
                    className: el.className || 'N/A',
                    text: el.textContent?.trim().substring(0, 50) || 'N/A'
                }));
            }
        """)
        print("\n[+] Bulunan Form Elemanları:\n")
        for i, sel in enumerate(selectors):
            print(f"{i+1}. {sel['tag']} (type={sel['type']})")
            print(f"   name: {sel['name']}")
            print(f"   id: {sel['id']}")
            print(f"   placeholder: {sel['placeholder']}")
            print(f"   class: {sel['className'][:50]}")
            if sel['text'] != 'N/A':
                print(f"   text: {sel['text']}")
            print()
        # Screenshot al
        screenshot_path = "/home/ali/vise-os-bot/debug/screenshots/selector_extraction.png"
        page.screenshot(path=screenshot_path)
        print(f"[+] Screenshot kaydedildi: {screenshot_path}")
        # Sonuçları JSON olarak kaydet
        json_path = "/tmp/vfs_form_elements.json"
        with open(json_path, 'w') as f:
            json.dump(selectors, f, indent=2)
        print(f"[+] JSON kaydedildi: {json_path}")
        print("\n[*] 10 saniye daha beklenecek, sayfayı manuel inceleyebilirsin...")
        time.sleep(10)
if __name__ == "__main__":
    extract_vfs_selectors()
