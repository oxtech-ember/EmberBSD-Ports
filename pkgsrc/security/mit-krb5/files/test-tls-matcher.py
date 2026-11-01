#!/usr/bin/env python3
"""Exercise the patched k5tls certificate matcher against selected OpenSSL."""
import argparse
import pathlib
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source', required=True, type=pathlib.Path,
                    help='patched krb5 src directory')
parser.add_argument('--cc', required=True, type=pathlib.Path)
parser.add_argument('--prefix', required=True, type=pathlib.Path)
parser.add_argument('--compile-only', action='store_true',
                    help='only compile, for a cross compiler')
args = parser.parse_args()
text = (args.source / 'plugins/tls/k5tls/openssl.c').read_text()
start = text.index('/* Return the passed-in character')
end = text.index('static int\nverify_callback', start)
# The matcher relies on the file's compatibility macros for OpenSSL < 4.0.
compat_start = text.index('#if OPENSSL_VERSION_NUMBER < 0x40000000L')
compat = text[compat_start:text.index('#endif\n', compat_start) + 7]
preamble = '''#include <openssl/x509.h>
#include <openssl/x509v3.h>
#include <arpa/inet.h>
#include <string.h>
#include <stdio.h>
typedef int krb5_boolean;
#define TRUE 1
#define FALSE 0
#define KRB5_UPPER(x) ((x) >= 'A' && (x) <= 'Z')
''' + compat
main = '''int main(void) {
 X509 *x = X509_new(); X509_EXTENSION *ext; int ok = 1;
 ext = X509V3_EXT_conf_nid(NULL, NULL, NID_subject_alt_name,
     "DNS:*.example.com,DNS:kdc*.example.net,IP:127.0.0.1");
 if (!x || !ext || !X509_add_ext(x, ext, -1)) return 2;
 X509_EXTENSION_free(ext);
 ok &= check_cert_name_or_ip(x, "kdc.example.com");
 ok &= !check_cert_name_or_ip(x, "kdc1.example.net");
 ok &= !check_cert_name_or_ip(x, "wrong.example.org");
 ok &= check_cert_name_or_ip(x, "127.0.0.1");
 ok &= !check_cert_name_or_ip(x, "127.0.0.2");
 X509_free(x); puts(ok ? "TLS matcher PASS" : "TLS matcher FAIL");
 return ok ? 0 : 1;
}
'''
with tempfile.TemporaryDirectory(dir=str(pathlib.Path.cwd())) as tmp:
    tmp = pathlib.Path(tmp)
    (tmp / 'test.c').write_text(preamble + text[start:end] + main)
    command = [str(args.cc), '-I' + str(args.prefix / 'include'),
               '-Werror=incompatible-pointer-types-discards-qualifiers',
               str(tmp / 'test.c')]
    if args.compile_only:
        subprocess.run(command + ['-fsyntax-only'], check=True)
        print('TLS matcher compiles')
    else:
        subprocess.run(command + ['-L' + str(args.prefix / 'lib'), '-lcrypto',
                                  '-o', str(tmp / 'test')], check=True)
        subprocess.run([str(tmp / 'test')], check=True)
