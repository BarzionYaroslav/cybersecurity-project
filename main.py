import os
from dotenv import load_dotenv

load_dotenv()

secret = os.getenv("APP_SECRET")
if not secret:
    print("ERROR: Secret key not found")
    exit(1)

print(f"System started. Secret hash: {secret[0:3]}**")
