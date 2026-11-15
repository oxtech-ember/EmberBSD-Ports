#!/usr/bin/env python3
"""Exercise the patched upstream manager without GTK or network access."""
import importlib.util
import pathlib
import locale
import shlex
import sys
import tempfile
import types

if not hasattr(locale, 'bindtextdomain'):
    locale.bindtextdomain = lambda *args: None
root = pathlib.Path(sys.argv[1])
gi = types.ModuleType('gi')
repository = types.ModuleType('gi.repository')
repository.GObject = types.SimpleNamespace()
gi.repository = repository
sys.modules.update({'gi': gi, 'gi.repository': repository})
pil = types.ModuleType('PIL')
pil.Image = types.ModuleType('PIL.Image')
pil.Image.Image = object
sys.modules.update({'PIL': pil, 'PIL.Image': pil.Image, 'requests': types.ModuleType('requests')})
spec = importlib.util.spec_from_file_location('common', root / 'usr/lib/webapp-manager/common.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    for key in ('ICE_DIR', 'APPS_DIR', 'PROFILES_DIR', 'FIREFOX_PROFILES_DIR', 'FIREFOX_FLATPAK_PROFILES_DIR', 'ICONS_DIR', 'EPIPHANY_PROFILES_DIR', 'EPIPHANY_DESKTOP_DIR', 'FALKON_PROFILES_DIR'):
        setattr(module, key, str(tmp / key))
    assert not module.ember_webapp_validation("Example webapp", "https://example.org/a%20b?q=x&v=%25")
    for name, url in [("   ", "https://example.org/"), ("App", "https://u:p@example.org/"), ("App", "https://example.org/a b"), ("App", "https://example.org:99999/")]:
        assert module.ember_webapp_validation(name, url), (name, url)
    manager = module.WebAppManager()
    browser = next(b for b in manager.get_supported_browsers() if b.browser_type == module.BROWSER_TYPE_EMBER)
    name = 'Example "app" $HOME'
    url = 'https://example.org/a%20b?q=x&v=%25'
    manager.create_webapp(name, '', url, 'icon', 'Network', browser, '--no-sandbox', False, False, True)
    app, = manager.get_webapps()
    assert app.isolate_profile
    assert len(app.codename) == 24 and all(c in '0123456789abcdef' for c in app.codename)
    argv = [arg.replace('%%', '%').replace('\\$', '$').replace('\\`', '`') for arg in shlex.split(app.exec)]
    assert argv == [browser.exec_path, '--webapp-id=' + app.codename, '--webapp-url=' + url, '--webapp-name=' + name, '--webapp-private'], argv
    assert '--no-sandbox' not in app.exec
    manager.edit_webapp(app.path, 'New name', '', browser, url, 'icon', 'Network', '', app.codename, True, False, False)
    app, = manager.get_webapps()
    assert '--webapp-name=New name' in [arg.replace('%%', '%').replace('\\$', '$').replace('\\`', '`') for arg in shlex.split(app.exec)]
    assert '--webapp-private' not in app.exec
    manager.delete_webbapp(app)
    assert not manager.get_webapps()
print('launcher creation, escaping, edit and deletion passed')
