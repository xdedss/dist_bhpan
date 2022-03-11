

import rsa
import base64



def encrypt(message, public_key):
    '''
    RSA + base64
    '''

    pubkey = rsa.PublicKey.load_pkcs1_openssl_pem(public_key)
    # crypto = b''
    # divide = int(len(message) / 117)
    # divide = divide if (divide > 0) else divide + 1
    # line = divide if (len(message) % 117 == 0) else divide + 1
    # for i in range(line):
    #     print(message[i * 117:(i + 1) * 117])
    #     crypto += rsa.encrypt(message[i * 117:(i + 1) * 117].encode(), pubkey)
    crypto = rsa.encrypt(message.encode(), pubkey)
    crypto1 = base64.b64encode(crypto)
    return crypto1.decode()



