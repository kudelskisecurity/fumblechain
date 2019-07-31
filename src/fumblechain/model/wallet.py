"""
author: YRO

Implements the basic wallet functionalities, such as creating a keypair, signing a transaction, etc.
"""
from crypto.rsabased import RsaBased as Crypt


class Wallet:
    """Represents a wallet."""

    def __init__(self):
        self.skey = None
        self.pkeyi = None

    def create_keys(self):
        """Generate a new key pair for this wallet."""
        self.skey, self.pkey = Crypt.generate_keypair()

    def sign(self, data):
        """Sign the given data with this wallet's private key and return the signature produced."""
        sig = Crypt.sign(data, self.skey)
        return sig

    def verify(self, sig, data, pkey=None):
        """Returns True if the given signature `sig` is verified for the given `data`."""
        if pkey is None:
            pkey = self.pkey
        sig = Crypt.verify(sig, data, pkey)
        return sig

    def _set_keys(self, skey, pkey):
        """Sets the given private key `skey` and public key `pkey` for this wallet."""
        self.skey = skey
        self.pkey = pkey

    def get_address(self):
        """Returns this wallet's public address."""
        return Crypt.get_address(self.pkey)

    def get_private_key(self):
        """Returns this walet's private key."""
        return Crypt.get_private_key(self.skey)

    def sign_transaction(self, trans):
        """Sign the given transaction `trans` with this wallet's private key.
        Returns True if successful. False otherise."""
        sig = self.sign(bytes.fromhex(trans.get_hash()))
        return trans.add_signature(sig.hex())

    @staticmethod
    def verify_transaction(trans):
        """Returns true if the given transaction has a valid signature. False otherwise."""
        try:
            return Crypt.verify(bytes.fromhex(trans.signature),
                                bytes.fromhex(trans.get_hash()),
                                Crypt.get_public_key_from_address(trans.src))
        except:
            return False

    @staticmethod
    def load_keys(filename):
        """Sets this wallet's public and private keys from data stored
        in the file located at given path `filename`."""
        skey, pkey = Crypt.load_keys(filename)
        w = Wallet()
        w._set_keys(skey, pkey)
        return w

    @staticmethod
    def load_keys_from_bytes(b):
        """Sets this wallet's public and private keys from data stored
        in the given bytes `b`."""
        skey, pkey = Crypt.load_keys_from_bytes(b)
        w = Wallet()
        w._set_keys(skey, pkey)
        return w

    def save_key(self, filename):
        """Write this wallet's private key to a file located at given path `filename`."""
        return Crypt.save_private_key(self.skey, filename)
