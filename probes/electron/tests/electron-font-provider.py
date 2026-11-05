#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check shared font owner, role, checksums and FreeType build policy."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

owner = Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, owner/path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
controller = load('electron', 'build-electron.py')
font = load('font', 'image-provider.py')
features = '#define FT_CONFIG_OPTION_SUBPIXEL_RENDERING\n#define FT_CONFIG_OPTION_USE_HARFBUZZ\n#define FT_CONFIG_OPTION_USE_HARFBUZZ_DYNAMIC\n'
with tempfile.TemporaryDirectory(prefix='electron-font-provider-') as tmp:
    root = Path(tmp).resolve(); host = root/'host'; target = root/'sysroot/usr/pkg'; view = root/'view'
    packages = {'host': {}, 'target': {}}; inputs = {}
    for role, prefix, suffix in (('host',host,'.dylib'),('target',target,'.so')):
        for name,(path,base,minimum,libraries,modules,headers) in font.FONT_PROVIDERS.items():
            package = prefix/'pkgdb'/(base+'-'+'.'.join(map(str,minimum[:3]))+'nb'+str(minimum[3])); package.mkdir(parents=True)
            packages[role][path] = [package]
            entries = list(headers)+['lib/pkgconfig/'+m+'.pc' for m in modules]+['lib/'+lib+suffix for lib in libraries]
            contents = []
            for entry in entries:
                data = features if entry.endswith('/ftoption.h') else 'owned'
                f = prefix/entry; f.parent.mkdir(parents=True,exist_ok=True); f.write_text(data)
                contents += [entry, '@comment MD5:'+hashlib.md5(data.encode(),usedforsecurity=False).hexdigest()]
                if role == 'host' and entry.endswith('.pc'):
                    inputs[str(f)] = {}; v = view/entry; v.parent.mkdir(parents=True,exist_ok=True); v.write_text('selected')
            (package/'+CONTENTS').write_text('\n'.join(contents)+'\n')
            for name in ('+BUILD_INFO','+BUILD_VERSION'): (package/name).write_text('owned')
    metadata = root/'metadata'; metadata.mkdir(); (metadata/'selection.json').write_text(json.dumps({'identity':{'inputs':inputs}}))
    options = SimpleNamespace(shared_font=True,host_prefix=host,sysroot=root/'sysroot',host_buildlink_pkgsrc=root/'pkgsrc',
        _common_native_packages=packages['host'],_common_target_packages=packages['target'],
        _compression_catalog={'recipes':{x[0]:{} for x in font.FONT_PROVIDERS.values()}})
    native=SimpleNamespace(host={'os':'Darwin'},tool=lambda n:'/selected/'+n)
    sdk={'process':SimpleNamespace(capture=lambda command,env:SimpleNamespace(stdout=('1.0\n'*(len(command)-command.index('--modversion')-1)).encode()))}
    env={'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK':str(metadata)}
    with patch.object(controller,'validate_package_source') as verify:
        result=font.select_fonts(controller,options,sdk,native,env,view)
        assert verify.call_count==4 and len(env['EMBERBSD_FONT_SOURCE_SHA256'])==64
        assert result['use_system_freetype'] and result['use_system_harfbuzz']
        assert len(result['emberbsd_harfbuzz_host_libraries'])==2
        table_entry='share/freetype2/generated/pstables.h'; table=target/table_entry
        package=packages['target']['graphics/freetype2'][0]; manifest=package/'+CONTENTS'
        lines=manifest.read_text().splitlines(); index=lines.index(table_entry)+1
        table.write_text('different table'); lines[index]='@comment MD5:'+hashlib.md5(b'different table',usedforsecurity=False).hexdigest();manifest.write_text('\n'.join(lines)+'\n')
        try: font.select_fonts(controller,options,sdk,native,env,view)
        except ValueError as error: assert 'source tables differ' in str(error)
        else: raise AssertionError('different host and target tables accepted')
        table.write_text('owned');lines[index]='@comment MD5:'+hashlib.md5(b'owned',usedforsecurity=False).hexdigest();manifest.write_text('\n'.join(lines)+'\n')
        entry='include/freetype2/freetype/config/ftoption.h'; config=target/entry
        altered=features.replace('#define FT_CONFIG_OPTION_USE_HARFBUZZ_DYNAMIC','/* disabled */');config.write_text(altered)
        package=packages['target']['graphics/freetype2'][0]; manifest=package/'+CONTENTS'
        lines=manifest.read_text().splitlines(); lines[lines.index(entry)+1]='@comment MD5:'+hashlib.md5(altered.encode(),usedforsecurity=False).hexdigest();manifest.write_text('\n'.join(lines)+'\n')
        try: font.select_fonts(controller,options,sdk,native,env,view)
        except ValueError as error: assert 'FT_CONFIG_OPTION_USE_HARFBUZZ_DYNAMIC' in str(error)
        else: raise AssertionError('disabled FreeType dynamic HarfBuzz accepted')
print('PASS: font owner roles, checksums and FreeType feature policy')
