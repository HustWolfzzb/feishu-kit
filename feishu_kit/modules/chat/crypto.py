"""飞书 Encrypt Key AES-256-CBC 解密"""

import base64
import hashlib
import json

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding


def decrypt_feishu_event(encrypt_key: str, encrypt_data: str) -> str:
    """解密飞书 webhook 加密事件。

    Args:
        encrypt_key: 飞书开发者后台配置的 Encrypt Key（原始字符串）
        encrypt_data: webhook body 中的 encrypt 字段值（base64 编码）

    Returns:
        解密后的 JSON 字符串
    """
    # 1. SHA-256(encrypt_key) 作为 AES key
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()

    # 2. Base64 解码密文
    encrypted_bytes = base64.b64decode(encrypt_data)

    # 3. 前 16 字节为 IV，其余为密文
    iv = encrypted_bytes[:16]
    ciphertext = encrypted_bytes[16:]

    # 4. AES-256-CBC 解密 + PKCS7 去 padding
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(ciphertext) + decryptor.finalize()

    # 5. PKCS7 unpadding
    unpadder = sym_padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(decrypted) + unpadder.finalize()

    # 6. 末尾 32 字节为签名，前面是实际 JSON
    plaintext_str = plaintext.decode("utf-8")
    # 飞书格式: plaintext 内容是 JSON 字符串（已去掉末尾签名）
    # 但实际上 padding 后的 plaintext 直接就是 JSON
    try:
        json.loads(plaintext_str)
        return plaintext_str
    except json.JSONDecodeError:
        # 可能有末尾签名，去掉试试
        return plaintext_str[:-32] if len(plaintext_str) > 32 else plaintext_str
