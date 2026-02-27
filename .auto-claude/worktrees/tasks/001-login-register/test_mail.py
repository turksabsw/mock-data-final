#!/usr/bin/env python3
"""Test IMAP mail server connection"""
import os
from dotenv import load_dotenv
from imaplib import IMAP4_SSL
load_dotenv()
host = os.getenv("MAILCOW_HOST")
user = os.getenv("MAILCOW_USER")
password = os.getenv("MAILCOW_PASS")
port = 993  # IMAP SSL
print(f"Host: {host}")
print(f"User: {user}")
print(f"Port: {port}")
print("\n[*] Bağlanıyor...")
try:
    mail = IMAP4_SSL(host, port)
    print("✅ SSL bağlantı başarılı")
    mail.login(user, password)
    print("✅ Giriş başarılı")
    mail.select('INBOX')
    print("✅ INBOX seçildi")
    status, data = mail.search(None, 'ALL')
    msg_count = len(data[0].split()) if data[0] else 0
    print(f"✅ Toplam mesaj: {msg_count}")
    # Son 5 mail başlıklarını göster
    if msg_count > 0:
        print("\n[*] Son 5 mail başlığı:")
        msg_ids = data[0].split()[-5:]  # Son 5 mesaj
        for msg_id in msg_ids:
            status, msg_data = mail.fetch(msg_id, '(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])')
            print(f"\n--- Mesaj {msg_id.decode()} ---")
            print(msg_data[0][1].decode('utf-8', errors='ignore'))
    mail.logout()
    print('\n✅✅✅ MAIL SUNUCU ÇALIŞIYOR!')
except Exception as e:
    print(f'\n❌ HATA: {e}')
    print('Mail konfigürasyonu yanlış olabilir!')
