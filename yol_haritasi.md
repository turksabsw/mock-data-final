# VISE OS — VFS Global Register & Login Bot: Yol Haritası

**Hedef:** Playwright + Camoufox kullanarak VFS Global üzerinden register olup login yapabilen bir bot geliştirmek  
**Platform:** Cross-platform (macOS, Windows, Linux)  
**Ülke:** Türkiye çıkışlı tüm VFS Global ülkeleri (MVP: düşük korumalı ülke ile başla)  
**Yaklaşım:** Vibe Coding — adım adım, test ederek ilerle  
**Tarih:** Şubat 2026

---

## ÖN KOŞULLAR (Faz 0 — Ortam Hazırlığı)

### 0.1 Geliştirme Ortamı (Cross-Platform)

**macOS:**
- [ ] Python 3.11+ kurulumu (`brew install python@3.11`)
- [ ] Sanal ortam: `python3.11 -m venv ~/vise-env && source ~/vise-env/bin/activate`

**Windows:**
- [ ] Python 3.11+ kurulumu (python.org'dan installer)
- [ ] Sanal ortam: `python -m venv C:\vise-env && C:\vise-env\Scripts\activate`

**Linux:**
- [ ] Python 3.11+: `sudo apt install python3.11 python3.11-venv`
- [ ] Xvfb (headless GUI): `sudo apt install -y xvfb libgtk-3-0 libx11-xcb1 libasound2`
- [ ] Sanal ortam: `python3.11 -m venv ~/vise-env && source ~/vise-env/bin/activate`

### 0.2 Bağımlılıklar (Tüm platformlar)
- [ ] `pip install -U "camoufox[geoip]"`
- [ ] `pip install beautifulsoup4 requests python-dotenv`
- [ ] `python -m camoufox fetch` (Firefox ikili ~400MB — platform otomatik algılanır)
- [ ] macOS: Gatekeeper izni kontrolü (ilk seferde gerekebilir)

### 0.3 Mailcow Hazırlığı
- [ ] Mailcow mail server çalışır durumda (atonota.com)
- [ ] Test mail adresi oluşturulmuş (ör. `test001@atonota.com`)
- [ ] n8n iş akışı aktif: gelen doğrulama maillerine otomatik tıklama
- [ ] IMAP bağlantısı test edilmiş (Python ile bağlan, mail oku)

### 0.4 Ağ Altyapısı
- [ ] Residential proxy hesabı (Bright Data, Oxylabs veya benzeri) — en az 1 adet
- [ ] Proxy bağlantısı test edilmiş
- [ ] Proxy olmadan ilk testler yapılabilir ama CF engelleyebilir

---

## FAZ 1 — PROJE İSKELETİ VE TEMEL TESTLER (Gün 1-2)

> **Amaç:** Proje yapısını oluşturmak, cross-platform algılamanın çalıştığını ve Camoufox'un VFS Global'e erişebildiğini doğrulamak.

### 1.1 Proje İskeleti (ADIM 1-4)
- [ ] `~/vise-os-bot/` dizinini ve tüm alt klasörleri oluştur
- [ ] `.env` dosyasını oluştur (placeholder değerlerle)
- [ ] `config/countries.json` dosyasını oluştur (tüm ülke tanımlarıyla)
- [ ] `config/selectors/` klasörünü oluştur (boş — keşif sonrası doldurulacak)
- [ ] `src/platform_config.py` → `platform_ayarlari_al()`, `parmak_izi_os_sec()`, `camoufox_config_olustur()`
- [ ] `src/country_manager.py` → `UlkeYonetici` sınıfı + genel selector şablonu
- [ ] `src/utils.py` → `log()`, `screenshot_al()`, `insan_gibi_bekle()`, `insan_gibi_yaz()`, `element_bul()`
- [ ] Doğrulama: `python -c "from src.platform_config import *; print(platform_ayarlari_al())"`
- [ ] Doğrulama: `python -c "from src.country_manager import *; y=UlkeYonetici(); print(y.aktif_vfs_ulkeleri())"`
- [ ] **Başarı kriteri:** Platform algılama + ülke yönetimi çalışıyor ✓

### 1.2 Camoufox Sağlık Testi (ADIM 5)
- [ ] `src/browser.py` → `tarayici_baslat(ulke_kodu)`, `sayfa_git(page, url)`
- [ ] Camoufox'u basit bir siteyle test et (google.com)
- [ ] Platform'a uygun headless mod kullanıldığını doğrula
- [ ] Parmak izi OS'unun her çalıştırmada farklı olduğunu doğrula
- [ ] **Başarı kriteri:** Camoufox açılıp sayfa yükleniyor, OS rotasyonu çalışıyor ✓

### 1.3 Bot Tespit Testi
- [ ] `https://bot.sannysoft.com` sitesine git — parmak izi sızıntısı var mı?
- [ ] `https://browserleaks.com/canvas` — Canvas fingerprint tutarlı mı?
- [ ] `https://browserleaks.com/webrtc` — WebRTC IP sızıntısı var mı?
- [ ] Sonuçların ekran görüntüsünü kaydet → `debug/screenshots/`
- [ ] **Başarı kriteri:** navigator.webdriver = undefined, major leak yok ✓

### 1.4 VFS Global İlk Temas (MVP Ülkesi)
- [ ] MVP ülkesini seç (önerilen: `aut`, `hrv` veya `che` — düşük koruma)
- [ ] `UlkeYonetici.url_olustur(ulke_kodu, "login")` ile URL üret
- [ ] O ülkenin login sayfasına git (önce proxy olmadan)
- [ ] Cloudflare challenge davranışını gözlemle
- [ ] Ekran görüntüsü al
- [ ] **Başarı kriteri:** VFS sayfası herhangi bir formunu gösteriyor ✓ veya Cloudflare challenge görünüyor (beklenen) △

### 1.5 Proxy ile VFS Global Temas
- [ ] Residential proxy ekleyerek aynı testi tekrarla
- [ ] `geoip=True` ile proxy'nin coğrafi konumuna uygun locale ayarla
- [ ] Cloudflare'ın davranış farkını gözlemle
- [ ] **Başarı kriteri:** Login formu görünür hale geliyor ✓

---

## FAZ 2 — REGISTER (KAYIT) AKIŞI (Gün 3-5)

> **Amaç:** Botun VFS Global'de yeni hesap oluşturabilmesini sağlamak.

### 2.1 Mail Okuyucu ve CAPTCHA Hazırlığı (ADIM 6-7)
- [ ] `src/otp_reader.py` → Mailcow IMAP bağlantısı, OTP çekme, link çekme
- [ ] IMAP bağlantısı testi: Mailcow'a bağlan, son maili oku
- [ ] `src/captcha_solver.py` → Turnstile / reCAPTCHA / hCaptcha iskeletleri + CapSolver API
- [ ] **Başarı kriteri:** IMAP bağlantısı çalışıyor, CAPTCHA iskeletleri hazır ✓

### 2.2 Register Akışı Geliştirme (ADIM 8)
- [ ] `src/register.py` → `register_yap(ulke_kodu)` fonksiyonu
- [ ] URL'yi `UlkeYonetici`'den üretir
- [ ] Selector'ları `selectors_yukle()`'den okur (başlangıçta genel şablon)
- [ ] **Başarı kriteri:** Register kodu yazıldı, derleniyor ✓

### 2.3 Manuel Akış Keşfi (GELİŞTİRİCİ YAPACAK)
- [ ] MVP ülkesinin register sayfasını Camoufox ile aç (`headless=False`)
- [ ] DevTools (F12) ile tüm form alanlarını tespit et:
  - [ ] Input name/id/class/placeholder değerleri
  - [ ] Zorunlu alanlar hangileri?
  - [ ] Dropdown veya özel bileşen var mı?
- [ ] Network trafiğini kaydet (hangi API çağrıları yapılıyor?)
- [ ] CAPTCHA tipini tespit et (Turnstile? reCAPTCHA? hCaptcha?)
- [ ] Çıktı: `config/selectors/vfs_{ulke_kodu}.json` dosyasını doldur
- [ ] Çıktı: `config/countries.json`'da `captcha_tipi` alanını güncelle
- [ ] **Başarı kriteri:** Gerçek selector'lar ve CAPTCHA tipi tespit edilmiş ✓

### 2.4 Form Doldurma ve Gönderim Testi
- [ ] Gerçek selector'larla formu otomatik doldur
- [ ] İnsan benzeri yazma gecikmesi ekle (50-150ms/karakter)
- [ ] Alanlar arası rastgele bekleme (0.5-2.5 sn)
- [ ] CAPTCHA geçişini test et
- [ ] Submit butonuna tıkla ve yanıtı kontrol et
- [ ] **Başarı kriteri:** Form gönderildi, VFS yanıt verdi ✓

### 2.5 E-posta Doğrulama
- [ ] Mailcow'a gelen doğrulama e-postasını kontrol et
- [ ] n8n otomasyonu linke tıklıyor mu? VEYA Python IMAP ile linki çek
- [ ] Doğrulama sonrası VFS'in yanıtını kontrol et
- [ ] **Başarı kriteri:** E-posta doğrulaması otomatik tamamlanıyor ✓

### ★ 2.6 REGISTER ENTEGRASYON TESTİ ★
- [ ] Uçtan uca: Yeni mail → Register → Form → CAPTCHA → Submit → Doğrulama
- [ ] 3 farklı mail adresiyle dene
- [ ] Başarı oranını kaydet
- [ ] **KRİTİK BAŞARI KRİTERİ:** En az 1 hesap başarıyla oluşturulmuş ✓✓✓

---

## FAZ 3 — LOGIN (GİRİŞ) AKIŞI (Gün 6-8)

> **Amaç:** Oluşturulan hesapla VFS Global'e giriş yapabilmek.

### 3.1 Login Akışı Geliştirme (ADIM 9)
- [ ] `src/login.py` → `login_yap(ulke_kodu)` fonksiyonu
- [ ] URL'yi `UlkeYonetici`'den üretir
- [ ] OTP entegrasyonu: `otp_reader.py`'dan çek, forma gir
- [ ] **Başarı kriteri:** Login kodu yazıldı ✓

### 3.2 Login Sayfası Keşfi (GELİŞTİRİCİ YAPACAK)
- [ ] Login sayfasını Camoufox ile aç (`headless=False`)
- [ ] DevTools ile login form alanlarını haritalandır
- [ ] OTP giriş alanını tespit et (login sonrası)
- [ ] `config/selectors/vfs_{ulke_kodu}.json`'da login bölümünü güncelle
- [ ] **Başarı kriteri:** Login selector'ları haritalanmış ✓

### 3.3 Giriş Otomasyonu (OTP Öncesi)
- [ ] Faz 2'de oluşturulan hesabın bilgileriyle giriş dene
- [ ] E-posta + şifre otomatik doldur
- [ ] CAPTCHA geçişi
- [ ] Submit sonrası OTP sayfasına ulaşılıyor mu?
- [ ] **Başarı kriteri:** OTP giriş alanı görünüyor ✓

### 3.4 OTP Okuma ve Girme
- [ ] Python IMAP ile Mailcow'dan OTP kodunu çek
- [ ] Zamanlama: Mail gelişi → OTP okuma → Forma girme < 30 sn
- [ ] OTP'yi forma gir ve gönder
- [ ] **Başarı kriteri:** OTP başarıyla girildi ✓

### 3.5 Dashboard Erişimi
- [ ] OTP sonrası dashboard sayfasına yönlendirme var mı?
- [ ] Oturumun aktif olduğunu doğrula
- [ ] **Başarı kriteri:** Dashboard sayfası yüklendi ✓

### ★ 3.6 LOGIN ENTEGRASYON TESTİ ★
- [ ] Uçtan uca: Login → Kimlik bilgileri → CAPTCHA → OTP → Dashboard
- [ ] 3 hesapla dene
- [ ] Başarı oranını kaydet
- [ ] **KRİTİK BAŞARI KRİTERİ:** En az 1 hesapla dashboard'a ulaşıldı ✓✓✓

---

## FAZ 4 — CLI VE SAĞLAMLAŞTIRMA (Gün 9-12)

> **Amaç:** CLI giriş noktası, güvenilirlik ve tekrarlanabilirlik.

### 4.1 CLI Giriş Noktası (ADIM 10)
- [ ] `main.py` → argparse ile komut satırı arayüzü
- [ ] `python main.py register --country aut`
- [ ] `python main.py login --country aut`
- [ ] `python main.py test --country aut` (register → login uçtan uca)
- [ ] **Başarı kriteri:** CLI çalışıyor, ülke kodu parametre olarak geçiyor ✓

### 4.2 Hata Yakalama ve Loglama
- [ ] Her adımda try/except ile hata yakala
- [ ] Hata anında otomatik screenshot + HAR kaydet
- [ ] Log formatı: `[TIMESTAMP][ADIM][DURUM] mesaj`
- [ ] Platform'a uygun log dizini

### 4.3 Selector Dayanıklılığı
- [ ] Birden fazla fallback selector tanımla
- [ ] Selector bulunamazsa log + screenshot + alarm
- [ ] Text-based arama yedek

### 4.4 Zamanlama Optimizasyonu
- [ ] Her adımın süresini ölç ve logla
- [ ] OTP pipeline süresini optimize et (hedef: < 20 sn)

### 4.5 Testler (ADIM 11)
- [ ] `test_platform_detection.py`: Platform algılama testi
- [ ] `test_register_e2e.py`: Uçtan uca register (ülke parametreli)
- [ ] `test_login_e2e.py`: Uçtan uca login (ülke parametreli)
- [ ] Aynı senaryoyu 5 kez çalıştır, başarı oranını kaydet
- [ ] **Başarı kriteri:** 5 testin en az 3'ü başarılı ✓

### 4.6 Ek Ülke Testi
- [ ] MVP ülkesi çalıştıktan sonra 2. bir ülkeyle test et
- [ ] Selector'lar aynı mı farklı mı? → Sonucu kaydet
- [ ] **Başarı kriteri:** 2. ülkede de çalışıyor ✓

---

## FAZ 5 — KARAR NOKTASI (Gün 13)

> **Bu faz, projenin geleceğini belirler.**

### Değerlendirme Matrisi

| Metrik | Hedef | Gerçekleşen | Durum |
|--------|-------|-------------|-------|
| Platform algılama | 3 OS'ta çalışıyor | ? | |
| Ülke parametresi | CLI ile ülke geçilebiliyor | ? | |
| Cloudflare bypass | En az 1 ülkede geçiyor | ? | |
| Register başarı oranı | ≥ %66 (2/3) | ? | |
| Login başarı oranı | ≥ %66 (2/3) | ? | |
| OTP pipeline süresi | < 30 sn | ? | |
| Hesap yasaklanma | Test süresince yok | ? | |
| Ek ülke | 2. ülkede de çalışıyor | ? | |
| Toplam uçtan uca süre | < 5 dk | ? | |

### Karar

| Sonuç | Aksiyon |
|-------|---------|
| ✅ Tüm metrikler yeşil | → Katmanlı mimari geliştirmeye başla (randevu tarama, çoklu hesap yönetimi) |
| ⚠️ Bazı metrikler sarı | → Sorunlu alanları iyileştir, 1 hafta daha test |
| ❌ Çoğu metrik kırmızı | → Alternatif yaklaşımları değerlendir (Nodriver, SeleniumBase UC) |

---

## DOSYA YAPISI

```
~/vise-os-bot/
├── .env                              # Hassas bilgiler — GIT'E EKLEME
├── config/
│   ├── countries.json                # Tüm ülke konfigürasyonları
│   ├── proxy_list.json               # Proxy listesi
│   └── selectors/                    # Ülke bazlı selector dosyaları
│       ├── vfs_ita.json              # (keşif sonrası doldurulacak)
│       ├── vfs_nld.json
│       ├── vfs_aut.json
│       └── ...
├── src/
│   ├── __init__.py
│   ├── platform_config.py            # Cross-platform algılama + parmak izi rotasyonu
│   ├── country_manager.py            # Ülke konfigürasyon yönetimi
│   ├── browser.py                    # Camoufox başlatma ve yönetim
│   ├── register.py                   # Register akışı (ülke-agnostik)
│   ├── login.py                      # Login akışı — OTP dahil (ülke-agnostik)
│   ├── otp_reader.py                 # Mailcow IMAP OTP okuyucu
│   ├── captcha_solver.py             # CAPTCHA çözüm stratejileri
│   └── utils.py                      # log, screenshot, bekleme fonksiyonları
├── tests/
│   ├── test_camoufox_health.py
│   ├── test_platform_detection.py
│   ├── test_register_e2e.py
│   └── test_login_e2e.py
├── debug/
│   ├── screenshots/
│   ├── har/
│   └── logs/
└── main.py                           # CLI: python main.py register -c aut
```

---

## ZAMAN ÇİZELGESİ ÖZET

| Faz | Gün | Açıklama | Çıktı |
|-----|-----|----------|-------|
| 0 | 0 | Ortam hazırlığı | Çalışan dev ortamı |
| 1 | 1-2 | İskelet + temel testler | Platform algılama + Camoufox + VFS ilk temas |
| 2 | 3-5 | Register akışı | Çalışan register botu (ülke parametreli) |
| 3 | 6-8 | Login akışı | Çalışan login botu (OTP dahil, ülke parametreli) |
| 4 | 9-12 | CLI + sağlamlaştırma | Güvenilir, loglanmış, çoklu ülke destekli sistem |
| 5 | 13 | Karar noktası | GO / NO-GO kararı |
