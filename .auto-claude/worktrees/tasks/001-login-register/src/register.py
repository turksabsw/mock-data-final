"""
VISE OS — Registration Flow (v3)

FIXES v3:
  - Submit sonrasi: Angular Material snackbar/toast/mat-error kontrolu
  - Email: Otomatik benzersiz email uretimi (test2001, test2002...)
  - Hata tespiti: VFS'in gercek hata mesajlarini yakalama
  - Sayfa degisimi: body text hash + navigation + dialog kontrolu
  - Debug: Submit sonrasi tam sayfa metni loglama
"""

import os
import random
import time
import hashlib

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


# --- Error Detection Patterns (genisletilmis) ---
HATA_EMAIL_KAYITLI = [
    "email already registered",
    "email is already in use",
    "already exists",
    "already been registered",
    "email zaten kayitli",
    "bu e-posta",
    "account already exists",
    "this email",
    "email address is already",
    "user already exists",
    "duplicate",
]

HATA_FORM_VALIDATION = [
    "mandatory field cannot be left blank",
    "mandatory field",
    "required field",
    "field cannot be left blank",
    "this field is required",
    "please fill",
]

HATA_SIFRE_POLITIKASI = [
    "password must",
    "password should",
    "password requirements",
    "password policy",
    "too weak",
    "too short",
    "at least",
    "sifre gereksinimleri",
    "minimum",
    "uppercase",
    "lowercase",
    "special character",
]

# --- Basari Tespiti Kaliplari ---
BASARI_KALIPLARI = [
    "almost done",
    "registration has been completed",
    "your registration has been completed",
    "we've sent you an email",
    "activate your account",
    "finish setting up",
    "verification",
    "verify your email",
    "check your email",
    "confirmation email",
    "email sent",
    "successfully registered",
    "registration successful",
    "account created",
    "account has been created",
    "dogrulama",
    "e-posta gonderildi",
    "please verify",
    "we have sent",
    "check your inbox",
    "please click on the link",
]

# --- Bekleme Ayarlari ---
SUBMIT_AKTIF_TIMEOUT = 180
SUBMIT_POLL_ARALIK = 3


# =====================================================================
# YARDIMCI FONKSIYONLAR
# =====================================================================

def _cookie_modal_kapat(page):
    """Close OneTrust cookie consent modal if present."""
    log("[REGISTER] Cookie modal kontrolu...")
    try:
        page.evaluate("""
            () => {
                const onetrust = document.getElementById('onetrust-consent-sdk');
                if (onetrust) { onetrust.remove(); return true; }
                const overlay = document.querySelector('.onetrust-pc-dark-filter');
                if (overlay) { overlay.remove(); return true; }
                return false;
            }
        """)
        log("[REGISTER] Cookie modal JS ile temizlendi")
        insan_gibi_bekle(0.5, 1.0)
        return True
    except Exception as e:
        log(f"[REGISTER] Cookie JS hatasi: {e}")

    for selector in [
        "button#onetrust-accept-btn-handler",
        "button:has-text('Accept All Cookies')",
        "button:has-text('Accept All')",
    ]:
        try:
            el = page.locator(selector)
            if el.count() > 0 and el.is_visible():
                el.click(timeout=5000)
                log(f"[REGISTER] Cookie kapatildi: {selector}")
                insan_gibi_bekle(1.0, 2.0)
                return True
        except Exception:
            continue

    log("[REGISTER] Cookie modal yok veya kapali")
    return False


def _env_kimlik_bilgileri_al():
    """Load registration credentials from .env."""
    email = os.getenv("VFS_EMAIL", "")
    password = os.getenv("VFS_PASSWORD", "")
    mobile_number = os.getenv("VFS_MOBILE_NUMBER", "")

    eksik = []
    if not email:
        eksik.append("VFS_EMAIL")
    if not password:
        eksik.append("VFS_PASSWORD")
    if not mobile_number:
        eksik.append("VFS_MOBILE_NUMBER")
    if eksik:
        raise ValueError(
            f"Kayit icin gerekli .env degiskenleri eksik: {', '.join(eksik)}"
        )

    return {
        "email": email,
        "password": password,
        "mobile_number": mobile_number,
    }


def _elemente_scroll(page, selector):
    """Scroll element into view."""
    try:
        page.evaluate(f"""
            () => {{
                const el = document.querySelector('{selector}');
                if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            }}
        """)
        insan_gibi_bekle(0.3, 0.6)
    except Exception as e:
        log(f"[REGISTER] Scroll hatasi ({selector}): {e}")


def _alan_doldur(page, ulke_kodu, alan_adi, metin):
    """Find a form field and fill with human-like typing."""
    element = element_bul(page, ulke_kodu, "register", alan_adi)
    try:
        element.scroll_into_view_if_needed()
    except Exception:
        pass
    element.click()
    insan_gibi_bekle(0.3, 0.8)
    for karakter in metin:
        element.type(karakter, delay=random.randint(50, 150))
    insan_gibi_bekle(0.5, 1.5)


