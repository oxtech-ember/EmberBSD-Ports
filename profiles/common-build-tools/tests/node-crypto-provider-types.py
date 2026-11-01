#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Compile Node's extracted crypto expressions against both provider APIs."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--node-source', type=Path, required=True,
                    help='unmodified prepared Node source')
parser.add_argument('--patch', type=Path, required=True,
                    help='shared Node crypto provider patch')
parser.add_argument('--patch-tool', type=Path, required=True,
                    help='selected host GNU patch')
parser.add_argument('--host-prefix', type=Path, required=True,
                    help='selected host tool prefix')
parser.add_argument('--cxx', type=Path, required=True,
                    help='selected target C++ compiler binding')
parser.add_argument('--openssl-include', type=Path, required=True,
                    help='selected target OpenSSL include root')
parser.add_argument('--boringssl-include', type=Path, required=True,
                    help='Electron BoringSSL include root')
parser.add_argument('--work', type=Path, required=True,
                    help='new diagnostics directory')
a = parser.parse_args()
node_source = a.node_source.resolve(strict=True)
patch = a.patch.resolve(strict=True)
patch_tool = a.patch_tool.resolve(strict=True)
host_prefix = a.host_prefix.resolve(strict=True)
cxx = a.cxx.resolve(strict=True)
openssl = a.openssl_include.resolve(strict=True)
boringssl = a.boringssl_include.resolve(strict=True)
work = a.work.resolve()
if work.exists():
    parser.error('--work must be a new directory')
if not (node_source / 'src/crypto/crypto_common.cc').is_file():
    parser.error('--node-source is not a prepared Node source tree')
if not os.access(patch_tool, os.X_OK) or not os.access(cxx, os.X_OK):
    parser.error('select executable patch and compiler tools')
if 'GNU patch' not in subprocess.run([str(patch_tool), '--version'], check=True,
                                     text=True, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT).stdout:
    parser.error('--patch-tool must be GNU patch')
work.mkdir(parents=True)
source_files = ('crypto_common.cc', 'crypto_context.cc', 'crypto_hash.cc',
                'crypto_x509.cc', 'crypto_x509.h')
base_root = work / 'baseline'
patched_root = work / 'patched'
for root in (base_root, patched_root):
    target = root / 'src/crypto'
    target.mkdir(parents=True)
    for name in source_files:
        shutil.copyfile(node_source / 'src/crypto' / name, target / name)
env = dict(os.environ)
env['PATH'] = str(host_prefix / 'bin')
subprocess.run([str(patch_tool), '--batch', '--forward', '--fuzz=0', '-p0',
                '-d', str(patched_root), '-i', str(patch)],
               check=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
               text=True)

def for_header(text, selector):
    """Return the complete production for-header containing selector."""
    position = 0
    matches = []
    while True:
        start = text.find('for (', position)
        if start < 0:
            break
        opening = start + len('for ')
        depth = 0
        end = None
        for index in range(opening, len(text)):
            char = text[index]
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            raise ValueError('unterminated production for header')
        header = text[start:end]
        if selector in header:
            after = end
            while after < len(text) and text[after].isspace():
                after += 1
            if after >= len(text) or text[after] != '{':
                raise ValueError('selected production loop has no block')
            matches.append(header)
        position = end
    if len(matches) != 1:
        raise ValueError(f'expected one production loop for {selector}, got {len(matches)}')
    return ' '.join(matches[0].split())

def issuer_index_declaration(text):
    start = text.index('MaybeLocal<Object> AddIssuerChainToObject(')
    loop = text.index('for (i = 0; i < sk_X509_num(peer_certs.get()); i++) {', start)
    previous = [line.strip() for line in text[start:loop].splitlines()
                if re.fullmatch(r'\s*(?:int|decltype\(.+\))\s+i;\s*', line)]
    if not previous:
        raise ValueError('missing AddIssuerChainToObject index declaration')
    return previous[-1]

def function_last_parameter(text, marker):
    start = text.index(marker) + len(marker)
    opening = text.index('(', start - 1)
    depth = 0
    end = None
    for index in range(opening, len(text)):
        if text[index] == '(':
            depth += 1
        elif text[index] == ')':
            depth -= 1
            if depth == 0:
                end = index
                break
    if end is None:
        raise ValueError('unterminated NewWithIssuers signature')
    return ' '.join(text[opening + 1:end].split(',')[-1].split())

