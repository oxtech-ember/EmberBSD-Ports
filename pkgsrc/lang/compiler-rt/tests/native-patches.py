#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Apply the native package patch set to its actual selected archive members."""
import argparse
from pathlib import Path
import shlex
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'files'))
import source as owner


def main():
    arguments = owner.load_sdk(sys.argv[1:])
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('bmake', 'pkgsrc', 'makeconf', 'archive', 'git', 'patch', 'work'):
        cli.add_argument('--' + name, required=True)
    cli.add_argument('--make-arg', action='append', default=[])
    args = cli.parse_args(arguments)
    work = Path(args.work)
    work.mkdir()
    # Read the current owner Makefile through the caller's complete pkgsrc
    # framework. This does not edit an export or start any package target.
    keys = ('DISTNAME', 'EXTRACT_ELEMENTS', 'PATCH_STRIP')
    command = [args.bmake, '-C', str(Path(args.pkgsrc) / 'lang/compiler-rt'),
        '-f', str(owner.OWNER / 'Makefile'), 'MAKECONF=' + args.makeconf,
        *args.make_arg, *[arg for key in keys for arg in ('-V', key + '=${' + key + '}')]]
    result = owner.process.capture(command)
    values = dict(line.split('=', 1) for line in result.stdout.decode().splitlines())
    owner.require(set(values) == set(keys), 'native recipe metadata is incomplete')
    owner.require(values['PATCH_STRIP'] == '-p1', 'native patch strip differs')
    root_name = values['DISTNAME']
    elements = shlex.split(values['EXTRACT_ELEMENTS'])
    owner.require(elements and all(name.startswith(root_name + '/') for name in elements),
                  'native extraction escapes the selected LLVM release')
    components = [name[len(root_name) + 1:] for name in elements]
    metadata, patches = owner.recipe(args.git)
    archive = Path(args.archive)
    hashes = owner.sourceprep.archive_hashes(owner.read(archive))
    owner.require(archive.name == metadata['source']['archive'] and all(
        hashes[key] == metadata['source'][key] for key in ('sha512', 'blake2s', 'size')),
        'native archive differs from the common release')
    owner.sourceprep.extract_archive(archive, work, root_name, 'native compiler-rt',
        components=components, max_members=500000, max_bytes=4 * 1024**3)
    root = work / root_name
    for path, subdirectory, strip in patches:
        if subdirectory != '.':
            continue  # Native compiler-rt imports the installed LLVM CMake package.
        data = owner.read(path)
        owner.sourceprep.apply_patch(args.patch, path, data, root, 'native compiler-rt',
            patch_args=('-p' + str(strip), '-f', '-N', '-F0', '-V', 'none'), allow_dev_null=True)
    module = root / 'libunwind/cmake/config-ix.cmake'
    owner.require('function(libunwind_check_library_exists' in module.read_text(),
                  'native extraction did not receive the common libunwind patch')
    # Causal control: the previous extraction omitted libunwind. Applying the
    # actual new patch to that layout must fail, rather than skip its content.
    missing = work / 'missing-libunwind'
    missing.mkdir()
    patch = owner.OWNER / 'patches/patch-20-libunwind-library-probes'
    try:
        owner.sourceprep.apply_patch(args.patch, patch, owner.read(patch), missing,
            'missing native libunwind', patch_args=('-p1', '-f', '-N', '-F0', '-V', 'none'))
    except owner.SDKError:
        pass
    else:
        raise AssertionError('absent libunwind patch input was accepted')
    print('PASS: native EXTRACT_ELEMENTS accepts every common runtime patch; missing libunwind is rejected')


if __name__ == '__main__':
    main()
