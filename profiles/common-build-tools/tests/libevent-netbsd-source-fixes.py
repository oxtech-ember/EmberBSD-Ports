#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise donor fixes against the actual prepared libevent source.

Use selected native Clang and GNU patch; work-dir is inside the build workspace.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'patch-file', 'patch-tool', 'clang', 'work-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()


def closure(text):
    start = text.index('static void\nevbuffer_get_waste(')
    end = text.index('\n#define evbuffer_validate(buf)', start)
    return text[start:end]


with tempfile.TemporaryDirectory(dir=args.work_dir) as directory:
    root = Path(directory)
    fixed = root / 'source'
    shutil.copytree(args.source, fixed)
    subprocess.run([str(args.patch_tool), '-p0', '-f', '-N', '-F0', '-V', 'none',
                    '-i', str(args.patch_file)], cwd=fixed, check=True, capture_output=True)
    for label, src in (('baseline', args.source), ('fixed', fixed)):
        body = closure((src / 'test/regress_buffer.c').read_text())
        harness = root / (label + '.c')
        harness.write_text('''#include <stddef.h>
struct evbuffer_chain { struct evbuffer_chain *next; size_t buffer_len, misalign, off; };
struct evbuffer { struct evbuffer_chain *first; };
''' + body + '''
int main(void) {
    struct evbuffer_chain tail = {0, 8, 0, 0};
    struct evbuffer_chain head = {&tail, 10, 0, 3};
    struct evbuffer buffer = {&head};
    size_t allocated = 0, wasted = 0, used = 0;
    evbuffer_get_waste(&buffer, &allocated, &wasted, &used);
    return allocated == 18 && wasted == 0 && used == 3 ? 0 : 1;
}
''')
        binary = root / label
        subprocess.run([str(args.clang), '-std=c11', '-Wall', '-Werror', str(harness), '-o', str(binary)], check=True)
        try:
            result = subprocess.run([str(binary)], timeout=2)
        except subprocess.TimeoutExpired:
            assert label == 'baseline', 'fixed empty-chain walk did not terminate'
        else:
            assert label == 'fixed' and result.returncode == 0, label
    include = root / 'include'
    (include / 'openssl').mkdir(parents=True)
    (include / 'openssl/bio.h').write_text('')
    (include / 'util-internal.h').write_text('')
    for label, src in (('baseline', args.source), ('fixed', fixed)):
        (include / 'openssl-compat.h').write_bytes((src / 'openssl-compat.h').read_bytes())
        for version, expected in (('0x20700000L', True), ('0x30400000L', True), ('0x30500000L', label == 'baseline')):
            result = subprocess.run([str(args.clang), '-E', '-dM', '-x', 'c', '-I' + str(include),
                                     '-DOPENSSL_VERSION_NUMBER=0x30000000L',
                                     '-DLIBRESSL_VERSION_NUMBER=' + version, '-'],
                                    input='#include "openssl-compat.h"\n', text=True, capture_output=True, check=True)
            assert ('#define BIO_get_init(' in result.stdout) == expected, (label, version)
    assert 'evbuffer_add_printf(buf, "%*.*s", (int)j, (int)j, abc);' in (fixed / 'test/regress_buffer.c').read_text()
    fmt = root / 'format.c'
    fmt.write_text('''#include <stdio.h>
#include <string.h>
int main(void) {
    const char *s = "abcdefghijklmnopqrstvuwxyz";
    char format[32], old[128], fixed[128];
    for (unsigned j = 1; j < strlen(s); ++j) {
        snprintf(format, sizeof(format), "%%%u.%us", j, j);
        snprintf(old, sizeof(old), format, s);
        snprintf(fixed, sizeof(fixed), "%*.*s", (int)j, (int)j, s);
        if (strcmp(old, fixed)) return 1;
    }
    return 0;
}
''')
    binary = root / 'format'
    subprocess.run([str(args.clang), '-std=c11', '-Wall', '-Werror', str(fmt), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print('libevent donor empty-chain and LibreSSL regressions: PASS')
