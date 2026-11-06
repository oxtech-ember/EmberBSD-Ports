# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Select common image and font libraries for both GN roles."""
import hashlib
import json
from pathlib import Path
import re

PROVIDERS = {
    'jpeg': ('graphics/libjpeg-turbo', 'libjpeg-turbo', (3, 2, 1, 1),
             ('libjpeg',), ('libjpeg',), ('include/jconfig.h', 'include/jerror.h',
             'include/jmorecfg.h', 'include/jpeglib.h')),
    'webp': ('graphics/libwebp', 'libwebp', (1, 6, 0, 4),
             ('libwebp', 'libwebpdemux', 'libwebpmux', 'libsharpyuv'),
             ('libwebp', 'libwebpdemux', 'libwebpmux', 'libsharpyuv'),
             ('include/webp/decode.h', 'include/webp/demux.h', 'include/webp/encode.h',
              'include/webp/mux.h', 'include/webp/mux_types.h', 'include/webp/types.h',
              'include/webp/sharpyuv/sharpyuv.h', 'include/webp/sharpyuv/sharpyuv_csp.h')),
}

FONT_PROVIDERS = {
    'freetype': ('graphics/freetype2', 'freetype2', (2, 15, 0, 2),
                 ('libfreetype',), ('freetype2',),
                 ('include/freetype2/ft2build.h', 'include/freetype2/freetype/freetype.h',
                  'include/freetype2/freetype/ftcolor.h', 'include/freetype2/freetype/ftmm.h',
                  'include/freetype2/freetype/config/ftoption.h',
                  'share/freetype2/generated/pstables.h')),
    'harfbuzz': ('fonts/harfbuzz', 'harfbuzz', (15, 0, 0, 3),
                 ('libharfbuzz', 'libharfbuzz-subset'), ('harfbuzz', 'harfbuzz-subset'),
                 ('include/harfbuzz/hb.h', 'include/harfbuzz/hb-ft.h',
                  'include/harfbuzz/hb-subset.h')),
}


def package_at_least(name, base, minimum):
    """Compare numeric release components separately from the pkgsrc revision."""
    match = re.fullmatch(re.escape(base) + r'-(\d+(?:\.\d+)+)(?:nb(\d+))?', name)
    if not match:
        return False
    release = tuple(map(int, match.group(1).split('.')))
    floor_release, floor_revision = minimum[:-1], minimum[-1]
    width = max(len(release), len(floor_release))
    actual = (release + (0,) * (width - len(release)), int(match.group(2) or 0))
    floor = (floor_release + (0,) * (width - len(floor_release)), floor_revision)
    return actual >= floor


def select(controller, options, sdk, native, environment, buildlink):
    if not getattr(options, 'shared_image', False):
        return {}
    return select_roles(controller, options, sdk, native, environment, buildlink, PROVIDERS,
                        {'emberbsd_common_image': True, 'use_system_libjpeg': True},
                        'EMBERBSD_IMAGE_SOURCE_SHA256')


def select_fonts(controller, options, sdk, native, environment, buildlink):
    if not getattr(options, 'shared_font', False):
        return {}
    return select_roles(controller, options, sdk, native, environment, buildlink, FONT_PROVIDERS,
                        {'emberbsd_common_font': True, 'use_system_freetype': True,
                         'use_system_harfbuzz': True}, 'EMBERBSD_FONT_SOURCE_SHA256')


