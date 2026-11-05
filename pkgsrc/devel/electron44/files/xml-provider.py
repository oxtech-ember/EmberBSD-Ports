# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Select the common libxml2 and libxslt providers for both GN roles."""
import hashlib
import json
from pathlib import Path
import re

PROVIDERS = {
    'xml': ('textproc/libxml2', 'libxml2', 'libxml-2.0', (2, 15, 4, 5), 'include/libxml2/libxml/'),
    'xslt': ('textproc/libxslt', 'libxslt', 'libxslt', (1, 1, 45, 3), 'include/libxslt/'),
}


def select(controller, options, sdk, native, environment, buildlink):
    if not getattr(options, 'shared_xml', False):
        return {}
    require = controller.require
    require(buildlink, 'shared XML requires the selected host buildlink')
    selection_work = environment.get('EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK')
    require(selection_work, 'shared XML requires host buildlink metadata')
    selection = json.loads((Path(selection_work)/'selection.json').read_text())['identity']['inputs']
    host_prefix = Path(options.host_prefix).resolve(strict=True)
    target_prefix = (Path(options.sysroot)/'usr/pkg').resolve(strict=True)
    result, identities = {}, {}
    for name, (pkgpath, library, module, minimum, header_prefix) in PROVIDERS.items():
        hosts = options._common_native_packages.get(pkgpath, [])
        targets = options._common_target_packages.get(pkgpath, [])
        require(len(hosts) == len(targets) == 1 and hosts[0].name == targets[0].name,
                'shared XML package missing or mismatched: ' + pkgpath)
        match = re.fullmatch(re.escape(library) + r'-(\d+)\.(\d+)\.(\d+)(?:nb(\d+))?', hosts[0].name)
        require(match and tuple(int(n or 0) for n in match.groups()) >= minimum,
                'shared XML package is too old: ' + pkgpath)
        recipe = options._compression_catalog['recipes'][pkgpath]
        export = Path(options.host_buildlink_pkgsrc)/pkgpath
        for package in (hosts[0], targets[0]):
            controller.validate_package_source(package, recipe, export, distinfo=True,
                                               package_path=pkgpath, allow_empty_patches=True)
        pc = 'lib/pkgconfig/' + module + '.pc'
        require(str(host_prefix/pc) in selection and (Path(buildlink)/pc).is_file(),
                'shared XML host pkg-config provider is not selected: ' + module)
        versions = []
        for role, package, prefix, suffix in (
                ('host', hosts[0], host_prefix, '.dylib' if native.host['os'] == 'Darwin' else '.so'),
                ('target', targets[0], target_prefix, '.so')):
            manifest = (package/'+CONTENTS').read_text().splitlines()
            require(pc in manifest, 'shared XML pkg-config file is not owned: ' + module)
            headers = [line for line in manifest if line.startswith(header_prefix) and line.endswith('.h')]
            require(headers and len(headers) == len(set(headers)), 'missing or duplicate public XML headers')
            files = []
            for entry in headers + [pc]:
                path = (prefix/entry).resolve(strict=True)
                require(path.is_relative_to(prefix) and path.is_file(), 'XML input escapes selected prefix')
                index = manifest.index(entry)
                require(index+1 < len(manifest) and re.fullmatch(r'@comment MD5:[0-9a-f]{32}', manifest[index+1]),
                        'XML input has no package checksum: ' + entry)
                info = path.stat()
                digest = hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()
                require(path.stat() == info and digest == manifest[index+1].split(':', 1)[1],
                        'XML input differs from installed package: ' + entry)
                files.append(str(path))
            selected = controller.selected_owned_library(prefix, library + suffix, [package])
            selected_path = Path(selected)
            selected_entry = str(selected_path.relative_to(prefix))
            index = manifest.index(selected_entry)
            require(index+1 < len(manifest) and re.fullmatch(r'@comment MD5:[0-9a-f]{32}', manifest[index+1]),
                    'XML library has no package checksum: ' + selected_entry)
            info = selected_path.stat()
            digest = hashlib.md5(selected_path.read_bytes(), usedforsecurity=False).hexdigest()
            require(selected_path.stat() == info and digest == manifest[index+1].split(':', 1)[1],
                    'XML library differs from installed package: ' + selected_entry)
            result['emberbsd_' + name + '_' + role + '_library'] = selected
            result['emberbsd_' + name + '_' + role + '_inputs'] = sorted(set(files + [selected] +
                [str(package/item) for item in ('+CONTENTS', '+BUILD_INFO', '+BUILD_VERSION')]))
            pc_prefix = Path(buildlink) if role == 'host' else target_prefix
            env = dict(environment, PKG_CONFIG_LIBDIR=str(pc_prefix/'lib/pkgconfig'))
            env.pop('PKG_CONFIG_PATH', None)
            if role == 'host':
                env.pop('PKG_CONFIG_SYSROOT_DIR', None)
            else:
                env['PKG_CONFIG_SYSROOT_DIR'] = str(options.sysroot)
            command = [native.tool('pkg-config')] + (['--define-prefix'] if role == 'host' else [])
            version = sdk['process'].capture(command + ['--modversion', module], env=env).stdout.decode().strip()
            require(version, 'empty shared XML pkg-config version: ' + module)
            versions.append(version)
        require(versions[0] == versions[1], 'host and target XML versions differ: ' + module)
        identities[pkgpath] = {'package': hosts[0].name, 'recipe': recipe, 'version': versions[0]}
    environment['EMBERBSD_XML_SOURCE_SHA256'] = hashlib.sha256(
        json.dumps(identities, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return result