def _checkbox_tikla(page, checkbox_id, checkbox_index):
    """Angular Material checkbox'u tikla — Angular FormControl'u GUNCELLE.

    PROBLEM:
      label[for="..."].click() → DOM checked=true, Angular FormControl=false
      input.click() → DOM checked=true, Angular FormControl=false
      Neden: Angular Material MDC, kendi ic event handler'ini kullanir.
             Native checkbox toggle Angular'in haberi olmadan gerceklesir.

    COZUM:
      mat-checkbox ELEMENTINI tikla — Angular component click handler tetiklenir.
      Handler iceride: checked toggle + ControlValueAccessor.onChange() + FormControl update

    DOGRULAMA:
      DOM checked degil, Angular form ng-valid class'ini kontrol et.
    """
    log(f"[REGISTER] Checkbox {checkbox_index} tiklaniyor: #{checkbox_id}")

    # ===== YONTEM 1: Playwright click on mat-checkbox component =====
    # Bu Angular'in kendi click handler'ini tetikler.
    # mat-checkbox componenti (change) event'ini dinler ve FormControl'u gunceller.
    try:
        all_cb = page.locator("mat-checkbox")
        count = all_cb.count()
        idx = checkbox_index - 1
        if idx < count:
            cb = all_cb.nth(idx)
            cb.scroll_into_view_if_needed()
            insan_gibi_bekle(0.3, 0.5)

            # Tikla — Playwright tam event chain: mousedown->mouseup->click
            cb.click(timeout=5000)
            insan_gibi_bekle(0.5, 0.8)

            # Dogrula — Angular ng-invalid kalkmis mi?
            ng_valid = _checkbox_angular_valid_mi(page, idx)
            dom_checked = page.evaluate(f"""
                () => document.getElementById('{checkbox_id}')?.checked || false
            """)
            log(f"[REGISTER] CB{checkbox_index}: dom_checked={dom_checked}, angular_valid={ng_valid}")

            if dom_checked and ng_valid:
                log(f"[REGISTER] CB{checkbox_index} BASARILI (mat-checkbox click)")
                return True
            elif dom_checked and not ng_valid:
                log(f"[REGISTER] CB{checkbox_index} DOM ok ama Angular INVALID — yontem 2 denenecek")
            # devam et
    except Exception as e:
        log(f"[REGISTER] CB{checkbox_index} mat-checkbox click hatasi: {e}")

    # ===== YONTEM 2: Click on .mdc-checkbox div inside mat-checkbox =====
    # Kullanicinin gercekte tikladigi gorunur checkbox karesi
    try:
        all_cb = page.locator("mat-checkbox")
        idx = checkbox_index - 1
        if idx < all_cb.count():
            # mdc-checkbox div — gorunur kare
            mdc = all_cb.nth(idx).locator(".mdc-checkbox")
            if mdc.count() > 0:
                mdc.first.click(timeout=5000)
                insan_gibi_bekle(0.5, 0.8)

                ng_valid = _checkbox_angular_valid_mi(page, idx)
                dom_checked = page.evaluate(f"""
                    () => document.getElementById('{checkbox_id}')?.checked || false
                """)
                log(f"[REGISTER] CB{checkbox_index} mdc-click: dom={dom_checked}, ng={ng_valid}")

                if dom_checked and ng_valid:
                    log(f"[REGISTER] CB{checkbox_index} BASARILI (mdc-checkbox click)")
                    return True
    except Exception as e:
        log(f"[REGISTER] CB{checkbox_index} mdc-checkbox hatasi: {e}")

    # ===== YONTEM 3: Angular ng API — dogrudan FormControl guncelle =====
    # Nuclear option: Angular'in internal API'sini kullanarak component'i toggle et
    try:
        result = page.evaluate(f"""
            () => {{
                const idx = {idx};
                const matCheckboxes = document.querySelectorAll('mat-checkbox');
                const matCb = matCheckboxes[idx];
                if (!matCb) return {{ success: false, reason: 'mat-checkbox not found' }};

                // Angular 9+ ng.getComponent API
                let toggled = false;

                // Yontem A: ng.getComponent ile component instance'a eris
                if (window.ng && window.ng.getComponent) {{
                    try {{
                        const comp = window.ng.getComponent(matCb);
                        if (comp) {{
                            // MatCheckbox component toggle methodu
                            if (typeof comp.toggle === 'function') {{
                                comp.toggle();
                                toggled = true;
                            }} else if ('checked' in comp) {{
                                comp.checked = !comp.checked;
                                // Change detection tetikle
                                if (comp._changeDetectorRef) {{
                                    comp._changeDetectorRef.markForCheck();
                                }}
                                toggled = true;
                            }}
                        }}
                    }} catch(e) {{
                        // ng.getComponent calismadi
                    }}
                }}

                // Yontem B: __ngContext__ uzerinden
                if (!toggled) {{
                    try {{
                        // Angular component'in iç state'ine doğrudan eriş
                        const input = matCb.querySelector('input[type="checkbox"]');
                        if (input) {{
                            // Önce DOM'u güncelle
                            input.checked = true;

                            // Angular Material'in beklediği event'leri dispatch et
                            // Sıra önemli: change -> input -> click
                            input.dispatchEvent(new Event('change', {{ bubbles: true, cancelable: true }}));

                            // mat-checkbox üzerinde de click tetikle
                            const clickEvent = new MouseEvent('click', {{
                                bubbles: true, cancelable: true,
                                clientX: matCb.getBoundingClientRect().x + 10,
                                clientY: matCb.getBoundingClientRect().y + 10,
                                view: window
                            }});
                            matCb.querySelector('.mdc-checkbox')?.dispatchEvent(clickEvent);

                            toggled = true;
                        }}
                    }} catch(e) {{}}
                }}

                // Dogrula
                const input = document.getElementById('{checkbox_id}');
                const checked = input ? input.checked : false;
                const ngValid = !matCb.classList.contains('ng-invalid');

                return {{ success: toggled, checked: checked, ng_valid: ngValid }};
            }}
        """)

        if result.get("success") and result.get("checked"):
            log(f"[REGISTER] CB{checkbox_index} Angular API: checked={result['checked']}, ng_valid={result['ng_valid']}")
            if result.get("ng_valid"):
                log(f"[REGISTER] CB{checkbox_index} BASARILI (Angular API)")
                return True
            else:
                log(f"[REGISTER] CB{checkbox_index} checked ama ng-invalid hala var")
    except Exception as e:
        log(f"[REGISTER] CB{checkbox_index} Angular API hatasi: {e}")

    # ===== YONTEM 4: Son care — tum mat-checkbox'lara click event chain =====
    try:
        page.evaluate(f"""
            () => {{
                const idx = {idx};
                const matCb = document.querySelectorAll('mat-checkbox')[idx];
                if (!matCb) return;

                // Tam mouse event simulasyonu — kullanici davranisi
                const rect = matCb.getBoundingClientRect();
                const x = rect.left + rect.width / 2;
                const y = rect.top + rect.height / 2;

                const events = ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'];
                for (const type of events) {{
                    const evt = new PointerEvent(type, {{
                        bubbles: true, cancelable: true, composed: true,
                        clientX: x, clientY: y, view: window,
                        button: 0, buttons: type.includes('down') ? 1 : 0,
                        pointerId: 1, pointerType: 'mouse'
                    }});
                    matCb.dispatchEvent(evt);
                }}
            }}
        """)
        insan_gibi_bekle(0.5, 0.8)

        dom_checked = page.evaluate(f"""
            () => document.getElementById('{checkbox_id}')?.checked || false
        """)
        ng_valid = _checkbox_angular_valid_mi(page, checkbox_index - 1)
        log(f"[REGISTER] CB{checkbox_index} event-chain: dom={dom_checked}, ng={ng_valid}")

        if dom_checked:
            log(f"[REGISTER] CB{checkbox_index} event-chain ile checked (ng_valid={ng_valid})")
            return True
    except Exception as e:
        log(f"[REGISTER] CB{checkbox_index} event-chain hatasi: {e}")

    log(f"[REGISTER] CB{checkbox_index} BASARISIZ — hicbir yontem calismadi!")
    screenshot_al(page, f"cb{checkbox_index}_failed")
    return False


