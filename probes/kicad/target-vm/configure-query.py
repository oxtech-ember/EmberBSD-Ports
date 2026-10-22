#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Select explicit target providers for GI execution.
from vm import canonical, entrypoint, parser, sdk
import os


def main():
    args = parser(__doc__, ['work', 'build_root', 'sysroot', 'readelf', 'new_config']).parse_args()
    inventory, jsonio, paths, process, identity = sdk(args.sdk_source)
    work, build, sysroot, readelf = map(canonical, [args.work, args.build_root, args.sysroot, args.readelf])
    output = paths.canonical_new(args.new_config)
    if not args.new_config.is_absolute() or args.new_config.exists() or args.new_config.is_symlink():
        raise ValueError('new absolute config required')
    if not os.access(work / 'bin/ssh', os.X_OK) or not os.access(readelf, os.X_OK):
        raise ValueError('private SSH wrapper and readelf must be executable')
    jsonio.write_json(output, dict(target='aarch64', build_root=str(build), sysroot=str(sysroot), cache=str(work / 'cache'),
                      readelf=str(readelf), ssh='ember-e14-query', host_key_alias='ember-e14-query', library_dirs=[]), mode=0o600)
    print(f'Use EMBERBSD_GI_QUERY_CONFIG={output} and prepend {work}/bin to PATH.')


if __name__ == '__main__':
    entrypoint(main)
