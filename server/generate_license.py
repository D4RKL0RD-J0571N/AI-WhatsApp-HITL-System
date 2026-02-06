
import jwt
import datetime
from cryptography.hazmat.primitives import serialization

# Path to your OFFLINE private key
PRIVATE_KEY_PATH = "keys/private.pem"

def generate_license(license_data: dict, private_key_path: str = None) -> str:
    """
    Generates a signed JWT license key.
    
    Expected license_data keys:
    - business_name (str)
    - plan (str) ["starter", "pro", "enterprise"]
    - features (list)
    - max_seats (int)
    - days_valid (int) - helper to calc expires_at
    """
    if private_key_path is None:
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        private_key_path = os.path.join(base_dir, PRIVATE_KEY_PATH)
    
    # Calculate Expiration
    days = license_data.pop("days_valid", 365)
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=days)
    
    payload = {
        **license_data,
        "expires_at": expires_at.isoformat() + "Z"
    }
    
    # Load Private Key
    with open(private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
        
    # Sign Token (EdDSA is robust and modern)
    token = jwt.encode(payload, private_key, algorithm="EdDSA")
    return token

if __name__ == "__main__":
    # Example License Generation (FOR DEV/SALES USE ONLY)
    dummy_data = {
        "business_name": "Test Enterprise",
        "plan": "pro",
        "features": ["whatsapp", "hitl_review", "analytics", "branding"],
        "max_seats": 5,
        "days_valid": 365
    }
    
    key = generate_license(dummy_data)
    print("\n--- GENERATED LICENSE KEY ---\n")
    print(key)
    print("\n----------------------------\n")