def _checkbox_angular_valid_mi(page, mat_checkbox_index):
    """mat-checkbox element'inin Angular FormControl tarafindan valid sayilip sayilmadigini kontrol et."""
    try:
        return page.evaluate(f"""
            () => {{
                const cbs = document.querySelectorAll('mat-checkbox');
                if ({mat_checkbox_index} >= cbs.length) return false;
                const cb = cbs[{mat_checkbox_index}];
                // ng-valid class'i varsa veya ng-invalid class'i yoksa valid
                return cb.classList.contains('ng-valid') || !cb.classList.contains('ng-invalid');
            }}
        """)
    except Exception:
        return False


# =====================================================================
# TURNSTILE & SUBMIT BEKLEME
# =====================================================================

def _turnstile_durumu_kontrol(page):
    """Cloudflare Turnstile durumunu detayli kontrol et."""
    try:
        return page.evaluate("""
            () => {
                const status = {
                    widget_var: false, iframe_var: false,
                    cozuldu: false, token_len: 0, detay: ''
                };

                // Angular container
                if (document.querySelector('app-cloudflare-captcha-container')) {
                    status.widget_var = true;
                    status.detay += 'angular-container ';
                }

                // cf-turnstile div
                if (document.querySelector('.cf-turnstile, #cf-turnstile, [data-sitekey]')) {
                    status.widget_var = true;
                    status.detay += 'cf-div ';
                }

                // iframe
                for (const iframe of document.querySelectorAll('iframe')) {
                    const src = iframe.src || '';
                    if (src.includes('challenges.cloudflare.com') || src.includes('turnstile')) {
                        status.iframe_var = true;
                        status.detay += 'iframe ';
                        break;
                    }
                }

                // Token
                const tokenInput = document.querySelector('input[name="cf-turnstile-response"]');
                if (tokenInput) {
                    status.detay += 'token-input ';
                    if (tokenInput.value && tokenInput.value.length > 10) {
                        status.cozuldu = true;
                        status.token_len = tokenInput.value.length;
                        status.detay += 'TOKEN-OK ';
                    } else {
                        status.detay += 'token-bos ';
                    }
                }

                return status;
            }
        """)
    except Exception as e:
        return {"widget_var": False, "iframe_var": False, "cozuldu": False,
                "token_len": 0, "detay": f"error: {e}"}


def _submit_buton_aktif_mi(page):
    """Submit butonunun aktif olup olmadigini kontrol et."""
    try:
        result = page.evaluate("""
            () => {
                const btn = document.querySelector('button#trigger');
                if (!btn) return { found: false, disabled: true };
                return { found: true, disabled: btn.disabled };
            }
        """)
        return result.get("found") and not result.get("disabled", True)
    except Exception:
        return False


def _submit_aktif_bekle(page, timeout=SUBMIT_AKTIF_TIMEOUT):
    """Submit butonunun aktif olmasini bekle."""
    if _submit_buton_aktif_mi(page):
        log("[REGISTER] Submit butonu zaten AKTIF!")
        return True

    ts = _turnstile_durumu_kontrol(page)
    log(f"[REGISTER] Turnstile: {ts['detay'].strip()}")

    if ts["widget_var"] or ts["iframe_var"]:
        log("=" * 60)
        log("[REGISTER] CLOUDFLARE TURNSTILE BEKLENIYOR")
        log("[REGISTER] Tarayicida Cloudflare captcha'yi cozun!")
        log(f"[REGISTER] Max bekleme: {timeout}sn")
        log("=" * 60)
    else:
        log("[REGISTER] Submit buton aktivasyonu bekleniyor...")

    screenshot_al(page, "waiting_submit_active")

    baslangic = time.time()
    son_log = baslangic

    while (time.time() - baslangic) < timeout:
        if _submit_buton_aktif_mi(page):
            gecen = int(time.time() - baslangic)
            log(f"[REGISTER] SUBMIT AKTIF! ({gecen}sn)")
            screenshot_al(page, "submit_enabled")
            return True

        simdi = time.time()
        if (simdi - son_log) >= 15:
            kalan = int(timeout - (simdi - baslangic))
            ts = _turnstile_durumu_kontrol(page)
            log(f"[REGISTER] Bekleniyor... kalan={kalan}sn | {ts['detay'].strip()}")
            son_log = simdi

        time.sleep(SUBMIT_POLL_ARALIK)

    log(f"[REGISTER] TIMEOUT! {timeout}sn — submit aktif olmadi")
    screenshot_al(page, "submit_wait_timeout")
    return False


# =====================================================================
# SUBMIT SONRASI ANALIZ (KRITIK DUZELTME)
# =====================================================================

def _sayfa_degisimi_bekle(page, onceki_body_hash, timeout=15):
    """Submit sonrasi sayfa iceriginin degismesini bekle.

    Angular SPA'da URL degismeyebilir — body text hash degisimini izle.
    Ayrica navigation event veya Angular route degisimini kontrol et.

    Returns:
        bool: True if page content changed.
    """
    log("[REGISTER] Sayfa degisimi bekleniyor...")
    baslangic = time.time()

    while (time.time() - baslangic) < timeout:
        try:
            yeni_hash = _body_text_hash(page)
            if yeni_hash != onceki_body_hash:
                log(f"[REGISTER] Sayfa icerigi degisti! (hash: {onceki_body_hash[:8]}.. -> {yeni_hash[:8]}..)")
                return True
        except Exception:
            pass
        time.sleep(1)

    log(f"[REGISTER] Sayfa {timeout}sn icerisinde degismedi")
    return False


def _body_text_hash(page):
    """Sayfa body text'inin hash'ini al."""
    try:
        body_text = page.inner_text("body")
        return hashlib.md5(body_text.encode()).hexdigest()
    except Exception:
        return ""


