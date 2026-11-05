# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Select the common JPEG and WebP providers for both GN roles."""
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


def select(controller, options, sdk, native, environment, buildlink):
    if not getattr(options, 'shared_image', False):
        return {}
    require = controller.require
    require(buildlink, 'shared image providers require host buildlink')
    selection_work = environment.get('EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK')
    require(selection_work, 'shared image providers need host buildlink metadata')
    selection = json.loads((Path(selection_work)/'selection.json').read_text())['identity']['inputs']
    host_prefix = Path(options.host_prefix).resolve(strict=True)
    target_prefix = (Path(options.sysroot)/'usr/pkg').resolve(strict=True)
    result = {'emberbsd_common_image': True, 'use_system_libjpeg': True}
    identities = {}
    for name, (pkgpath, pkgbase, minimum, libraries, modules, headers) in PROVIDERS.items():
        hosts = options._common_native_packages.get(pkgpath, [])
        targets = options._common_target_packages.get(pkgpath, [])
        require(len(hosts) == len(targets) == 1 and hosts[0].name == targets[0].name,
                'shared image package missing or mismatched: ' + pkgpath)
        match = re.fullmatch(re.escape(pkgbase) + r'-(\d+)\.(\d+)\.(\d+)(?:nb(\d+))?', hosts[0].name)
        require(match and tuple(int(n or 0) for n in match.groups()) >= minimum,
                'shared image package is too old: ' + pkgpath)
        recipe = options._compression_catalog['recipes'][pkgpath]
        export = Path(options.host_buildlink_pkgsrc)/pkgpath
        versions = []
        for role, package, prefix, suffix in (
                ('host', hosts[0], host_prefix, '.dylib' if native.host['os'] == 'Darwin' else '.so'),
                ('target', targets[0], target_prefix, '.so')):
            controller.validate_package_source(package, recipe, export, distinfo=True,
                                               package_path=pkgpath, allow_empty_patches=True)
            manifest = (package/'+CONTENTS').read_text().splitlines()
            pc_files = ['lib/pkgconfig/'+module+'.pc' for module in modules]
            for pc in pc_files:
                require(pc in manifest, 'image pkg-config file not owned: '+pc)
                if role == 'host':
                    require(str(host_prefix/pc) in selection and (Path(buildlink)/pc).is_file(),
                            'native image pkg-config provider is not selected: '+pc)
            selected = [controller.selected_owned_library(prefix, lib+suffix, [package]) for lib in libraries]
            entries = list(headers) + pc_files + [str(Path(lib).relative_to(prefix)) for lib in selected]
            files = []
            for entry in entries:
                require(entry in manifest, 'image input is not owned: '+entry)
                path = (prefix/entry).resolve(strict=True)
                require(path.is_relative_to(prefix) and path.is_file(), 'image input escapes selected prefix')
                index = manifest.index(entry)
                require(index+1 < len(manifest) and re.fullmatch(r'@comment MD5:[0-9a-f]{32}', manifest[index+1]),
                        'image input has no package checksum: '+entry)
                info = path.stat(); digest = hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()
                require(path.stat() == info and digest == manifest[index+1].split(':', 1)[1],
                        'image input differs from installed package: '+entry)
                files.append(str(path))
            result['emberbsd_'+name+'_'+role+'_libraries'] = selected
            result['emberbsd_'+name+'_'+role+'_inputs'] = sorted(set(files +
                [str(package/item) for item in ('+CONTENTS', '+BUILD_INFO', '+BUILD_VERSION')]))
            pc_prefix = Path(buildlink) if role == 'host' else target_prefix
            env = dict(environment, PKG_CONFIG_LIBDIR=str(pc_prefix/'lib/pkgconfig'))
            env.pop('PKG_CONFIG_PATH', None)
            if role == 'host': env.pop('PKG_CONFIG_SYSROOT_DIR', None)
            else: env['PKG_CONFIG_SYSROOT_DIR'] = str(options.sysroot)
            command = [native.tool('pkg-config')] + (['--define-prefix'] if role == 'host' else [])
            result_versions = sdk['process'].capture(command + ['--modversion', *modules], env=env).stdout.decode().splitlines()
            require(len(result_versions) == len(modules) and all(result_versions),
                    'invalid image pkg-config versions: '+pkgpath)
            require(len(set(result_versions)) == 1, 'image component versions disagree: '+pkgpath)
            versions.append(result_versions)
        require(versions[0] == versions[1], 'host and target image versions differ: '+pkgpath)
        identities[pkgpath] = {'package': hosts[0].name, 'recipe': recipe, 'versions': versions[0]}
    environment['EMBERBSD_IMAGE_SOURCE_SHA256'] = hashlib.sha256(
        json.dumps(identities, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return result
