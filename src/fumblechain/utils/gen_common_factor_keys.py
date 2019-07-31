#!/usr/bin/env python3

from math import gcd

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateNumbers, RSAPublicNumbers

from model.wallet import Wallet


class KeyUtils:
    @staticmethod
    def generate_keypair():
        skey: rsa.RSAPrivateKey = rsa.generate_private_key(
            public_exponent=3,
            key_size=1024,
            backend=default_backend()
        )

        pkey: rsa.RSAPublicKey = skey.public_key()

        return skey, pkey

    @staticmethod
    def make_private_key(p, q, e=65537):
        n = p * q
        public_numbers = RSAPublicNumbers(e, n)
        m = (p - 1) * (q - 1)
        d = rsa._modinv(e, m)
        dmp1 = rsa.rsa_crt_dmp1(d, p)
        dmq1 = rsa.rsa_crt_dmq1(d, q)
        iqmp = rsa.rsa_crt_iqmp(p, q)
        private_numbers = RSAPrivateNumbers(p, q, d, dmp1, dmq1, iqmp, public_numbers)
        private_key = private_numbers.private_key(default_backend())
        return private_key

    @staticmethod
    def make_wallet(private_key):
        skey = private_key
        pkey = skey.public_key()
        w = Wallet()
        w._set_keys(skey, pkey)
        return w


def gen_common_factor_wallets():
    skey1, _ = KeyUtils.generate_keypair()
    skey2, _ = KeyUtils.generate_keypair()

    pnum1 = skey1.private_numbers()
    pnum2 = skey2.private_numbers()

    p = pnum1.p
    q = pnum1.q
    q2 = pnum2.q

    pkey1 = KeyUtils.make_private_key(p, q)
    pkey2 = KeyUtils.make_private_key(p, q2)

    w1 = KeyUtils.make_wallet(pkey1)
    w2 = KeyUtils.make_wallet(pkey2)

    pn1 = pkey1.public_key().public_numbers()
    pn2 = pkey2.public_key().public_numbers()

    n1 = pn1.n
    n2 = pn2.n

    g = gcd(n1, n2)
    if not g == p:
        print("Key generation failed. Aborting...")
        raise Exception("g != p")

    return w1, w2


def main():
    gen_common_factor_wallets()


if __name__ == '__main__':
    main()