def _submit_sonrasi_analiz(page, kesin_sinyal_only=False):
    """Submit sonrasi sayfayi detayli analiz et.

    Args:
        page: Playwright page object.
        kesin_sinyal_only: True ise sadece kesin sinyallere bak
            (snackbar, mat-error, dialog). "Form hala gorunur" gibi
            belirsiz sinyalleri DONDURME — submit sonrasi ilk 3sn'de
            sayfa degismemis olabilir.

    Returns:
        dict: basarili, hata, mesaj, detay
    """
    log("[REGISTER] Submit sonrasi detayli analiz baslatiliyor...")

    sonuc = {
        "basarili": False,
        "hata": None,
        "mesaj": "",
        "detay": {},
    }

    try:
        analiz = page.evaluate("""
            () => {
                const result = {
                    url: window.location.href,
                    snackbar: null,
                    mat_errors: [],
                    dialog: null,
                    alerts: [],
                    toasts: [],
                    body_snippet: '',
                    form_gorunur: false,
                    kayit_formu_var: false,
                };

                // 1. Angular Material Snackbar (EN ONEMLI)
                const snackbar = document.querySelector(
                    'mat-snack-bar-container, .mat-mdc-snack-bar-container, ' +
                    'simple-snack-bar, .mat-mdc-simple-snack-bar, ' +
                    '.mat-snack-bar-container, snack-bar-container'
                );
                if (snackbar) {
                    result.snackbar = snackbar.innerText.trim();
                }

                // Snackbar overlay'da da olabilir
                const snackOverlay = document.querySelector(
                    '.cdk-overlay-container .mat-mdc-snack-bar-container, ' +
                    '.cdk-overlay-container mat-snack-bar-container, ' +
                    '.cdk-overlay-container simple-snack-bar'
                );
                if (snackOverlay && !result.snackbar) {
                    result.snackbar = snackOverlay.innerText.trim();
                }

                // 2. Angular Material Error mesajlari
                const matErrors = document.querySelectorAll(
                    'mat-error, .mat-mdc-form-field-error, .mat-error'
                );
                matErrors.forEach(el => {
                    const text = el.innerText.trim();
                    if (text) result.mat_errors.push(text);
                });

                // 3. Dialog / Modal
                const dialog = document.querySelector(
                    'mat-dialog-container, .mat-mdc-dialog-container, ' +
                    '.cdk-overlay-container mat-dialog-container'
                );
                if (dialog) {
                    result.dialog = dialog.innerText.trim().substring(0, 500);
                }

                // 4. Genel alert/toast
                const alertSelectors = [
                    '.alert', '.toast', '[role="alert"]',
                    '.notification', '.message-box',
                    '.error-message', '.success-message',
                    '.alert-danger', '.alert-success', '.alert-warning'
                ];
                for (const sel of alertSelectors) {
                    document.querySelectorAll(sel).forEach(el => {
                        const text = el.innerText.trim();
                        if (text && text.length > 3) {
                            result.alerts.push(text.substring(0, 200));
                        }
                    });
                }

                // 5. Body text snippet (ilk 1000 karakter)
                const body = document.body?.innerText || '';
                result.body_snippet = body.substring(0, 1000);

                // 6. Kayit formu hala gorunur mu
                const form = document.querySelector('form');
                if (form) {
                    result.form_gorunur = true;
                    // "Create an account" hala var mi kontrol et
                    const heading = document.querySelector('h1, h2, h3');
                    if (heading) {
                        const hText = heading.innerText.toLowerCase();
                        if (hText.includes('create') || hText.includes('register')) {
                            result.kayit_formu_var = true;
                        }
                    }
                }

                return result;
            }
        """)

        log(f"[REGISTER] Analiz — URL: {analiz['url']}")
        log(f"[REGISTER] Analiz — Snackbar: {analiz['snackbar']}")
        log(f"[REGISTER] Analiz — Mat-errors: {analiz['mat_errors']}")
        log(f"[REGISTER] Analiz — Dialog: {analiz['dialog']}")
        log(f"[REGISTER] Analiz — Alerts: {analiz['alerts']}")
        log(f"[REGISTER] Analiz — Form gorunur: {analiz['form_gorunur']}")
        log(f"[REGISTER] Analiz — Kayit formu var: {analiz['kayit_formu_var']}")

        sonuc["detay"] = analiz

        # Body snippet'i debug icin logla (ilk 300 karakter)
        snippet = analiz.get("body_snippet", "")[:300]
        log(f"[REGISTER] Sayfa icerik (ilk 300): {snippet}")

        # --- Analiz Sonuclari ---

        # Snackbar mesaji var mi?
        snackbar = analiz.get("snackbar", "")
        if snackbar:
            log(f"[REGISTER] SNACKBAR MESAJI: '{snackbar}'")
            snack_lower = snackbar.lower()

            # Basari mesaji mi?
            for kalip in BASARI_KALIPLARI:
                if kalip in snack_lower:
                    sonuc["basarili"] = True
                    sonuc["mesaj"] = f"Snackbar basari: {snackbar}"
                    return sonuc

            # Hata mesaji mi?
            for kalip in HATA_EMAIL_KAYITLI:
                if kalip in snack_lower:
                    sonuc["hata"] = f"Email kayitli: {snackbar}"
                    sonuc["mesaj"] = snackbar
                    return sonuc

            for kalip in HATA_SIFRE_POLITIKASI:
                if kalip in snack_lower:
                    sonuc["hata"] = f"Sifre hatasi: {snackbar}"
                    sonuc["mesaj"] = snackbar
                    return sonuc

            for kalip in HATA_FORM_VALIDATION:
                if kalip in snack_lower:
                    sonuc["hata"] = f"Form validation: {snackbar}"
                    sonuc["mesaj"] = snackbar
                    return sonuc

            # Bilinmeyen snackbar — hata olarak degerlendri
            sonuc["hata"] = f"Bilinmeyen snackbar: {snackbar}"
            sonuc["mesaj"] = snackbar
            return sonuc

        # Mat-error mesajlari var mi?
        mat_errors = analiz.get("mat_errors", [])
        if mat_errors:
            hata_mesaj = "; ".join(mat_errors)
            log(f"[REGISTER] MAT-ERROR: {hata_mesaj}")
            sonuc["hata"] = f"Form hatalari: {hata_mesaj}"
            sonuc["mesaj"] = hata_mesaj
            return sonuc

        # "Mandatory field" kirmizi yazi — snackbar degil, sayfa iceriginde olabilir
        body_lower = analiz.get("body_snippet", "").lower()
        for kalip in HATA_FORM_VALIDATION:
            if kalip in body_lower:
                log(f"[REGISTER] BODY'DE FORM VALIDATION HATASI: '{kalip}'")
                sonuc["hata"] = f"Form validation (body): {kalip}"
                sonuc["mesaj"] = kalip
                return sonuc

        # Dialog var mi?
        dialog = analiz.get("dialog", "")
        if dialog:
            log(f"[REGISTER] DIALOG: {dialog[:200]}")
            dialog_lower = dialog.lower()
            for kalip in BASARI_KALIPLARI:
                if kalip in dialog_lower:
                    sonuc["basarili"] = True
                    sonuc["mesaj"] = f"Dialog basari: {dialog[:200]}"
                    return sonuc

        # Alert mesajlari var mi?
        alerts = analiz.get("alerts", [])
        if alerts:
            alerts_text = "; ".join(alerts)
            log(f"[REGISTER] ALERTS: {alerts_text}")
            alerts_lower = alerts_text.lower()
            for kalip in BASARI_KALIPLARI:
                if kalip in alerts_lower:
                    sonuc["basarili"] = True
                    sonuc["mesaj"] = f"Alert basari: {alerts_text}"
                    return sonuc

        # URL degisti mi?
        if "register" not in analiz.get("url", "").lower():
            log("[REGISTER] URL degisti — kayit basarili olabilir!")
            sonuc["basarili"] = True
            sonuc["mesaj"] = f"URL degisti: {analiz['url']}"
            return sonuc

        # Body text'te basari kaliplari var mi?
        body_lower = analiz.get("body_snippet", "").lower()
        for kalip in BASARI_KALIPLARI:
            if kalip in body_lower:
                sonuc["basarili"] = True
                sonuc["mesaj"] = f"Body'de basari mesaji: '{kalip}'"
                return sonuc

        # Kayit formu hala gorunur mu?
        # NOT: kesin_sinyal_only modda bunu ATLIYORUZ
        # cunku submit sonrasi ilk 3sn'de sayfa henuz degismemis olabilir
        if not kesin_sinyal_only and analiz.get("kayit_formu_var"):
            sonuc["hata"] = "Kayit formu hala gorunur — submit Angular FormControl'a ulasmamis olabilir"
            sonuc["mesaj"] = "Form hala sayfada — checkbox'lar Angular'a yansimamis olabilir"
            return sonuc

        # Bilinmeyen durum
        sonuc["mesaj"] = "Sonuc belirlenemedi — screenshot kontrol edin"
        return sonuc

    except Exception as e:
        log(f"[REGISTER] Analiz hatasi: {type(e).__name__}: {e}")
        sonuc["mesaj"] = f"Analiz hatasi: {e}"
        return sonuc


