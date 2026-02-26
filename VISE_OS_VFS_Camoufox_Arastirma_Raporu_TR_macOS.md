# Playwright ve Camoufox ile VFS Global Otomasyonu: Parmak İzi Gizleme, OTP Entegrasyonu ve Anti-Bot Atlatma (2026)

**Versiyon:** 2.0 — Cross-Platform  
**Tarih:** Şubat 2026  
**Platform:** macOS / Windows / Linux (cross-platform)  
**Ülke Kapsamı:** Türkiye çıkışlı tüm VFS Global ülkeleri

---

## Yönetici Özeti

**Camoufox, Playwright ile birlikte kullanıldığında Firefox tabanlı otomasyon için mevcut en derin parmak izi gizleme çözümünü sunmaktadır. Ancak VFS Global'in katmanlı savunmaları — Cloudflare Bot Management, e-posta OTP, çift CAPTCHA ve hesap düzeyinde yasaklar — 2026'da tam otomasyonu hareketli bir hedef haline getirmektedir.** Bu rapor; Camoufox'un mimarisini, VFS Global'in güncel koruma yığınını, eksiksiz entegrasyon kodlarını ve Mailcow + n8n üzerinden e-posta doğrulama otomasyonunu kapsamaktadır.

Pratik gerçeklik şudur: İlk Cloudflare engellerini aşmak teknik olarak mümkündür, ancak otomatik oturumları hesap yasaklarına maruz kalmadan sürdürmek; dikkatli davranışsal simülasyon, residential proxy kullanımı ve CAPTCHA çözüm servisleri gerektirmektedir.

---

## 1. Camoufox Nedir? — JavaScript Yaması Değil, C++ Düzeyinde Modifiye Firefox

