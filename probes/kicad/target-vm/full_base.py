# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Full base metadata and pinned etc staging.
"""Helpers for the full-base mode of the existing target guest builder."""
import hashlib
import json
import os
import posixpath
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile


# etc/install-etc-files invokes these source-owned configinstall rules.
# Export configuration and make inputs only. Do not export the complete OS.
SOURCE_PATHS = [
    'Makefile.inc', 'build.sh', 'etc', 'share/mk', 'sys/conf',
    'sys/sys/param.h', 'sys/arch/aarch64/include', 'sys/arch/arm/include',
    'sys/arch/evbarm/conf/mk.generic64', 'sys/arch/aarch64/conf/majors.aarch64',
    'external/bsd/dhcpcd/Makefile.inc', 'external/bsd/dhcpcd/sbin/dhcpcd/Makefile',
    'external/bsd/dhcpcd/dist/src/dhcpcd.conf',
    'external/bsd/zstd/Makefile.zstd', 'external/bsd/zstd/lib/Makefile',
    'usr.bin/Makefile.inc', 'usr.bin/mail/Makefile', 'usr.bin/mail/misc/mail.rc',
    'usr.sbin/Makefile.inc', 'usr.sbin/certctl', 'usr.sbin/pf/Makefile',
    'usr.sbin/pf/etc', 'dist/pf/etc',
    'crypto/external/bsd/openssh/Makefile.inc', 'crypto/external/bsd/openssh/bin',
    'crypto/external/bsd/openssh/dist/ssh_config',
    'crypto/external/bsd/openssh/dist/sshd_config', 'crypto/external/bsd/openssh/dist/moduli',
    'crypto/external/bsd/openssh/lib/Makefile',
    'crypto/external/bsd/openssl/lib/libcrypto/Makefile',
    'lib/libcrypt/Makefile', 'lib/libz/Makefile',
    'external/ibm-public/postfix/Makefile', 'external/ibm-public/postfix/Makefile.inc',
    'external/ibm-public/postfix/etc', 'external/ibm-public/postfix/lib',
    'external/ibm-public/postfix/dist/conf',
]
COMPILERS = {'usr/bin/' + name for name in ('cc', 'c++', 'gcc', 'g++', 'clang', 'clang++')}


def relative_name(name):
    if name.startswith('./'):
        name = name[2:]
    if name == '.':
        return '.'
    if not name or name.startswith('/') or '\x00' in name or any(x in ('', '.', '..') for x in name.split('/')):
        raise ValueError('Unsafe base archive path: ' + repr(name))
    return name


def escape(value):
    return ''.join(chr(byte) if chr(byte) in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./:+,-' else f'\\{byte:03o}'
                   for byte in value.encode('utf-8'))


def records(archive, expected):
    if not re.fullmatch('[0-9a-f]{64}', expected or ''):
        raise ValueError('Full base requires an explicit archive SHA256.')
    with archive.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
            raise ValueError('Base archive SHA256 mismatch.')
    with tarfile.open(archive) as stream:
        entries = {}
        for entry in stream.getmembers():
            name = relative_name(entry.name)
            if name in entries or not (entry.isdir() or entry.isreg() or entry.issym() or entry.islnk()):
                raise ValueError('Duplicate or unsupported base archive entry: ' + name)
            if not 0 <= entry.uid < 2**32 or not 0 <= entry.gid < 2**32:
                raise ValueError('Invalid base ownership: ' + name)
            entries[name] = entry
    if '.' not in entries or not entries['.'].isdir() or entries['.'].uid != 0 or entries['.'].gid != 0 or entries['.'].mode & 0o7777 != 0o755:
        raise ValueError('Full base requires canonical root:wheel/0755 metadata.')
    if COMPILERS.intersection(entries) or any(n.startswith('usr/pkg/') for n in entries):
        raise ValueError('Use a base set without compiler commands or preinstalled packages.')
    for name, entry in entries.items():
        for parent in PurePosixPath(name).parents:
            if str(parent) not in entries or not entries[str(parent)].isdir():
                raise ValueError('Missing or non-directory base ancestor: ' + name)
        if entry.islnk():
            target = relative_name(entry.linkname)
            if target not in entries or not entries[target].isreg():
                raise ValueError('Base hardlink must name a regular archive file: ' + name)
            peer = entries[target]
            if (entry.uid, entry.gid, entry.mode & 0o7777) != (peer.uid, peer.gid, peer.mode & 0o7777):
                raise ValueError('Conflicting hardlink metadata: ' + name)
        if entry.issym():
            if '\x00' in entry.linkname or not entry.linkname:
                raise ValueError('Invalid base symlink: ' + name)
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), entry.linkname))
            if target == '..' or target.startswith('../'):
                raise ValueError('Base symlink escapes the image: ' + name)
    return entries


