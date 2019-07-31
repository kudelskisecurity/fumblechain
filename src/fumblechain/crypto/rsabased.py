"""
author: YRO

"""
import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization as ser
from cryptography.hazmat.primitives.asymmetric import rsa, padding, utils


class RsaBased:
    """Wallet crypto implementation using RSA.
    Useful because some attacks on RSA can be leveraged in the context of FumbleChain."""

    @staticmethod
    def generate_keypair():
        """Generate a new keypair."""
        skey: rsa.RSAPrivateKey = rsa.generate_private_key(
            public_exponent=3,
            key_size=1024,
            backend=default_backend()
        )

        pkey: rsa.RSAPublicKey = skey.public_key()

        return skey, pkey

    @staticmethod
    def sign(data, skey: rsa.RSAPrivateKey):
        """Sign the given data `data` with the given private key `skey`.
        Returns the signature."""
        sig = skey.sign(data, padding.PKCS1v15(), utils.Prehashed(hashes.MD5()))
        return sig

    @staticmethod
    def verify(sig, data, pkey: rsa.RSAPublicKey):
        """Verify that the signature `sig` is valid for data `data` and public key `pkey`.
        Returns True if the signature is valid, False otherwise."""
        try:
            pkey.verify(sig, data, padding.PKCS1v15(), utils.Prehashed(hashes.MD5()))
        except InvalidSignature:
            return False
        return True

    @staticmethod
    def get_address(public_key):
        """Returns the wallet address associated with the given public key."""
        pem = public_key.public_bytes(
            encoding=ser.Encoding.PEM,
            format=ser.PublicFormat.SubjectPublicKeyInfo
        )
        return base64.b64encode(pem).decode('utf-8')

    @staticmethod
    def get_public_key_from_address(data):
        """Returns the public key associated to the given address."""
        pkey_pem = base64.b64decode(data.encode('utf-8'))
        pkey = ser.load_pem_public_key(pkey_pem, backend=default_backend())
        return pkey

    @staticmethod
    def save_private_key(skey, filename):
        """Write the given private key `skey` to the file located at given path `filename`."""
        pem_data = RsaBased.get_private_key(skey)
        with open(filename, "wb") as f:
            f.write(pem_data)

    @staticmethod
    def get_private_key(skey):
        """Returns the given private key `skey` in PEM format."""
        pem_data = skey.private_bytes(
            encoding=ser.Encoding.PEM,
            format=ser.PrivateFormat.PKCS8,
            encryption_algorithm=ser.NoEncryption()
        )
        return pem_data

    @staticmethod
    def load_keys(filename):
        """Returns the private and public keys contained in the PEM file located at given path `filename`."""
        with open(filename, "rb") as f:
            pem_data = f.read()
        return RsaBased.load_keys_from_bytes(pem_data)

    @staticmethod
    def load_keys_from_bytes(b):
        """Returns the private and public keys contained in the given PEM bytes `b`.
        Returns a tuple (private key, public key)."""
        skey: rsa.RSAPrivateKeyWithSerialization = ser.load_pem_private_key(
            b,
            password=None,
            backend=default_backend()
        )
        pkey = skey.public_key()
        return (skey, pkey)