def _sayfa_hata_kontrol(page, hata_kaliplari, hata_turu):
    """Check page content for known error patterns."""
    try:
        sayfa_metni = page.inner_text("body").lower()
        for kalip in hata_kaliplari:
            if kalip.lower() in sayfa_metni:
                log(f"[REGISTER] {hata_turu} hatasi: '{kalip}'")
                screenshot_al(page, f"register_{hata_turu.lower()}")
                return kalip
    except Exception as e:
        log(f"[REGISTER] Hata kontrol hatasi: {type(e).__name__}: {e}")
    return None


def _angular_checkbox_force_set(page):
    """Angular FormControl degerlerini JavaScript ile dogrudan set et.

    Bu NUCLEAR OPTION — normal click yontemleri calismadiysa kullanilir.
    Angular'in ng API'sini veya __ngContext__ uzerinden FormControl'a erisir.
    """
    log("[REGISTER] Angular checkbox FormControl'lar zorla set ediliyor...")
    try:
        result = page.evaluate("""
            () => {
                const results = [];
                const matCheckboxes = document.querySelectorAll('mat-checkbox');

                for (let i = 0; i < matCheckboxes.length; i++) {
                    const matCb = matCheckboxes[i];
                    const input = matCb.querySelector('input[type="checkbox"]');
                    let success = false;

                    // Yontem A: ng.getComponent API
                    if (window.ng && window.ng.getComponent) {
                        try {
                            const comp = window.ng.getComponent(matCb);
                            if (comp && 'checked' in comp) {
                                comp.checked = true;
                                // writeValue cagir (ControlValueAccessor)
                                if (comp.writeValue) comp.writeValue(true);
                                // onChange callback'i cagir
                                if (comp._controlValueAccessor && comp._controlValueAccessor.onChange) {
                                    comp._controlValueAccessor.onChange(true);
                                }
                                // Change detection
                                if (comp._changeDetectorRef) {
                                    comp._changeDetectorRef.markForCheck();
                                    comp._changeDetectorRef.detectChanges();
                                }
                                success = true;
                            }
                        } catch(e) {}
                    }

                    // Yontem B: FormControl'a dogrudan eris
                    if (!success) {
                        try {
                            // mat-checkbox icindeki ng context'ten form control'a eris
                            const formEl = document.querySelector('form');
                            if (formEl && window.ng) {
                                const formComp = window.ng.getComponent(formEl) ||
                                                 window.ng.getComponent(formEl.parentElement);
                                if (formComp) {
                                    // registerForm.controls icinden checkbox control'lari bul
                                    const form = formComp.registerForm || formComp.form || formComp.formGroup;
                                    if (form && form.controls) {
                                        // Checkbox FormControl isimlerini tahmin et
                                        const cbNames = ['termsCheck', 'privacyCheck', 'dataTransferCheck',
                                                         'checkbox1', 'checkbox2', 'checkbox3',
                                                         'terms', 'privacy', 'dataTransfer',
                                                         'consent1', 'consent2', 'consent3'];
                                        let setCount = 0;
                                        for (const name of cbNames) {
                                            if (form.controls[name]) {
                                                form.controls[name].setValue(true);
                                                form.controls[name].markAsDirty();
                                                form.controls[name].markAsTouched();
                                                setCount++;
                                            }
                                        }
                                        // Tum boolean false control'lari true yap
                                        for (const [key, ctrl] of Object.entries(form.controls)) {
                                            if (ctrl.value === false) {
                                                ctrl.setValue(true);
                                                ctrl.markAsDirty();
                                                ctrl.markAsTouched();
                                                setCount++;
                                            }
                                        }
                                        if (setCount > 0) success = true;
                                    }
                                }
                            }
                        } catch(e) {}
                    }

                    // DOM'u da guncelle
                    if (input) input.checked = true;

                    results.push({
                        index: i,
                        success: success,
                        checked: input ? input.checked : false,
                        ngValid: !matCb.classList.contains('ng-invalid')
                    });
                }

                // Angular zone'da change detection tetikle
                try {
                    if (window.ng && window.ng.applyChanges) {
                        window.ng.applyChanges(document.querySelector('form'));
                    }
                } catch(e) {}

                // Form validity kontrol
                const form = document.querySelector('form');
                const formValid = form ? form.classList.contains('ng-valid') : false;

                return { checkboxes: results, formValid: formValid };
            }
        """)

        log(f"[REGISTER] Force set sonuc: {result}")
        return result.get("formValid", False)
    except Exception as e:
        log(f"[REGISTER] Force set hatasi: {e}")
        return False


