#!/usr/bin/env python3
"""Test manager persistence and desktop execution with selected GLib/Gio."""
import argparse
import ctypes
import importlib.util
import locale
import os
import shlex
from pathlib import Path
import sys
import tempfile
import time
import types

parser = argparse.ArgumentParser()
parser.add_argument('source', type=Path)
parser.add_argument('--host-prefix', required=True, type=Path)
args = parser.parse_args()
if not args.host_prefix.is_absolute() or not args.host_prefix.is_dir():
    parser.error('--host-prefix must be an existing absolute directory')
suffix = '.dylib' if sys.platform == 'darwin' else '.so'
libdir = (args.host_prefix / 'lib').resolve()
def library(name):
    p = (libdir / ('lib' + name + '-2.0' + suffix)).resolve(strict=True)
    if not p.is_relative_to(args.host_prefix.resolve()):
        raise RuntimeError('library escapes selected host prefix')
    return ctypes.CDLL(str(p))
lib = library('glib'); gio = library('gio'); gobject = library('gobject')
gobject.g_object_unref.argtypes = [ctypes.c_void_p]
lib.g_error_free.argtypes = [ctypes.c_void_p]
lib.g_key_file_new.restype = ctypes.c_void_p
for name in ('g_key_file_set_string', 'g_key_file_set_value'):
    getattr(lib, name).argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
for name in ('g_key_file_get_string', 'g_key_file_get_value'):
    fn = getattr(lib, name)
    fn.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
    fn.restype = ctypes.c_void_p
lib.g_free.argtypes = [ctypes.c_void_p]
lib.g_key_file_unref.argtypes = [ctypes.c_void_p]
gio.g_desktop_app_info_new_from_filename.argtypes = [ctypes.c_char_p]
gio.g_desktop_app_info_new_from_filename.restype = ctypes.c_void_p
gio.g_app_info_get_display_name.argtypes = [ctypes.c_void_p]
gio.g_app_info_get_display_name.restype = ctypes.c_char_p
gio.g_app_info_launch.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
gio.g_app_info_launch.restype = ctypes.c_int
class KeyFile:
    """Thin ctypes binding to real GLib, not a KeyFile implementation."""
    def __init__(self): self.ptr = lib.g_key_file_new()
    def __del__(self): lib.g_key_file_unref(self.ptr)
    def set_string(self, group, key, value): lib.g_key_file_set_string(self.ptr, group.encode(), key.encode(), value.encode())
    def set_value(self, group, key, value): lib.g_key_file_set_value(self.ptr, group.encode(), key.encode(), value.encode())
    def get_string(self, group, key): return self._get('g_key_file_get_string', group, key)
    def get_value(self, group, key): return self._get('g_key_file_get_value', group, key)
    def _get(self, name, group, key):
        error = ctypes.c_void_p()
        result = getattr(lib, name)(self.ptr, group.encode(), key.encode(), ctypes.byref(error))
        if error.value:
            lib.g_error_free(error)
            if result: lib.g_free(result)
            raise ValueError('invalid Desktop Entry string')
        if not result: raise ValueError('missing Desktop Entry string')
        try: return ctypes.string_at(result).decode()
        finally: lib.g_free(result)
