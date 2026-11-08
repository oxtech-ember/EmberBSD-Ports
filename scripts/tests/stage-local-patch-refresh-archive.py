#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check bounded archive links and patch endpoints before patch execution."""
import argparse
import hashlib
import importlib.util
import io
from pathlib import Path
import sys
import tarfile
import tempfile
from types import SimpleNamespace

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', type=Path, required=True)
parser.add_argument('--patch', type=Path, required=True)
args = parser.parse_args()
if not args.sdk_source.is_absolute() or not args.patch.is_absolute() or not args.patch.is_file():
    parser.error('select absolute SDK source and patch tool paths')
sys.path.insert(0, str(args.sdk_source / 'src'))
from emberbsd_sdk import archive_metadata, jsonio, paths, sourceprep
from emberbsd_sdk.errors import SDKError

helper = Path(__file__).resolve().parents[1] / 'stage-local-patch-refresh.py'
spec = importlib.util.spec_from_file_location('stage_local_patch_refresh', helper)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def check_component_selection():
    patch = b'--- src/item.txt.orig\n+++ src/item.txt\n@@ -1 +1 @@\n-a\n+b\n'
    selected = module.archive_replay_components(
        [(Path('patch-a'), patch)],
        ('config/ports.conf', 'assets/*.css', 'Source/WebInspectorUI/Scripts/*.pl',
         'tools/run.pl', 'tools/run.pl.new'))
    required = {'src/item.txt', 'src/item.txt.orig', 'src/item.txt.orig.orig',
                'config/ports.conf', 'assets',
                'Source/WebInspectorUI/Scripts', 'tools/run.pl', 'tools/run.pl.new'}
    if not required.issubset(selected):
        raise AssertionError('patch endpoints or SUBST inputs are missing from replay components')
    if 'Documentation' in selected:
        raise AssertionError('unrelated paths entered bounded replay components')
    if module.archive_replay_components([(Path('patch-a'), patch)], ('*.mk',)) is not None:
        raise AssertionError('root-level SUBST glob did not request complete archive validation')
    print('PASS component selection')


