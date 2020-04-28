from base64 import b64encode, b64decode
import hashlib
from Cryptodome.Cipher import AES
import os
from Cryptodome.Random import get_random_bytes

#AES

def encrypt (plain_text, password):
    salt = get_random_bytes(AES.block_size)
    
    private_key = hashlib.scrypt(password.encode(), salt = salt, n=2**14, r=8, p=1, dklen=32)

    cipher_config = AES.new(private_key, AES.MODE_GCM)

    cipher_text, tag = cipher_config.encrypt_and_digest(bytes(plain_text, 'utf-8'))

    output = {
        'cipher_text': b64encode(cipher_text).decode('utf-8'),
        'salt': b64encode(salt).decode('utf-8'),
        'nonce' : b64encode(cipher_config.nonce).decode('utf-8'),
        'tag': b64encode(tag).decode('utf-8')
    }
    result = output['salt'] + '.' + output['nonce'] + '.' + output['tag'] + '.' + output['cipher_text']
    return result
    


def decrypt(message, password):
    parts = message.split('.', 3)
    salt = b64decode(parts[0])
    nonce = b64decode(parts[1])
    tag = b64decode(parts[2])
    cipher_text = b64decode(parts[3])


    private_key = hashlib.scrypt(
        password.encode(), salt = salt, n=2**14, r=8, p=1, dklen=32
    )

    cipher = AES.new(private_key, AES.MODE_GCM, nonce = nonce)

    decrypted = cipher.decrypt_and_verify(cipher_text, tag)

    return decrypted

#elliptic curve diffie hellman

P = 2 ** 255 - 19
A = 486662
def expmod(b, e, m):
    if e == 0:
         return 1
    t = expmod(b, e // 2, m) ** 2 % m
    if e & 1:
         t = (t * b) % m
    return t

def inv(x):
    return expmod(x, P - 2, P)

def add(xnzn, xmzm, xdzd):
    xn, zn = xnzn
    xm, zm = xmzm
    xd, zd = xdzd
    x = 4 * (xm * xn - zm * zn) ** 2 * zd
    z = 4 * (xm * zn - zm * xn) ** 2 * xd
    return (x % P, z % P)

def double(xnzn):
    xn, zn = xnzn
    x = (xn ** 2 - zn ** 2) ** 2
    z = 4 * xn * zn * (xn ** 2 + A * xn * zn + zn ** 2)
    return (x % P, z % P)

def curve25519(n, base=9):
    one = (base,1)
    two = double(one)
    # f(m) evaluates to a tuple
    # containing the mth multiple and the
    # (m+1)th multiple of base.
    def f(m):
        if m == 1: 
            return (one, two)
        (pm, pm1) = f(m // 2)
        if (m & 1):
            return (add(pm, pm1, one), double(pm1))
        return (double(pm), add(pm, pm1, one))
    ((x,z), _) = f(n)
    return (x * inv(z)) % P

import random

def genkey(n=0):
    n = n or random.randint(0,P)
    n &= ~7
    n &= ~(128 << 8 * 31)
    n |= 64 << 8 * 31
    return n