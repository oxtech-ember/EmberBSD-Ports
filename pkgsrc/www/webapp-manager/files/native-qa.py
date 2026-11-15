#!/usr/bin/env python3
"""On-target Web App Manager GUI, GSettings and Gio launcher acceptance.

Creates fixtures only in a new, explicit temporary HOME and never removes it.
Run with the target Python matching the installed package. Requires a desktop
session with a real DISPLAY or WAYLAND_DISPLAY, plus installed dependencies.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('--prefix', required=True, help='absolute target package prefix')
parser.add_argument('--temp-home', required=True, help='new, nonexistent directory for this run')
args = parser.parse_args()
prefix = Path(args.prefix)
home = Path(args.temp_home)
if not prefix.is_absolute() or not home.is_absolute():
    parser.error('both paths must be absolute')
if not prefix.is_dir():
    parser.error('prefix must be an existing installed prefix')
if '..' in home.parts:
    parser.error('temp-home must not contain parent-directory components')
try:
    parent = home.parent.resolve(strict=True)
    real_home = Path.home().resolve(strict=True)
except (OSError, RuntimeError) as exc:
    parser.error('cannot resolve temp-home parent or real HOME: ' + str(exc))
if not parent.is_dir() or home.name in ('', '.', '..'):
    parser.error('the parent of temp-home must be an existing directory')
home = parent / home.name
if home == real_home or home.is_relative_to(real_home):
    parser.error('temp-home must not be inside the real HOME')
try:
    home.mkdir(mode=0o700)
except FileExistsError:
    parser.error('temp-home must not already exist; choose a fresh path')
for name in ('config', 'data', 'cache'):
    (home / name).mkdir(mode=0o700)
os.environ.update(HOME=str(home), XDG_CONFIG_HOME=str(home / 'config'),
                  XDG_DATA_HOME=str(home / 'data'), XDG_CACHE_HOME=str(home / 'cache'),
                  GSETTINGS_BACKEND='memory')
data_dirs = [str(prefix / 'share')]
data_dirs.extend(os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':'))
os.environ['XDG_DATA_DIRS'] = ':'.join(dict.fromkeys(data_dirs))
capture = home / 'capture.json'
os.environ['WEBAPP_QA_CAPTURE'] = str(capture)

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('XApp', '1.0')
from gi.repository import Gio, GLib, Gtk, XApp
ok, _ = Gtk.init_check(None)
assert ok, 'GTK could not connect to the selected graphical session'
schema_source = Gio.SettingsSchemaSource.get_default()
assert schema_source is not None, 'no GSettings schema source'
assert schema_source.lookup('org.x.webapp-manager', True), 'manager schema not compiled/visible'
settings = Gio.Settings.new('org.x.webapp-manager')
assert settings is not None
icon = prefix / 'share/icons/hicolor/scalable/apps/webapp-manager.svg'
assert icon.is_file(), f'manager icon not installed: {icon}'
theme = Gtk.IconTheme.get_default()
theme.append_search_path(str(prefix / 'share/icons'))
assert theme.has_icon('webapp-manager'), 'GTK cannot resolve the manager icon'
assert XApp.IconChooserButton() is not None, 'XApp icon chooser unavailable'

module_dir = prefix / 'lib/webapp-manager'
sys.path.insert(0, str(module_dir))
import common
assert Path(common.APPS_DIR).resolve().is_relative_to(home), 'refusing to touch real webapps'
assert Path(common.ICE_DIR).resolve().is_relative_to(home), 'refusing to touch real profiles'
assert hasattr(common, 'ember_webapp_validation'), 'installed manager lacks Ember validator'

# Stub only the browser executable, not GLib/Gio, the manager, GTK or parser.
# It records the exact execve argv with the target's own Python interpreter.
recorder = home / 'argv-recorder'
recorder.write_text('#!' + sys.executable + '\n'
                    'import json, os, sys\n'
                    'target = os.environ["WEBAPP_QA_CAPTURE"]\n'
                    'with open(target + ".tmp", "x", encoding="utf-8") as f:\n'
                    '    json.dump(sys.argv[1:], f, ensure_ascii=False)\n'
                    'os.replace(target + ".tmp", target)\n'
                    'if sys.argv[1:] and sys.argv[1].startswith("--webapp-clear=") and os.environ.get("WEBAPP_QA_CLEAR_FAIL") == "1": sys.exit(7)\n', encoding='utf-8')
recorder.chmod(0o700)
common.EMBER_BROWSER_PATH = str(recorder)
browser = common.Browser(common.BROWSER_TYPE_EMBER, 'Ember Browser', str(recorder), str(recorder))
common.WebAppManager.get_supported_browsers = staticmethod(lambda: [browser])
spec = importlib.util.spec_from_file_location('webapp_manager_qa', module_dir / 'webapp-manager.py')
manager_ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager_ui)
application = Gtk.Application(application_id='org.emberbsd.WebAppManager.QA', flags=Gio.ApplicationFlags.NON_UNIQUE)
assert application.register(None), 'could not register non-unique Gtk.Application'
window = manager_ui.WebAppManagerWindow(application)
application.add_window(window.window)
window.window.show()
while Gtk.events_pending():
    Gtk.main_iteration_do(False)
window.on_add_button(None)

name = ' Почта Name=\\имя "Тест" $HOME `tick` %25 '
url = 'https://example.org/a%20b?q=x%25y&lang=ru'
for bad_name, bad_url in [('   ', 'https://example.org/'), ('App', 'https://u:p@example.org/'),
                          ('App', 'https://example.org/a b'), ('App', 'https://example.org:99999/')]:
    window.name_entry.set_text(bad_name)
    window.url_entry.set_text(bad_url)
    assert not window.ok_button.get_sensitive(), (bad_name, bad_url)
    assert window.validation_label.get_visible() and window.validation_label.get_text(), 'no visible validation reason'
window.name_entry.set_text(name)
window.url_entry.set_text(url)
window.privatewindow_switch.set_active(True)
assert window.ok_button.get_sensitive(), 'valid values are rejected'
window.on_ok_button(None)
apps = window.manager.get_webapps()
assert len(apps) == 1, f'expected one fixture, got {len(apps)}'
app = apps[0]
desktop = Path(app.path)
assert desktop.parent == Path(common.APPS_DIR) and desktop.is_file()
assert app.name == name and app.url == url and app.isolate_profile
key = GLib.KeyFile()
key.load_from_file(str(desktop), GLib.KeyFileFlags.NONE)
assert key.get_string('Desktop Entry', 'Name') == name
assert key.get_string('Desktop Entry', 'StartupWMClass') == 'WebApp-' + app.codename
assert key.get_string('Desktop Entry', 'X-WebApp-URL') == url
assert Gio.DesktopAppInfo.new_from_filename(str(desktop)), 'invalid desktop launcher'

# Use the manager's real Run action; it must delegate to Gio, not a shell.
window.run_webapp(app)
context = GLib.MainContext.default()
end = time.monotonic() + 15
while not capture.exists() and time.monotonic() < end:
    while context.pending():
        context.iteration(False)
    time.sleep(.05)
assert capture.exists(), 'Gio launch did not run the fixture executable'
actual = json.loads(capture.read_text(encoding='utf-8'))
expected = ['--webapp-id=' + app.codename, '--webapp-url=' + url,
            '--webapp-name=' + name, '--webapp-private']
assert actual == expected, f'execve argv mismatch: {actual!r} != {expected!r}'

# Exercise the GUI's edit flow and the backend deletion, without any real data.
window.selected_webapp = app
window.on_edit_button(None)
new_name = ' Новое Name=\\имя "Пример" $HOME `tick` %42 '
new_url = 'https://example.org/edit?value=100%25'
window.name_entry.set_text(new_name)
window.url_entry.set_text(new_url)
assert window.ok_button.get_sensitive()
window.on_ok_button(None)
updated, = window.manager.get_webapps()
assert updated.codename == app.codename and updated.name == new_name and updated.url == new_url
capture.unlink()
window.run_webapp(updated)
end = time.monotonic() + 15
while not capture.exists() and time.monotonic() < end:
    while context.pending():
        context.iteration(False)
    time.sleep(.05)
assert capture.exists(), 'edited launcher did not run'
assert json.loads(capture.read_text(encoding='utf-8')) == [
    '--webapp-id=' + app.codename, '--webapp-url=' + new_url,
    '--webapp-name=' + new_name, '--webapp-private']
os.environ['WEBAPP_QA_CLEAR_FAIL'] = '1'
try:
    window.manager.delete_webbapp(updated)
    raise AssertionError('failed profile clear unexpectedly succeeded')
except RuntimeError:
    pass
assert desktop.exists() and json.loads(capture.read_text()) == ['--webapp-clear=' + app.codename]
os.environ['WEBAPP_QA_CLEAR_FAIL'] = '0'
window.manager.delete_webbapp(updated)
assert json.loads(capture.read_text()) == ['--webapp-clear=' + app.codename]
assert not desktop.exists() and not window.manager.get_webapps(), 'fixture deletion failed'
window.window.destroy()
print('PASS GTK/XApp, compiled schema, icon, visible validation, create/edit/delete, real Gio argv')
print('Fixture HOME retained for inspection:', home)
