# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
"""Compare the existing compact and default SHA256 paths with hashlib."""
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path
from common import arguments

args = arguments('Check both SHA256 implementations and chunk boundaries')
harness = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <u-boot/sha256.h>
int
main(int argc, char **argv)
{
	sha256_context ctx;
	uint8_t buf[4096], out[32];
	size_t n, chunk;
	if (argc != 2 || !(chunk = strtoul(argv[1], NULL, 10)) ||
	    chunk > sizeof(buf))
		return 2;
	sha256_starts(&ctx);
	while ((n = fread(buf, 1, chunk, stdin)) != 0)
		sha256_update(&ctx, buf, n);
	if (ferror(stdin))
		return 3;
	sha256_finish(&ctx, out);
	for (n = 0; n < sizeof(out); n++)
		printf("%02x", out[n]);
	putchar('\n');
	return 0;
}
'''
header = r'''
#include <stdint.h>
#define SHA256_DER_LEN 19
#define CONFIG_IS_ENABLED(x) SHA_SMALL
typedef struct {
	uint32_t total[2], state[8];
	uint8_t buffer[64];
} sha256_context;
void sha256_starts(sha256_context *);
void sha256_update(sha256_context *, const uint8_t *, uint32_t);
void sha256_finish(sha256_context *, uint8_t *);
'''
vectors = [b'', b'abc', b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq', b'a' * 1000000]
vectors += [bytes((i * 37 + 11) % 256 for i in range(n)) for n in
            (1, 2, 7, 55, 56, 57, 63, 64, 65, 119, 120, 121, 127, 128, 129, 255, 256, 4097)]
env = dict(os.environ)
env['PATH'] = os.pathsep.join((str(args.host_prefix / 'bin'), str(args.host_prefix / 'gnu/bin')))
with tempfile.TemporaryDirectory(prefix='uboot-sha256-test-') as directory:
    work = Path(directory)
    (work / 'u-boot').mkdir()
    (work / 'linux').mkdir()
    (work / 'u-boot/sha256.h').write_text(header)
    (work / 'u-boot/schedule.h').write_text('/* No scheduler in this host harness. */\n')
    (work / 'linux/compiler_attributes.h').write_text('#undef __weak\n#define __weak __attribute__((weak))\n')
    (work / 'test.c').write_text(harness)
    for mode in (0, 1):
        subprocess.run([str(args.clang), '-fuse-ld=lld', '-O1', '-g',
                        '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer',
                        f'-DSHA_SMALL={mode}', f'-I{work}', str(args.source / 'lib/sha256.c'),
                        str(work / 'test.c'), '-o', str(work / f'sha-{mode}')], check=True, env=env)
    checks = 0
    for vector in vectors:
        expected = hashlib.sha256(vector).hexdigest()
        for chunk in (1, 7, 63, 64, 65, 511, 4096):
            for mode in (0, 1):
                actual = subprocess.check_output([str(work / f'sha-{mode}'), str(chunk)],
                                                 input=vector, env=env).decode().strip()
                assert actual == expected, (mode, len(vector), chunk, actual, expected)
                checks += 1
    print(f'{checks} SHA256 comparisons passed ({len(vectors)} vectors, 7 chunk sizes)')