def exercise(root, mode):
    recipe = root / 'pkgsrc/cat/demo'
    patchdir = recipe / 'patches'
    patchdir.mkdir(parents=True)
    work = root / 'work'
    work.mkdir()
    live = work / 'demo-1'
    (live / 'real').mkdir(parents=True)
    (live / 'real/file').write_bytes(b'old\n')
    archive = root / 'demo-1.tar'
    if mode == 'new-file':
        target = 'added/file'
        patch = b'--- /dev/null\n+++ added/file\n@@ -0,0 +1 @@\n+new file\n'
    else:
        target = 'real/file' if mode in ('valid', 'backup', 'size', 'casefold', 'selected-casefold', 'header-orig') else 'alias/file' if mode == 'ancestor' else 'alias'
        patch = (('--- real/file.orig\n+++ real/file\n' if mode == 'header-orig' else
                  '--- ' + target + '\n+++ ' + target + '\n') +
                 '@@ -1 +1 @@\n-old\n+new\n').encode()
    (patchdir / 'patch-a').write_bytes(patch)
    (recipe / 'Makefile').write_text('# fixture\n')
    with tarfile.open(archive, 'w') as tar:
        entry = tarfile.TarInfo('demo-1/real/file')
        entry.size = 4
        tar.addfile(entry, io.BytesIO(b'old\n'))
        if mode == 'casefold':
            for name, data in (
                    ('Documentation/webkitgtk-6.0/type_func.register_URL.html', b'upper case\n'),
                    ('Documentation/webkitgtk-6.0/type_func.register_url.html', b'lower case\n')):
                other = tarfile.TarInfo('demo-1/' + name)
                other.size = len(data)
                tar.addfile(other, io.BytesIO(data))
        if mode == 'header-orig':
            backup = tarfile.TarInfo('demo-1/real/file.orig.orig')
            backup.type = tarfile.SYMTYPE
            backup.linkname = 'file'
            tar.addfile(backup)
        if mode == 'selected-casefold':
            other = tarfile.TarInfo('demo-1/real/File')
            other.size = 6
            tar.addfile(other, io.BytesIO(b'other\n'))
        link = tarfile.TarInfo('demo-1/' + ('real/file.orig' if mode == 'backup' else 'alias'))
        link.type = tarfile.SYMTYPE
        link.linkname = 'file' if mode == 'backup' else 'real' if mode == 'ancestor' else 'real/file'
        tar.addfile(link)
    raw = archive.read_bytes()
    base = (f'BLAKE2s ({archive.name}) = {hashlib.blake2s(raw).hexdigest()}\n'
            f'SHA512 ({archive.name}) = {hashlib.sha512(raw).hexdigest()}\n'
            f'Size ({archive.name}) = {len(raw)} bytes\n')
    old_info = ('$NetBSD$\n\n' + base).encode()
    (recipe / 'distinfo').write_bytes(old_info + f'SHA1 (patch-a) = {hashlib.sha1(patch).hexdigest()}\n'.encode())
    (work / '.patch_done').write_bytes(b'')
    version = root / 'BUILD_VERSION'
    version.write_text('cat/demo/distinfo: ' + hashlib.sha256(old_info).hexdigest() + '\n')
    calls = []
    extracts = []
    def apply(*positional, **keyword):
        calls.append(1)
        return sourceprep.apply_patch(*positional, **keyword)
    def extract(*positional, **keyword):
        extracts.append(keyword)
        return sourceprep.extract_archive(*positional, **keyword)
    proxy = SimpleNamespace(ARCHIVE_INTERNAL_SYMLINKS_API=sourceprep.ARCHIVE_INTERNAL_SYMLINKS_API,
                            ARCHIVE_OPTIONAL_COMPONENTS_API=sourceprep.ARCHIVE_OPTIONAL_COMPONENTS_API,
                            archive_hashes=sourceprep.archive_hashes,
                            extract_archive=extract, apply_patch=apply)
    sdk = dict(paths=paths, sourceprep=proxy, archive_metadata=archive_metadata, jsonio=jsonio)
    scratch = root / 'scratch'
    scratch.mkdir()
    if mode == 'size':
        module.MAX_STAGE_ARCHIVE_BYTES = 3
    try:
        result = module.prepare(sdk, recipe, work, archive, 'demo-1', version,
                                args.patch, ['-E', '-p0', '--batch', '--forward',
                                             '-V', 'simple', '-z', '.orig'], scratch)
    except (ValueError, SDKError) as exc:
        if mode == 'valid':
            raise
        if calls:
            raise AssertionError(mode + ': patch invoked before refusal') from exc
        expected = ('extraction size limit' if mode == 'size' else
                    'duplicate old archive member' if mode == 'selected-casefold' else
                    'regular file')
        if mode in ('ancestor', 'leaf'):
            if not any(reason in str(exc) for reason in ('symlink', 'real directory', 'regular file')):
                raise AssertionError(mode + ': wrong refusal: ' + str(exc)) from exc
            if (live / 'real/file').read_bytes() != b'old\n' or (live / 'alias').exists():
                raise AssertionError(mode + ': refusal changed live source')
        elif expected not in str(exc):
            raise AssertionError(mode + ': wrong refusal: ' + str(exc)) from exc
    else:
        if mode in ('valid', 'casefold'):
            if len(calls) != 1 or result[0][0][1:3] != (b'old\n', b'new\n'):
                raise AssertionError(mode + ': unexpected successful replay')
        elif mode == 'new-file':
            if len(calls) != 1 or result[0][0] != ('added/file', None, b'new file\n', None, 0o644):
                raise AssertionError('new-file: /dev/null target did not replay')
            if not all(call.get('require_components') is False and
                       'added/file' in call.get('components', ()) for call in extracts):
                raise AssertionError('new-file: missing archive preimage was not optional')
        else:
            raise AssertionError(mode + ': unexpected successful replay')
        if mode == 'casefold':
            for call in extracts:
                if any(path.startswith('Documentation/') for path in call.get('components', ())):
                    raise AssertionError('unrelated Documentation collision entered the replay subset')
    finally:
        module.MAX_STAGE_ARCHIVE_BYTES = 512 * 1024 * 1024
    print('PASS', mode)


