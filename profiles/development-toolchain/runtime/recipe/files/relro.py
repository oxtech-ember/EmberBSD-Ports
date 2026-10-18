# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted authenticated link-only runtime hardening.
from pathlib import Path
from emberbsd_sdk import jsonio
import inheritance
from runtime import Invalid, SOURCE_SHA256, Stage, require, hash_file, hash_claims, text

COMPONENTS = {'libgcc': 'libgcc_s.so.1', 'libgomp': 'libgomp.so.1.0', 'libatomic': 'libatomic.so.3.0'}
PARENT = ('inputs.txt', 'stage.sha256', 'stage.symlinks', 'build-success', 'inheritance.json')


def _verify(work, pkgsrc, archive, current, expected_source=SOURCE_SHA256):
    work, pkgsrc = Path(work), Path(pkgsrc)
    file = work / 'relink.json'
    receipt = jsonio.read_json(file)
    require(type(receipt['format']) is int and receipt['format'] == 1, 'Unknown relink format')
    require(hash_claims(text(work / 'inputs.txt'), file) == [hash_file(file)], 'Relink receipt not pinned')
    parent_work = Path(receipt['parent_work']).resolve(strict=True)
    require(text(parent_work / 'build-success') == 'runtime-libstdcxx-rebuild\n', 'Expected original completed libstdc++ rebuild')
    for name in PARENT:
        require(hash_file(parent_work / name) == receipt['parent_receipts'][name], 'Relink parent receipt changed')
    parent = Stage(parent_work, pkgsrc, archive, expected_source=expected_source, historical=True).verify()
    for key in ('GCC_RUNTIME_TARGET', 'GCC_RUNTIME_TRIPLET', 'GCC_RUNTIME_LIBRARIES', 'EMBERBSD_SEED_SOURCE'):
        require(current['metadata'][key] == parent['metadata'][key], 'Relink parent identity changed')
    require(hash_file(receipt['backup']['path']) == receipt['backup']['sha256'], 'Archived build changed')
    for path, digest in receipt['inputs'].items():
        require(Path(path).is_absolute() and str(Path(path).resolve(strict=True)) == path, 'Relink inputs require canonical absolute paths')
        require(hash_file(path) == digest, 'Relink input changed')
    old = inheritance.inventory(parent_work / 'stage')
    expected = dict(old)
    commands = jsonio.read_json(work / 'commands.json')
    require(set(receipt['components']) == set(COMPONENTS), 'Unexpected relink component set')
    for library, basename in COMPONENTS.items():
        relative = 'usr/pkg/gcc16/lib/' + basename
        record = receipt['components'][library]
        require(record['path'] == relative and record['before'] == old[relative]['sha256'], 'Wrong relink path or original bytes')
        before, after = work / 'proof' / (basename + '.baseline'), work / 'proof' / (basename + '.relro')
        require(hash_file(before) == record['before'], 'Baseline did not reproduce accepted DSO')
        require(hash_file(after) == record['after'] and record['after'] != record['before'], 'Relink output changed or retained old bytes')
        pair = [item for item in commands if item['component'] == library]
        require(len(pair) == 2 and [item['status'] for item in pair] == [0, 0], 'Missing real baseline/final commands')
        argv = list(pair[0]['argv'])
        require('-o' in argv, 'Missing baseline output')
        index = argv.index('-o')
        require(index + 1 < len(argv) and argv[index + 1] == str(before), 'Wrong baseline output')
        argv[index + 1] = str(after)
        require(pair[1]['argv'] == argv + ['-Wl,-z,relro'], 'Unexpected link transformation')
        expected[relative] = dict(old[relative], sha256=record['after'])
    require(inheritance.inventory(work / 'stage') == expected, 'Relink changed unowned stage file')
    return {'GCC_RUNTIME_BUILD_MODE': 'libstdcxx-and-runtime-relro-relink', 'GCC_RUNTIME_RELINK_SHA256': hash_file(file), 'GCC_RUNTIME_LOCALE_INPUTS_SHA256': receipt['parent_receipts']['inputs.txt']}


def verify(work, pkgsrc, archive, current, expected_source=SOURCE_SHA256):
    try:
        return _verify(work, pkgsrc, archive, current, expected_source)
    except (KeyError, TypeError, ValueError, IndexError) as error:
        raise Invalid("Invalid relro receipt: " + str(error)) from error
