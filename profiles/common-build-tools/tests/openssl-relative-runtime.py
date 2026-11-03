#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Run with the Python in a disposable relocated SDK (no producer access)."""
import ctypes
from pathlib import Path
import ssl
import subprocess
import sys

root = Path(sys.executable).resolve().parents[1]
assert ssl.get_default_verify_paths().capath == str(root / 'etc/openssl/certs')
assert ssl.create_default_context(cafile=root / 'etc/openssl/certs/ca-certificates.crt').cert_store_stats()['x509_ca'] > 0
library = ctypes.CDLL(str(root / 'lib/libcrypto.4.dylib'))
for function, relative in (('X509_get_default_private_dir', 'etc/openssl/private'),
                           ('X509_get_default_cert_dir', 'etc/openssl/certs'),
                           ('X509_get_default_cert_file', 'etc/openssl/cert.pem')):
    getter = getattr(library, function)
    getter.restype = ctypes.c_char_p
    assert getter().decode() == str(root / relative)
# A default CT config is optional in ordinary OpenSSL. Create an empty one only
# in this disposable test installation, without replacing existing configuration.
config = root / 'etc/openssl/ct_log_list.cnf'
with config.open('x') as output:
    output.write('enabled_logs =\n')
library.CTLOG_STORE_new.restype = ctypes.c_void_p
library.CTLOG_STORE_load_default_file.argtypes = [ctypes.c_void_p]
library.CTLOG_STORE_free.argtypes = [ctypes.c_void_p]
store = library.CTLOG_STORE_new()
try:
    assert store and library.CTLOG_STORE_load_default_file(store) == 1
finally:
    if store:
        library.CTLOG_STORE_free(store)
    config.unlink()
subprocess.run([str(root / 'bin/openssl'), 'list', '-providers', '-provider', 'legacy'], check=True)
print('PASS: relocated X509, public CA, CT configuration and provider paths')