if not hasattr(locale, 'bindtextdomain'): locale.bindtextdomain = lambda *a: None
gi = types.ModuleType('gi'); repository = types.ModuleType('gi.repository')
repository.GObject = types.SimpleNamespace(); repository.GLib = types.SimpleNamespace(KeyFile=KeyFile)
gi.repository = repository; sys.modules.update({'gi': gi, 'gi.repository': repository})
pil = types.ModuleType('PIL'); pil.Image = types.ModuleType('PIL.Image'); pil.Image.Image = object
sys.modules.update({'PIL': pil, 'PIL.Image': pil.Image, 'requests': types.ModuleType('requests')})
spec = importlib.util.spec_from_file_location('common', args.source / 'usr/lib/webapp-manager/common.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='webapp-owner-test-') as tmp:
    t = Path(tmp)
    for key in ('ICE_DIR', 'APPS_DIR', 'PROFILES_DIR', 'FIREFOX_PROFILES_DIR', 'FIREFOX_FLATPAK_PROFILES_DIR', 'ICONS_DIR', 'EPIPHANY_PROFILES_DIR', 'EPIPHANY_DESKTOP_DIR', 'FALKON_PROFILES_DIR'):
        setattr(module, key, str(t / key))
    assert not module.ember_webapp_validation('Example webapp', 'https://example.org/a%20b?q=x&v=%25')
    for name, url in [('   ', 'https://example.org/'), ('App', 'https://u:p@example.org/'), ('App', 'https://example.org/a b'), ('App', 'https://example.org:99999/')]:
        assert module.ember_webapp_validation(name, url), (name, url)
    capture = t / 'argv'; exe = t / 'capture'
    exe.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > ' + shlex.quote(str(capture)) + '\n'); exe.chmod(0o755)
    manager = module.WebAppManager()
    browser = next(b for b in manager.get_supported_browsers() if b.browser_type == module.BROWSER_TYPE_EMBER)
    browser.exec_path = str(exe)
    name = ' Почта Name=\\имя "Тест" $HOME `tick` %25 '
    desc = ' Comment=описание \\test '
    url = 'https://example.org/a%20b?q=x&v=%25'
    manager.create_webapp(name, desc, url, 'icon', 'Network', browser, '--no-sandbox', False, False, True)
    app, = manager.get_webapps()
    assert app.isolate_profile and len(app.codename) == 24 and all(c in '0123456789abcdef' for c in app.codename)
    def check(expected_name, expected_desc, private):
        assert app.name == expected_name and app.desc == expected_desc, (app.name, app.desc)
        capture.unlink(missing_ok=True)
        obj = gio.g_desktop_app_info_new_from_filename(os.fsencode(app.path))
        assert obj, 'Gio rejected desktop file'
        assert gio.g_app_info_get_display_name(obj).decode() == expected_name
        error = ctypes.c_void_p()
        assert gio.g_app_info_launch(obj, None, None, ctypes.byref(error)) and not error.value
        for _ in range(150):
            if capture.exists() and capture.stat().st_size: break
            time.sleep(.02)
        actual = capture.read_text().splitlines()
        expected = ['--webapp-id=' + app.codename, '--webapp-url=' + url, '--webapp-name=' + expected_name]
        if private: expected.append('--webapp-private')
        assert actual == expected, (actual, expected)
        assert '--no-sandbox' not in actual
        gobject.g_object_unref(obj)
    check(name, desc, True)
    new_name = ' Новое Name=\\имя %42 '; new_desc = ' Comment=новое \\значение '
    manager.edit_webapp(app.path, new_name, new_desc, browser, url, 'icon', 'Network', '', app.codename, True, False, False)
    app, = manager.get_webapps(); check(new_name, new_desc, False)
    legacy = Path(module.APPS_DIR) / 'WebApp-whitespace.desktop'
    legacy.write_text('[Desktop Entry]\nName=Chromium App\nComment=Web App\nIcon=icon  \n'
                      'StartupWMClass=WebApp-whitespace\nX-WebApp-Browser=Chromium  \n'
                      'X-WebApp-URL=https://example.org/  \nX-WebApp-Isolated=true  \n'
                      'X-WebApp-PrivateWindow=true  \nCategories=GTK;Network;  \n')
    chromium = next(item for item in manager.get_webapps() if item.path == str(legacy))
    assert (chromium.web_browser, chromium.url, chromium.icon, chromium.category,
            chromium.isolate_profile, chromium.privatewindow) == (
                'Chromium', 'https://example.org/', 'icon', 'Network', True, True)
    legacy.unlink()
    bad = Path(module.APPS_DIR) / 'WebApp-malformed.desktop'
    bad.write_text('[Desktop Entry]\nName=bad\\q\nIcon=icon\nStartupWMClass=WebApp-malformed\n')
    assert [x.path for x in manager.get_webapps()] == [app.path], 'invalid item must not hide valid launcher'
    bad.unlink()
    # Invoke a real temporary executable for clear; failed clear preserves launcher.
    module.EMBER_BROWSER_PATH = str(exe)
    exe.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > ' + shlex.quote(str(capture)) +
                   '\nexit "${WEBAPP_CLEAR_EXIT:-0}"\n')
    os.environ['WEBAPP_CLEAR_EXIT'] = '7'
    try:
        manager.delete_webbapp(app)
        raise AssertionError('failed clear unexpectedly deleted launcher')
    except RuntimeError:
        pass
    assert Path(app.path).is_file() and capture.read_text().splitlines() == ['--webapp-clear=' + app.codename]
    os.environ['WEBAPP_CLEAR_EXIT'] = '0'
    manager.delete_webbapp(app)
    assert not manager.get_webapps() and not Path(app.path).exists()
    assert capture.read_text().splitlines() == ['--webapp-clear=' + app.codename]
    del os.environ['WEBAPP_CLEAR_EXIT']
print('PASS GLib/Gio create, edit, malformed item isolation and delete')
