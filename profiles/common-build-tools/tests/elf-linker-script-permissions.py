#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise the exported metadata permission loop with real target ELF inputs."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--metadata', required=True)
p.add_argument('--readelf', required=True)
p.add_argument('--elf', required=True)
a = p.parse_args()
s = Path(a.metadata).read_text()
guard = next(line.strip().removesuffix('\\').strip() for line in s.splitlines() if 'metadata requires selected readelf' in line)
guard = guard.replace('${TEST}', 'test').replace('${ECHO}', 'echo').replace('${TOOLS_PATH.readelf:Q}', '"$READELF"')
for absent in ('', '/nonexistent/readelf'):
 missing = subprocess.run(['/bin/sh', '-c', guard], env=dict(os.environ, READELF=absent), capture_output=True)
 assert missing.returncode != 0 and b'metadata requires selected readelf' in missing.stderr
start = s.index('\t\tfor i in $$linklibs;')
end = s.index('\n\t\trequires=', start)
loop = s[start:end].replace('$$', '$').replace('${TEST}', 'test').replace('${CHMOD}', 'chmod').replace('${ECHO}', 'echo').replace('${TOOLS_PATH.readelf:Q}', '"$READELF"').replace('${PKG_DEVELOPER:Uno:Q}', 'no').replace('${CHECK_SHLIBS_SKIP:U:@p@${DESTDIR}${PREFIX}/${p}) continue ;;@}', '*/skip.so) continue ;;')
loop = '\n'.join(line.strip().removesuffix('\\') for line in loop.splitlines())
with tempfile.TemporaryDirectory() as d:
 root = Path(d); elf = root/'elf.so'; text = root/'script.so'; skip = root/'skip.so'; link = root/'link.so'
 elf.write_bytes(Path(a.elf).read_bytes()); text.write_text('INPUT(libc++.so.1)\n'); skip.write_bytes(elf.read_bytes()); link.symlink_to(elf.name)
 for f in (elf,text,skip): f.chmod(0o644)
 env = dict(os.environ, READELF=a.readelf, linklibs=' '.join(map(str,(elf,text,skip,link))))
 subprocess.run(['/bin/sh','-c',loop], env=env, check=True)
 assert elf.stat().st_mode & 0o111 and not text.stat().st_mode & 0o111 and not skip.stat().st_mode & 0o111 and link.is_symlink()
print('PASS: ELF chmod, linker script, skip and symlink')
