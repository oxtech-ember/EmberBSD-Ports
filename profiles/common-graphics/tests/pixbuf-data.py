#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). No target, SSH connection, SDK or download is used.
"""The GdkPixbuf target runner replays stored per-platform target data.

With EMBERBSD_GI_DUMP_MODE=replay (the cross recipe default) target-tools.py
answers --loaders and --mime from files/target-data/PLATFORM without the SDK,
a query configuration or a target, and refuses data for another platform,
recipe, package or loader module set. Capture stores the normalized output
of a live query once. Without a mode the runner keeps its live behavior.

Usage: pixbuf-data.py [--helper target-tools.py]   (run with Python 3.15)
"""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ARGS = None
MODULES = ('ani', 'bmp', 'png')
IDENT = {'EMBERBSD_GI_DUMP_PLATFORM': 'NetBSD-11.0-aarch64', 'EMBERBSD_GI_DUMP_RECIPE': 'graphics/gdk-pixbuf2',
         'EMBERBSD_GI_DUMP_PACKAGE': 'gdk-pixbuf2-2.44.8'}
MIME = b'image/bmp;image/png;image/x-ani;'


def loader_output(paths):
    text = ('# GdkPixbuf Image Loader Modules file\n# Automatically generated file, do not edit\n'
            '# Created by gdk-pixbuf-query-loaders from gdk-pixbuf-2.44.8\n#\n'
            '# LoaderDir = /usr/pkg/lib/gdk-pixbuf-2.0/2.10.0/loaders\n#\n')
    for path in paths:
        name = Path(path).name[len('libpixbufloader-'):-3]
        text += f'"{path}"\n"{name}" 5 "gdk-pixbuf" "The {name.upper()} image format" "LGPL"\n"image/{name}" ""\n"{name}" ""\n\n'
    return text.encode()


