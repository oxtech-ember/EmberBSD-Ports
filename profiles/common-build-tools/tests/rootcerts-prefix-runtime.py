#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check an installed SDK CA directory with a verified HTTPS request."""
import argparse
import json
import os
from pathlib import Path
import ssl
import urllib.parse
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', required=True, type=Path)
    parser.add_argument('--url', required=True)
    args = parser.parse_args()
    if not args.prefix.is_absolute() or not args.prefix.is_dir():
        parser.error('--prefix must name the installed absolute SDK prefix')
    if urllib.parse.urlsplit(args.url).scheme != 'https':
        parser.error('--url must use HTTPS')
    if any(name in os.environ for name in ('SSL_CERT_FILE', 'SSL_CERT_DIR')):
        parser.error('Remove trust-path environment overrides before acceptance')
    expected = args.prefix / 'etc/openssl/certs'
    paths = ssl.get_default_verify_paths()
    if paths.capath is None or Path(paths.capath).resolve() != expected.resolve():
        raise RuntimeError('OpenSSL does not select the installed SDK CA directory')
    if not expected.is_dir():
        raise RuntimeError('The installed SDK CA directory is absent')
    hashes = list(expected.glob('????????.[0-9]*'))
    if not hashes or any(not path.is_file() or
                         not path.resolve().is_relative_to(expected.resolve()) for path in hashes):
        raise RuntimeError('The SDK CA hash entries are absent or leave the CA directory')
    context = ssl.create_default_context()
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        raise RuntimeError('TLS certificate and hostname verification must remain enabled')
    with urllib.request.urlopen(args.url, context=context, timeout=30) as response:
        if urllib.parse.urlsplit(response.url).scheme != 'https':
            raise RuntimeError('The response left HTTPS')
        response.read(1)
        status = response.status
    print(json.dumps(dict(capath=str(expected), cafile=paths.cafile,
        hash_entries=len(hashes), trust=context.cert_store_stats(),
        url=args.url, status=status), indent=2))


if __name__ == '__main__':
    main()