def exercise_omitted_old_target(root):
    recipe = root / 'pkgsrc/cat/demo'
    previous = root / 'previous/pkgsrc/cat/demo'
    current_patches = recipe / 'patches'
    previous_patches = previous / 'patches'
    current_patches.mkdir(parents=True)
    previous_patches.mkdir(parents=True)
    previous.mkdir(parents=True, exist_ok=True)
    (recipe / 'Makefile').write_text('# current recipe\n')
    (previous / 'Makefile').write_text('# previous recipe\n')

    archive = root / 'demo-1.tar'
    with tarfile.open(archive, 'w') as tar:
        for name, data in (('omitted', b'old source\n'), ('updated', b'base\n'), ('added', b'new source\n')):
            entry = tarfile.TarInfo('demo-1/' + name)
            entry.size = len(data)
            entry.mode = 0o644
            tar.addfile(entry, io.BytesIO(data))
    raw = archive.read_bytes()
    archive_lines = (f'BLAKE2s ({archive.name}) = {hashlib.blake2s(raw).hexdigest()}\n'
                     f'SHA512 ({archive.name}) = {hashlib.sha512(raw).hexdigest()}\n'
                     f'Size ({archive.name}) = {len(raw)} bytes\n')
    old_patch = b'--- omitted\n+++ omitted\n@@ -1 +1 @@\n-old source\n+old patched\n'
    current_patch = b'--- updated\n+++ updated\n@@ -1 +1 @@\n-base\n+changed\n'
    added_patch = b'--- /dev/null\n+++ added\n@@ -0,0 +1 @@\n+added\n'
    (previous_patches / 'patch-a').write_bytes(old_patch)
    (current_patches / 'patch-a').write_bytes(current_patch)
    (current_patches / 'patch-b').write_bytes(added_patch)
    old_info = ('$NetBSD$\n\n' + archive_lines +
                f'SHA1 (patch-a) = {hashlib.sha1(old_patch).hexdigest()}\n').encode()
    current_info = ('$NetBSD$\n\n' + archive_lines +
                    f'SHA1 (patch-a) = {hashlib.sha1(current_patch).hexdigest()}\n' +
                    f'SHA1 (patch-b) = {hashlib.sha1(added_patch).hexdigest()}\n').encode()
    (previous / 'distinfo').write_bytes(old_info)
    (recipe / 'distinfo').write_bytes(current_info)
    work = root / 'work'
    live = work / 'demo-1'
    live.mkdir(parents=True)
    for name, data in (('omitted', b'old source\n'), ('updated', b'base\n'), ('added', b'new source\n')):
        (live / name).write_bytes(data)
    (work / '.patch_done').write_bytes(b'')
    scratch = root / 'scratch'
    scratch.mkdir()
    sdk = dict(paths=paths, sourceprep=sourceprep, archive_metadata=archive_metadata, jsonio=jsonio)
    def replace_interpreter(candidate, replay_targets):
        if 'omitted' in replay_targets:
            path = candidate / 'omitted'
            path.write_bytes(b'#!/selected/tool\n' + path.read_bytes())
    result, _cookie, inventory = module.prepare(
        sdk, recipe, work, archive, 'demo-1', None, args.patch,
        ['-E', '-p0', '--batch', '--forward', '-V', 'simple', '-z', '.orig'], scratch,
        old_cookie=b'', previous_recipe=previous, patchdir=current_patches,
        distinfo=recipe / 'distinfo', previous_patchdir=previous_patches,
        previous_distinfo=previous / 'distinfo',
        old_pre_transform=replace_interpreter, pre_transform=replace_interpreter)
    rows = {row[0]: row for row in result}
    if (inventory != ['patch-a', 'patch-b'] or 'omitted' not in rows or
            rows['omitted'][1] != b'#!/selected/tool\nold source\n' or
            rows['omitted'][1] != rows['omitted'][2]):
        raise AssertionError('unapplied previous target was omitted from replay preimages')


