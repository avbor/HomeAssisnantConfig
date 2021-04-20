import pytest
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from base64 import b64decode, b64encode


def encode(message, key):
    digest = hashlib.sha384(key.encode()).digest()
    iv = digest[-16:]
    key = digest[:32]

    padder = padding.PKCS7(128).padder()
    message = padder.update(message.encode('UTF-8')) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(message) + encryptor.finalize()

    encode = b64encode(encrypted)
    encode = encode.decode() + hashlib.md5(encode).hexdigest()

    return encode


def decode(message, key):
    digest = hashlib.sha384(key.encode()).digest()
    iv = digest[-16:]
    key = digest[:32]

    message = message[:-32]
    message = b64decode(message)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(message) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    decrypted = unpadder.update(decrypted) + unpadder.finalize()

    return decrypted.decode()


testdata_crypt = [
    (
        '{"lang":"ru","command":"getTimeSlots","data":{}}',
        '+gv9fGmmskc6QqhxZ2+3Juau43uPWxqvR4Ps++h4G24=',
        '4xUSzydJBMlzVsr+IDEM1uS0Kq/7gHV+AHTj3Bt2qfvomkE9X2v/Z+QrU3svUVpzK/W7TlC68kUeAaGNuJeFpw==4f5d27f2f1629d79e979cd9ee76a7a8c'
    ),
    (
        '{"message_id":"5","command":"token","result":{"result":"93938"},"message":""}',
        '+gv9fGmmskc6QqhxZ2+3Juau43uPWxqvR4Ps++h4G24=',
        'dRvExXJrlBNrzFtyaoVXGCytA28fR2GmA9MtFAD6Q9I3dnqkGwNamDUUXrwDSBS0lmwgqzCcDG9l4lWma2VBgYzIukZxDpEwdt8nK07BOlg=a75b8d18b5b97167e1cb109f31092065',
    ),
    (
        '{"message_id":"a","command":"token","result":{"result":"93938"},"message":""}',
        'aDgJg2hy0KIs2Re9wTiEpJ/YbC1slvdN4ch1A12ZEEk=',
        'XCUFdy+zMmNpiQsN1C7Aw/qvUQpje+bS1p3EBzdSyxr2OgN1+DKzsYPihjjXijkBpCz4AEeJxT+Q0vDiU3MlVGa1WK147oPZURNX/rFIQnE=f03bf2ee805807d756c8269a0fa699fe',
    ),
]


@pytest.mark.parametrize("message,key,expected", testdata_crypt)
def test_crypt(message, key, expected):
    assert encode(message, key) == expected


testdata_decrypt = [
    (
        '4xUSzydJBMlzVsr+IDEM1uS0Kq/7gHV+AHTj3Bt2qfvomkE9X2v/Z+QrU3svUVpzK/W7TlC68kUeAaGNuJeFpw==4f5d27f2f1629d79e979cd9ee76a7a8c',
        '+gv9fGmmskc6QqhxZ2+3Juau43uPWxqvR4Ps++h4G24=',
        '{"lang":"ru","command":"getTimeSlots","data":{}}',
    ),
    (
        'dRvExXJrlBNrzFtyaoVXGCytA28fR2GmA9MtFAD6Q9I3dnqkGwNamDUUXrwDSBS0lmwgqzCcDG9l4lWma2VBgYzIukZxDpEwdt8nK07BOlg=a75b8d18b5b97167e1cb109f31092065',
        '+gv9fGmmskc6QqhxZ2+3Juau43uPWxqvR4Ps++h4G24=',
        '{"message_id":"5","command":"token","result":{"result":"93938"},"message":""}',
    ),
    (
        'XCUFdy+zMmNpiQsN1C7Aw/qvUQpje+bS1p3EBzdSyxr2OgN1+DKzsYPihjjXijkBpCz4AEeJxT+Q0vDiU3MlVGa1WK147oPZURNX/rFIQnE=f03bf2ee805807d756c8269a0fa699fe',
        'aDgJg2hy0KIs2Re9wTiEpJ/YbC1slvdN4ch1A12ZEEk=',
        '{"message_id":"a","command":"token","result":{"result":"93938"},"message":""}',
    ),
]


@pytest.mark.parametrize("message,key,expected", testdata_decrypt)
def test_decrypt(message, key, expected):
    assert decode(message, key) == expected