class PixbufData(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.build = root / 'build'
        (self.build / 'loaders').mkdir(parents=True)
        self.modules = []
        for name in MODULES:
            module = self.build / 'loaders' / f'libpixbufloader-{name}.so'
            module.write_bytes(b'\x7fELF')
            self.modules.append(str(module.resolve()))
        for tool in ('gdk-pixbuf-query-loaders', 'gdk-pixbuf-print-mime-types'):
            (self.build / tool).write_bytes(b'\x7fELF')
        self.capture_dir = root / 'capture'
        self.capture_dir.mkdir()
        self.data = self.capture_dir / IDENT['EMBERBSD_GI_DUMP_PLATFORM'] / 'graphics_gdk-pixbuf2'
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith('EMBERBSD_')}
        self.env.update(IDENT, EMBERBSD_GI_DUMP_MODE='replay', EMBERBSD_PIXBUF_DATA_DIR=str(self.data),
                        EMBERBSD_GI_DUMP_CAPTURE_DIR=str(self.capture_dir), PYTHONDONTWRITEBYTECODE='1')
        spec = importlib.util.spec_from_file_location('pixbuf_data', Path(ARGS.helper).parent / 'pixbuf_data.py')
        self.pixbuf_data = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.pixbuf_data)

    def tearDown(self):
        self.temp.cleanup()

    def run_helper(self, *args, **changes):
        env = dict(self.env)
        for key, value in changes.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        return subprocess.run([sys.executable, '-E', '-S', ARGS.helper, *map(str, args)], env=env,
                              capture_output=True, timeout=60)

    def store(self):
        self.pixbuf_data.capture(self.env, 'loaders', self.modules, loader_output(self.modules))
        cache = self.build / 'loaders.cache'
        cache.write_bytes(loader_output(self.modules))
        self.pixbuf_data.capture(self.env, 'mime', [str(cache)], MIME)
        return cache

    def loaders(self, modules=None, **changes):
        return self.run_helper('--loaders', self.build / 'gdk-pixbuf-query-loaders', *(modules or self.modules),
                               **changes)

    def test_stored_data_are_normalized(self):
        self.store()
        text = (self.data / 'loaders.cache').read_text()
        self.assertTrue(text.startswith('# EmberBSD GdkPixbuf target data 1\n# platform: NetBSD-11.0-aarch64\n'
                                        '# recipe: graphics/gdk-pixbuf2\n# package: gdk-pixbuf2-2.44.8\n'
                                        '# query: loaders\n# modules: libpixbufloader-ani.so '
                                        'libpixbufloader-bmp.so libpixbufloader-png.so\n# data-sha256: '))
        self.assertIn('"@MODULE@/libpixbufloader-png.so"\n', text)
        self.assertNotIn(str(self.build), text)
        self.assertTrue((self.data / 'mime-types.txt').read_text().endswith('#\n' + MIME.decode() + '\n'))

    def test_replay_needs_no_sdk_query_or_target(self):
        cache = self.store()
        result = self.loaders(EMBERBSD_SDK_SOURCE=None, EMBERBSD_GI_QUERY_CONFIG=None, PATH='/nonexistent')
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout.decode()
        for module in self.modules:
            self.assertIn(f'"{module}"\n', output)
        self.assertNotIn('@MODULE@', output)
        # Relative module arguments report the same canonical paths.
        relative = [os.path.relpath(path) for path in self.modules]
        self.assertEqual(self.loaders(relative).stdout, result.stdout)
        mime = self.run_helper('--mime', self.build / 'gdk-pixbuf-print-mime-types', cache,
                               EMBERBSD_SDK_SOURCE=None, PATH='/nonexistent')
        self.assertEqual(mime.returncode, 0, mime.stderr)
        self.assertEqual(mime.stdout, MIME)

    def test_replay_refuses_other_builds(self):
        self.store()
        for key, other in (('EMBERBSD_GI_DUMP_PLATFORM', 'NetBSD-11.0-x86_64'),
                           ('EMBERBSD_GI_DUMP_PACKAGE', 'gdk-pixbuf2-2.44.9'),
                           ('EMBERBSD_GI_DUMP_RECIPE', 'graphics/gdk-pixbuf')):
            with self.subTest(key=key):
                result = self.loaders(**{key: other})
                self.assertEqual(result.returncode, 1)
                self.assertIn(b'stored data are for', result.stderr)
                self.assertEqual(result.stdout, b'')
        fewer = self.loaders(self.modules[:2])
        self.assertEqual(fewer.returncode, 1)
        self.assertIn(b'loader modules', fewer.stderr)
        tool = self.run_helper('--loaders', self.build / 'gdk-pixbuf-print-mime-types', *self.modules)
        self.assertEqual(tool.returncode, 1)
        self.assertIn(b'unexpected target tool', tool.stderr)

    def test_replay_refuses_missing_or_changed_data(self):
        missing = self.loaders()
        self.assertEqual(missing.returncode, 1)
        self.assertIn(b'No stored GdkPixbuf target data for NetBSD-11.0-aarch64 in graphics/gdk-pixbuf2',
                      missing.stderr)
        self.store()
        path = self.data / 'loaders.cache'
        path.write_text(path.read_text().replace('"LGPL"', '"GPL"', 1))
        changed = self.loaders()
        self.assertEqual(changed.returncode, 1)
        self.assertIn(b'checksum', changed.stderr)

    def test_capture_refuses_incomplete_output_and_overwrites(self):
        with self.assertRaises(self.pixbuf_data.DataError):
            self.pixbuf_data.capture(self.env, 'loaders', self.modules, loader_output(self.modules[:2]))
        with self.assertRaises(self.pixbuf_data.DataError):
            self.pixbuf_data.capture(self.env, 'mime', [], b'not a mime list')
        self.store()
        with self.assertRaises(FileExistsError):
            self.pixbuf_data.capture(self.env, 'loaders', self.modules, loader_output(self.modules))

    def test_modes(self):
        self.store()
        invalid = self.loaders(EMBERBSD_GI_DUMP_MODE='record')
        self.assertEqual(invalid.returncode, 1)
        self.assertIn(b'EMBERBSD_GI_DUMP_MODE must be replay, live or capture', invalid.stderr)
        # Without a mode (and in live mode) the runner still selects the SDK for a live query.
        for mode in (None, 'live'):
            with self.subTest(mode=mode):
                live = self.loaders(EMBERBSD_GI_DUMP_MODE=mode, EMBERBSD_SDK_SOURCE=None)
                self.assertEqual(live.returncode, 1)
                self.assertIn(b'EMBERBSD_SDK_SOURCE', live.stderr)


def main():
    global ARGS
    parser = argparse.ArgumentParser()
    parser.add_argument('--helper', default=str((Path(__file__).resolve().parent /
                        '../../../pkgsrc/graphics/gdk-pixbuf2/files/target-tools.py').resolve()))
    ARGS, rest = parser.parse_known_args()
    if sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 15):
        parser.error('run with the selected build-host CPython 3.15')
    unittest.main(argv=[sys.argv[0], *rest])


if __name__ == '__main__':
    main()
