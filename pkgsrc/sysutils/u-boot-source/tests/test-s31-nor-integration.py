# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
"""Exercise the NOR producer with explicitly supplied prepared inputs."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('host-prefix', 'mkimage', 'spl-rom', 'opensbi', 'uboot', 'uboot-elf', 'firmware-dtb', 'kernel-fit', 'kernel-elf', 'root-fs'):
    parser.add_argument('--' + name, type=Path, required=True)
a = parser.parse_args()
producer = Path(__file__).resolve().parents[1] / 'files/board/espressif/esp32s31/make-nor-image.py'
args = [sys.executable, str(producer)]
for key, value in vars(a).items():
    args += ['--' + key.replace('_', '-'), str(value)]
with tempfile.TemporaryDirectory(prefix='s31-nor-test-') as directory:
    work = Path(directory)
    first, second = work/'first.bin', work/'second.bin'
    for out in (first, second):
        subprocess.run([*args, '--output', str(out)], check=True)
    data = first.read_bytes()
    if data != second.read_bytes() or len(data) != 0x1000000:
        raise SystemExit('NOR output is not deterministic or has wrong size')
    spl = a.spl_rom.read_bytes()
    if data[:0x2000] != b'\xff' * 0x2000 or data[0x2000:0x2000+len(spl)] != spl:
        raise SystemExit('SPL NOR offset mismatch')
    if data[0x2000+len(spl):0x20000] != b'\xff' * (0x1e000-len(spl)) or data[0x20000:0x20004] != b'\xd0\r\xfe\xed':
        raise SystemExit('gap or FIT NOR offset mismatch')
    print('two complete NOR images identical; ROM, gap and FIT offsets verified; SHA256', hashlib.sha256(data).hexdigest())
