#!/usr/bin/env python3
"""Check OpenSSH new-file scopes and the selected SDK's patch path guard."""
import argparse
import importlib.util
from pathlib import Path
import sys
import tempfile

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

parser = argparse.ArgumentParser()
parser.add_argument('--patch', type=Path, required=True)
args = parser.parse_args(module.load_sdk(sys.argv[1:]))
delta = (b'--- /dev/null\n+++ darwin-defaults.c\n@@ -0,0 +1 @@\n+defaults\n'
         b'--- /dev/null\n+++ darwin-defaults-gen.c\n@@ -0,0 +1 @@\n+generator\n')
module.validate_darwin_creation(delta)
for bad in (delta.replace(b'darwin-defaults.c', b'other.c'),
            delta.replace(b'+++ darwin-defaults.c', b'+++ ../escape.c'),
            delta.replace(b'+++ darwin-defaults.c', b'+++ /tmp/escape.c'),
            delta + b'--- /dev/null\n+++ extra.c\n',
            delta + b'--- deleted.c\n+++ /dev/null\n',
            delta.replace(b'--- /dev/null\n+++ darwin-defaults.c',
                          b'--- darwin-defaults.c\n+++ /dev/null')):
    try:
        module.validate_darwin_creation(bad)
    except module.SDKError:
        continue
    raise AssertionError('unexpected Darwin creation or deletion accepted')

with tempfile.TemporaryDirectory(prefix='openssh-paths-') as directory:
    work = Path(directory)
    root = work / 'source'
    root.mkdir()
    patch_file = work / 'patch'

    def apply(data, allow=True):
        patch_file.write_bytes(data)
        module.sourceprep.apply_patch(str(args.patch), patch_file, data, root, 'openssh',
            patch_args=('-p0', '-f', '-N', '-F0', '-V', 'none'),
            backup_directory=work / 'backups', allow_dev_null=allow)

    # The previous caller policy rejects these valid creation headers.
    try:
        apply(delta, allow=False)
    except module.SDKError as error:
        assert 'unsafe openssh patch path' in str(error), error
    else:
        raise AssertionError('negative control accepted /dev/null')
    # The exact creation exception does not permit other unsafe paths.
    for name in (b'../escape.c', b'/tmp/escape.c', b'a/../escape.c', b'a//escape.c'):
        bad = delta + b'--- ' + name + b'\n+++ ' + name + b'\n@@ -1 +1 @@\n-old\n+new\n'
        module.validate_darwin_creation(bad)
        try:
            apply(bad)
        except module.SDKError as error:
            assert 'unsafe openssh patch path' in str(error), error
        else:
            raise AssertionError('unsafe path accepted with Darwin creations')
        assert not list(root.iterdir()), 'path rejection modified the source'
    apply(delta)
    assert (root / 'darwin-defaults.c').read_bytes() == b'defaults\n'
    assert (root / 'darwin-defaults-gen.c').read_bytes() == b'generator\n'
print('OpenSSH Darwin creation scope and SDK traversal guard: PASS')