def stage(archive, entries, root):
    """Keep target permissions in mtree, not in host ownership or set-ID bits."""
    for name, entry in sorted(entries.items(), key=lambda item: (item[0].count('/'), item[0])):
        if entry.isdir() and name != '.':
            (root / name).mkdir(mode=0o700)
    hashes = {}
    with tarfile.open(archive) as stream:
        for name, entry in entries.items():
            if not entry.isreg():
                continue
            with stream.extractfile(entry) as src, (root / name).open('xb') as dst:
                shutil.copyfileobj(src, dst)
            with (root / name).open('rb') as src:
                hashes[name] = hashlib.file_digest(src, 'sha256').hexdigest()
            (root / name).chmod((entry.mode & 0o777) | 0o600)
    for name, entry in entries.items():
        if entry.islnk():
            os.link(root / relative_name(entry.linkname), root / name)
        elif entry.issym():
            (root / name).symlink_to(entry.linkname)
    return hashes


def metadata(entries):
    lines = []
    for name, entry in sorted(entries.items()):
        kind = 'dir' if entry.isdir() else 'link' if entry.issym() else 'file'
        text = f'{escape("." if name == "." else "./" + name)} type={kind} uid={entry.uid} gid={entry.gid} mode=0{entry.mode & 0o7777:o}'
        if entry.issym():
            text += ' link=' + escape(entry.linkname)
        lines.append(text + '\n')
    return ''.join(lines)


def source_tree(repository, revision, work, run):
    archive = work / 'artifacts/etc-source.tar'
    run('etc-source-export', 'git', '-C', repository, 'archive', '--format=tar', '--output=' + str(archive), revision, '--', *SOURCE_PATHS)
    source = work / 'source'
    with tarfile.open(archive) as stream:
        stream.extractall(source, filter='data')
    # bsd.own.mk uses build.sh plus tools/ to identify the source root.
    (source / 'tools').mkdir(exist_ok=True)
    obj = work / 'etc-obj'
    obj.mkdir()
    for parent, directories, files in os.walk(source):
        if 'Makefile' in files or Path(parent) == source:
            (obj / Path(parent).relative_to(source)).mkdir(parents=True, exist_ok=True)
    with archive.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def install_etc(work, tools, repository, revision, run):
    source, root, obj = work / 'source', work / 'root', work / 'etc-obj'
    temporary = work / 'tmp'
    temporary.mkdir(mode=0o700, exist_ok=True)
    timestamp = run('source-timestamp', 'git', '-C', repository, 'show', '-s', '--format=%ct', revision).decode().strip()
    environment = dict(PATH=str(tools) + ':/usr/bin:/bin', LC_ALL='C', HOST_SH='/bin/sh', BSHELL='/bin/sh',
        TMPDIR=str(temporary), TMP=str(temporary), TEMP=str(temporary),
        MACHINE='evbarm', MACHINE_ARCH='aarch64', NETBSDSRCDIR=str(source), NETBSDOBJDIR=str(obj),
        TOOLDIR=str(tools.parent), DESTDIR=str(root), METALOG=str(work / 'artifacts/etc.mtree'),
        MAKECONF='/dev/null', MAKEOBJDIR='${.CURDIR:S,' + str(source) + ',' + str(obj) + ',}',
        _SRC_TOP_=str(source), _SRC_TOP_OBJ_=str(obj), USETOOLS='yes', MKUNPRIVED='yes', MKUPDATE='no',
        MKCOMPAT='no', MKRUMP='no', MKKMOD='no', MKX11='no', MKATF='no', MKKYUA='no', MKMAN='no', MKHTML='no', MKLINT='no',
        MKGCC='no', MKGCCCMDS='no', MKBINUTILS='no', MKLLVM='no', MKLLVMRT='no', MKGDB='no',
        MKREPRO='yes', MKREPRO_TIMESTAMP=timestamp, BUILDINFO='EmberBSD:' + revision)
    try:
        run('etc-directories', tools / 'nbmake', '-m', source / 'share/mk', '-C', source / 'etc', 'distrib-dirs', env=environment)
    finally:
        root.chmod(0o700)
    run('etc-install', tools / 'nbmake', '-m', source / 'share/mk', '-C', source / 'etc', 'install-etc-files', env=environment)
    return environment


