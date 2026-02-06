
import jwt
import datetime
import os
from fastapi import HTTPException
from cryptography.hazmat.primitives import serialization

# In production, this might be loaded from env or a secure volume
PUBLIC_KEY_PATH = "keys/public.pem"

class LicensingService:
    @staticmethod
    def get_public_key():
        # Lazy loading or caching could be implemented here
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            key_path = os.path.join(base_dir, "..", PUBLIC_KEY_PATH)
            
            with open(key_path, "rb") as f:
                return serialization.load_pem_public_key(f.read())
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="License validation key missing on server.")

    @staticmethod
    def verify_license(token: str) -> dict:
        public_key = LicensingService.get_public_key()
        
        try:
            # Decode & Verify Signature
            # Note: We must explicitly trust the algorithm used for signing
            payload = jwt.decode(token, public_key, algorithms=["EdDSA"])
            
            # Validate Expiration
            exp_str = payload.get("expires_at", "")
            if not exp_str:
                raise jwt.InvalidTokenError("Missing expiration")
                
            # Parse ISOv8601-like string
            expires_at = datetime.datetime.fromisoformat(exp_str.replace("Z", ""))
            
            if datetime.datetime.utcnow() > expires_at:
                raise HTTPException(status_code=402, detail="License Expired. Please renew subscription.")
                
            return payload
            
        except jwt.InvalidSignatureError:
            raise HTTPException(status_code=402, detail="Invalid License Signature.")
        except jwt.InvalidTokenError as e:
             raise HTTPException(status_code=402, detail=f"Invalid License: {str(e)}")
        except Exception as e:
             # Catch-all for malformed strings
             raise HTTPException(status_code=402, detail="Malformed License Key.")

    @staticmethod
    def require_feature(feature_name: str, license_token: str):
        """Helper to check feature flags programmatically"""
        payload = LicensingService.verify_license(license_token)
        if feature_name not in payload.get("features", []):
            raise HTTPException(
                status_code=403, 
                detail=f"Feature '{feature_name}' is not included in your {payload.get('plan', 'basic')} plan."
            )
        return payload