def _angular_form_durumu_kontrol(page):
    """Angular Reactive Form'un durumunu kontrol et.

    Checkbox'lar tiklandiktan sonra Angular FormControl'larin
    gercekten guncellenip guncellenmedigini dogrular.
    """
    try:
        form_durumu = page.evaluate("""
            () => {
                const result = {
                    checkboxes_dom: [],
                    form_valid: null,
                    form_errors: [],
                    submit_disabled: null,
                };

                // 1. DOM checkbox durumlari
                const inputs = document.querySelectorAll(
                    'input[type="checkbox"].mdc-checkbox__native-control'
                );
                inputs.forEach((inp, i) => {
                    result.checkboxes_dom.push({
                        id: inp.id,
                        checked: inp.checked,
                        indeterminate: inp.indeterminate,
                    });
                });

                // 2. Angular form valid durumu (ng-valid/ng-invalid class'lari)
                const form = document.querySelector('form');
                if (form) {
                    result.form_valid = form.classList.contains('ng-valid');
                    if (form.classList.contains('ng-invalid')) {
                        result.form_valid = false;
                    }
                }

                // 3. mat-checkbox ng-valid/ng-invalid kontrol
                const matCbs = document.querySelectorAll('mat-checkbox');
                matCbs.forEach((cb, i) => {
                    const isInvalid = cb.classList.contains('ng-invalid');
                    const isDirty = cb.classList.contains('ng-dirty');
                    const isTouched = cb.classList.contains('ng-touched');
                    if (isInvalid) {
                        result.form_errors.push(
                            `mat-checkbox[${i}]: ng-invalid (dirty=${isDirty}, touched=${isTouched})`
                        );
                    }
                });

                // 4. Submit buton durumu
                const btn = document.querySelector('button#trigger');
                if (btn) result.submit_disabled = btn.disabled;

                return result;
            }
        """)

        log(f"[REGISTER] Angular Form Durumu:")
        log(f"[REGISTER]   DOM Checkboxes: {form_durumu['checkboxes_dom']}")
        log(f"[REGISTER]   Form valid (ng-valid): {form_durumu['form_valid']}")
        log(f"[REGISTER]   Form errors: {form_durumu['form_errors']}")
        log(f"[REGISTER]   Submit disabled: {form_durumu['submit_disabled']}")

        if form_durumu.get("form_errors"):
            log("[REGISTER] UYARI: Angular FormControl'lar INVALID — checkbox click Angular'a ulasmamis olabilir!")
            log("[REGISTER] Playwright click ile tekrar deneniyor...")
            return False

        return True

    except Exception as e:
        log(f"[REGISTER] Angular form kontrol hatasi: {e}")
        return False


# =====================================================================
# FORM DOLDURMA
# =====================================================================

def _form_doldur(page, ulke_kodu, kimlik):
    """Fill the VFS registration form.

    Adimlar:
        1. Email
        2. Password
        3. Confirm Password
        4. Dial Code + Mobile Number
        5. Scroll asagi
        6. Checkbox'lar (3 adet)
        7. Submit buton aktivasyonu bekle (Turnstile)
    """
    log("[REGISTER] Form doldurma baslatiliyor...")

    # --- 1. Email ---
    log("[REGISTER] [1/7] Email dolduruluyor...")
    _alan_doldur(page, ulke_kodu, "email", kimlik["email"])
    log(f"[REGISTER] Email: {kimlik['email']}")
    insan_gibi_bekle(0.5, 1.5)

    # --- 2. Password ---
    log("[REGISTER] [2/7] Sifre dolduruluyor...")
    _alan_doldur(page, ulke_kodu, "password", kimlik["password"])
    log("[REGISTER] Sifre dolduruldu")
    insan_gibi_bekle(0.5, 1.5)

    # --- 3. Confirm Password ---
    log("[REGISTER] [3/7] Sifre tekrar dolduruluyor...")
    _alan_doldur(page, ulke_kodu, "password_confirm", kimlik["password"])
    log("[REGISTER] Sifre tekrar dolduruldu")
    insan_gibi_bekle(0.5, 1.5)

    # --- 4. Dial Code + Mobile Number ---
    log("[REGISTER] [4/7] Dial Code + Mobil numara...")
    _dial_code_sec(page)
    insan_gibi_bekle(0.5, 1.0)
    _alan_doldur(page, ulke_kodu, "mobile_number", kimlik["mobile_number"])
    log(f"[REGISTER] Mobil numara: {kimlik['mobile_number']}")
    insan_gibi_bekle(0.5, 1.5)

    # --- 5. Scroll ---
    log("[REGISTER] [5/7] Sayfayi asagi scroll...")
    _elemente_scroll(page, "button#trigger")
    insan_gibi_bekle(1.0, 2.0)
    screenshot_al(page, "scrolled_to_bottom")

    # --- 6. Checkboxes ---
    log("[REGISTER] [6/7] Checkbox'lar tiklaniyor...")

    cb1 = _checkbox_tikla(page, "mat-mdc-checkbox-0-input", 1)
    insan_gibi_bekle(0.5, 1.0)
    cb2 = _checkbox_tikla(page, "mat-mdc-checkbox-1-input", 2)
    insan_gibi_bekle(0.5, 1.0)
    cb3 = _checkbox_tikla(page, "mat-mdc-checkbox-2-input", 3)
    insan_gibi_bekle(0.5, 1.0)

    log(f"[REGISTER] Checkbox: CB1={cb1}, CB2={cb2}, CB3={cb3}")

    if not (cb1 and cb2 and cb3):
        log("[REGISTER] UYARI: Bazi checkbox'lar tiklanamadi!")
        screenshot_al(page, "checkboxes_incomplete")

    # Angular form durumunu kontrol et
    form_ok = _angular_form_durumu_kontrol(page)

    # Eger form hala invalid ise — KURTARMA: FormControl'lari dogrudan set et
    if not form_ok:
        log("[REGISTER] KURTARMA: Angular FormControl'lar dogrudan set edilecek...")
        _angular_checkbox_force_set(page)
        insan_gibi_bekle(0.5, 1.0)
        _angular_form_durumu_kontrol(page)  # tekrar kontrol

    # --- 7. Submit buton bekle ---
    log("[REGISTER] [7/7] Submit aktivasyonu bekleniyor...")
    insan_gibi_bekle(2.0, 3.0)

    ts = _turnstile_durumu_kontrol(page)
    log(f"[REGISTER] Turnstile: {ts['detay'].strip()}")
    screenshot_al(page, "before_turnstile_wait")

    submit_aktif = _submit_aktif_bekle(page)
    if not submit_aktif:
        log("[REGISTER] UYARI: Submit aktif olmadi — yine de deneyecegiz")

    log("[REGISTER] Form doldurma tamamlandi")
    screenshot_al(page, "form_filled")
    return True


