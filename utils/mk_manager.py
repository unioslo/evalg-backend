#!/usr/bin/env python3
"""
Master Key manager for eValg

Standalone program that uses the nacl library to:
 - generate key-pair (private / public key)
 - decrypt encrypted private key from eValg
"""
import argparse
import base64
import io
import os
import sys

import nacl.encoding
import nacl.public


def get_key_pair_string():
    """
    Returns a randomly generated key-pair

    :return: (privkey, pubkey) tuple of the base64 encoded key-pair
    :rtype: tuple
    """
    new_priv_key = nacl.public.PrivateKey.generate()
    new_pub_key = new_priv_key.public_key
    return (new_priv_key.encode(encoder=nacl.encoding.Base64Encoder).decode(),
            new_pub_key.encode(encoder=nacl.encoding.Base64Encoder).decode())


def get_decrypted_string(estring, privkey, pubkey):
    """
    Decrypts `estring` using `privkey` and checks signature using `pubkey`

    :param estring: Encrypted string
    :type estring: str

    :param privkey: base64 encoded private key for decryption
    :type privkey: str

    :param pubkey: base64 encoded public key used to check the signature
                   made by its corresponding private key
    :type pubkey: str

    :return: The decrypted string
    :rtype: str
    """
    try:
        errmsg = f'Invalid private key string: {privkey}'
        priv = nacl.public.PrivateKey(privkey,
                                      encoder=nacl.encoding.Base64Encoder)
        errmsg = f'Invalid public key string: {pubkey}'
        pub = nacl.public.PublicKey(pubkey,
                                    encoder=nacl.encoding.Base64Encoder)
        errmsg = 'Invalid encrypted string (nonce:payload) format'
        nonce, payload = estring.split(':')
        errmsg = 'Unable to create a decryption-box'
        dbox = nacl.public.Box(priv, pub)
        errmsg = 'Unable to decrypt estring'
        return base64.b64encode(
            dbox.decrypt(payload.encode(),
                         nonce=base64.b64decode(nonce.encode()),
                         encoder=nacl.encoding.Base64Encoder)).decode()
    except Exception:
        print(errmsg,
              file=sys.stdout,
              flush=True)
        sys.exit(1)


def main(args=None):
    """Main runtime"""
    parser = argparse.ArgumentParser(
        description='The following options are available')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-d', '--decrypt',
        action='store_true',
        dest='decrypt',
        default=False,
        help=('Decrypts encrypted string (-e) and checks signature using '
              'public key (-p / --pubkey)'))
    group.add_argument(
        '-g', '--generate',
        action='store_true',
        dest='generate',
        default=False,
        help=('Generates private and public key-pair and sends base64 '
              'encoding to stdout'))
    parser.add_argument(
        '-e', '--estring',
        metavar='<encrypted string>',
        type=str,
        dest='estring',
        default='',
        help=('The base64 encoded public key used to check the '
              'encryption signature'))
    parser.add_argument(
        '-o', '--output',
        metavar='<new key file>',
        type=str,
        dest='output',
        default='',
        help='The optional file to store the restored key to')
    parser.add_argument(
        '-p', '--pubkey',
        metavar='<public key>',
        type=str,
        dest='pubkey',
        default='',
        help=('The base64 encoded public key used to check the '
              'encryption signature'))
    args = parser.parse_args(args)
    if args.generate:
        priv, pub = get_key_pair_string()
        print('Private key: {priv}{sep}Public key: {pub}'.format(
            priv=priv,
            sep=os.linesep,
            pub=pub))
    elif args.decrypt:
        print('Enter master key (private key): ', end='', flush=True)
        privkey = sys.stdin.readline()
        dstring = get_decrypted_string(args.estring,
                                       privkey.strip(),
                                       args.pubkey)
        print(f'Decrypted string: {dstring}', flush=True)
        if args.output:
            with io.open(args.output,
                         'w',
                         encoding='utf-8',
                         newline='\r\n') as fp:
                fp.write(('{dstring}{sep}Offentlig nøkkel / Public key: '
                          '{pubkey}').format(dstring=dstring,
                                             sep=os.linesep,
                                             pubkey=args.pubkey))


if __name__ == '__main__':
    main()
