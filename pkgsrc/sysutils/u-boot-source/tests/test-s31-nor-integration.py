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
parser.add_argument('--root-mode', choices=('ram', 'nor'), default='ram')
parser.add_argument('--root-offset', type=lambda value: int(value, 0))
parser.add_argument('--root-size', type=lambda value: int(value, 0))
parser.add_argument('--erase-size', type=lambda value: int(value, 0))
parser.add_argument('--bootargs')
a = parser.parse_args()
producer = Path(__file__).resolve().parents[1] / 'files/board/espressif/esp32s31/make-nor-image.py'
args = [sys.executable, str(producer)]
for key, value in vars(a).items():
    if key in ('root_mode', 'root_offset', 'root_size', 'erase_size', 'bootargs'):
        continue
    args += ['--' + key.replace('_', '-'), str(value)]
if a.root_mode != 'ram':
    args += ['--root-mode', a.root_mode]
for key in ('root_offset', 'root_size', 'erase_size', 'bootargs'):
    value = getattr(a, key)
    if value is not None:
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
    fdtget = a.host_prefix / 'bin/fdtget'
    kernel_fdt = subprocess.run(
        [str(fdtget), '-t', 'bx', str(a.kernel_fit), '/images/fdt', 'data'],
        check=True, stdout=subprocess.PIPE, text=True).stdout
    kernel_dtb = work/'kernel.dtb'
    kernel_dtb.write_bytes(bytes(int(value, 16) for value in kernel_fdt.split()))
    invalid = work/'kernel-dtb.bin'
    bad_args = args.copy()
    bad_args[bad_args.index('--firmware-dtb') + 1] = str(kernel_dtb)
    bad = subprocess.run([*bad_args, '--output', str(invalid)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if (bad.returncode == 0 or
        'firmware DTB lacks valid OpenSBI heap or S31 SRAM layout' not in bad.stderr or
        invalid.exists()):
        raise SystemExit('kernel DTB was not rejected as a firmware input')
    print('two complete NOR images identical; ROM, gap and FIT offsets verified; SHA256', hashlib.sha256(data).hexdigest())