def _dial_code_sec(page):
    """Dial Code dropdown'dan +90 (Turkey) sec."""
    log("[REGISTER] Dial Code aciliyor...")
    try:
        dial_select = page.locator("mat-select[formcontrolname='dialcode']")
        if dial_select.count() == 0:
            log("[REGISTER] Dial code bulunamadi")
            return

        dial_select.first.scroll_into_view_if_needed()
        dial_select.first.click(timeout=5000)
        insan_gibi_bekle(1.0, 2.0)

        for selector in [
            "mat-option:has-text('+90')",
            "mat-option:has-text('Turkey')",
            "mat-option:has-text('90')",
        ]:
            try:
                option = page.locator(selector)
                if option.count() > 0:
                    option.first.click(timeout=5000)
                    log(f"[REGISTER] Turkey (+90) secildi")
                    insan_gibi_bekle(0.5, 1.0)
                    return
            except Exception:
                continue

        log("[REGISTER] Turkey secilemedi")
        page.keyboard.press("Escape")
    except Exception as e:
        log(f"[REGISTER] Dial Code hatasi: {e}")


# =====================================================================
# FORM GONDERME (KRITIK DUZELTME)
# =====================================================================

def _form_gonder(page, ulke_kodu):
    """Submit the registration form ve sonucu analiz et.

    TEK SUBMIT STRATEJISI:
      1. Playwright Locator click (button#trigger)
      2. Network POST response bekle (VFS API yaniti)
      3. Sayfa degisimi analiz et

    NEDEN TEK STRATEJI:
      Turnstile token TEK KULLANIMLIK. Birden fazla submit denemesi
      token'i tuketir/gecersiz kilar ve "Mandatory field cannot be left blank"
      hatasina yol acar.

    Returns:
        dict: Analiz sonucu (basarili, hata, mesaj)
    """
    log("[REGISTER] Form gonderiliyor...")

    # Submit locator bul
    submit_locator = page.locator("button#trigger")
    if submit_locator.count() == 0:
        submit_locator = page.locator("button[type='submit']")

    try:
        submit_locator.first.scroll_into_view_if_needed()
    except Exception:
        _elemente_scroll(page, "button#trigger")

    insan_gibi_bekle(0.5, 1.0)

    # Submit AKTIF mi kontrol
    is_disabled = submit_locator.first.is_disabled()
    if is_disabled:
        log("[REGISTER] Submit DISABLED — Turnstile bekleniyor...")
        aktif = _submit_aktif_bekle(page, timeout=SUBMIT_AKTIF_TIMEOUT)
        if not aktif:
            log("[REGISTER] Submit aktif olmadi!")
            screenshot_al(page, "submit_still_disabled")
            raise Exception("Submit butonu aktif olmadi — Turnstile cozulmedi")

    log("[REGISTER] Submit butonu AKTIF")

    # Son Turnstile token kontrolu — submit oncesi
    ts = _turnstile_durumu_kontrol(page)
    log(f"[REGISTER] Submit oncesi Turnstile: {ts['detay'].strip()}")
    if not ts.get("cozuldu"):
        log("[REGISTER] UYARI: Turnstile token bos ama buton aktif — devam ediliyor")

    # Body hash (degisim tespiti icin)
    onceki_hash = _body_text_hash(page)
    screenshot_al(page, "before_submit")

    # ===== TEK SUBMIT: Main World click =====
    # Camoufox izole JS dunyasi kullanir — locator.click() Angular'a ulasmaz
    # mw: prefix ile ana dunyada click yapiyoruz — Angular Zone.js bunu yakalar
    log("[REGISTER] Submit tiklaniyor (main world click)...")
    try:
        page.evaluate("mw:document.getElementById('trigger').click()")
        log("[REGISTER] Main world click TAMAM")
    except Exception as e:
        log(f"[REGISTER] mw click hatasi: {e} — locator click deneniyor...")
        try:
            submit_locator.first.click(timeout=5000)
            log("[REGISTER] Fallback locator click TAMAM")
        except Exception as e2:
            log(f"[REGISTER] Locator click de basarisiz: {e2}")

    # --- Submit sonrasi bekleme ---
    # Angular'in response'u isleyip DOM'u guncellemesi icin bekle
    log("[REGISTER] Sayfa guncellenmesi bekleniyor (5sn)...")
    insan_gibi_bekle(5, 7)

    # ILK ANALIZ
    ilk_analiz = _submit_sonrasi_analiz(page, kesin_sinyal_only=True)
    screenshot_al(page, "after_submit_ilk")

    if ilk_analiz["basarili"] or ilk_analiz["hata"]:
        log(f"[REGISTER] Sonuc: basarili={ilk_analiz['basarili']}, "
            f"hata={ilk_analiz['hata']}, mesaj={ilk_analiz['mesaj']}")
        return ilk_analiz

    # Sayfa degisimi bekle (10sn daha)
    log("[REGISTER] Ek bekleme (10sn)...")
    son_hash = _body_text_hash(page)
    degisti = _sayfa_degisimi_bekle(page, son_hash, timeout=10)

    if degisti:
        log("[REGISTER] Sayfa degisti!")
        insan_gibi_bekle(2, 3)

    # SON ANALIZ (tam)
    son_analiz = _submit_sonrasi_analiz(page, kesin_sinyal_only=False)
    screenshot_al(page, "after_submit_final")

    log(f"[REGISTER] Son analiz: basarili={son_analiz['basarili']}, "
        f"hata={son_analiz['hata']}, mesaj='{son_analiz['mesaj']}'")

    return son_analiz


# =====================================================================
# EMAIL DOGRULAMA
# =====================================================================

def _email_dogrulama_yap(page, ulke_kodu):
    """Handle email verification after registration."""
    log("[REGISTER] Email dogrulama baslatiliyor...")

    okuyucu = OtpOkuyucu()
    try:
        okuyucu.baglan()
        sonuc = okuyucu.otp_bekle(timeout=60, max_deneme=3)

        if sonuc.get("link"):
            log(f"[REGISTER] Dogrulama linki: {sonuc['link']}")
            sayfa_git(page, sonuc["link"])
            insan_gibi_bekle(3.0, 5.0)
            screenshot_al(page, "verify_link_visited")
            log("[REGISTER] Dogrulama linki ziyaret edildi")
            return True

        if sonuc.get("otp"):
            log(f"[REGISTER] OTP kodu: {sonuc['otp']}")
            return _otp_kodu_gir(page, ulke_kodu, sonuc["otp"])

        log("[REGISTER] OTP/link bulunamadi")
        return False

    except TimeoutError:
        log("[REGISTER] Email dogrulama timeout")
        return False
    except ConnectionError as e:
        log(f"[REGISTER] IMAP hatasi: {e}")
        return False
    except Exception as e:
        log(f"[REGISTER] Email dogrulama hatasi: {type(e).__name__}: {e}")
        return False
    finally:
        okuyucu.kapat()


