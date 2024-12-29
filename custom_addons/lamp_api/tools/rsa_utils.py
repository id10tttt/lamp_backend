# -*- coding: utf-8 -*-
import base64
from odoo.tools import config
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import utils
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

RSA_ENCRYPT_PWD = 'no35mGlegbokwedwiecIk6'


class RSAUtils:
    def __init__(self):
        self.private_key_name = 'private_key.pem'
        self.public_key_name = 'public_key.pem'
        self.private_key = config.get('private_key_path')
        self.public_key = config.get('public_key_path')
        self.default_split_size = 128

    def generate_public_and_private_pem(self):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(RSA_ENCRYPT_PWD.encode())
        )
        public_key = private_key.public_key()
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        with open(self.private_key_name, 'wb') as f:
            f.write(private_key_pem)
        with open(self.public_key_name, 'wb') as f:
            f.write(public_key_pem)

    def rsa_encrypt_long_bytes(self, pub_key, bytes_str):
        if not isinstance(bytes_str, bytes):
            return None

        count = len(bytes_str) // self.default_split_size
        if len(bytes_str) % self.default_split_size > 0:
            count = count + 1
        cry_bytes = b''

        # rsa加密要以max_msg_length分组, 每组分别加密(加密的数据长度为key_length, 解密时每key_length长度解密然后相加)
        for i in range(count):
            start = self.default_split_size * i
            size = self.default_split_size
            content = bytes_str[start: start + size]
            # rsa 分组 加密
            crypto = pub_key.encrypt(
                content,
                padding.PKCS1v15()
            )
            cry_bytes = cry_bytes + crypto
        return cry_bytes

    def rsa_decrypt_long_bytes(self, pri_key, bytes_str, default_size=256):
        if not isinstance(bytes_str, bytes):
            return None

        count = len(bytes_str) // default_size
        if len(bytes_str) % default_size > 0:
            count = count + 1
        d_cty_bytes = b''
        # rsa加密要以max_msg_length分组, 每组分别加密(加密的数据长度为key_length, 解密时每key_length长度解密然后相加)
        for i in range(count):
            start = default_size * i
            size = default_size
            content = bytes_str[start: start + size]
            # RSA 解密
            plaintext = pri_key.decrypt(
                content,
                padding.PKCS1v15()
            )
            d_cty_bytes = d_cty_bytes + plaintext
        return d_cty_bytes

    def encrypt_rsa_msg(self, msg):
        with open(self.public_key, "rb") as key_file:
            public_key = serialization.load_pem_public_key(
                key_file.read(),
                backend=default_backend()
            )

        # ciphertext = public_key.encrypt(
        #     msg.encode(),
        #     padding.OAEP(
        #         mgf=padding.MGF1(algorithm=hashes.SHA256()),
        #         algorithm=hashes.SHA256(),
        #         label=None
        #     )
        # )
        # ciphertext = public_key.encrypt(
        #     msg.encode(),
        #     padding.PKCS1v15()
        # )
        ciphertext = self.rsa_encrypt_long_bytes(public_key, msg.encode())
        base64_ciphertext = base64.b64encode(ciphertext)
        return base64_ciphertext

    def decrypt_rsa_list_msg(self, private_key, list_ciphertext):
        plaintext = b''
        for cipher_text in list_ciphertext:
            ciphertext = base64.b64decode(cipher_text)
            plaintext += self.rsa_decrypt_long_bytes(private_key, ciphertext)
        return plaintext

    def decrypt_rsa_message(self, ciphertext):
        with open(self.private_key, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=RSA_ENCRYPT_PWD.encode(),
                backend=default_backend()
            )

        if isinstance(ciphertext, list):
            plaintext = self.decrypt_rsa_list_msg(private_key, ciphertext)
        else:
            ciphertext = base64.b64decode(ciphertext)
            plaintext = self.rsa_decrypt_long_bytes(private_key, ciphertext)
        # plaintext = private_key.decrypt(
        #     ciphertext,
        #     padding.OAEP(
        #         mgf=padding.MGF1(algorithm=hashes.SHA256()),
        #         algorithm=hashes.SHA256(),
        #         label=None
        #     )
        # )
        # plaintext = private_key.decrypt(
        #     ciphertext,
        #     padding.PKCS1v15()
        # )

        return plaintext

    def rsa_sign_msg(self, sign_msg):
        with open(self.private_key, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=RSA_ENCRYPT_PWD.encode(),
                backend=default_backend()
            )

        chosen_hash = hashes.SHA256()
        hasher = hashes.Hash(chosen_hash)
        hasher.update(sign_msg.encode)
        digest = hasher.finalize()
        sig = private_key.sign(
            digest,
            padding.PKCS1v15(),
            utils.Prehashed(chosen_hash)
        )
        return sig

    def rsa_verify_sign(self, sign_msg, verify_msg):
        with open(self.public_key, "rb") as key_file:
            public_key = serialization.load_pem_public_key(
                key_file.read(),
                backend=default_backend()
            )
        chosen_hash = hashes.SHA256()
        hasher = hashes.Hash(chosen_hash)
        hasher.update(verify_msg.encode())
        digest = hasher.finalize()
        public_key.verify(
            sign_msg,
            digest,
            padding.PKCS1v15(),
            utils.Prehashed(chosen_hash)
        )


if __name__ == '__main__':
    # generate_public_and_private_key()
    _msg = 'hello world' * 1000
    encrypt_msg = RSAUtils().encrypt_rsa_msg(_msg)
    print('encrypt_msg: ', encrypt_msg)
    # RSAUtils().decrypt_rsa_message(encrypt_msg)