def etc_metadata(path):
    """Keep target metadata while excluding hashes of customized config files."""
    result = []
    for line in path.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        words = line.split()
        relative_name(words[0])
        fields = [word for word in words[1:] if word.partition('=')[0] in
                  {'type', 'uid', 'gid', 'uname', 'gname', 'mode', 'link'}]
        result.append(words[0] + ' ' + ' '.join(fields) + '\n')
    return ''.join(result)


def add_user(root):
    """Add one unprivileged, key-only runtime user to the pinned source accounts."""
    for relative, expected in [('etc/master.passwd', 10), ('etc/group', 4)]:
        path = root / relative
        for line in path.read_text().splitlines():
            if not line or line.startswith('#'):
                continue
            fields = line.split(':')
            if len(fields) != expected or fields[0] == 'ember' or fields[2] == '1000':
                raise ValueError('Conflicting or invalid source account: ' + relative)
    with (root / 'etc/group').open('a') as stream:
        stream.write('ember:*:1000:\n')
    with (root / 'etc/master.passwd').open('a') as stream:
        stream.write('ember:*:1000:1000::0:0:EmberBSD runtime:/home/ember:/bin/sh\n')
    (root / 'home/ember/.ssh').mkdir(mode=0o700, parents=True)
    (root / 'home/ember').chmod(0o700)
    return ('./home/ember type=dir uid=1000 gid=1000 mode=0700\n'
            './home/ember/.ssh type=dir uid=1000 gid=1000 mode=0700\n'
            './home/ember/.ssh/authorized_keys type=file uid=1000 gid=1000 mode=0600\n')


def runtime_inputs(manifest, work):
    """Bind the existing query checks to the recorded full-base staging input."""
    receipt = work / 'artifacts/staging.json'
    if hashlib.sha256(receipt.read_bytes()).hexdigest() != manifest['staging_sha256']:
        raise ValueError('Full-base staging receipt changed.')
    staging = json.loads(receipt.read_text())
    if any(staging[key] != manifest[key] for key in ('base', 'base_revision', 'base_profile')):
        raise ValueError('Full-base staging identity differs from the image.')
    entries = records(Path(staging['base']), staging['archive_sha256'])
    root = work / 'root'
    payload = staging['full_base']['payload_sha256']
    sources = {}
    for name, entry in entries.items():
        if entry.isreg():
            sources[str(root / name)] = payload[name]
        elif entry.islnk():
            sources[str(root / name)] = payload[relative_name(entry.linkname)]
        elif entry.issym():
            sources[str(root / name)] = {'symlink': entry.linkname}
    return dict(manifest, base=str(root), sources_sha256=sources)
