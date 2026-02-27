"""
VISE OS — Mailcow IMAP OTP Reader

Connects to Mailcow IMAP server via imap-tools library to retrieve OTP codes
and verification links from VFS Global emails. Supports IDLE mode for
near-instant email detection instead of naive polling.

Credentials loaded from .env: MAILCOW_HOST, MAILCOW_USER, MAILCOW_PASS, MAILCOW_PORT.
"""

import os
import re

from imap_tools import MailBox, AND

from src.utils import log, insan_gibi_bekle


class OtpOkuyucu:
    """Mailcow IMAP OTP reader for VFS verification emails.

    Uses imap-tools MailBox for IMAP SSL connection with IDLE mode support.
    Credentials loaded from .env via MAILCOW_HOST/USER/PASS/PORT.

    Usage:
        okuyucu = OtpOkuyucu()
        okuyucu.baglan()
        try:
            sonuc = okuyucu.otp_bekle(timeout=60)
            if sonuc["otp"]:
                # Use OTP code
            elif sonuc["link"]:
                # Open verification link
        finally:
            okuyucu.kapat()
    """

    # VFS email sender patterns for filtering
    VFS_GONDERICI_KALIPLARI = [
        "vfsglobal.com",
        "vfsevisa.com",
        "noreply",
        "no-reply",
    ]

    # Regex patterns for OTP code extraction (checked in order)
    OTP_KALIPLARI = [
        r'(?:OTP|code|verification|doğrulama|kod)[:\s]+(\d{4,8})',
        r'\b(\d{6})\b',
        r'\b(\d{4})\b',
        r'\b(\d{8})\b',
    ]

    # Regex patterns for verification link extraction (checked in order)
    LINK_KALIPLARI = [
        r'(https?://[^\s<>"]+(?:verify|confirm|activate|validate)[^\s<>"]*)',
        r'(https?://[^\s<>"]+(?:token|code|otp)[^\s<>"]*)',
        r'(https?://visa\.vfsglobal\.com[^\s<>"]+)',
    ]

    def __init__(self):
        """Initialize OTP reader with credentials from .env.

        Reads MAILCOW_HOST, MAILCOW_USER, MAILCOW_PASS, MAILCOW_PORT
        from environment. Logs a warning if credentials are missing.
        """
        self._host = os.getenv("MAILCOW_HOST", "")
        self._user = os.getenv("MAILCOW_USER", "")
        self._pass = os.getenv("MAILCOW_PASS", "")
        self._port = int(os.getenv("MAILCOW_PORT", "993"))
        self._mailbox = None
        self._bagli = False

        if not self._host:
            log("[OTP] UYARI: MAILCOW_HOST .env'de tanimli degil")
        if not self._user or not self._pass:
            log("[OTP] UYARI: MAILCOW_USER veya MAILCOW_PASS .env'de tanimli degil")

    def baglan(self):
        """Connect to Mailcow IMAP server via SSL.

        Uses imap-tools MailBox with login to INBOX folder.
        Connection is kept open for subsequent operations (IDLE, fetch).

        Raises:
            Exception: If connection or authentication fails. Logged before re-raising.
        """
        log(f"[OTP] IMAP baglaniliyor: {self._host}:{self._port}")

        try:
            self._mailbox = MailBox(self._host, port=self._port)
            self._mailbox.login(self._user, self._pass, "INBOX")
            self._bagli = True
            log("[OTP] IMAP baglantisi basarili")
        except Exception as e:
            log(f"[OTP] IMAP baglanti hatasi: {type(e).__name__}: {e}")
            self._bagli = False
            raise

    def otp_bekle(self, timeout=60, max_deneme=3):
        """Wait for a VFS OTP email and extract the code or verification link.

        Pipeline:
            1. First checks for existing unread VFS emails
            2. If none found, enters IDLE mode to wait for new emails
            3. On IDLE update, fetches unseen emails and extracts OTP/link
            4. Retries up to max_deneme times with ~10s intervals between attempts

        Designed to complete within 30 seconds of email arrival (OTP validity: 60-90s).

        Args:
            timeout: IDLE wait timeout in seconds per attempt (default: 60).
            max_deneme: Maximum retry attempts (default: 3).

        Returns:
            dict: Result with keys:
                - otp: Extracted OTP code string (or None if link-based)
                - link: Verification URL string (or None if OTP-based)
                - konu: Email subject
                - gonderen: Email sender

        Raises:
            ConnectionError: If not connected (baglan() not called).
            TimeoutError: If no VFS email received after all retries.
            Exception: If IMAP operation fails. Logged before re-raising.
        """
        if not self._bagli or not self._mailbox:
            raise ConnectionError(
                "[OTP] IMAP baglantisi yok — once baglan() cagirilmali"
            )

        log(f"[OTP] OTP bekleniyor: timeout={timeout}s, max_deneme={max_deneme}")

        # First check if there's already an unread VFS email
        sonuc = self._mevcut_otp_ara()
        if sonuc:
            return sonuc

        # IDLE mode: wait for new emails in real-time
        for deneme in range(1, max_deneme + 1):
            log(f"[OTP] IDLE deneme {deneme}/{max_deneme} (timeout={timeout}s)")

            try:
                responses = self._mailbox.idle.wait(timeout=timeout)

                if responses:
                    log(f"[OTP] IDLE guncelleme alindi: {len(responses)} yanit")

                    # Fetch unseen VFS emails after IDLE update
                    sonuc = self._mevcut_otp_ara()
                    if sonuc:
                        return sonuc

                    log("[OTP] Guncelleme alindi ama VFS emaili bulunamadi")
                else:
                    log(f"[OTP] IDLE timeout — {timeout}s icinde guncelleme yok")

            except Exception as e:
                log(
                    f"[OTP] IDLE hatasi deneme {deneme}/{max_deneme}: "
                    f"{type(e).__name__}: {e}"
                )
                if deneme == max_deneme:
                    raise

            # Wait between retries (except after last attempt)
            if deneme < max_deneme:
                log("[OTP] Yeniden denemeden once bekleniyor...")
                insan_gibi_bekle(8.0, 12.0)

        raise TimeoutError(
            f"[OTP] OTP emaili {max_deneme} denemede alinamadi "
            f"(toplam ~{max_deneme * timeout}s beklendi)"
        )

    def _mevcut_otp_ara(self):
        """Search for existing unread VFS emails and extract OTP/link.

        Fetches unseen emails (newest first) and checks each against
        VFS sender/subject patterns. Returns the first successful extraction.

        Returns:
            dict or None: Extraction result dict if found, None otherwise.

        Raises:
            Exception: If IMAP fetch operation fails. Logged before re-raising.
        """
        try:
            for msg in self._mailbox.fetch(AND(seen=False), reverse=True):
                # Check if this is a VFS-related email
                if not self._vfs_emaili_mi(msg):
                    continue

                log(
                    f"[OTP] VFS emaili bulundu: "
                    f"konu='{msg.subject}', gonderen='{msg.from_}'"
                )

                # Try OTP extraction first (more common for login)
                otp_kod = self.otp_cikart(msg)
                if otp_kod:
                    log(f"[OTP] OTP kodu cikarildi: {otp_kod}")
                    return {
                        "otp": otp_kod,
                        "link": None,
                        "konu": msg.subject,
                        "gonderen": msg.from_,
                    }

                # Try verification link extraction (more common for registration)
                link = self.link_cikart(msg)
                if link:
                    log(f"[OTP] Dogrulama linki cikarildi: {link}")
                    return {
                        "otp": None,
                        "link": link,
                        "konu": msg.subject,
                        "gonderen": msg.from_,
                    }

                log(
                    f"[OTP] VFS emailinde OTP veya link bulunamadi: "
                    f"konu='{msg.subject}'"
                )

        except Exception as e:
            log(f"[OTP] Email arama hatasi: {type(e).__name__}: {e}")
            raise

        return None

    def _vfs_emaili_mi(self, msg):
        """Check if an email message is from VFS Global.

        Matches against known VFS sender patterns and subject keywords.

        Args:
            msg: imap-tools message object with .from_ and .subject attributes.

        Returns:
            bool: True if message appears to be from VFS.
        """
        gonderen = (msg.from_ or "").lower()
        konu = (msg.subject or "").lower()

        # Check sender patterns
        for kalip in self.VFS_GONDERICI_KALIPLARI:
            if kalip in gonderen:
                return True

        # Check subject for VFS-related keywords
        vfs_konu_kaliplari = [
            "vfs", "verification", "verify", "otp",
            "one-time", "password", "doğrulama", "kod",
        ]
        for kalip in vfs_konu_kaliplari:
            if kalip in konu:
                return True

        return False

    def otp_cikart(self, msg):
        """Extract OTP code from email message body.

        Searches both plain text and HTML content with multiple regex patterns.
        Patterns are tried in priority order: labeled codes first, then
        positional digit patterns (6-digit, 4-digit, 8-digit).

        Args:
            msg: imap-tools message object with .text and .html attributes.

        Returns:
            str or None: Extracted OTP code string, or None if not found.
        """
        # Collect available content bodies
        icerikler = []
        if msg.text:
            icerikler.append(msg.text)
        if msg.html:
            icerikler.append(msg.html)

        if not icerikler:
            log("[OTP] Email govdesi bos — OTP cikarilemiyor")
            return None

        for icerik in icerikler:
            for kalip in self.OTP_KALIPLARI:
                eslesme = re.search(kalip, icerik, re.IGNORECASE)
                if eslesme:
                    kod = eslesme.group(1)
                    log(f"[OTP] Regex eslesti: kalip='{kalip}', kod='{kod}'")
                    return kod

        return None

    def link_cikart(self, msg):
        """Extract verification link from email message body.

        Searches both plain text and HTML content for verification URLs.
        Patterns prioritize VFS-specific URLs and common verification paths.

        Args:
            msg: imap-tools message object with .text and .html attributes.

        Returns:
            str or None: Extracted verification URL string, or None if not found.
        """
        # Collect available content bodies
        icerikler = []
        if msg.text:
            icerikler.append(msg.text)
        if msg.html:
            icerikler.append(msg.html)

        if not icerikler:
            log("[OTP] Email govdesi bos — link cikarilemiyor")
            return None

        for icerik in icerikler:
            for kalip in self.LINK_KALIPLARI:
                eslesme = re.search(kalip, icerik, re.IGNORECASE)
                if eslesme:
                    link = eslesme.group(1)
                    # Clean trailing punctuation from URL
                    link = link.rstrip(".,;:!?)'\"")
                    log(f"[OTP] Link regex eslesti: kalip='{kalip}'")
                    return link

        return None

    def kapat(self):
        """Close IMAP connection and cleanup.

        Safe to call multiple times — handles already-closed connections gracefully.
        Always resets internal state regardless of logout success.
        """
        log("[OTP] IMAP baglantisi kapatiliyor...")

        if self._mailbox:
            try:
                self._mailbox.logout()
                log("[OTP] IMAP baglantisi kapatildi")
            except Exception as e:
                log(f"[OTP] IMAP kapatma hatasi: {type(e).__name__}: {e}")
            finally:
                self._mailbox = None
                self._bagli = False
        else:
            log("[OTP] IMAP baglantisi zaten kapali")