Camoufox, Firefox'un **Gecko motorunun özel fork'u** üzerine inşa edilmiş açık kaynaklı bir anti-detect (tespit edilemez) tarayıcıdır. [@daijro](https://github.com/daijro/camoufox) tarafından geliştirilmiş olup, doğrudan C++ kaynak koduna uygulanan yaklaşık 50 yama ile **140'tan fazla tarayıcı özelliğini** motor seviyesinde değiştirir: Canvas, WebGL, AudioContext, navigator, screen, fontlar, WebRTC ve TLS.

### Neden JavaScript Yamalarından Farklı?

Stealth eklentileri (örn. `playwright-stealth`) JavaScript override'ları enjekte eder. Bu override'lar, prototip zinciri analizi ve yarış koşulları (race condition) ile tespit edilebilir. Camoufox ise SpiderMonkey/Gecko seviyesinde müdahale eder. Bir web sitesinin JS'i `navigator.userAgent` sorguladığında, C++ API'si sahte (spoofed) değeri **doğal (native) olarak** döndürür — JavaScript katmanında hiçbir iz kalmaz.

### Playwright Entegrasyonu: Juggler Protokolü

Python kütüphanesi (`camoufox` — PyPI'da, güncel sürüm **v0.4.11**) Playwright'ın API'sini sarar ve BrowserForge aracılığıyla istatistiksel olarak gerçekçi parmak izleri üretir. Tarayıcı ile iletişim Mozilla'nın **Juggler protokolü** üzerinden gerçekleşir — Chrome DevTools Protokolü (CDP) değil. Juggler, Playwright'ın dahili kodunu sayfa JavaScript'inden **görünmez** bir sandbox (yalıtılmış dünya) içinde çalıştırır. Sonuç:

- `navigator.webdriver = true` → **Yok**
- `window.__playwright__binding__` → **Yok**  
- CDP'ye özgü yapıtlar (artifacts) → **Yok**

### 2026 Güncel Durum

Proje, orijinal geliştiricisinin Mart 2025'te hastaneye kaldırılmasının ardından bir yıllık bakım boşluğu yaşamıştır. Geliştirme **Clover Labs** altında yeniden başlamış olup, Ocak 2026'da v146.0.1-beta.25 yayınlanmıştır (macOS-öncelikli, deneysel). Kararlı (stable) üretim dalı `releases/135` olarak kalmaktadır. [@coryking](https://github.com/coryking/camoufox) tarafından sürdürülen topluluk fork'u Firefox 142 derlemesi sunmaktadır.

Cloudflare'e karşı performans, eskiyen Firefox tabanı ve yeni keşfedilen parmak izi tutarsızlıkları nedeniyle tahminen **~%80 bypass oranına** gerilemiştir (zirvedeki ~%100'den).

### Alternatiflerle Karşılaştırma

| Özellik | Camoufox | Nodriver | SeleniumBase UC | Playwright + stealth |
|---------|----------|----------|-----------------|---------------------|
| Motor | Firefox (C++ modifiye) | Chrome (değiştirilmemiş) | Chrome (yamalı driver) | Chromium/Firefox |
| Sahtecilik derinliği | **140+ özellik, C++ seviyesi** | Yok (gerçek Chrome kimliği) | Yüzeysel driver kopuşu | JS enjeksiyonu (~20 özellik) |
| Protokol | Juggler (sandbox) | CDP (doğrudan) | WebDriver (bağlantı kes/aç) | CDP veya Juggler |
| TLS parmak izi | Gerçek Firefox JA3/JA4 | Gerçek Chrome JA3/JA4 | Gerçek Chrome JA3/JA4 | Motor bağımlı |
| CF bypass oranı (tahmini) | ~%80 | ~%90 | ~%85 | ~%60 |
| Dahili CAPTCHA | Hayır | Hayır | Evet (`uc_gui_click_captcha`) | Hayır |
| Bakım durumu (2026) | Beta, toparlanıyor | Aktif | Aktif, olgun | Aktif |

**Camoufox'un temel avantajı:** Canvas anti-fingerprinting, gürültü (noise) ekleme yerine modifiye Skia derlemesi ile alt piksel işlemeyi (subpixel rendering) değiştiren yamalı bir yapı kullanır — gürültü ekleme tespit edilebilirken bu yöntem edilemez. WebRTC IP sahteciliği de protokol seviyesinde çalışır.

**Temel dezavantajı:** Güncel beta kararsızlığı ve yalnızca Firefox desteği (bazı siteler Firefox trafiğine farklı içerik sunar veya farklı kurallar uygular).

---

## 2. VFS Global'in 2026'daki Çok Katmanlı Savunma Yığını

VFS Global, `visa.vfsglobal.com` adresinde JavaScript yoğun bir Tek Sayfa Uygulaması (SPA) olarak çalışmaktadır. URL yapısı ISO standartlarını izler:

```
https://visa.vfsglobal.com/{kaynak_ulke_alpha3}/{dil}/{hedef_ulke_alpha3}/{sayfa}
```

Türkiye çıkışlı VFS Global ülkeleri (örnek rotalar):

| Rota | Register URL | Login URL | Cloudflare Seviyesi |
|------|-------------|-----------|---------------------|
| Türkiye → İtalya (`ita`) | `.../tur/en/ita/register` | `.../tur/en/ita/login` | Yüksek (yoğun talep) |
| Türkiye → Hollanda (`nld`) | `.../tur/en/nld/register` | `.../tur/en/nld/login` | Yüksek |
| Türkiye → Avusturya (`aut`) | `.../tur/en/aut/register` | `.../tur/en/aut/login` | Orta |
| Türkiye → İsviçre (`che`) | `.../tur/en/che/register` | `.../tur/en/che/login` | Orta |
| Türkiye → Hırvatistan (`hrv`) | `.../tur/en/hrv/register` | `.../tur/en/hrv/login` | Düşük (MVP adayı) |
| Türkiye → Belçika (`bel`) | `.../tur/en/bel/register` | `.../tur/en/bel/login` | Orta |

> **Not:** Almanya (`deu`) artık VFS değil → Auslandsportal. Fransa (`fra`) ve İngiltere (`gbr`) → TLScontact. Bu ülkeler farklı adaptörler gerektirir.

Bu URL'lere yapılan doğrudan HTTP istekleri **HTTP 403** döndürür — Cloudflare, tarayıcı olmayan istemcileri anında engellemektedir. SPA, tam tarayıcı işleme (rendering) olmaksızın yalnızca "Loading" veya "This website requires JavaScript" mesajını döndürür — statik kazıma (scraping) kesinlikle mümkün değildir.

### Beş Koruma Katmanı

**Katman 1 — Cloudflare Bot Management:** Her isteği 1–99 arasında puanlar. Makine öğrenmesi modelleri; JA3/JA4 TLS parmak izlerini, HTTP/2 SETTINGS çerçevelerini, JavaScript tarayıcı sondalarını ve davranışsal sinyalleri kullanır. 30'un altındaki puanlar challenge veya blok tetikler. Cloudflare ayrıca **User-Agent/JA3 korelasyonu** yapar — başlıklar Chrome iddia edip TLS parmak izi Python `requests` eşleşirse anında engel.

**Katman 2 — Cloudflare Waiting Room:** Yoğun talep dönemlerinde (randevu slotlarının açıldığı anlar) devreye girer, kullanıcıları kuyruğa alır ve bekleme süresinde ek davranışsal analiz uygular.

**Katman 3 — Çift CAPTCHA Doğrulama:** Hem giriş sayfasında hem de randevu süreci ortasında challenge çözdürür. Kaynaklar, rotaya ve zamana göre reCAPTCHA ve Cloudflare Managed Challenge karışımı olduğunu bildirmektedir.

**Katman 4 — E-posta OTP Kimlik Doğrulaması:** Her girişte kayıtlı e-postaya tek kullanımlık şifre gönderir. OTP yaklaşık **60–90 saniye** geçerlidir ve giriş alanı daha erken kapanabilir. Birden fazla başarısız OTP girişi **24 saatlik hesap kilidi** tetikler.

**Katman 5 — Hesap Düzeyinde Yasaklar (Account-Level Bans):** En önemli güncel ekleme. VFS Global artık otomatik davranış kalıpları sergileyen hesapları **kalıcı olarak** yasaklamaktadır. Bu, IP engellenmesinden farklıdır ve proxy değişikliğinden bağımsız olarak devam eder. GitHub'daki `barrriwa/vfsauto` projesi tam olarak bu nedenle terk edilmiştir: "VFSGlobal hesap yasakları ekledi, dolayısıyla bu script artık işe yaramıyor."

### Tespit Mekanizmalarının Evrimi

| Dönem | Koruma |
|-------|--------|
| 2023 öncesi | Temel Cloudflare + CAPTCHA (Selenium UC mode genelde yeterliydi) |
| 2023–2024 | Waiting Room, çift CAPTCHA kontrol noktaları, ikincil sayfalarda Selenium tespiti |
| 2024–2025 | Hesap düzeyinde yasaklar, zorunlu e-posta OTP |
| 2025–2026 | Yapay zeka destekli müşteriye özel baseline tespiti, 50+ yeni HTTP/2 parmak izi buluşsalı (heuristic), gelişmiş residential proxy ağ tespiti, JA3'ü tamamlayan JA4 parmak izi |

---

## 3. Camoufox Kurulumu ve Playwright ile Başlatma (Cross-Platform)

### 3.1 Ön Gereksinimler

**macOS:**
```bash
brew install python@3.11
python3.11 -m venv vise-env
source vise-env/bin/activate
```
> macOS'ta Linux'taki `libgtk-3-0`, `libx11-xcb1`, `libasound2` gibi sistem bağımlılıkları gerekmez. Camoufox, macOS'ta native Cocoa/AppKit çerçevesini kullanır.

**Windows:**
```powershell
# python.org'dan Python 3.11+ installer indir ve kur
python -m venv vise-env
vise-env\Scripts\activate
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv xvfb libgtk-3-0 libx11-xcb1 libasound2
python3.11 -m venv vise-env
source vise-env/bin/activate
```

### 3.2 Camoufox Kurulumu (Tüm Platformlar)

```bash
# Ana paket + GeoIP veritabanı (~50MB)
pip install -U "camoufox[geoip]"

# Özel Firefox ikili dosyasını indir (~300-400MB)
# Platform otomatik algılanır: macOS ARM64/x86_64, Windows x64, Linux x64
python -m camoufox fetch
```

> **Apple Silicon (M1/M2/M3/M4) Notu:** `camoufox fetch` ARM64 ikiliyi otomatik indirir.  
> **macOS Gatekeeper:** İlk çalıştırmada engellenebilir → System Preferences → Privacy & Security → Allow Anyway

### 3.3 Headless Modları (Platforma Göre)

| Mod | Parametre | macOS | Windows | Linux |
|-----|-----------|-------|---------|-------|
| Görünür (GUI) | `headless=False` | ✅ Önerilir | ✅ Önerilir | GUI varsa çalışır |
| Virtual headless | `headless="virtual"` | Native offscreen | Xvfb gerekmez | **Xvfb gerekli** |
| True headless | `headless=True` | ⚠️ Tespit riski | ⚠️ Tespit riski | ⚠️ Tespit riski |

> **Stealth tavsiyesi:** macOS ve Windows'ta `headless=False` en güvenli. Linux sunucularda `headless="virtual"` + Xvfb kullanın. `headless=True` hiçbir platformda önerilmez — parmak izi tutarsızlıkları oluşturur.

### 3.4 Cross-Platform Algılama ve Parmak İzi Rotasyonu

Bot çalışırken iki farklı OS kavramı vardır:
- **Çalışma OS'u:** Botun fiilen çalıştığı makine (macOS, Windows, Linux)
- **Parmak izi OS'u:** Camoufox'un VFS'e "Ben bu cihazdan geliyorum" diye gösterdiği sahte kimlik

Bu ikisi **bağımsızdır** — Linux sunucuda çalışıp kendini Windows kullanıcısı olarak gösterebilirsiniz.

```python
import platform, os, random

def platform_ayarlari_al():
    """Çalışma ortamını algıla, platform-spesifik ayarları belirle."""
    sistem = platform.system()  # "Darwin" (macOS), "Windows", "Linux"
    
    ayarlar = {"sistem": sistem, "headless": False, "profile_dir": "", "debug_dir": ""}
    
    if sistem == "Darwin":  # macOS
        ayarlar["headless"] = False
        ayarlar["profile_dir"] = os.path.expanduser("~/Library/Application Support/VISE-OS/vfs-profile")
        ayarlar["debug_dir"] = os.path.expanduser("~/vise-os-bot/debug")
    elif sistem == "Windows":
        ayarlar["headless"] = False
        ayarlar["profile_dir"] = os.path.join(os.environ.get("APPDATA", ""), "VISE-OS", "vfs-profile")
        ayarlar["debug_dir"] = os.path.join(os.environ.get("USERPROFILE", ""), "vise-os-bot", "debug")
    elif sistem == "Linux":
        ayarlar["headless"] = "virtual"  # Xvfb gerekli
        ayarlar["profile_dir"] = os.path.expanduser("~/.config/vise-os/vfs-profile")
        ayarlar["debug_dir"] = os.path.expanduser("~/vise-os-bot/debug")
    
    os.makedirs(ayarlar["profile_dir"], exist_ok=True)
    os.makedirs(ayarlar["debug_dir"], exist_ok=True)
    return ayarlar

def parmak_izi_os_sec():
    """VFS'e gösterilecek sahte OS'u Türkiye kullanıcı dağılımına göre seç."""
    return random.choices(["windows", "macos", "linux"], weights=[75, 17, 8], k=1)[0]
```

### 3.5 Temel Başlatma Kalıpları

#### Senkron Kullanım (Basit Test İçin)

```python
from camoufox.sync_api import Camoufox
import time, random

p = platform_ayarlari_al()
secilen_os = parmak_izi_os_sec()
ulke_kodu = "aut"  # Parametrik — düşük korumalı ülkeyle başla

with Camoufox(
    headless=p["headless"],          # Platform'a göre otomatik
    humanize=True,                   # İnsan benzeri imleç hareketi
    os=secilen_os,                   # Her oturumda farklı parmak izi OS'u
    geoip=True,                      # Proxy IP'den otomatik timezone/locale
    proxy={
        "server": "http://residential-proxy:8080",
        "username": "kullanici",
        "password": "sifre"
    },
    disable_coop=True,               # Cloudflare Turnstile iframe erişimi için zorunlu
) as browser:
    page = browser.new_page()
    page.goto(f"https://visa.vfsglobal.com/tur/en/{ulke_kodu}/login")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(random.randint(5000, 10000))
    
    print(f"Platform: {p['sistem']} | Parmak izi OS: {secilen_os} | Ülke: {ulke_kodu}")
    print(f"Sayfa başlığı: {page.title()}")
```

#### Asenkron Kullanım (Üretim Ortamı İçin)

```python
import asyncio, random
from camoufox.async_api import AsyncCamoufox

async def main():
    p = platform_ayarlari_al()
    ulke_kodu = "aut"
    
    async with AsyncCamoufox(
        headless=p["headless"],      # Platform'a göre otomatik
        humanize=True,
        os=parmak_izi_os_sec(),      # Rastgele parmak izi
        geoip=True,
        proxy={"server": "http://proxy:8080", "username": "u", "password": "p"},
        disable_coop=True,
    ) as browser:
        page = await browser.new_page()
        await page.goto(f"https://visa.vfsglobal.com/tur/en/{ulke_kodu}/login")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(random.randint(5000, 10000))
        print("Sayfa başlığı:", await page.title())

asyncio.run(main())
```

#### Kalıcı Oturum (Cookie Tekrar Kullanımı İçin)

```python
from camoufox.sync_api import Camoufox
import os

p = platform_ayarlari_al()
ulke_kodu = "aut"
# Ülke bazlı ayrı profil dizini — platform otomatik algılanır
profile_dir = os.path.join(p["profile_dir"], ulke_kodu)
os.makedirs(profile_dir, exist_ok=True)

with Camoufox(
    persistent_context=True,
    user_data_dir=profile_dir,       # Cross-platform yol
    headless=p["headless"],          # Platform'a göre otomatik
    os=parmak_izi_os_sec(),          # Rastgele parmak izi
    humanize=True,
    disable_coop=True,
) as context:
    page = context.new_page()
    page.goto(f"https://visa.vfsglobal.com/tur/en/{ulke_kodu}/login")
    page.wait_for_load_state("networkidle")
    # Cloudflare çerezleri profile_dir içinde saklanır
```

### 3.6 Tüm Konfigürasyon Parametreleri

| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| `os` | `str` veya `list` | Parmak izi OS'u: `parmak_izi_os_sec()` ile rastgele seç — sabit yazma |
| `humanize` | `bool` veya `float` | İnsan benzeri imleç; float değer maks hareket süresini belirler (saniye) |
| `geoip` | `bool` veya `str` | Proxy IP'den otomatik timezone/locale; veya belirli IP geçilebilir |
| `proxy` | `dict` | `{"server": ..., "username": ..., "password": ...}` |
| `headless` | `bool` veya `"virtual"` | `platform_ayarlari_al()["headless"]` ile otomatik belirle |
| `disable_coop` | `bool` | Cross-origin iframe erişimi için zorunlu (Turnstile) |
| `persistent_context` | `bool` | Çalıştırmalar arası çerez/oturum kaydet |
| `user_data_dir` | `str` | `platform_ayarlari_al()["profile_dir"]` ile cross-platform yol kullan |
| `block_images` | `bool` | Bant genişliği tasarrufu |
| `block_webrtc` | `bool` | WebRTC IP sızıntısını engelle |
| `addons` | `list[str]` | Firefox `.xpi` eklenti dosya yolları |

---

## 4. VFS Global Register (Kayıt) ve Login (Giriş) Akışı

### 4.1 Register Akışı

```
[1] Sayfaya Git → https://visa.vfsglobal.com/tur/en/{ULKE_KODU}/register
[2] Cloudflare Challenge Bekle (5-15 sn)
[3] Kayıt Formunu Doldur:
    ├── Ad (First Name)
    ├── Soyad (Last Name)
    ├── E-posta (Email) → Mailcow adresimiz
    ├── Şifre (Password)
    ├── Şifre Tekrar (Confirm Password)
    ├── Telefon Numarası (opsiyonel)
    └── Kullanım Koşulları Onayı (Terms & Conditions checkbox)
[4] CAPTCHA Çöz (Turnstile veya reCAPTCHA — ülkeye göre değişir)
[5] Formu Gönder
[6] E-posta Doğrulama Bekle → Mailcow + n8n otomasyonu
[7] Doğrulama Linkine Tıkla / OTP Gir
[8] Kayıt Tamamlandı ✓
```

### 4.2 Login Akışı

```
[1] Sayfaya Git → https://visa.vfsglobal.com/tur/en/{ULKE_KODU}/login
[2] Cloudflare Challenge Bekle (5-15 sn)
[3] Kimlik Bilgilerini Gir:
    ├── E-posta (Email)
    └── Şifre (Password)
[4] CAPTCHA Çöz
[5] Giriş Yap Butonuna Tıkla
[6] E-posta OTP Bekle → Mailcow'dan IMAP ile çek
[7] OTP Kodunu Gir (60-90 sn zaman penceresi!)
[8] Giriş Tamamlandı ✓ → Dashboard sayfası
```

### 4.3 Register Otomasyonu — Tam Kod Örneği (Cross-Platform)

```python
from camoufox.sync_api import Camoufox
import time, random, os
from dotenv import load_dotenv

load_dotenv()  # .env dosyasından oku

# === YAPILANDIRMA (.env'den) ===
ULKE_KODU = os.getenv("VFS_DEFAULT_COUNTRY", "aut")
VFS_REGISTER_URL = f"https://visa.vfsglobal.com/tur/en/{ULKE_KODU}/register"
EMAIL = os.getenv("VFS_EMAIL")
PASSWORD = os.getenv("VFS_PASSWORD")
FIRST_NAME = os.getenv("VFS_FIRST_NAME")
LAST_NAME = os.getenv("VFS_LAST_NAME")

# Cross-platform profil dizini
p = platform_ayarlari_al()
PROFILE_DIR = os.path.join(p["profile_dir"], f"{ULKE_KODU}-register")
os.makedirs(PROFILE_DIR, exist_ok=True)

def insan_gibi_yaz(page, selector, metin):
    """Her karakter arasında rastgele gecikme ile yaz."""
    element = page.locator(selector)
    element.click()
    time.sleep(random.uniform(0.3, 0.8))
    for karakter in metin:
        element.type(karakter, delay=random.randint(50, 150))
        time.sleep(random.uniform(0.02, 0.08))

def rastgele_bekle(min_sn=1.0, max_sn=3.0):
    time.sleep(random.uniform(min_sn, max_sn))

# === ANA AKIŞ ===
secilen_os = parmak_izi_os_sec()
print(f"[SİSTEM] Platform: {p['sistem']} | Parmak izi OS: {secilen_os} | Ülke: {ULKE_KODU}")

with Camoufox(
    headless=p["headless"],          # Platform'a göre otomatik
    humanize=True,
    os=secilen_os,                   # Rastgele parmak izi OS
    geoip=True,
    persistent_context=True,
    user_data_dir=PROFILE_DIR,       # Cross-platform yol
    disable_coop=True,
) as context:
    page = context.new_page()
    page.set_default_timeout(60000)
    
    # ---- ADIM 1: Register sayfasına git ----
    print(f"[1/8] Register sayfasına gidiliyor: {VFS_REGISTER_URL}")
    page.goto(VFS_REGISTER_URL, wait_until="networkidle")
    
    # ---- ADIM 2: Cloudflare challenge bekleme ----
    print("[2/8] Cloudflare challenge bekleniyor...")
    page.wait_for_timeout(random.randint(5000, 12000))
    
    try:
        page.wait_for_selector("input[type='email'], input[name='email'], #email", timeout=30000)
        print("  ✓ Cloudflare geçildi, form görünür.")
    except:
        print("  ✗ Cloudflare challenge geçilemedi!")
        ss_path = os.path.join(p["debug_dir"], "screenshots", "vfs_cf_fail.png")
        os.makedirs(os.path.dirname(ss_path), exist_ok=True)
        page.screenshot(path=ss_path)
        print(f"  Screenshot: {ss_path}")
        raise Exception("Cloudflare engeli aşılamadı")

    # ---- ADIM 3: Formu doldur ----
    print("[3/8] Kayıt formu dolduruluyor...")
    insan_gibi_yaz(page, "input[name='firstName'], input[id='firstName'], input[placeholder*='First']", FIRST_NAME)
    rastgele_bekle(0.5, 1.5)
    insan_gibi_yaz(page, "input[name='lastName'], input[id='lastName'], input[placeholder*='Last']", LAST_NAME)
    rastgele_bekle(0.5, 1.5)
    insan_gibi_yaz(page, "input[type='email'], input[name='email']", EMAIL)
    rastgele_bekle(0.8, 2.0)
    
    sifre_alanlari = page.locator("input[type='password']")
    sifre_alanlari.nth(0).click()
    rastgele_bekle(0.3, 0.8)
    sifre_alanlari.nth(0).type(PASSWORD, delay=random.randint(50, 120))
    rastgele_bekle(0.5, 1.5)
    if sifre_alanlari.count() > 1:
        sifre_alanlari.nth(1).click()
        rastgele_bekle(0.3, 0.8)
        sifre_alanlari.nth(1).type(PASSWORD, delay=random.randint(50, 120))
    rastgele_bekle(0.8, 2.0)
    
    print("[4/8] Kullanım koşulları onaylanıyor...")
    checkbox = page.locator("input[type='checkbox']").first
    if not checkbox.is_checked():
        checkbox.click()
    rastgele_bekle(1.0, 2.5)
    
    print("[5/8] CAPTCHA bekleniyor...")
    page.wait_for_timeout(random.randint(3000, 6000))
    
    print("[6/8] Form gönderiliyor...")
    page.locator("button[type='submit'], input[type='submit']").click()
    page.wait_for_load_state("networkidle")
    rastgele_bekle(2.0, 4.0)
    
    print("[7/8] E-posta doğrulama bekleniyor (n8n otomasyonu)...")
    page.wait_for_timeout(30000)
    
    print("[8/8] Kayıt durumu kontrol ediliyor...")
    current_url = page.url
    if "login" in current_url.lower() or "success" in page.content().lower():
        print("  ✓ KAYIT BAŞARILI!")
    else:
        ss_path = os.path.join(p["debug_dir"], "screenshots", "vfs_register_result.png")
        page.screenshot(path=ss_path)
        print(f"  ? Sonuç belirsiz. Screenshot: {ss_path}")
    print(f"  Son URL: {current_url}")
```

### 4.4 Login Otomasyonu — OTP Entegrasyonlu Tam Kod (Cross-Platform)

```python
from camoufox.sync_api import Camoufox
import imaplib, email, re, time, random, os
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# === OTP OKUYUCU SINIFI ===
class OTPOkuyucu:
    """Mailcow IMAP üzerinden VFS Global OTP kodunu okur."""
    
    def __init__(self, host, kullanici, sifre, port=993):
        self.imap = imaplib.IMAP4_SSL(host, port)
        self.imap.login(kullanici, sifre)
    
    def otp_bekle(self, gonderici_filtre="vfsglobal", zaman_asimi=90, yoklama_araligi=3):
        baslangic = time.time()
        while time.time() - baslangic < zaman_asimi:
            self.imap.select("INBOX")
            _, mesajlar = self.imap.search(None, "UNSEEN")
            for eid in reversed(mesajlar[0].split()):
                _, veri = self.imap.fetch(eid, "(RFC822)")
                msg = email.message_from_bytes(veri[0][1])
                if gonderici_filtre.lower() in msg.get("From", "").lower():
                    govde = self._govde_al(msg)
                    otp = re.search(r'\b(\d{4,6})\b', govde)
                    if otp:
                        self.imap.store(eid, "+FLAGS", "\\Seen")
                        return otp.group(1)
            time.sleep(yoklama_araligi)
        return None
    
    def _govde_al(self, msg):
        if msg.is_multipart():
            for parca in msg.walk():
                if parca.get_content_type() == "text/plain":
                    return parca.get_payload(decode=True).decode("utf-8", errors="replace")
                elif parca.get_content_type() == "text/html":
                    html = parca.get_payload(decode=True).decode("utf-8", errors="replace")
                    return BeautifulSoup(html, "html.parser").get_text()
        return msg.get_payload(decode=True).decode("utf-8", errors="replace")
    
    def kapat(self):
        try: self.imap.logout()
        except: pass

# === YAPILANDIRMA (.env'den) ===
ULKE_KODU = os.getenv("VFS_DEFAULT_COUNTRY", "aut")
VFS_LOGIN_URL = f"https://visa.vfsglobal.com/tur/en/{ULKE_KODU}/login"
EMAIL = os.getenv("VFS_EMAIL")
PASSWORD = os.getenv("VFS_PASSWORD")

p = platform_ayarlari_al()
PROFILE_DIR = os.path.join(p["profile_dir"], f"{ULKE_KODU}-login")
os.makedirs(PROFILE_DIR, exist_ok=True)

otp_okuyucu = OTPOkuyucu(os.getenv("MAILCOW_HOST"), os.getenv("MAILCOW_USER"), os.getenv("MAILCOW_PASS"))

try:
    secilen_os = parmak_izi_os_sec()
    print(f"[SİSTEM] Platform: {p['sistem']} | Parmak izi OS: {secilen_os} | Ülke: {ULKE_KODU}")
    
    with Camoufox(
        headless=p["headless"],
        humanize=True,
        os=secilen_os,               # Rastgele parmak izi OS
        geoip=True,
        persistent_context=True,
        user_data_dir=PROFILE_DIR,   # Cross-platform yol
        disable_coop=True,
    ) as context:
        page = context.new_page()
        page.set_default_timeout(60000)
        
        print(f"[1/8] Login sayfasına gidiliyor: {VFS_LOGIN_URL}")
        page.goto(VFS_LOGIN_URL, wait_until="networkidle")
        
        print("[2/8] Cloudflare challenge bekleniyor...")
        page.wait_for_timeout(random.randint(5000, 12000))
        
        try:
            page.wait_for_selector("input[type='email'], input[name='email']", timeout=30000)
            print("  ✓ Cloudflare geçildi.")
        except:
            ss = os.path.join(p["debug_dir"], "screenshots", "vfs_cf_login_fail.png")
            os.makedirs(os.path.dirname(ss), exist_ok=True)
            page.screenshot(path=ss)
            raise Exception(f"Cloudflare engeli! Screenshot: {ss}")
        
        print("[3/8] E-posta giriliyor...")
        email_input = page.locator("input[type='email'], input[name='email']")
        email_input.click()
        time.sleep(random.uniform(0.5, 1.2))
        email_input.fill(EMAIL)
        time.sleep(random.uniform(0.8, 2.0))
        
        print("[4/8] Şifre giriliyor...")
        pass_input = page.locator("input[type='password']")
        pass_input.click()
        time.sleep(random.uniform(0.5, 1.2))
        pass_input.fill(PASSWORD)
        time.sleep(random.uniform(1.0, 3.0))
        
        print("[5/8] CAPTCHA bekleniyor...")
        page.wait_for_timeout(random.randint(2000, 5000))
        
        print("[6/8] Giriş yapılıyor...")
        page.locator("button[type='submit']").click()
        page.wait_for_load_state("networkidle")
        time.sleep(random.uniform(2.0, 4.0))
        
        print("[7/8] OTP alanı bekleniyor...")
        try:
            otp_alani = page.wait_for_selector(
                "input[name='otp'], input[placeholder*='OTP'], input[placeholder*='code']", timeout=30000)
            print("  ✓ OTP alanı göründü. Mailcow'dan OTP çekiliyor...")
            
            otp_kodu = otp_okuyucu.otp_bekle(gonderici_filtre="vfsglobal", zaman_asimi=90)
            if otp_kodu:
                print(f"  ✓ OTP kodu alındı: {otp_kodu}")
                otp_alani.click()
                time.sleep(random.uniform(0.3, 0.8))
                otp_alani.fill(otp_kodu)
                time.sleep(random.uniform(0.5, 1.5))
                page.locator("button[type='submit']").click()
                page.wait_for_load_state("networkidle")
                time.sleep(random.uniform(2.0, 4.0))
            else:
                print("  ✗ OTP kodu alınamadı! Zaman aşımı.")
                ss = os.path.join(p["debug_dir"], "screenshots", "vfs_otp_timeout.png")
                page.screenshot(path=ss)
        except Exception as e:
            print(f"  OTP alanı bulunamadı veya hata: {e}")
        
        print("[8/8] Giriş durumu kontrol ediliyor...")
        current_url = page.url
        if "dashboard" in current_url.lower() or "appointment" in current_url.lower():
            print("\n  ═══════════════════════════════════")
            print("  ✓✓✓ GİRİŞ BAŞARILI! Dashboard'a ulaşıldı.")
            print("  ═══════════════════════════════════")
        else:
            ss = os.path.join(p["debug_dir"], "screenshots", "vfs_login_result.png")
            page.screenshot(path=ss)
            print(f"  ? Sonuç belirsiz. URL: {current_url} | Screenshot: {ss}")

finally:
    otp_okuyucu.kapat()
```

---

## 5. Mailcow + n8n E-posta Doğrulama Otomasyonu

### 5.1 Sistem Mimarisi

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  VFS Global  │───►│   Mailcow    │───►│     n8n      │
│  (e-posta    │    │  (IMAP/SMTP) │    │  (otomasyon) │
│   gönderir)  │    │              │    │              │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                         ┌─────────────────────┤
                         ▼                     ▼
                  ┌──────────────┐    ┌──────────────┐
                  │ Link Tıklama │    │ OTP Kodu Bot │
                  │ (HTTP GET)   │    │ (API → Bot)  │
                  └──────────────┘    └──────────────┘
```

### 5.2 Mailcow IMAP Bağlantı Ayarları

| Parametre | Değer |
|-----------|-------|
| Sunucu | `mail.atonota.com` (kendi alan adınız) |
| Port | **993** (SSL/TLS) |
| Şifreleme | SSL/TLS (STARTTLS değil) |
| Kullanıcı Adı | Tam e-posta adresi (ör. `suna2001@atonota.com`) |
| Şifre | Mailbox şifresi |
| Protokol | IMAP4 (IDLE desteği var — push bildirim) |

### 5.3 n8n İş Akışı: Doğrulama Linki Otomatik Tıklama

#### n8n IMAP Tetikleyici Ayarları

```json
{
  "user": "suna2001@atonota.com",
  "password": "MailKutusuSifresi",
  "host": "mail.atonota.com",
  "port": 993,
  "secure": true
}
```

#### n8n Code Node: Link/OTP Çıkarma

```javascript
const html = items[0].json.textHtml || '';
const text = items[0].json.textPlain || '';
const otpEslesmesi = text.match(/\b(\d{4,6})\b/);
const otp = otpEslesmesi ? otpEslesmesi[1] : null;
const linkRegex = /href=["'](https?:\/\/[^"']*(?:verify|confirm|token|activate)[^"']*)/gi;
const linkler = [];
let m;
while ((m = linkRegex.exec(html)) !== null) linkler.push(m[1].replace(/&amp;/g, '&'));
return [{ json: { otp, dogrulamaLinki: linkler[0] || null, tumLinkler: linkler } }];
```

### 5.4 Doğrudan Python IMAP Entegrasyonu (Daha Hızlı)

```python
import imaplib, email, re, time
from bs4 import BeautifulSoup

class MailcowDogrulamaci:
    """Mailcow'dan VFS doğrulama linkini veya OTP'yi hızlıca çeker."""
    
    def __init__(self, host, kullanici, sifre, port=993):
        self.host, self.kullanici, self.sifre, self.port = host, kullanici, sifre, port
    
    def dogrulama_linki_bekle(self, gonderici="vfsglobal", zaman_asimi=120, yoklama=3):
        imap = imaplib.IMAP4_SSL(self.host, self.port)
        imap.login(self.kullanici, self.sifre)
        baslangic = time.time()
        try:
            while time.time() - baslangic < zaman_asimi:
                imap.select("INBOX")
                _, mesajlar = imap.search(None, "UNSEEN")
                for eid in reversed(mesajlar[0].split()):
                    _, veri = imap.fetch(eid, "(RFC822)")
                    msg = email.message_from_bytes(veri[0][1])
                    if gonderici.lower() not in msg.get("From", "").lower():
                        continue
                    govde_html = self._html_govde_al(msg)
                    if govde_html:
                        soup = BeautifulSoup(govde_html, "html.parser")
                        for a in soup.find_all("a", href=True):
                            if any(kw in a["href"].lower() for kw in ["verify","confirm","activate","token"]):
                                imap.store(eid, "+FLAGS", "\\Seen")
                                return a["href"]
                time.sleep(yoklama)
        finally:
            imap.logout()
        return None
    
    def _html_govde_al(self, msg):
        if msg.is_multipart():
            for p in msg.walk():
                if p.get_content_type() == "text/html":
                    return p.get_payload(decode=True).decode("utf-8", errors="replace")
        elif msg.get_content_type() == "text/html":
            return msg.get_payload(decode=True).decode("utf-8", errors="replace")
        return None
```

---

## 6. Cloudflare Turnstile Çözüm Stratejileri

### 6.1 Yöntem 1: Camoufox humanize ile Otomatik Geçiş

```python
from camoufox.sync_api import Camoufox

p = platform_ayarlari_al()
ulke_kodu = "aut"

with Camoufox(
    disable_coop=True, humanize=True,
    headless=p["headless"],          # Platform'a göre otomatik
    os=parmak_izi_os_sec()           # Rastgele parmak izi
) as browser:
    page = browser.new_page()
    page.goto(f"https://visa.vfsglobal.com/tur/en/{ulke_kodu}/login")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(5000)
    
    turnstile_frame = page.frame_locator("iframe[src*='challenges.cloudflare.com']")
    if turnstile_frame:
        turnstile_frame.locator("input[type='checkbox']").click()
```

### 6.2 Yöntem 2: Harici CAPTCHA Çözücü (CapSolver API)

```python
import requests, time

def turnstile_coz(site_key, sayfa_url, capsolver_api_key):
    """CapSolver API ile Cloudflare Turnstile token'ı al."""
    yanit = requests.post("https://api.capsolver.com/createTask", json={
        "appId": capsolver_api_key,
        "task": {"type": "AntiTurnstileTaskProxyLess", "websiteURL": sayfa_url, "websiteKey": site_key}
    })
    gorev_id = yanit.json().get("taskId")
    for _ in range(20):
        time.sleep(2)
        sonuc = requests.post("https://api.capsolver.com/getTaskResult", json={"appId": capsolver_api_key, "taskId": gorev_id})
        if sonuc.json().get("status") == "ready":
            return sonuc.json()["solution"]["token"]
    return None
```

### 6.3 Yöntem 3: Turnstile'ı Hiç Tetiklememek (İdeal Senaryo)

En iyi strateji CAPTCHA'yı çözmek değil, hiç tetiklememektir:

- Yüksek kaliteli **residential/mobile proxy** kullan
- `geoip=True` ile proxy IP'sine uygun timezone/locale ayarla
- `humanize=True` ile doğal fare hareketi
- Önceki oturumun `cf_clearance` çerezini `persistent_context` ile koru
- İstekler arası **2-8 saniye** rastgele bekleme

---

## 7. Pratik Dikkat Noktaları ve Bilinen Sınırlamalar

### Residential Proxy Zorunludur
Veri merkezi (datacenter) IP'leri Cloudflare'ın proxy tespiti tarafından anında işaretlenir. Cloudflare 2025'te tek bir haftada proxy ağlarından 11 milyar istek tespit etmiştir — residential IP'ler bile artan incelemeyle karşı karşıyadır.

### Hesap Yasakları En Zor Engel
Hesap yasakları kayıtlı hesabı kalıcı olarak yok eder. Yasakları tetikleyen davranış kalıpları: hızlı sayfa geçişleri, tutarlı zamanlama aralıkları ve tekrarlayan slot kontrol döngüleri.

### OTP Zamanlama Penceresi Dardır
Kodlar 60-90 saniye geçerli. E-postadan tarayıcıya pipeline **30 saniyenin altında** tamamlanmalı. Doğrudan Python IMAP (her 3 sn'de yoklama) n8n'den daha güvenilirdir.

### Camoufox 2026 Kararlılığı Belirsiz
v146 beta'da kırıcı değişiklikler var, kararlı v135 dalı eski Firefox. Topluluk fork'u (Firefox 142) veya `releases/135` önerilir.

### Platforma Özgü Dikkat Noktaları

| Konu | macOS | Windows | Linux |
|------|-------|---------|-------|
| **İlk çalıştırma engeli** | Gatekeeper → Privacy & Security → Allow | Windows Defender uyarı verebilir → Allow | Yok |
| **Apple Silicon / ARM** | ARM64 native (yeni sürümler) | N/A | ARM64 deneysel |
| **Enerji tasarrufu** | `caffeinate -i python script.py` | Güç planını "Yüksek Performans" yap | `systemd-inhibit` veya `caffeine` |
| **Profil dizini** | `~/Library/Application Support/VISE-OS/` | `%APPDATA%\VISE-OS\` | `~/.config/vise-os/` |
| **Headless modu** | `False` önerilir | `False` önerilir | `"virtual"` + Xvfb |
| **Ekran izni** | Ekran kaydı izni gerekebilir | Yok | Xvfb kurulumu gerekli |

---

## 8. Sonuç ve Stratejik Değerlendirme

**Camoufox + Playwright + Mailcow OTP otomasyonu** teknik yığını, VFS Global'in tespit katmanlarının her birini farklı şekilde ele alır:

| Katman | Çözüm |
|--------|-------|
| TLS / Tarayıcı Parmak İzi | Camoufox C++ seviyesi sahtecilik + her oturumda rastgele OS |
| CDP Tespiti | Juggler protokolü (CDP değil) |
| IP / Coğrafi Konum Uyumsuzluğu | Residential proxy + `geoip=True` |
| CAPTCHA (Turnstile) | `humanize=True` + CapSolver yedek |
| E-posta OTP | Doğrudan IMAP yoklama (3 sn aralık) |
| Hesap Yasakları | **Çözülmemiş** — davranışsal simülasyon kalitesi belirleyici |

Bu araştırmadan çıkan en kritik içgörü: **VFS Global'in hesap düzeyinde yasaklara geçişi, Cloudflare'ın teknik bypass'ını gerekli ama yetersiz kılmıştır.** Artık otomatik bir oturumun ilk girişten sonra hayatta kalıp kalamayacağını belirleyen şey, davranışsal simülasyon kalitesidir.

---

## Ek: Hızlı Başvuru — Platform Bazlı Kurulum Komutları

**macOS:**
```bash
brew install python@3.11
python3.11 -m venv ~/vise-env && source ~/vise-env/bin/activate
pip install -U "camoufox[geoip]" beautifulsoup4 requests python-dotenv
python -m camoufox fetch
caffeinate -i python main.py test -c aut   # Enerji tasarrufu engelle
```

**Windows (PowerShell):**
```powershell
# Python 3.11+ python.org'dan kur
python -m venv C:\vise-env
C:\vise-env\Scripts\activate
pip install -U "camoufox[geoip]" beautifulsoup4 requests python-dotenv
python -m camoufox fetch
python main.py test -c aut
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install -y python3.11 python3.11-venv xvfb libgtk-3-0 libx11-xcb1 libasound2
python3.11 -m venv ~/vise-env && source ~/vise-env/bin/activate
pip install -U "camoufox[geoip]" beautifulsoup4 requests python-dotenv
python -m camoufox fetch
xvfb-run python main.py test -c aut       # Xvfb ile çalıştır
```
