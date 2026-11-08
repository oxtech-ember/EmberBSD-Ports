#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check native Fontconfig defaults using a copied library at another prefix.

No compilation or changes to the supplied installation. Dependencies may still
load from its native prefix; full package relocation qualification is separate.
"""
import argparse
import ctypes
from html import escape
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def worker(library, producer, scenario):
    root = library.parent.parent
    for key in ('FONTCONFIG_FILE', 'FONTCONFIG_PATH', 'FONTCONFIG_SYSROOT'):
        os.environ.pop(key, None)
    os.environ.update(HOME=str(root / 'home'), XDG_CONFIG_HOME=str(root / 'home/config'),
                      XDG_CACHE_HOME=str(root / 'home/cache'),
                      XDG_DATA_HOME=str(root / 'home/data'), XDG_DATA_DIRS=str(root / 'xdg-data'))
    config_dir = root / 'etc/fontconfig'
    config_dir.mkdir(parents=True, exist_ok=True)
    templates = root / 'share/fontconfig/conf.avail'
    templates.mkdir(parents=True, exist_ok=True)
    template = templates / '10-relocation-test.conf'
    template.write_text('<fontconfig><description>relocation test</description></fontconfig>')
    default = config_dir / 'fonts.conf'
    outside = root.parent / 'external-fonts'

    def configuration(path, font, cache=True):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('<fontconfig><dir>' + escape(str(font)) + '</dir><dir>' +
                        escape(str(outside)) + '</dir>' +
                        ('<cachedir>' + escape(str(root / 'explicit-cache')) + '</cachedir>' if cache else '') +
                        '</fontconfig>')

    expected_font = root / 'selected-fonts'
    configuration(default, expected_font)
    if scenario == 'file':
        chosen = root / 'custom/config.xml'
        configuration(chosen, expected_font)
        os.environ['FONTCONFIG_FILE'] = str(chosen)
    elif scenario == 'path':
        chosen = root / 'custom/fonts.conf'
        configuration(chosen, expected_font)
        os.environ['FONTCONFIG_PATH'] = str(chosen.parent)
    elif scenario == 'cache':
        chosen = default
        configuration(default, expected_font, cache=False)
    elif scenario == 'fallback':
        chosen = None
        default.unlink()
    else:
        chosen = default

    lib = ctypes.CDLL(str(library))
    lib.FcInitLoadConfig.argtypes = []
    lib.FcInitLoadConfig.restype = ctypes.c_void_p
    lib.FcConfigDestroy.argtypes = [ctypes.c_void_p]
    lib.FcConfigDestroy.restype = None
    lib.FcStrListNext.argtypes = [ctypes.c_void_p]
    lib.FcStrListNext.restype = ctypes.c_char_p
    lib.FcStrListDone.argtypes = [ctypes.c_void_p]
    lib.FcStrListDone.restype = None
    lib.FcConfigFileInfoIterInit.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.FcConfigFileInfoIterInit.restype = None
    lib.FcConfigFileInfoIterNext.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.FcConfigFileInfoIterNext.restype = ctypes.c_int
    lib.FcConfigFileInfoIterGet.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
    lib.FcConfigFileInfoIterGet.restype = ctypes.c_int
    lib.FcStrFree.argtypes = [ctypes.c_void_p]
    lib.FcStrFree.restype = None

    def paths(config, name):
        getter = getattr(lib, name)
        getter.argtypes = [ctypes.c_void_p]
        getter.restype = ctypes.c_void_p
        values = getter(config)
        assert values, name
        result = []
        try:
            while True:
                value = lib.FcStrListNext(values)
                if value is None:
                    return result
                result.append(os.fsdecode(value))
        finally:
            lib.FcStrListDone(values)

    config = lib.FcInitLoadConfig()
    assert config, 'configuration initialization failed'
    try:
        files = paths(config, 'FcConfigGetConfigFiles')
        fonts = paths(config, 'FcConfigGetFontDirs')
        caches = paths(config, 'FcConfigGetCacheDirs')
        available = []
        iterator = (ctypes.c_void_p * 3)()
        lib.FcConfigFileInfoIterInit(config, ctypes.byref(iterator))
        while True:
            name, enabled = ctypes.c_void_p(), ctypes.c_int()
            if not lib.FcConfigFileInfoIterGet(config, ctypes.byref(iterator),
                                             ctypes.byref(name), None, ctypes.byref(enabled)):
                break
            try:
                available.append(os.fsdecode(ctypes.string_at(name)))
            finally:
                lib.FcStrFree(name)
            lib.FcConfigFileInfoIterNext(config, ctypes.byref(iterator))
        if chosen:
            assert str(chosen) in files, ('selected config not read', scenario, files)
            assert str(expected_font) in fonts and str(outside) in fonts, fonts
            assert str(template) in available, ('relocated template not scanned', available)
        else:
            assert str(root / 'share/fonts/X11') in fonts, ('fallback font path', fonts)
        if scenario in ('cache', 'fallback'):
            assert str(root / 'var/cache/fontconfig') in caches, ('fallback cache path', caches)
        for path in files + available + fonts + caches:
            assert path != str(producer) and not path.startswith(str(producer) + '/'), path
    finally:
        lib.FcConfigDestroy(config)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('library', type=Path)
    parser.add_argument('--producer-prefix', type=Path, required=True)
    parser.add_argument('--worker', choices=('default', 'file', 'path', 'cache', 'fallback'), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        worker(args.library, args.producer_prefix, args.worker)
        return
    library = args.library.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='fontconfig-paths-λ&-') as temporary:
        root = Path(temporary).resolve()
        (root / 'lib').mkdir()
        copied = root / 'lib' / library.name
        shutil.copy2(library, copied)
        for scenario in ('default', 'file', 'path', 'cache', 'fallback'):
            subprocess.run([sys.executable, '-I', str(Path(__file__).resolve()), str(copied),
                            '--producer-prefix', str(args.producer_prefix), '--worker', scenario], check=True)
    print('PASS: relocated defaults, overrides, external paths, templates and fallback XML')


if __name__ == '__main__':
    main()