def expressions(root):
    common = (root / 'src/crypto/crypto_common.cc').read_text()
    context = (root / 'src/crypto/crypto_context.cc').read_text()
    hash_source = (root / 'src/crypto/crypto_hash.cc').read_text()
    x509_cc = (root / 'src/crypto/crypto_x509.cc').read_text()
    x509_h = (root / 'src/crypto/crypto_x509.h').read_text()
    loops = [
        (common, 'sk_X509_num(ssl_certs)', None, 'ssl_certs'),
        (common, 'sk_X509_num(peer_certs.get())', issuer_index_declaration(common),
         'peer_certs.get()'),
        (context, 'sk_X509_num(extra_certs)', None, 'extra_certs'),
        (context, 'sk_X509_num(certs)', None, 'certs'),
        (context, 'sk_X509_num(extra_certs.get())', None, 'extra_certs.get()'),
    ]
    out = ['''#include <openssl/evp.h>\n#include <openssl/stack.h>\n#include <openssl/x509.h>\n\nstruct TestStack {\n  const STACK_OF(X509)* get() const { return nullptr; }\n  operator const STACK_OF(X509)*() const { return nullptr; }\n};\n''']
    for number, (text, selector, declaration, stack_expr) in enumerate(loops):
        header = for_header(text, selector)
        name = { 'ssl_certs':'ssl_certs', 'peer_certs.get()':'peer_certs',
                 'extra_certs':'extra_certs', 'certs':'certs',
                 'extra_certs.get()':'extra_certs' }[stack_expr]
        if name in ('ssl_certs', 'certs'):
            init = f'const STACK_OF(X509)* {name} = nullptr;'
        else:
            init = f'TestStack {name};'
        out.append(f'void loop_{number}() {{\n  {init}\n')
        if declaration:
            out.append('  ' + declaration + '\n')
        out.append('  ' + header + ' {\n')
        out.append(f'    (void)sk_X509_value({stack_expr}, i);\n  }}\n}}\n')
    source_param = function_last_parameter(x509_cc, 'X509Certificate::NewWithIssuers')
    header_param = function_last_parameter(x509_h, 'NewWithIssuers')
    if source_param != header_param:
        raise ValueError('NewWithIssuers declaration and definition parameter differ')
    out.append(f'''struct TestCertificate {{
  static void new_with_issuers(const STACK_OF(X509)* issuer_chain, {header_param});
}};
void TestCertificate::new_with_issuers(
    const STACK_OF(X509)* issuer_chain, {source_param}) {{
  if (issuer_chain != nullptr && start < sk_X509_num(issuer_chain)) {{
    (void)sk_X509_value(issuer_chain, start);
  }}
}}
''')
    declaration = next((line.strip() for line in hash_source.splitlines()
                        if 'output_length = EVP_MD_size(md);' in line), None)
    comparison = next((line.strip() for line in hash_source.splitlines()
                       if 'if (output_length != EVP_MD_size(md)) {' in line), None)
    if declaration is None or comparison is None:
        raise ValueError('missing production digest-size declaration/comparison')
    out.append(f'''void check_hash_length(const EVP_MD* md) {{
  {declaration}
  {comparison}
  }}
}}
''')
    return ''.join(out)

fixture = work / 'provider-expressions.cc'
source = expressions(base_root)
fixture.write_text(source)
patched_fixture = work / 'provider-expressions-patched.cc'
patched_fixture.write_text(expressions(patched_root))

def compile_one(provider, include, fixture_path, expect_failure=False):
    command = [str(cxx), '-std=c++23', '-Werror=sign-compare', '-fsyntax-only',
               '-isystem', str(include), str(fixture_path)]
    result = subprocess.run(command, cwd=work, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    sign_errors = 'sign-compare' in result.stderr and 'error:' in result.stderr
    if expect_failure:
        if result.returncode == 0 or not sign_errors:
            raise RuntimeError(f'{provider} unpatched baseline did not fail for signed comparison:\n{result.stderr}')
        print(f'{provider} baseline: expected signed-comparison failure')
    elif result.returncode:
        raise RuntimeError(f'{provider} compile failed:\n{result.stderr}')
    else:
        print(f'{provider}: PASS')

compile_one('OpenSSL', openssl, fixture)
compile_one('BoringSSL', boringssl, fixture, expect_failure=True)
compile_one('OpenSSL patched', openssl, patched_fixture)
compile_one('BoringSSL patched', boringssl, patched_fixture)
print('Production-extracted Node crypto provider expressions: PASS')
