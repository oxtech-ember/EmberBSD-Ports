#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check source mirror identity, byte checks, and bounded directory scans."""
import errno
import importlib.util
import os
from pathlib import Path
import tempfile
from unittest.mock import patch


owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'source_view', owner / 'electron44/files/protobuf-source-view.py')
view = importlib.util.module_from_spec(spec)
spec.loader.exec_module(view)


def rejected(call):
    try:
        call()
    except (ValueError, OSError):
        return
    raise AssertionError('invalid source mirror was accepted')


class CountedEntry:
    def __init__(self, entry, counts):
        self.entry = entry
        self.counts = counts

    @property
    def name(self):
        return self.entry.name

    @property
    def path(self):
        return self.entry.path

    def stat(self, *, follow_symlinks=True):
        key = (os.fspath(self.path), follow_symlinks)
        self.counts['entry_stats'][key] = self.counts['entry_stats'].get(key, 0) + 1
        return self.entry.stat(follow_symlinks=follow_symlinks)

    def __getattr__(self, name):
        return getattr(self.entry, name)


class CountedScan:
    def __init__(self, scan, counts):
        self.scan = scan
        self.counts = counts

    def __enter__(self):
        self.scan.__enter__()
        return self

    def __exit__(self, *args):
        return self.scan.__exit__(*args)

    def __iter__(self):
        for entry in self.scan:
            yield CountedEntry(entry, self.counts)