def select_roles(controller, options, sdk, native, environment, buildlink, providers, result, identity_key,
                 *, static_libraries=False):
    require = controller.require
    require(buildlink, 'shared providers require host buildlink')
    selection_work = environment.get('EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK')
    require(selection_work, 'shared providers need host buildlink metadata')
    selection = json.loads((Path(selection_work)/'selection.json').read_text())['identity']['inputs']
    host_prefix = Path(options.host_prefix).resolve(strict=True)
    target_prefix = (Path(options.sysroot)/'usr/pkg').resolve(strict=True)
    identities = {}
    for name, (pkgpath, pkgbase, minimum, libraries, modules, headers) in providers.items():
        hosts = options._common_native_packages.get(pkgpath, [])
        targets = options._common_target_packages.get(pkgpath, [])
        require(len(hosts) == len(targets) == 1 and hosts[0].name == targets[0].name,
                'shared package missing or mismatched: ' + pkgpath)
        require(package_at_least(hosts[0].name, pkgbase, minimum),
                'shared package is too old: ' + pkgpath)
        recipe = options._compression_catalog['recipes'][pkgpath]
        export = Path(options.host_buildlink_pkgsrc)/pkgpath
        versions = []
        tables = []
        for role, package, prefix, suffix in (
                ('host', hosts[0], host_prefix, '.dylib' if native.host['os'] == 'Darwin' else '.so'),
                ('target', targets[0], target_prefix, '.so')):
            controller.validate_package_source(package, recipe, export, distinfo=True,
                                               package_path=pkgpath, allow_empty_patches=True)
            manifest = (package/'+CONTENTS').read_text().splitlines()
            pc_files = ['lib/pkgconfig/'+module+'.pc' for module in modules]
            for pc in pc_files:
                require(pc in manifest, 'provider pkg-config file not owned: '+pc)
                if role == 'host':
                    require(str(host_prefix/pc) in selection and (Path(buildlink)/pc).is_file(),
                            'native pkg-config provider is not selected: '+pc)
            selected = [controller.selected_owned_library(prefix, lib+('.a' if static_libraries else suffix),
                                                          [package]) for lib in libraries]
            entries = list(headers) + pc_files + [str(Path(lib).relative_to(prefix)) for lib in selected]
            files = []
            for entry in entries:
                require(entry in manifest, 'provider input is not owned: '+entry)
                path = (prefix/entry).resolve(strict=True)
                require(path.is_relative_to(prefix) and path.is_file(), 'provider input escapes selected prefix')
                index = manifest.index(entry)
                require(index+1 < len(manifest) and re.fullmatch(r'@comment MD5:[0-9a-f]{32}', manifest[index+1]),
                        'provider input has no package checksum: '+entry)
                info = path.stat(); digest = hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()
                after = path.stat()
                stable = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_size,
                                        value.st_mtime_ns, value.st_ctime_ns)
                require(stable(after) == stable(info) and digest == manifest[index+1].split(':', 1)[1],
                        'provider input differs from installed package: '+entry)
                files.append(str(path))
            result['emberbsd_'+name+'_'+role+'_libraries'] = selected
            result['emberbsd_'+name+'_'+role+'_inputs'] = sorted(set(files +
                [str(package/item) for item in ('+CONTENTS', '+BUILD_INFO', '+BUILD_VERSION')]))
            if name == 'freetype':
                tables.append((prefix / 'share/freetype2/generated/pstables.h').resolve(strict=True))
                config = (prefix / 'include/freetype2/freetype/config/ftoption.h').read_text()
                for macro in ('FT_CONFIG_OPTION_SUBPIXEL_RENDERING',
                              'FT_CONFIG_OPTION_USE_HARFBUZZ',
                              'FT_CONFIG_OPTION_USE_HARFBUZZ_DYNAMIC'):
                    require(re.search(r'^#\s*define\s+' + macro + r'\b', config, re.M),
                            'selected FreeType configuration lacks ' + macro)
            if name == 'spirv_tools':
                tables.append((prefix / 'share/spirv-tools/generated/core_tables_header.inc').resolve(strict=True))
            pc_prefix = Path(buildlink) if role == 'host' else target_prefix
            env = dict(environment, PKG_CONFIG_LIBDIR=str(pc_prefix/'lib/pkgconfig'))
            env.pop('PKG_CONFIG_PATH', None)
            if role == 'host': env.pop('PKG_CONFIG_SYSROOT_DIR', None)
            else: env['PKG_CONFIG_SYSROOT_DIR'] = str(options.sysroot)
            command = [native.tool('pkg-config')] + (['--define-prefix'] if role == 'host' else [])
            result_versions = (sdk['process'].capture(command + ['--modversion', *modules], env=env)
                               .stdout.decode().splitlines()) if modules else []
            require(len(result_versions) == len(modules) and all(result_versions),
                    'invalid provider pkg-config versions: '+pkgpath)
            require(not modules or len(set(result_versions)) == 1, 'provider component versions disagree: '+pkgpath)
            versions.append(result_versions)
        require(versions[0] == versions[1], 'host and target provider versions differ: '+pkgpath)
        identities[pkgpath] = {'package': hosts[0].name, 'recipe': recipe, 'versions': versions[0]}
        if name in ('freetype', 'spirv_tools'):
            table_hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in tables]
            require(len(set(table_hashes)) == 1, 'host and target ' + name + ' source tables differ')
            identities[pkgpath]['table_sha256'] = table_hashes[0]
            if name == 'freetype':
                options.font_table = tables[1]
            else:
                options.spirv_tools_table = tables[1]
    environment[identity_key] = hashlib.sha256(
        json.dumps(identities, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return result
