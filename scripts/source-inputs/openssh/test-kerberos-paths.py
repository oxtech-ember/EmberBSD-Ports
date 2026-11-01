#!/usr/bin/env python3
"""Check the new-file scope of the common OpenSSH Kerberos patch."""
import importlib.util
from pathlib import Path

source = Path(__file__).with_name('source.py')
spec = importlib.util.spec_from_file_location('openssh_source', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.SDKError = ValueError
module.validate_kerberos_creation(
    b'--- /dev/null\n+++ auth2-krb5.c\n--- auth2.c\n+++ auth2.c\n')
for patch in (b'--- /dev/null\n+++ other.c\n',
              b'--- /dev/null\n+++ auth2-krb5.c\n--- /dev/null\n+++ other.c\n',
              b'--- auth2-krb5.c\n+++ auth2-krb5.c\n'):
    try:
        module.validate_kerberos_creation(patch)
    except ValueError:
        continue
    raise AssertionError('unexpected new-file patch accepted')
print('OpenSSH Kerberos patch creation scope: PASS')
