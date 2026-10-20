#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Migrate package-set.rb without package installation.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import os
import shutil
from package_set_fixture import Fixture, check, metadata


def main():
    f = Fixture(sys.argv[1:])
    w = f.work
    payload = w / 'payload'
    long_name = 'share/pkgset/' + 'a'*90 + '/' + 'b'*90 + '/' + 'c'*90 + '/data'
    (payload / long_name).parent.mkdir(parents=True)
    (payload / long_name).write_text('Pkgtools payload fixture\n')
    os.link(payload / long_name, payload / 'share/pkgset/hardlink')
    (payload / 'share/pkgset/symlink').symlink_to('../../' + long_name)
    (payload / 'share/pkgset/root').write_text('Package root fixture\n')
    (payload / 'lib').mkdir()
    (payload / 'lib/libfixture.so.8.0').write_text('Package library fixture\n')
    (payload / 'lib/libfixture.so.8').symlink_to('libfixture.so.8.0')
    archives = []
    for name, files in [('pkgset-leaf-1.0', [long_name, 'share/pkgset/hardlink', 'share/pkgset/symlink', 'lib/libfixture.so.8.0', 'lib/libfixture.so.8']),
                        ('pkgset-root-1.0', ['share/pkgset/root'])]:
        build = metadata('aarch64') + f'PROVIDES=/usr/pkg/{files[0]}\nREQUIRES=/usr/lib/libc.so.12\n'.encode()
        build += (b'REQUIRES=/usr/pkg/lib/libfixture.so.8\n' if 'root' in name else
                  b'PROVIDES=/usr/pkg/lib/libfixture.so.8.0\nPROVIDES=/usr/pkg/lib/libfixture.so.8\n')
        archives.append(f.package(w/'cache', name, payload, files, build=build,
                                  dependencies='pkgset-leaf>=1.0' if 'root' in name else None))
    leaf, root = archives
    database = w / 'pkgdb'
    for archive in archives:
        f.database(archive, database)
    check(f.run([f.info, '-K', database, '-e', 'pkgset-leaf>=1.0']) == b'pkgset-leaf-1.0\n', 'real pkg_info resolution differs')
    index = w / 'archives.txt'
    def case(name, db, leaves, expected=None, root_archive=root):
        leaves = leaves if isinstance(leaves, list) else [leaves]
        index.write_text(''.join(str(p) + '\n' for p in [*leaves, root_archive]))
        destination, log = w / ('set-' + name), w / (name + '.copies.log')
        result = f.audit(db, index, destination, ['pkgset-root-1.0'], copy_log=log)
        f.result(name, result, expected, destination)
        if expected:
            check(not log.exists(), 'Rejected archive reached real copy')
        else:
            check(log.read_text().splitlines() == [str(leaf), str(root_archive)], 'Copy order differs')
            check((destination/'install-order.txt').read_bytes() == b'pkgset-leaf-1.0.tgz\npkgset-root-1.0.tgz\n', 'Dependency order differs')
            for line in (destination/'packages.sha256').read_text().splitlines():
                digest, path = line.split()
                check(f.sha(destination/path) == digest, 'Copied SHA256 differs')
            for source in (leaf, root):
                check((destination/'packages'/source.name).read_bytes() == source.read_bytes(), 'Archive bytes differ')
    case('valid-pax-hardlink-symlink', database, leaf)
    def mutate(name, expected, change):
        tree = w/name/'tree'; f.unpack(leaf, tree); change(tree)
        archive = w/name/leaf.name; f.pack(tree, archive)
        case(name, database, archive, expected)
    def replace(path, old, new):
        path.chmod(0o644); path.write_bytes(path.read_bytes().replace(old,new))
    mutate('stale-manifest', 'No archive with the installed manifest', lambda t: replace(t/'+CONTENTS', b'@name ', b'@comment stale\n@name '))
    mutate('wrong-architecture', 'Wrong target MACHINE_ARCH', lambda t: replace(t/'+BUILD_INFO', b'aarch64', b'x86_64'))
    mutate('wrong-os-abi', 'Wrong target OS_VERSION', lambda t: replace(t/'+BUILD_INFO', b'11.0', b'10.0'))
    mutate('corrupt-payload', 'Archive payload mismatch', lambda t: (t/long_name).write_text('Changed bytes with unchanged manifest\n'))
    race = w/'cache-race'; race.mkdir()
    source = race/leaf.name
    bad = w/'corrupt-payload'/leaf.name
    shutil.copyfile(bad, source)
    index.write_text(str(source)+'\n'+str(root)+'\n')
    destination = w/'set-cache-race'
    events = []
    result = f.audit(database,index,destination,['pkgset-root-1.0'],race=dict(source=source,good=leaf,bad=bad,events=events))
    check(events == ['hash-a-then-b','restore-a-before-copy'], 'A-to-B-to-A transitions did not occur')
    (race/'events.log').write_text('\n'.join(events)+'\n')
    f.result('reject-cache-a-to-b-to-a',result,'Archive payload mismatch',destination)
    def symlink(t):
        (t/'share/pkgset/symlink').unlink(); (t/'share/pkgset/symlink').symlink_to('wrong-target')
    mutate('changed-symlink','Archive payload mismatch',symlink)
    mutate('missing-payload','Missing archive member',lambda t:(t/long_name).unlink())
    mutate('unlisted-payload','Unlisted archive member',lambda t:(t/'share/pkgset/unlisted').write_text('not in manifest\n'))
    mutate('changed-metadata','Archive metadata mismatch +DESC',lambda t:replace(t/'+DESC', (t/'+DESC').read_bytes(), b'Different description\n'))
    for name, extra, expected in [
        ('stale-provider',b'PROVIDES=/usr/pkg/lib/libfixture.so.7\n','PROVIDES is absent from the manifest'),
        ('self-required-file',b'REQUIRES=/usr/pkg/share/pkgset/hardlink\n',"REQUIRES names the package's own payload"),
        ('self-required-symlink',b'REQUIRES=/usr/pkg/share/pkgset/symlink\n',"REQUIRES names the package's own payload")]:
        tree=w/name/'tree';f.unpack(leaf,tree);db=w/name/'pkgdb';shutil.copytree(database,db)
        data=(tree/'+BUILD_INFO').read_bytes()+extra
        for path in (tree/'+BUILD_INFO',db/'pkgset-leaf-1.0/+BUILD_INFO'):
            path.chmod(0o644);path.write_bytes(data)
        archive=w/name/leaf.name;f.pack(tree,archive);case(name,db,archive,expected)
    name='obsolete-library-consumer';tree=w/name/'tree';f.unpack(root,tree)
    db=w/name/'pkgdb';shutil.copytree(database,db)
    for path in (tree/'+BUILD_INFO',db/'pkgset-root-1.0/+BUILD_INFO'):
        replace(path,b'REQUIRES=/usr/pkg/lib/libfixture.so.8',b'REQUIRES=/usr/pkg/lib/libfixture.so.7')
    archive=w/name/root.name;f.pack(tree,archive)
    case(name,db,leaf,'Package-managed requirement is absent from the set: pkgset-root-1.0: /usr/pkg/lib/libfixture.so.7',archive)
    case('valid-after-stale-cache-copy',database,[w/'wrong-architecture'/leaf.name,leaf])
    missing=w/'missing-dependency-db';shutil.copytree(database,missing);shutil.rmtree(missing/'pkgset-leaf-1.0')
    case('missing-dependency',missing,leaf,'Unresolved or ambiguous dependency')
    truncated=w/'truncated';truncated.mkdir();(truncated/leaf.name).write_bytes(leaf.read_bytes()[:leaf.stat().st_size//2])
    case('truncated-archive',database,truncated/leaf.name,'No archive with the installed manifest')
    index.write_text(str(leaf)+'\n'+str(root)+'\n')
    accepted=w/'set-valid-pax-hardlink-symlink';before=(accepted/'packages.sha256').read_bytes()
    f.result('preserve-existing-output',f.audit(database,index,accepted,['pkgset-root-1.0']),'Output already exists')
    check((accepted/'packages.sha256').read_bytes()==before,'Existing output changed')
    destination=w/'set-duplicate-roots'
    f.result('reject-duplicate-roots',f.audit(database,index,destination,['pkgset-root-1.0']*2),'Duplicate root package',destination)
    print(f'PASS: {f.count} package-set cases with actual pkg_create/pkg_info and archive payloads')


if __name__ == '__main__':
    main()
