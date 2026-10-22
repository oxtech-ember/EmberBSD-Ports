#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Prepare a private coherent target execution guest.
import gzip
import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import sys
from vm import FSTAT_METADATA, OWNER, canonical, entrypoint, integer, parser, ram_mib, root_metadata, sdk, sdk_record, write


def main():
    args = parser(__doc__, ['base', 'kernel_gz', 'os_repository', 'netbsd_tools', 'new_work']).parse_args()
    inventory, jsonio, paths, process, identity = sdk(args.sdk_source)
    from emberbsd_sdk.errors import CommandError, SDKError
    base, kernel, source, tools = map(canonical, [args.base, args.kernel_gz, args.os_repository, args.netbsd_tools])
    work = Path(paths.canonical_new(args.new_work))
    if not args.new_work.is_absolute() or work != args.new_work or work.is_symlink() or work.exists():
        raise ValueError('Use a new absolute canonical work directory.')
    for path in (base, kernel, source, tools, args.sdk_source):
        paths.reject_overlap(str(work), str(path))
    revision = os.environ['EMBERBSD_BASE_REVISION']
    kernel_hash = os.environ['EMBERBSD_KERNEL_SHA256']
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('invalid source revision')
    if not re.fullmatch('[0-9a-f]{64}', kernel_hash) or inventory.sha256_file(kernel) != kernel_hash:
        raise ValueError('kernel hash mismatch')
    port = integer(os.environ.get('EMBERBSD_QUERY_PORT', '22614'), 1024, 65535, 'SSH port')
    disk_mib = integer(os.environ.get('EMBERBSD_QUERY_DISK_MIB', '384'), 384, 16384, 'disk MiB')
    free_inodes = integer(os.environ.get('EMBERBSD_QUERY_FREE_INODES', '16000'), 16000, 1000000, 'inode reserve')
    memory = ram_mib(os.environ.get('EMBERBSD_QUERY_RAM_MIB', '1024'))
    cpus = integer(os.environ.get('EMBERBSD_QUERY_CPUS', '2'), 1, 8, 'virtual CPUs')
    work.mkdir(mode=0o700)
    for name in ['root', 'keys', 'logs', 'artifacts', 'bin', 'cache', 'probes', 'source']:
        (work / name).mkdir(mode=0o700)
    root = work / 'root'
    def run(label, *command, env=None, cwd=None):
        argv = [str(arg) for arg in command]
        try:
            result = process.capture(argv, env=env, cwd=cwd)
            out, err, code = result.stdout, result.stderr, 0
        except CommandError as error:
            out, err, code = error.stdout, error.stderr, error.returncode
        write(work / 'logs' / (label + '.log'), out + err)
        if code:
            raise SDKError(f'{label} failed: {code}; inspect {work}/logs')
        return out
    source_files = ['etc/group', 'etc/master.passwd', 'etc/services', 'etc/protocols', 'etc/mtree/NetBSD.dist.base',
        'etc/MAKEDEV.awk', 'etc/MAKEDEV.tmpl', 'etc/etc.aarch64/MAKEDEV.conf', 'sys/conf/majors',
        'sys/arch/aarch64/conf/majors.aarch64', 'sys/arch/aarch64/include/disklabel.h',
        'sys/arch/arm/include/disklabel.h', 'sys/arch/evbarm/conf/mk.generic64']
    source_hashes = {}
    for relative in source_files:
        content = run('source-' + relative.replace('/', '-'), 'git', '-C', source, 'show', revision + ':' + relative)
        output = work / 'source' / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        write(output, content)
        source_hashes[relative] = hashlib.sha256(content).hexdigest()
    make_env = dict(os.environ, MACHINE='aarch64', MACHINE_ARCH='aarch64', NETBSDSRCDIR=str(work / 'source'))
    makedev = run('makedev-generate', 'awk', '-f', work / 'source/etc/MAKEDEV.awk', work / 'source/etc/MAKEDEV.tmpl', env=make_env)
    write(work / 'artifacts/MAKEDEV', makedev)
    devices = run('makedev-spec', 'sh', work / 'artifacts/MAKEDEV', '-s', 'std', 'fd', 'ptm', 'ld4', 'plcom0', cwd=work / 'artifacts')
    if not re.search(rb'ptmx.*device=netbsd,165,0', devices):
        raise ValueError('canonical ptmx major/minor absent')
    write(work / 'artifacts/devices.mtree', devices)
    origins = {str(kernel): kernel_hash}
    def copy_base(relative):
        src, dst = base / relative, root / relative
        dst.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        if src.is_symlink():
            target = os.readlink(src)
            dst.symlink_to(target)
            origins[str(src)] = {'symlink': target}
        elif src.is_file():
            os.link(src, dst)
            origins[str(src)] = inventory.sha256_file(src)
        else:
            raise ValueError(f'missing base file: {src}')
    for directory in ['lib', 'libexec', 'usr/lib/i18n', 'usr/share/i18n', 'usr/share/locale']:
        directory = base / directory
        if not directory.is_dir():
            raise ValueError(f'missing base runtime directory: {directory}')
        for parent, dirs, files in os.walk(directory, followlinks=False):
            for name in sorted(files + [name for name in dirs if (Path(parent) / name).is_symlink()]):
                path = Path(parent) / name
                if not str(path).endswith('.a'):
                    copy_base(path.relative_to(base))
    for pattern in ['usr/lib/*.so*', 'usr/lib/private/*.so*']:
        for path in sorted(base.glob(pattern)):
            copy_base(path.relative_to(base))
    for relative in '''bin/sh bin/sync bin/cat bin/chmod bin/cp bin/ls bin/mkdir bin/mv bin/rm bin/test
        bin/date bin/tar bin/sleep bin/stty bin/hostname bin/kill bin/df bin/pwd bin/ps
        sbin/init sbin/mount sbin/mount_ffs sbin/mount_ptyfs sbin/halt sbin/reboot sbin/sysctl sbin/ifconfig sbin/route sbin/nologin sbin/chown
        usr/bin/uname usr/bin/grep usr/bin/sha256 usr/bin/ldd usr/bin/sed usr/bin/awk usr/bin/env usr/bin/printf usr/bin/timeout usr/bin/mktemp
        usr/bin/id usr/bin/tty usr/bin/getent usr/bin/true usr/bin/false usr/bin/du usr/bin/locale usr/bin/chgrp usr/bin/sort usr/bin/realpath
        usr/bin/wc usr/bin/tr usr/bin/dirname usr/bin/basename usr/bin/ktrace usr/bin/kdump usr/bin/fstat usr/bin/cmp usr/bin/readlink usr/bin/tee
        usr/sbin/pkg_add usr/sbin/pkg_delete usr/sbin/pkg_info usr/sbin/pkg_admin usr/sbin/chown usr/sbin/sshd
        usr/libexec/sshd-session usr/libexec/sshd-auth usr/libexec/sftp-server usr/libexec/ld.elf_so'''.split():
        copy_base(relative)
    for directory in ['etc', 'etc/ssh', 'dev', 'dev/pts', 'tmp', 'var/run', 'var/log', 'var/chroot/sshd', 'var/empty', 'root', 'root/.ssh', 'usr/pkg/lib']:
        (root / directory).mkdir(mode=0o755, parents=True, exist_ok=True)
    (root / 'tmp').chmod(0o1777)
    (root / 'root/.ssh').chmod(0o700)
    for name in ['group', 'master.passwd', 'services', 'protocols']:
        shutil.copyfile(work / 'source/etc' / name, root / 'etc' / name)
    run('password-database', tools / 'nbpwd_mkdb', '-d', root, '-p', root / 'etc/master.passwd')
    for name in ['client', 'host']:
        run('keygen-' + name, 'ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'emberbsd-query-' + name, '-f', work / 'keys' / name)
    for src, dst in [('host', 'etc/ssh/ssh_host_ed25519_key'), ('host.pub', 'etc/ssh/ssh_host_ed25519_key.pub'), ('client.pub', 'root/.ssh/authorized_keys')]:
        shutil.copyfile(work / 'keys' / src, root / dst)
    (root / 'etc/ssh/ssh_host_ed25519_key').chmod(0o600)
    (root / 'root/.ssh/authorized_keys').chmod(0o600)
    key_type, key_data = (work / 'keys/host.pub').read_text().split()[:2]
    write(work / 'keys/known_hosts', f'ember-e14-query {key_type} {key_data}\n')
    write(work / 'ssh.conf', f'''Host ember-e14-query
  HostName 127.0.0.1
  Port {port}
  User root
  IdentityFile {work}/keys/client
  IdentitiesOnly yes
  UserKnownHostsFile {work}/keys/known_hosts
  GlobalKnownHostsFile /dev/null
  HostKeyAlias ember-e14-query
  StrictHostKeyChecking yes
  BatchMode yes
  ConnectTimeout 5
  ServerAliveInterval 10
  ServerAliveCountMax 3
''')
    write(work / 'bin/ssh', f'#!/bin/sh\nexec /usr/bin/ssh -F {shlex.quote(str(work / "ssh.conf"))} "$@"\n', mode=0o755)
    write(root / 'etc/ssh/sshd_config', '''Port 22
ListenAddress 10.0.2.15
HostKey /etc/ssh/ssh_host_ed25519_key
PidFile /var/run/sshd.pid
AuthorizedKeysFile .ssh/authorized_keys
PermitRootLogin prohibit-password
PasswordAuthentication no
PermitEmptyPasswords no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
UsePAM no
UseDNS no
PrintMotd no
Subsystem sftp /usr/libexec/sftp-server
''', mode=0o644)
    configuration = {'fstab': '/dev/ld4a / ffs rw 1 1\n', 'ttys': 'console "/bin/sh" vt100 off secure\n',
                     'hosts': '127.0.0.1 localhost\n10.0.2.15 ember-query\n', 'resolv.conf': 'nameserver 10.0.2.3\n',
                     'nsswitch.conf': 'group: files\npasswd: files\nhosts: files dns\n'}
    for name, text in configuration.items():
        write(root / 'etc' / name, text, mode=0o644)
    write(root / 'etc/rc', (OWNER / 'guest-rc.sh').read_bytes(), mode=0o755)
    mtree = '/set uid=0 gid=0\n' + run('mtree', tools / 'nbmtree', '-c', '-k', 'type,mode,link', '-p', root).decode()
    mtree += root_metadata(work / 'source/etc', tools, run)
    mtree += ''.join(re.sub(r'^\./', './dev/', line) for line in devices.decode().splitlines(keepends=True) if not line.startswith('. type=dir'))
    mtree += FSTAT_METADATA
    write(work / 'artifacts/guest.mtree', mtree)
    run('makefs', tools / 'nbmakefs', '-t', 'ffs', '-B', 'little', '-Z', '-s', f'{disk_mib}m', '-o', 'version=2,label=emberquery',
        '-f', str(free_inodes), '-F', work / 'artifacts/guest.mtree', '-N', work / 'source/etc', work / 'query.ffs', root)
    with gzip.open(kernel, 'rb') as src, (work / 'artifacts/kernel.elf').open('xb') as dst:
        shutil.copyfileobj(src, dst)
    run('kernel-binary', tools / 'aarch64--netbsd-objcopy', '-S', '-O', 'binary', work / 'artifacts/kernel.elf', work / 'artifacts/kernel.bin')
    run('kernel-arm64-image', tools / 'nbmkubootimage', '-f', 'arm64', '-u', '-a', '0x200000', work / 'artifacts/kernel.bin', work / 'artifacts/kernel.img')
    for filename, expected in origins.items():
        path = Path(filename)
        if isinstance(expected, dict):
            matches = path.is_symlink() and os.readlink(path) == expected['symlink']
        else:
            matches = inventory.sha256_file(path) == expected
        if not matches:
            raise ValueError('base input changed during build')
    manifest = dict(sdk_source=sdk_record(args.sdk_source, inventory),
                    helper_sha256={name: inventory.sha256_file(OWNER / name) for name in ['build.py', 'vm.py', 'guest-rc.sh']},
                    host_tools_sha256={name: inventory.sha256_file(tools / name) for name in ['nbmakefs','nbmtree','nbpwd_mkdb','nbmkubootimage','aarch64--netbsd-objcopy']},
                    base_revision=revision, base=str(base), port=port, ram_mib=memory, cpus=cpus,
                    disk_bytes=(work / 'query.ffs').stat().st_size, sparse_disk=True,
                    allocated_disk_bytes=(work / 'query.ffs').stat().st_blocks * 512, extra_free_inodes=free_inodes,
                    initial_disk_sha256=inventory.sha256_file(work / 'query.ffs'),
                    kernel_image_sha256=inventory.sha256_file(work / 'artifacts/kernel.img'),
                    sources_sha256=origins, configuration_sources_sha256=source_hashes,
                    builder_sha256=inventory.sha256_file(__file__), python=sys.version, python_executable=sys.executable)
    jsonio.write_json(str(work / 'artifacts/input.json'), manifest)
    print(f'Prepared private {disk_mib} MiB sparse target guest: {work}')


if __name__ == '__main__':
    entrypoint(main)
