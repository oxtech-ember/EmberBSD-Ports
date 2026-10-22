#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run only the prepared private guest.
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import sys
from vm import canonical, entrypoint, integer, parser, ram_mib, sdk, sdk_record


def main():
    args = parser(__doc__, ['work']).parse_args()
    inventory, jsonio, paths, process, identity = sdk(args.sdk_source)
    work = canonical(args.work)
    manifest = jsonio.read_json(str(work / 'artifacts/input.json'))
    memory = ram_mib(manifest.get('ram_mib', 1024))
    cpus = integer(manifest.get('cpus', 2), 1, 8, 'virtual CPUs')
    lock = os.open(work / 'runner.lock', os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    os.set_inheritable(lock, True)  # Keep exclusive disk ownership across exec.
    # Preserve the one active query-guest policy without relying on Linux /proc.
    result = subprocess.run(['ps', '-e', '-o', 'comm='], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
    if any(Path(line).name.startswith('qemu-system-') for line in result.stdout.decode().splitlines()):
        raise ValueError('another QEMU system guest is active')
    kernel, disk = work / 'artifacts/kernel.img', work / 'query.ffs'
    if inventory.sha256_file(kernel) != manifest['kernel_image_sha256']:
        raise ValueError('kernel differs from prepared input')
    if disk.is_symlink() or not disk.is_file() or disk.stat().st_nlink != 1:
        raise ValueError('disk path is not the owned regular file')
    selected = os.environ.get('QEMU_AARCH64', 'qemu-system-aarch64')
    candidate = shutil.which(selected)
    if candidate is None:
        raise ValueError('QEMU executable not found')
    qemu = Path(candidate).resolve(strict=True)
    with qemu.open('rb') as stream:
        header = stream.read(4)
    if not os.access(qemu, os.X_OK) or header not in (b'\x7fELF', b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca'):
        raise ValueError('QEMU must be an executable native ELF or Mach-O binary')
    version = subprocess.run([str(qemu), '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
    command = [str(qemu), '-name', 'ember-e14-query', '-machine', 'virt,accel=tcg', '-cpu', 'cortex-a72',
               '-m', str(memory), '-smp', str(cpus), '-display', 'none', '-serial', 'stdio', '-monitor', 'none', '-no-reboot',
               '-kernel', str(kernel), '-append', 'root=ld4a console=plcom0',
               '-drive', f'file={disk},if=none,format=raw,id=root', '-device', 'virtio-blk-pci,drive=root',
               '-netdev', f'user,id=net0,hostfwd=tcp:127.0.0.1:{integer(manifest["port"],1024,65535,"SSH port")}-:22',
               '-device', 'virtio-net-pci,netdev=net0,romfile=']
    if 'EMBERBSD_QUERY_QEMU_DATA' in os.environ:
        command += ['-L', str(canonical(Path(os.environ['EMBERBSD_QUERY_QEMU_DATA'])))]
    own = identity.process_identity(os.getpid())
    if own is None:
        raise ValueError('Cannot establish the runner process birth identity.')
    jsonio.write_json(str(work / 'artifacts/run.json'), dict(argv=command, process_start_time=str(own.birth),
        process_identity_backend=own.backend, qemu_version=version.stdout.decode('utf-8', 'strict'),
        loader_environment={key: os.environ[key] for key in ['DYLD_LIBRARY_PATH','LD_LIBRARY_PATH'] if key in os.environ},
        qemu_sha256=inventory.sha256_file(qemu), disk_sha256=inventory.sha256_file(disk),
        python=sys.version, sdk_source=sdk_record(args.sdk_source, inventory)), exclusive=False)
    (work / 'runner.pid').write_text(str(os.getpid()) + '\n')
    os.execv(str(qemu), command)


if __name__ == '__main__':
    entrypoint(main)
