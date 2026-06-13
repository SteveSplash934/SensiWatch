import datetime
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import NameOID
from cryptography import x509


def secure_file_permissions(filepath: Path) -> None:
    """Enforce strict ACLs on private key material based on the host OS."""
    if not filepath.exists():
        return

    if platform.system() == "Windows":
        # Remove inheritance, strictly grant access to SYSTEM and Administrators
        subprocess.run([
            "icacls", str(filepath),
            "/inheritance:r",
            "/grant:r", "SYSTEM:F",
            "/grant:r", "Administrators:F"
        ], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        # Strict POSIX mask
        os.chmod(filepath, 0o600)


class EmbeddedCA:
    """
    SensiWatch Internal Certificate Authority.
    Handles Root CA lifecycle and short-lived client certificate signing.
    """

    def __init__(self, ca_dir: Path):
        self.ca_dir = ca_dir
        self.ca_dir.mkdir(parents=True, exist_ok=True)
        self.ca_key_path = self.ca_dir / "ca_key.pem"
        self.ca_cert_path = self.ca_dir / "ca_cert.pem"
        
        self.ca_private_key: Optional[PrivateKeyTypes] = None
        self.ca_certificate: Optional[x509.Certificate] = None
        
        self._initialize_ca()

    def _initialize_ca(self) -> None:
        """Loads existing CA or generates a new one if missing."""
        if self.ca_key_path.exists() and self.ca_cert_path.exists():
            self._load_ca()
        else:
            self._generate_ca()

    def _load_ca(self) -> None:
        """Loads existing CA assets into memory."""
        with open(self.ca_key_path, "rb") as f:
            self.ca_private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
            )
        with open(self.ca_cert_path, "rb") as f:
            self.ca_certificate = x509.load_pem_x509_certificate(f.read())

    def _generate_ca(self) -> None:
        """Bootstraps a highly secure ECDSA Root CA for mTLS."""
        # Using SECP256R1 for optimal performance vs security in TLS handshakes
        self.ca_private_key = ec.generate_private_key(ec.SECP256R1())
        
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SensiWatch Enterprise"),
            x509.NameAttribute(NameOID.COMMON_NAME, "SensiWatch Internal Root CA"),
        ])
        
        self.ca_certificate = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            self.ca_private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650) # 10 Year CA Life
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True
        ).sign(self.ca_private_key, hashes.SHA256())
        
        # Serialize and save to disk
        with open(self.ca_key_path, "wb") as f:
            f.write(self.ca_private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
            
        secure_file_permissions(self.ca_key_path)
            
        with open(self.ca_cert_path, "wb") as f:
            f.write(self.ca_certificate.public_bytes(serialization.Encoding.PEM))

    def sign_client_csr(self, csr_pem: bytes, valid_days: int = 7) -> bytes:
        """
        Validates a client Certificate Signing Request and issues a short-lived cert.
        
        Returns:
            bytes: The PEM-encoded signed client certificate.
        """
        # Runtime assertions to guarantee state for strict type checking
        if self.ca_certificate is None or self.ca_private_key is None:
            raise RuntimeError("CA Engine is not initialized.")
            
        if not isinstance(self.ca_private_key, ec.EllipticCurvePrivateKey):
            raise TypeError("CA private key must be an Elliptic Curve key.")

        csr = x509.load_pem_x509_csr(csr_pem)
        
        if not csr.is_signature_valid:
            raise ValueError("Invalid CSR signature")
            
        client_cert = x509.CertificateBuilder().subject_name(
            csr.subject
        ).issuer_name(
            self.ca_certificate.subject
        ).public_key(
            csr.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=valid_days)
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
            critical=True
        ).add_extension(
            # Restrict this explicitly to Client Authentication for mTLS
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=True
        ).sign(self.ca_private_key, hashes.SHA256())
        
        return client_cert.public_bytes(serialization.Encoding.PEM)