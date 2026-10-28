#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that native b2 cross builds accept the primary Clang toolset."""
import argparse
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
KEYS = ('PKGSRC_COMPILER', 'BOOST_TOOLSET', 'PKG_FAIL_REASON', 'BJAM_ARGS',
        'BJAM_BUILD', 'WRKDIR', 'CXX', 'AR', 'MACHINE_ARCH')
SELECTED = ('boost-headers', 'boost-jam', 'boost-libs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pkgsrc', required=True, help='exported Ports pkgsrc tree')
    parser.add_argument('--cross-makeconf', required=True, help='Clang cross mk.conf')
    parser.add_argument('--bmake', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    pkgsrc = Path(args.pkgsrc).resolve(strict=True)
    patch = root / 'profiles/common-build-tools/patches/pkgsrc-boost-cross-target.patch'
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        tree = work / 'pkgsrc'
        (tree / 'devel').mkdir(parents=True)
        for item in pkgsrc.iterdir():
            if item.name != 'devel':
                (tree / item.name).symlink_to(item, target_is_directory=item.is_dir())
        for item in (pkgsrc / 'devel').iterdir():
            if item.name not in SELECTED:
                (tree / 'devel' / item.name).symlink_to(item, target_is_directory=True)
        # Apply the repair to the pinned upstream recipes, as the export does.
        for name in SELECTED:
            shutil.copytree(root / 'upstream/pkgsrc/devel' / name, tree / 'devel' / name)
        subprocess.run(['patch', '-s', '-f', '--fuzz=0', '-p1', '-d', str(tree)],
                       input=patch.read_bytes(), check=True)
        argv = [args.bmake, 'MAKECONF=' + args.cross_makeconf,
                'WRKOBJDIR=' + str(work / 'objects'), 'MAKE_JOBS=1']
        query = [arg for key in KEYS for arg in ('-v', key)]
        result = subprocess.run(argv + query, cwd=tree / 'devel/boost-headers',
                                check=True, capture_output=True, text=True)
        value = dict(zip(KEYS, result.stdout.splitlines()))
        assert value['PKGSRC_COMPILER'].split()[0] == 'clang', value
        assert value['BOOST_TOOLSET'] == 'clang', value
        assert not value['PKG_FAIL_REASON'], value['PKG_FAIL_REASON']
        flags = shlex.split(value['BJAM_BUILD'])
        wanted = {'target-os=netbsd', 'address-model=64', 'binary-format=elf'}
        wanted.update(('architecture=arm', 'abi=aapcs') if value['MACHINE_ARCH'] == 'aarch64'
                      else ('architecture=x86', 'abi=sysv'))
        assert wanted <= set(flags), flags
        site = Path(value['WRKDIR']) / 'pkgsrc-cross-site-config.jam'
        assert '--site-config=' + str(site) in shlex.split(value['BJAM_ARGS']), value
        assert '--toolset=clang' in shlex.split(value['BJAM_ARGS'])
        # Run the real hook. The generated Jam file must name the cross tools.
        site.parent.mkdir(parents=True)
        subprocess.run(argv + ['pre-build'], cwd=tree / 'devel/boost-headers',
                       check=True, capture_output=True)
        expected = 'using clang : : %s : <archiver>%s ;\n' % (value['CXX'], value['AR'])
        assert site.read_text(encoding='utf-8') == expected, site.read_text(encoding='utf-8')
    print('PASS: Clang cross metadata, b2 toolset and site configuration for boost-headers.')


if __name__ == '__main__':
    main()
