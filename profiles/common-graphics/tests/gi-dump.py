#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). No target, SSH connection or download is used.
"""Stored GI dumps replay only for the exact inputs they were captured from.

Replay must work without the SDK, a query configuration or a target, write
the stored body to the scanner's output, and refuse a missing dump, any
identity difference (platform, recipe, package, program, type list), a body
that differs from its recorded hash, and an existing output. Capture must
store a normalized body under an identity header that replay accepts. With
no mode set, target-query.py keeps its live behaviour.

Usage: gi-dump.py --files pkgsrc/devel/gobject-introspection/files [--python PYTHON]
"""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ARGS = None
IDENTITY = {
    'EMBERBSD_GI_DUMP_PLATFORM': 'NetBSD-11.0-aarch64',
    'EMBERBSD_GI_DUMP_RECIPE': 'x11/gtk3',
    'EMBERBSD_GI_DUMP_PACKAGE': 'gtk3+-3.24.52',
}
BODY = b'<?xml version="1.0"?>\n<dump>\n  <class name="GtkWidget" get-type="gtk_widget_get_type"/>\n</dump>\n'
TYPES = b'gtk_widget_get_type\n'


def load_module():
    spec = importlib.util.spec_from_file_location('gi_dump', ARGS.files / 'gi_dump.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StoredDumps(unittest.TestCase):
    def setUp(self):
        self.gi = load_module()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.types = self.root / 'types.txt'
        self.types.write_bytes(TYPES)
        self.dumps = self.root / 'dumps'
        self.dumps.mkdir()
        self.program = str(self.root / 'build' / 'Gtk-3.0')
        self.env = dict(IDENTITY, EMBERBSD_GI_DUMP_DIR=str(self.dumps), EMBERBSD_GI_DUMP_MODE='replay')
        self.saved = dict(os.environ)
        os.environ.update(self.env)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.saved)
        self.temp.cleanup()

    def arguments(self, output='out.xml'):
        return [self.program, f'--introspect-dump={self.types},{self.root / output}']

    def store(self, body=BODY, **changes):
        values = self.gi.identity(self.program, str(self.types))
        values['dump-sha256'] = hashlib.sha256(body).hexdigest()
        values.update(changes)
        (self.dumps / 'Gtk-3.0.xml').write_bytes(self.gi.render(values, body))

    def query(self, arguments, **env):
        command = [ARGS.python, '-E', '-S', str(ARGS.files / 'target-query.py'), *arguments]
        clean = {key: value for key, value in os.environ.items() if not key.startswith('EMBERBSD_')}
        clean.update(self.env)
        clean.update(env)
        return subprocess.run(command, capture_output=True, text=True, timeout=60, env=clean)

    def test_replay_writes_the_stored_body_without_sdk_or_target(self):
        self.store()
        result = self.query(self.arguments())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / 'out.xml').read_bytes(), BODY)

    def test_replay_refuses_a_missing_dump(self):
        result = self.query(self.arguments())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no stored GI dump', result.stderr)
        self.assertIn('capture', result.stderr)
        self.assertFalse((self.root / 'out.xml').exists())

    def test_replay_refuses_each_identity_difference(self):
        changes = {
            'platform': 'NetBSD-11.0-x86_64',
            'recipe': 'x11/gtk4',
            'package': 'gtk3+-3.24.51',
            'program': 'Gdk-3.0',
            'types-sha256': '0' * 64,
        }
        for name, value in changes.items():
            with self.subTest(field=name):
                self.store(**{name: value})
                result = self.query(self.arguments(f'out-{name}.xml'))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f'{name} is {value}', result.stderr)
                self.assertFalse((self.root / f'out-{name}.xml').exists())

    def test_replay_refuses_a_changed_body(self):
        self.store()
        path = self.dumps / 'Gtk-3.0.xml'
        path.write_bytes(path.read_bytes().replace(b'GtkWidget', b'GtkWindow'))
        result = self.query(self.arguments())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('differs from its dump-sha256', result.stderr)

    def test_replay_refuses_a_header_less_dump(self):
        (self.dumps / 'Gtk-3.0.xml').write_bytes(BODY)
        result = self.query(self.arguments())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no EmberBSD GI dump 1 header', result.stderr)

    def test_replay_refuses_an_existing_output(self):
        self.store()
        (self.root / 'out.xml').write_bytes(b'old')
        result = self.query(self.arguments())
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.root / 'out.xml').read_bytes(), b'old')

    def test_replay_refuses_target_execution_without_query(self):
        result = self.query(['--sdk-source', '/ember-missing-sdk', self.program, '--version'])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('replay supports only introspection dumps', result.stderr)

    def test_unset_or_live_mode_keeps_the_live_query(self):
        for env in ({'EMBERBSD_GI_DUMP_MODE': 'live'}, {}):
            with self.subTest(env=env):
                self.store()
                current = dict(self.env)
                del self.env['EMBERBSD_GI_DUMP_MODE']
                try:
                    result = self.query(self.arguments('live.xml'), **env)
                finally:
                    self.env = current
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('EMBERBSD_SDK_SOURCE', result.stderr)
                self.assertFalse((self.root / 'live.xml').exists())

    def test_capture_mode_queries_the_target_first(self):
        result = self.query(self.arguments(), EMBERBSD_GI_DUMP_MODE='capture',
                            EMBERBSD_GI_DUMP_CAPTURE_DIR=str(self.root))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('EMBERBSD_SDK_SOURCE', result.stderr)

    def test_invalid_mode_is_refused(self):
        result = self.query(self.arguments(), EMBERBSD_GI_DUMP_MODE='record')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('must be live, replay or capture', result.stderr)

    def test_capture_stores_a_normalized_dump_that_replays(self):
        capture = self.root / 'capture'
        capture.mkdir()
        os.environ['EMBERBSD_GI_DUMP_CAPTURE_DIR'] = str(capture)
        raw = BODY.replace(b'\n', b'  \r\n') + b'\n\n'
        live_output = self.root / 'live.xml'
        live_output.write_bytes(raw)
        self.assertEqual(self.gi.capture(self.arguments('live.xml')), 0)
        stored = capture / 'NetBSD-11.0-aarch64' / 'x11_gtk3' / 'Gtk-3.0.xml'
        data = stored.read_bytes()
        self.assertTrue(data.startswith(b'<!-- EmberBSD GI dump 1\nplatform: NetBSD-11.0-aarch64\n'))
        values, body = self.gi.parse(data)
        self.assertEqual(body, BODY)
        self.assertEqual(values['types-sha256'], hashlib.sha256(TYPES).hexdigest())
        with self.assertRaises(self.gi.DumpError):
            self.gi.capture(self.arguments('live.xml'))
        (self.dumps / 'Gtk-3.0.xml').write_bytes(data)
        self.assertEqual(self.query(self.arguments('replayed.xml')).returncode, 0)
        self.assertEqual((self.root / 'replayed.xml').read_bytes(), BODY)

    def test_capture_refuses_a_non_dump_body(self):
        os.environ['EMBERBSD_GI_DUMP_CAPTURE_DIR'] = str(self.root)
        for raw in (b'\xff\xfe', b'<dump>', b'<repository/>\n'):
            with self.subTest(raw=raw):
                (self.root / 'bad.xml').write_bytes(raw)
                with self.assertRaises(self.gi.DumpError):
                    self.gi.capture(self.arguments('bad.xml'))
        self.assertFalse((self.root / 'NetBSD-11.0-aarch64').exists())

    def test_identity_never_accepts_host_like_values(self):
        os.environ['EMBERBSD_GI_DUMP_PLATFORM'] = 'NetBSD-11.0-aarch64 host'
        with self.assertRaises(self.gi.DumpError):
            self.gi.identity(self.program, str(self.types))


def main():
    global ARGS
    parser = argparse.ArgumentParser()
    parser.add_argument('--files', type=Path, required=True)
    parser.add_argument('--python', default=sys.executable)
    ARGS, rest = parser.parse_known_args()
    ARGS.files = ARGS.files.resolve()
    unittest.main(argv=[sys.argv[0], *rest])


if __name__ == '__main__':
    main()
