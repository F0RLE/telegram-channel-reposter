"""
Security module for Telegram Channel Reposter
Handles PIN protection and encryption
"""
import os
import json
import hashlib
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Security file path
SECURITY_FILE = os.path.join(os.environ.get("APPDATA", ""), "TelegramBotData", "data", "configs", "security.json")
SALT_FILE = os.path.join(os.environ.get("APPDATA", ""), "TelegramBotData", "data", "configs", ".salt")

class Security:
    """Security manager for PIN and encryption"""
    
    def __init__(self):
        self.data = self._load_data()
        self._salt = self._get_or_create_salt()
    
    def _load_data(self) -> dict:
        """Load security data"""
        default = {
            "pin_enabled": False,
            "pin_hash": None,
            "failed_attempts": 0,
            "lockout_until": None
        }
        try:
            if os.path.exists(SECURITY_FILE):
                with open(SECURITY_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    for key in default:
                        if key not in loaded:
                            loaded[key] = default[key]
                    return loaded
        except:
            pass
        return default
    
    def _save_data(self):
        """Save security data"""
        try:
            os.makedirs(os.path.dirname(SECURITY_FILE), exist_ok=True)
            with open(SECURITY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
        except:
            pass
    
    def _get_or_create_salt(self) -> bytes:
        """Get or create salt for hashing"""
        try:
            if os.path.exists(SALT_FILE):
                with open(SALT_FILE, 'rb') as f:
                    return f.read()
            else:
                salt = os.urandom(16)
                os.makedirs(os.path.dirname(SALT_FILE), exist_ok=True)
                with open(SALT_FILE, 'wb') as f:
                    f.write(salt)
                return salt
        except:
            return b'default_salt_12345'
    
    def _hash_pin(self, pin: str) -> str:
        """Hash PIN with salt"""
        salted = self._salt + pin.encode('utf-8')
        return hashlib.sha256(salted).hexdigest()
    
    def is_pin_enabled(self) -> bool:
        """Check if PIN protection is enabled"""
        return self.data.get("pin_enabled", False) and self.data.get("pin_hash") is not None
    
    def set_pin(self, pin: str) -> bool:
        """Set new PIN (4-8 digits)"""
        if not pin.isdigit() or len(pin) < 4 or len(pin) > 8:
            return False
        
        self.data["pin_enabled"] = True
        self.data["pin_hash"] = self._hash_pin(pin)
        self.data["failed_attempts"] = 0
        self.data["lockout_until"] = None
        self._save_data()
        return True
    
    def verify_pin(self, pin: str) -> bool:
        """Verify PIN"""
        if not self.is_pin_enabled():
            return True
        
        # Check lockout
        import time
        lockout_until = self.data.get("lockout_until")
        if lockout_until and time.time() < lockout_until:
            return False
        
        # Verify
        if self._hash_pin(pin) == self.data.get("pin_hash"):
            self.data["failed_attempts"] = 0
            self.data["lockout_until"] = None
            self._save_data()
            return True
        else:
            self.data["failed_attempts"] = self.data.get("failed_attempts", 0) + 1
            # Lockout after 5 failed attempts
            if self.data["failed_attempts"] >= 5:
                self.data["lockout_until"] = time.time() + 300  # 5 minutes
            self._save_data()
            return False
    
    def disable_pin(self) -> bool:
        """Disable PIN protection"""
        self.data["pin_enabled"] = False
        self.data["pin_hash"] = None
        self.data["failed_attempts"] = 0
        self.data["lockout_until"] = None
        self._save_data()
        return True
    
    def get_remaining_attempts(self) -> int:
        """Get remaining PIN attempts before lockout"""
        return max(0, 5 - self.data.get("failed_attempts", 0))
    
    def get_lockout_remaining(self) -> int:
        """Get remaining lockout time in seconds"""
        import time
        lockout_until = self.data.get("lockout_until")
        if lockout_until:
            remaining = int(lockout_until - time.time())
            return max(0, remaining)
        return 0
    
    def encrypt_value(self, value: str, pin: str) -> Optional[str]:
        """Encrypt a value using PIN as key"""
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(pin.encode()))
            f = Fernet(key)
            encrypted = f.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except:
            return None
    
    def decrypt_value(self, encrypted: str, pin: str) -> Optional[str]:
        """Decrypt a value using PIN as key"""
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(pin.encode()))
            f = Fernet(key)
            decrypted = f.decrypt(base64.urlsafe_b64decode(encrypted))
            return decrypted.decode()
        except:
            return None


# Global security instance
_security = None

def get_security() -> Security:
    """Get global security instance"""
    global _security
    if _security is None:
        _security = Security()
    return _security

