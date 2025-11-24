import os
import socket
import subprocess
import sys
import ipaddress
from pathlib import Path
from datetime import datetime, timedelta, timezone
# Import custom configuration variables
# CERTIFICATE_LIFETIME_DAYS: How many days the certificate is valid (e.g., 3650 for 10 years)
# CERTIFICATE_ORGANIZATION_NAME: The "Friendly Name" displayed in certificate details
from ZeCo_config import CERTIFICATE_LIFETIME_DAYS, CERTIFICATE_ORGANIZATION_NAME

try:
    # We use the 'cryptography' library for generating secure certificates.
    # It is a standard Python library for cryptographic recipes and primitives.
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
except ImportError:
    # If cryptography is not installed, we install it automatically using pip.
    print("Installing required package: cryptography...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

def get_local_ip():
    """
    Determines the local IP address of the machine.
    This is important so other devices on the network can connect to this server.
    """
    try:
        # We create a dummy socket connection to a public DNS (Google's 8.8.8.8)
        # to figure out which network interface is used for internet access.
        # No actual data is sent.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # Fallback to localhost if no network is available
        return "127.0.0.1"

def generate_self_signed_cert(cert_dir: Path):
    """
    Generates a self-signed SSL/TLS certificate and private key.
    
    A self-signed certificate allows us to use HTTPS (encryption) without paying 
    a Certificate Authority (CA). However, browsers will warn about it unless 
    we manually "trust" it (install it) on each device.
    """
    cert_dir.mkdir(exist_ok=True)
    key_path = cert_dir / "key.pem"   # The private key (KEEP SECRET)
    cert_path = cert_dir / "cert.pem" # The public certificate (Share this)

    if key_path.exists() and cert_path.exists():
        print(f"Certificates already exist in {cert_dir}")
        return cert_path

    hostname = socket.gethostname()
    ip = get_local_ip()
    
    print(f"Generating self-signed certificates for {hostname} ({ip})...")

    # 1. Generate Private Key
    # We use RSA algorithm with a key size of 2048 bits (standard security).
    # public_exponent=65537 is the industry standard default.
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # 2. Define Certificate Subject (Who owns this cert?)
    # Common Name (CN): Usually the hostname.
    # Organization Name (O): The "Friendly Name" you see in certificate details.
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, CERTIFICATE_ORGANIZATION_NAME),
    ])

    # 3. Define Subject Alternative Names (SANs)
    # These are ALL the valid addresses for this certificate.
    # If you access the site via an IP/name not in this list, you get a warning.
    alt_names = [
        x509.DNSName(hostname),
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        x509.IPAddress(ipaddress.ip_address(ip)),
    ]

    # 4. Build the Certificate
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer # Self-signed, so issuer is same as subject
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.now(timezone.utc)
    ).not_valid_after(
        # Validity period defined in config (default 10 years)
        datetime.now(timezone.utc) + timedelta(days=CERTIFICATE_LIFETIME_DAYS)
    ).add_extension(
        x509.SubjectAlternativeName(alt_names),
        critical=False,
    ).add_extension(
        # Key Usage: Defines what this cert can do.
        # digital_signature & key_encipherment are needed for TLS (HTTPS).
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
        # Extended Key Usage: Says this cert is for a Web Server and a Web Client.
        x509.ExtendedKeyUsage([
            x509.ExtendedKeyUsageOID.SERVER_AUTH,
            x509.ExtendedKeyUsageOID.CLIENT_AUTH,
        ]),
        critical=False,
    ).sign(key, hashes.SHA256()) # Sign with our own key using SHA256

    # 5. Save Private Key to file
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    # 6. Save Certificate to file
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
        # This command rebuilds the list of trusted CA certificates on Linux
        print("Updating CA certificates...")
        subprocess.run(["sudo", "update-ca-certificates"], check=True)
        
        print("Successfully added certificate to Trusted Root Store.")
    except subprocess.CalledProcessError as e:
        print("Failed to add certificate to trust store.")
        print(f"Error: {e}")

def trust_certificate(cert_path: Path):
    """Adds the certificate to the Trusted Root Store based on OS."""
    if os.name == 'nt': # Windows
        print("\nAttempting to add certificate to Windows Trusted Root Store...")
        print("You may see a User Account Control (UAC) prompt. Please click 'Yes'.")
        try:
            # We use the built-in Windows 'certutil' command.
            # -addstore "Root": Adds to the Trusted Root Certification Authorities store.
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
    
    # Step 1: Generate the certificate
    cert_path = generate_self_signed_cert(cert_dir)
    if not cert_path:
        cert_path = cert_dir / "cert.pem"
    
    # Step 2: Copy cert to frontend/public
    # This allows users to download it from http://localhost/zeco.crt
    frontend_public_cert = root_dir / "frontend" / "public" / "zeco.crt"
    import shutil
    try:
        shutil.copy(cert_path, frontend_public_cert)
        print(f"Copied certificate to {frontend_public_cert}")
    except Exception as e:
        print(f"Failed to copy certificate to frontend: {e}")

    # Step 3: Ensure environment files exist
    update_env_files(root_dir)
    
    # Step 4: Ask user to trust the certificate (Windows/Linux only)
    print("\nDo you want to trust this certificate to avoid browser warnings? (Requires Admin)")
    response = input("Type 'yes' to proceed, or anything else to skip: ").strip().lower()
    if response == 'yes':
        trust_certificate(cert_path)
    
    hostname = socket.gethostname()
    ip = get_local_ip()
    
    print("\n" + "="*50)
    print("Setup Complete!")
    print("="*50)
    print(f"To access your application:")
    print(f"Guest (HTTP): http://{hostname} or http://{ip}")
    print(f"Staff (HTTPS): https://{hostname} or https://{ip}")
    print("="*50)

if __name__ == "__main__":
    main()
