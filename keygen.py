from cryptography.fernet import Fernet

# Генерируем ключ (один раз!)
key = Fernet.generate_key()
print(key.decode()) # b'...'
