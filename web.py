from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

# Generate key pair
private_key = ec.generate_private_key(ec.SECP256R1())
private_bytes = private_key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption()
)
public_key = private_key.public_key()
public_bytes = public_key.public_bytes(
    serialization.Encoding.X962,
    serialization.PublicFormat.UncompressedPoint
)

print("Private Key (PEM):")
print(private_bytes.decode())
print("\nPublic Key (Base64 URL-safe):")
print(base64.urlsafe_b64encode(public_bytes).decode())
