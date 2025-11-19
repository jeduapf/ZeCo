import os
import socket
import subprocess
import sys
import ipaddress
from pathlib import Path
from datetime import datetime, timedelta, timezone

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("Installing required package: cryptography...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def generate_self_signed_cert(cert_dir: Path):
    """Generates self-signed certificate and key using cryptography library."""
    cert_dir.mkdir(exist_ok=True)
    key_path = cert_dir / "key.pem"
    cert_path = cert_dir / "cert.pem"

    if key_path.exists() and cert_path.exists():
        print(f"Certificates already exist in {cert_dir}")
        return cert_path

    hostname = socket.gethostname()
    ip = get_local_ip()
    
    print(f"Generating self-signed certificates for {hostname} ({ip})...")

    # Generate key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Generate certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ])

    alt_names = [
        x509.DNSName(hostname),
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        x509.IPAddress(ipaddress.ip_address(ip)),
    ]

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.now(timezone.utc)
    ).not_valid_after(
        datetime.now(timezone.utc) + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName(alt_names),
        critical=False,
    ).add_extension(
        x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=True,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False,
        ),
        critical=True,
    ).add_extension(
        x509.ExtendedKeyUsage([
            x509.ExtendedKeyUsageOID.SERVER_AUTH,
            x509.ExtendedKeyUsageOID.CLIENT_AUTH,
        ]),
        critical=False,
    ).sign(key, hashes.SHA256())

    # Write key
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    # Write cert
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    print(f"Successfully generated {key_path} and {cert_path}")
    return cert_path

def trust_certificate_linux(cert_path: Path):
    """Adds the certificate to the Linux Trusted Root Store (Debian/Ubuntu/Alpine)."""
    print("\nAttempting to add certificate to Linux Trusted Root Store...")
    print("This requires sudo privileges.")
    
    try:
        # 1. Copy to ca-certificates folder
        # Common path for Debian/Ubuntu/Alpine
        target_dir = Path("/usr/local/share/ca-certificates")
        if not target_dir.exists():
            # Fallback or try to create
            print(f"Target directory {target_dir} does not exist. Trying to create...")
            subprocess.run(["sudo", "mkdir", "-p", str(target_dir)], check=True)

        target_path = target_dir / "zeco-selfsigned.crt" # Must end in .crt
        
        print(f"Copying {cert_path} to {target_path}...")
        subprocess.run(["sudo", "cp", str(cert_path), str(target_path)], check=True)
        
        # 2. Update certificates
        print("Updating CA certificates...")
        subprocess.run(["sudo", "update-ca-certificates"], check=True)
        
        print("Successfully added certificate to Trusted Root Store.")
    except subprocess.CalledProcessError as e:
        print("Failed to add certificate to trust store.")
        print(f"Error: {e}")

def trust_certificate(cert_path: Path):
    """Adds the certificate to the Trusted Root Store based on OS."""
    if os.name == 'nt':
        print("\nAttempting to add certificate to Windows Trusted Root Store...")
        print("You may see a User Account Control (UAC) prompt. Please click 'Yes'.")
        try:
            subprocess.run(
                ["certutil", "-addstore", "Root", str(cert_path)], 
                check=True
            )
            print("Successfully added certificate to Trusted Root Store.")
        except subprocess.CalledProcessError as e:
            print("Failed to add certificate to trust store.")
            print(f"Error: {e}")
    elif os.name == 'posix':
        # Check if it's Linux (Darwin is macOS, which uses Keychain, not covered here yet)
        import platform
        if platform.system() == 'Linux':
            trust_certificate_linux(cert_path)
        else:
            print(f"Automatic trust configuration is not yet implemented for {platform.system()}.")
            print("Please manually add the certificate to your system's trust store.")
    else:
        print(f"Automatic trust configuration is not supported on {os.name}.")

def update_env_files(root_dir: Path):
    """Updates or creates .env files if needed."""
    backend_env = root_dir / "backend" / ".env"
    if not backend_env.exists():
        print("Creating backend/.env...")
        with open(backend_env, "w") as f:
            f.write("DEBUG=True\n")
            f.write("API_VERSION=v1\n")

def main():
    root_dir = Path(__file__).parent
    cert_dir = root_dir / "certs"
    
    # cert_path = generate_self_signed_cert(cert_dir)
    # if not cert_path:
    #     cert_path = cert_dir / "cert.pem"
        
    update_env_files(root_dir)
    
    # Ask user if they want to trust the cert
    # print("\nDo you want to trust this certificate to avoid browser warnings? (Requires Admin)")
    # response = input("Type 'yes' to proceed, or anything else to skip: ").strip().lower()
    # if response == 'yes':
    #     trust_certificate(cert_path)
    
    hostname = socket.gethostname()
    ip = get_local_ip()
    
    print("\n" + "="*50)
    print("Setup Complete!")
    print("="*50)
    print(f"To access your application (HTTP):")
    print(f"Frontend: http://{hostname}:5173")
    print(f"          http://{ip}:5173")
    print(f"          http://localhost:5173")
    print("="*50)

if __name__ == "__main__":
    main()