def exercise_interpreter_then_subst(root):
    recipe = root / 'pkgsrc/cat/demo'
    previous = root / 'previous/pkgsrc/cat/demo'
    patches = recipe / 'patches'
    old_patches = previous / 'patches'
    patches.mkdir(parents=True)
    old_patches.mkdir(parents=True)
    previous.mkdir(parents=True, exist_ok=True)
    (recipe / 'Makefile').write_text('# current recipe\n')
    (previous / 'Makefile').write_text('# previous recipe\n')
    original = b'#!/usr/bin/env python3\npython3\nold\n'
    archive = root / 'demo-1.tar'
    with tarfile.open(archive, 'w') as tar:
        entry = tarfile.TarInfo('demo-1/real/script.pl')
        entry.size = len(original)
        entry.mode = 0o755
        tar.addfile(entry, io.BytesIO(original))
    raw = archive.read_bytes()
    archive_lines = (f'BLAKE2s ({archive.name}) = {hashlib.blake2s(raw).hexdigest()}\n'
                     f'SHA512 ({archive.name}) = {hashlib.sha512(raw).hexdigest()}\n'
                     f'Size ({archive.name}) = {len(raw)} bytes\n')
    patch_data = (b'--- real/script.pl\n+++ real/script.pl\n'
                  b'@@ -1,3 +1,3 @@\n'
                  b' #!/usr/bin/env python3\n'
                  b' python3\n'
                  b'-old\n+new\n')
    (old_patches / 'patch-a').write_bytes(patch_data)
    (patches / 'patch-a').write_bytes(patch_data)
    old_info = ('$NetBSD$\n\n' + archive_lines +
                f'SHA1 (patch-a) = {hashlib.sha1(patch_data).hexdigest()}\n').encode()
    (previous / 'distinfo').write_bytes(old_info)
    (recipe / 'distinfo').write_bytes(old_info)
    work = root / 'work'
    live = work / 'demo-1/real/script.pl'
    live.parent.mkdir(parents=True)
    live.write_bytes(b'#!/selected/python3\npython3-custom\nunexpected\n')
    live.chmod(0o755)
    (work / '.patch_done').write_bytes(b'')
    scratch = root / 'scratch'
    scratch.mkdir()
    sdk = dict(paths=paths, sourceprep=sourceprep, archive_metadata=archive_metadata, jsonio=jsonio)
    def replace_interpreter(candidate, affected):
        name = 'real/script.pl'
        if name not in affected:
            raise AssertionError('interpreter fixture target missing')
        path = candidate / name
        data = path.read_bytes()
        if not data.startswith(b'#!/usr/bin/env python3-custom\n'):
            raise AssertionError('SUBST did not run before replace-interpreter')
        path.write_bytes(data.replace(b'#!/usr/bin/env python3-custom', b'#!/selected/python3', 1))
    def subst_python(candidate, affected):
        path = candidate / 'real/script.pl'
        data = path.read_bytes()
        if not data.startswith(b'#!/usr/bin/env python3\n'):
            raise AssertionError('SUBST did not run before replace-interpreter')
        path.write_bytes(data.replace(b'python3', b'python3-custom'))
    result, _cookie, inventory = module.prepare(
        sdk, recipe, work, archive, 'demo-1', None, args.patch,
        ['-E', '-p0', '--batch', '--forward', '-V', 'simple', '-z', '.orig'], scratch,
        old_cookie=b'', previous_recipe=previous, patchdir=patches, distinfo=recipe / 'distinfo',
        previous_patchdir=old_patches, previous_distinfo=previous / 'distinfo',
        old_pre_transform=replace_interpreter, pre_transform=replace_interpreter,
        old_transform=subst_python, transform=subst_python,
        subst_before_pre_transform=True)
    row = next(row for row in result if row[0] == 'real/script.pl')
    if row[1] != b'#!/selected/python3\npython3-custom\nold\n' or \
            row[2] != b'#!/selected/python3\npython3-custom\nnew\n':
        raise AssertionError('interpreter and SUBST pre-configure transforms were not replayed in order')
    original_live = live.read_bytes()
    before_mtime = live.stat().st_mtime_ns
    try:
        module.transaction(sdk, work, work / 'demo-1', result, b'', inventory, lambda: None)
    except ValueError as exc:
        if 'live preimage differs' not in str(exc):
            raise
    else:
        raise AssertionError('unexpected live source was accepted')
    if live.read_bytes() != original_live or live.stat().st_mtime_ns != before_mtime or \
            (work / '.patch_done').read_bytes() != b'' or (work / '.emberbsd-patch-refresh.json').exists():
        raise AssertionError('mismatched live source changed during refusal')


check_component_selection()

with tempfile.TemporaryDirectory(prefix='patch-refresh-archive-') as tmp:
    for case in ('valid', 'ancestor', 'leaf', 'backup', 'header-orig', 'size', 'casefold', 'selected-casefold', 'new-file'):
        case_root = Path(tmp) / case
        case_root.mkdir()
        exercise(case_root, case)
    omitted_root = Path(tmp) / 'omitted-old-target'
    omitted_root.mkdir()
    exercise_omitted_old_target(omitted_root)
    print('PASS omitted old target')
    transform_root = Path(tmp) / 'interpreter-subst'
    transform_root.mkdir()
    exercise_interpreter_then_subst(transform_root)
    print('PASS interpreter then SUBST; unexpected live edit refused')
