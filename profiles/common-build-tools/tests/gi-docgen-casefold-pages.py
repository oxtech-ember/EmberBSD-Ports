#!/usr/bin/env python3
"""Exercise gi-docgen page links for case-distinct type functions."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


GIR = '''<?xml version="1.0"?>
<repository version="1.2" xmlns="http://www.gtk.org/introspection/core/1.0" xmlns:c="http://www.gtk.org/introspection/c/1.0" xmlns:glib="http://www.gtk.org/introspection/glib/1.0">
  <include name="GObject" version="2.0"/>
  <namespace name="Casefold" version="1.0" shared-library="libcasefold.so" c:identifier-prefixes="Casefold" c:symbol-prefixes="casefold">
    <class name="Widget" c:type="CasefoldWidget" parent="GObject.Object" glib:type-name="CasefoldWidget" glib:get-type="casefold_widget_get_type">
      <function name="register_custom_URL_scheme" c:identifier="casefold_widget_register_custom_URL_scheme">
        <doc filename="casefold.h" line="1">See [func@Casefold.Widget.register_custom_url_scheme].</doc>
        <return-value transfer-ownership="none"><type name="none" c:type="void"/></return-value>
      </function>
      <function name="register_custom_url_scheme" c:identifier="casefold_widget_register_custom_url_scheme">
        <doc filename="casefold.h" line="2">Replacement API.</doc>
        <return-value transfer-ownership="none"><type name="none" c:type="void"/></return-value>
      </function>
    </class>
  </namespace>
</repository>
'''

CONFIG = '''[library]
name = "Casefold"
version = "1.0"
devhelp = true
search_index = true
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--python', required=True, type=Path)
    parser.add_argument('--source', required=True, type=Path,
                        help='gi-docgen source root containing gidocgen/')
    parser.add_argument('--gobject-gir', required=True, type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix='gi-docgen-casefold-') as tmp:
        root = Path(tmp)
        gir = root / 'Casefold-1.0.gir'
        config = root / 'Casefold.toml'
        output = root / 'html'
        gir.write_text(GIR, encoding='utf-8')
        config.write_text(CONFIG, encoding='utf-8')
        env = os.environ.copy()
        env['PYTHONPATH'] = str(args.source.resolve())
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        subprocess.run([
            str(args.python), '-B', '-c',
            'from gidocgen.gidocmain import main; main()',
            'generate', '--config', str(config),
            '--add-include-path', str(args.gobject_gir.parent),
            '--no-namespace-dir', '--output-dir', str(output), str(gir),
        ], check=True, env=env, stdout=subprocess.DEVNULL)
        subprocess.run([
            str(args.python), '-B', '-c',
            'from gidocgen.gidocmain import main; main()',
            'gen-index', '--config', str(config),
            '--add-include-path', str(args.gobject_gir.parent),
            '--output-dir', str(output), str(gir),
        ], check=True, env=env, stdout=subprocess.DEVNULL)

        expected = {
            'type_func.Widget.register_custom_URL_scheme.html',
            'type_func.Widget.register_custom_url_scheme.case-a44f07a8.html',
        }
        pages = {path.name for path in output.glob('type_func.Widget.*.html')}
        assert pages == expected, (pages, expected)
        assert len({name.casefold() for name in pages}) == len(pages)

        old_page = output / 'type_func.Widget.register_custom_URL_scheme.html'
        old_html = old_page.read_text(encoding='utf-8')
        new_page = next(output / name for name in expected if '.case-' in name)
        new_html = new_page.read_text(encoding='utf-8')
        link = new_page.name
        assert f'href="{link}"' in old_html
        assert f'href="{link}"' in (output / 'class.Widget.html').read_text(encoding='utf-8')
        index = json.loads((output / 'index.json').read_text(encoding='utf-8'))
        entries = [item for item in index['symbols'] if item.get('type') == 'type_func']
        assert {item['link'] for item in entries} == expected
        assert 'case "type_func": return doc.link;' in (output / 'search.js').read_text(encoding='utf-8')
        devhelp = next(output.glob('*.devhelp2')).read_text(encoding='utf-8')
        assert all(name in devhelp for name in expected)
        assert 'casefold_widget_register_custom_url_scheme' in new_html

    print('case-distinct type-function pages, Markdown, sidebar and search links pass')


if __name__ == '__main__':
    main()
