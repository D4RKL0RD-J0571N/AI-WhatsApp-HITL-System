
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# Generate Private Key
private_key = ed25519.Ed25519PrivateKey.generate()

# Serialize Private Key
pem_private = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# Generate Public Key
public_key = private_key.public_key()
pem_public = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

# Save to files
with open("dev_private_key.pem", "wb") as f:
    f.write(pem_private)

with open("dev_public_key.pem", "wb") as f:
    f.write(pem_public)

print("Keys generated: dev_private_key.pem (offline) and dev_public_key.pem (public)")