with tempfile.TemporaryDirectory(prefix='electron-source-mirror-') as temporary:
    root = Path(temporary)
    source = root / 'source'
    (source / 'nested').mkdir(parents=True)
    (source / 'regular.bin').write_bytes(b'same payload\n')
    (source / 'samebytes.txt').write_bytes(b'same payload\n')
    (source / 'nested/child.bin').write_bytes(b'child payload\n')
    (source / 'link').symlink_to('regular.bin')

    hardlink_view = root / 'hardlink-view'
    view.mirror(source, hardlink_view)
    assert os.stat(source / 'regular.bin').st_ino == os.stat(hardlink_view / 'regular.bin').st_ino
    view.mirror(source, hardlink_view, verify=True)

    copy_view = root / 'copy-view'
    def cross_device(*args, **kwargs):
        raise OSError(errno.EXDEV, 'fixture cross-device link')
    with patch.object(view.os, 'link', side_effect=cross_device):
        view.mirror(source, copy_view)
    assert os.stat(source / 'regular.bin').st_ino != os.stat(copy_view / 'regular.bin').st_ino
    view.mirror(source, copy_view, verify=True)

    replacement = source / 'replacement.bin'
    replacement.write_bytes(b'changed payload\n')
    replacement.replace(source / 'regular.bin')
    rejected(lambda: view.mirror(source, copy_view, verify=True))
    replacement.write_bytes(b'same payload\n')
    replacement.replace(source / 'regular.bin')
    view.mirror(source, copy_view, verify=True)
    (source / 'added.bin').write_bytes(b'new\n')
    rejected(lambda: view.mirror(source, copy_view, verify=True))
    (source / 'added.bin').unlink()
    view.mirror(source, copy_view, verify=True)
    (source / 'nested/child.bin').unlink()
    rejected(lambda: view.mirror(source, copy_view, verify=True))
    (source / 'nested/child.bin').write_bytes(b'child payload\n')
    view.mirror(source, copy_view, verify=True)
    (source / 'link').unlink()
    (source / 'link').symlink_to('nested/child.bin')
    rejected(lambda: view.mirror(source, copy_view, verify=True))

    # A symlink with identical bytes must not pass as a mirrored regular file.
    (source / 'link').unlink()
    (source / 'link').symlink_to('regular.bin')
    view.mirror(source, copy_view, verify=True)
    (copy_view / 'regular.bin').unlink()
    (copy_view / 'regular.bin').symlink_to('samebytes.txt')
    rejected(lambda: view.mirror(source, copy_view, verify=True))

    if hasattr(os, 'mkfifo'):
        fifo = source / 'fifo'
        output_fifo = copy_view / 'fifo'
        os.mkfifo(fifo)
        os.mkfifo(output_fifo)
        rejected(lambda: view.mirror(source, copy_view, verify=True))
        fifo.unlink()
        output_fifo.unlink()

    # Electron's build_electron_definitions GN action writes these two
    # products into the source view. Only regular files with these names may
    # be absent from the prepared electron source.
    electron_source = root / 'electron-source'
    electron_source.mkdir()
    (electron_source / 'build.gni').write_text('source entry\n')
    electron_view = root / 'electron-view'
    view.mirror(electron_source, electron_view)
    (electron_view / 'electron-api.json').write_text('{"api": true}\n')
    (electron_view / 'electron.d.ts').write_text('export {}\n')
    generated = {'electron-api.json', 'electron.d.ts'}
    view.mirror(electron_source, electron_view, verify=True, generated_files=generated)
    (electron_view / 'unexpected.json').write_text('{}\n')
    rejected(lambda: view.mirror(electron_source, electron_view, verify=True,
                                 generated_files=generated))
    (electron_view / 'unexpected.json').unlink()

    (electron_view / 'electron-api.json').unlink()
    (electron_view / 'electron-api.json').symlink_to('build.gni')
    rejected(lambda: view.mirror(electron_source, electron_view, verify=True,
                                 generated_files=generated))
    (electron_view / 'electron-api.json').unlink()
    (electron_view / 'electron.d.ts').unlink()
    (electron_view / 'electron.d.ts').mkdir()
    rejected(lambda: view.mirror(electron_source, electron_view, verify=True,
                                 generated_files=generated))

    # If a prepared source already owns a generated filename, it remains a
    # normal source entry and must still match byte-for-byte.
    electron_collision_source = root / 'electron-collision-source'
    electron_collision_source.mkdir()
    (electron_collision_source / 'electron-api.json').write_text('{"source": true}\n')
    electron_collision_view = root / 'electron-collision-view'
    view.mirror(electron_collision_source, electron_collision_view)
    view.mirror(electron_collision_source, electron_collision_view, verify=True,
                generated_files=generated)
    (electron_collision_view / 'electron-api.json').unlink()
    (electron_collision_view / 'electron-api.json').write_text('{"generated": true}\n')
    rejected(lambda: view.mirror(electron_collision_source, electron_collision_view,
                                 verify=True, generated_files=generated))

    # Count the exact scanner and DirEntry stat operations for a clean verify.
    measured_dest = root / 'measured-view'
    view.mirror(source, measured_dest)
    counts = {'scans': {}, 'entry_stats': {}, 'lstats': 0}
    real_scandir = os.scandir
    real_lstat = os.lstat
    def counted_scandir(path):
        key = os.fspath(path)
        counts['scans'][key] = counts['scans'].get(key, 0) + 1
        return CountedScan(real_scandir(path), counts)
    def counted_lstat(path):
        counts['lstats'] += 1
        return real_lstat(path)
    with patch.object(view.os, 'scandir', side_effect=counted_scandir):
        with patch.object(view.os, 'lstat', side_effect=counted_lstat):
            view.mirror(source, measured_dest, verify=True)
    assert counts['scans'] == {str(source): 1, str(measured_dest): 1,
                               str(source / 'nested'): 1,
                               str(measured_dest / 'nested'): 1}, counts['scans']
    assert counts['entry_stats'][(str(source / 'regular.bin'), False)] == 1
    assert counts['entry_stats'][(str(measured_dest / 'regular.bin'), False)] == 1
    new_metadata_calls = counts['lstats'] + sum(counts['entry_stats'].values())
    # Old implementation: 5 checks per regular file, 2 per symlink,
    # 4 per nested directory, and 2 for the top-level destination.
    legacy_metadata_calls = 5 * 3 + 2 + 4 + 2
    assert new_metadata_calls < legacy_metadata_calls, (new_metadata_calls,
                                                         legacy_metadata_calls)

    # A namespace mutation during enumeration must fail the saved directory
    # identity check instead of producing a partial verification result.
    mutation_dest = root / 'mutation-view'
    view.mirror(source, mutation_dest)
    original_scandir = os.scandir
    mutated = [False]
    def mutate_during_scan(path):
        scan = original_scandir(path)
        if os.fspath(path) == str(source) and not mutated[0]:
            mutated[0] = True
            class MutatingScan:
                def __enter__(self):
                    scan.__enter__()
                    return self
                def __exit__(self, *args):
                    return scan.__exit__(*args)
                def __iter__(self):
                    yield from scan
                    (source / 'during-scan').write_bytes(b'new entry\n')
            return MutatingScan()
        return scan
    with patch.object(view.os, 'scandir', side_effect=mutate_during_scan):
        rejected(lambda: view.mirror(source, mutation_dest, verify=True))
    (source / 'during-scan').unlink()

print('PASS: mirror identity/content checks, named Electron GN outputs, symlink types, scan/stat counts')
