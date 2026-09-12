import os
import json
import hashlib
import time
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("HASH_SECRET_KEY", "default-fallback-key")


class SecurityManager:
    @staticmethod
    def sign_data(data):
        clean_data = {k: v for k, v in data.items() if k != "signature"}
        payload = json.dumps(clean_data, sort_keys=True) + SECRET_KEY
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def is_payload_valid(message, receiver_id):
        sender_id = message.get("agent_id")

        try:
            float(message.get("position_x", 0))
            float(message.get("position_y", 0))
            float(message.get("speed", 0))
        except (ValueError, TypeError):
            print(f"[{receiver_id}] ❌ CORRUPT PACKAGE rejected from {sender_id}!")
            return False

        # LEVEL 2: Heartbeat & Anti-Ghosting
        msg_time = message.get("timestamp", time.time())
        if time.time() - msg_time > 2.0:
            return False  # Expired package / Ghost car

        # LEVEL 3: Authenticity
        received_sig = message.get("signature", "")
        expected_sig = SecurityManager.sign_data(message)

        if received_sig != expected_sig:
            print(
                f"[{receiver_id}] CYBER ATTACK DETECTED! Fake signature from {sender_id}!"
            )
            return False

        return True
