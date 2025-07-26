import os
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Base directory where your rpki_nodes folders are located
base_path = "."

# AS numbers: odd numbers from 01 to 19 (as01, as03, ..., as19)
as_numbers = [f"{i:02d}" for i in range(1, 21, 2)]

for asn in as_numbers:
    folder_name = f"as{asn}"
    folder_path = os.path.join(base_path, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    # Generate RSA private key (2048 bits)
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Save private key to PEM format inside AS folder
    key_filename = f"as_{asn}_private_key.pem"
    key_path = os.path.join(folder_path, key_filename)

    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    print(f"✅ Private key generated: {key_path}")