def _otp_kodu_gir(page, ulke_kodu, otp_kod):
    """Enter OTP code into the page."""
    try:
        otp_el = element_bul(page, ulke_kodu, "login", "otp_field", timeout=10000)
        otp_el.click()
        insan_gibi_bekle(0.3, 0.8)
        for karakter in otp_kod:
            otp_el.type(karakter, delay=random.randint(50, 150))
        insan_gibi_bekle(0.5, 1.0)
        log("[REGISTER] OTP girildi")

        # Submit
        try:
            submit_el = element_bul(page, ulke_kodu, "login", "submit_button", timeout=10000)
            submit_el.click()
            log("[REGISTER] OTP submit tiklandi")
            insan_gibi_bekle(3.0, 5.0)
        except Exception as e:
            log(f"[REGISTER] OTP submit hatasi: {e}")
        return True
    except Exception as e:
        log(f"[REGISTER] OTP giris hatasi: {type(e).__name__}: {e}")
        return False


# =====================================================================
# ANA AKIS
# =====================================================================

def register_yap(ulke_kodu: str):
    """Execute the full VFS Global registration flow.

    Akis:
        1. Ulke dogrula + kimlik yukle
        2. Tarayici baslat
        3. Kayit sayfasina git
        4. Cloudflare challenge kontrol
        5. Cookie modal kapat
        6. Form doldur (email, sifre, telefon, checkbox, Turnstile bekle)
        7. Form gonder + DETAYLI ANALIZ
        8. Sonuca gore islem yap
        9. Email dogrulama (gerekirse)
       10. Temizlik
    """
    log(f"[REGISTER] ===== KAYIT AKISI BASLATILIYOR: ulke={ulke_kodu} =====")

    pw = None
    context = None
    page = None

    try:
        # --- Step 1 ---
        log("[REGISTER] Adim 1: Ulke + kimlik")
        uy = UlkeYonetici()
        ulke = uy.ulke_al(ulke_kodu)
        log(f"[REGISTER] Ulke: {ulke['ad_en']} ({ulke_kodu})")

        kimlik = _env_kimlik_bilgileri_al()
        log(f"[REGISTER] Email: {kimlik['email']}")

        # --- Step 2 ---
        log("[REGISTER] Adim 2: Tarayici")
        pw, context, page = tarayici_baslat(ulke_kodu)
        log("[REGISTER] Tarayici OK")

        # --- Step 3 ---
        log("[REGISTER] Adim 3: Sayfa yukleme")
        register_url = uy.url_olustur(ulke_kodu, "register")
        log(f"[REGISTER] URL: {register_url}")
        sayfa_git(page, register_url)
        screenshot_al(page, "page_loaded")

        # --- Step 4 ---
        log("[REGISTER] Adim 4: Cloudflare kontrol")
        cf_var = cf_clearance_kontrol(context)
        if cf_var:
            log("[REGISTER] cf_clearance mevcut")

        # --- Step 5 ---
        log("[REGISTER] Adim 5: Cookie modal")
        _cookie_modal_kapat(page)

        # --- Step 6 ---
        log("[REGISTER] Adim 6: Form doldur")
        akis_calistir(
            "REGISTER_FORM_FILL",
            _form_doldur,
            page,
            ulke_kodu,
            kimlik,
        )

        # --- Step 7: Form gonder + analiz ---
        log("[REGISTER] Adim 7: Form gonder + analiz")
        submit_sonuc = akis_calistir(
            "REGISTER_FORM_SUBMIT",
            _form_gonder,
            page,
            ulke_kodu,
        )

        # --- Step 8: Sonuca gore islem ---
        log("[REGISTER] Adim 8: Sonuc degerlendirme")

        if isinstance(submit_sonuc, dict):
            if submit_sonuc.get("basarili"):
                log(f"[REGISTER] KAYIT BASARILI! Mesaj: {submit_sonuc.get('mesaj')}")
            elif submit_sonuc.get("hata"):
                hata = submit_sonuc["hata"]
                log(f"[REGISTER] KAYIT HATASI: {hata}")
                screenshot_al(page, "register_error_detected")
                raise Exception(f"Kayit basarisiz: {hata}")
            else:
                log(f"[REGISTER] Sonuc belirsiz: {submit_sonuc.get('mesaj')}")
                log("[REGISTER] Debug screenshot'lari kontrol edin")
        else:
            log("[REGISTER] submit_sonuc dict degil — eski davranis")

        # --- Step 9: Email dogrulama ---
        log("[REGISTER] Adim 9: Email dogrulama")
        otp_zorunlu = ulke.get("otp_zorunlu", False)

        # Basarili kayit sonrasi veya zorunlu ise dogrulama yap
        dogrulama_gerekli = otp_zorunlu

        if not dogrulama_gerekli:
            # Sayfa icerigi dogrulama istegi gosteriyor mu?
            try:
                sayfa_metni = page.inner_text("body").lower()
                for ipucu in BASARI_KALIPLARI:
                    if ipucu in sayfa_metni:
                        dogrulama_gerekli = True
                        log(f"[REGISTER] Sayfada dogrulama ipucu: '{ipucu}'")
                        break
            except Exception:
                pass

        if dogrulama_gerekli:
            log("[REGISTER] Email dogrulama baslatiliyor...")
            dogrulama_sonuc = _email_dogrulama_yap(page, ulke_kodu)
            if dogrulama_sonuc:
                log("[REGISTER] Email dogrulama BASARILI")
            else:
                log("[REGISTER] Email dogrulama BASARISIZ")
        else:
            log("[REGISTER] Email dogrulama gerekli degil")

        # --- Final ---
        screenshot_al(page, "register_completed")
        log(f"[REGISTER] ===== KAYIT TAMAMLANDI: ulke={ulke_kodu} =====")
        return True

    except ValueError as e:
        log(f"[REGISTER] DOGRULAMA HATASI: {e}")
        raise
    except Exception as e:
        log(f"[REGISTER] HATA: {type(e).__name__}: {e}")
        if page:
            screenshot_al(page, "register_critical_error")
        raise
    finally:
        log("[REGISTER] Tarayici kapatiliyor...")
        tarayici_kapat(pw, context, page)