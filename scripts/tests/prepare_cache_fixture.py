"""Write an include from the real pkg_add source. This does not run tools."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    text = args.source.read_text()
    header = '''#if defined(__APPLE__) && defined(__MACH__)
#include <mach-o/dyld.h>
#if defined(__MAC_11_0) && TARGET_OS_OSX
#define PKG_INSTALL_DYLD_SHARED_CACHE 1
/* Keep the API optional when this binary runs on an older macOS release. */
extern bool _dyld_shared_cache_contains_path(const char *)
    __attribute__((weak_import));
#endif
#endif'''
    if text.count(header) != 1:
        raise ValueError('The SDK, platform and weak-import guards differ')
    start = text.index('/* The active dyld cache describes this root,')
    end = text.index('\n/*\n * Install a required dependency', start)
    fragment = text[start:end]
    if fragment.count('required_library_in_shared_cache(libpath)') != 1:
        raise ValueError('The required-library check does not use the predicate')
    if 'missing required library: %s' not in fragment:
        raise ValueError('The missing-library diagnostic was removed')
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(fragment)


if __name__ == '__main__':
    main()
