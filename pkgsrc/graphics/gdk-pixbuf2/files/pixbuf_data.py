# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Stored per-platform GdkPixbuf target data for cross builds.

A cross build of graphics/gdk-pixbuf2 needs two outputs of target programs:
the loader cache of gdk-pixbuf-query-loaders (input to the thumbnailer MIME
list; not installed, the package rebuilds it on the target at install time)
and the MIME list of gdk-pixbuf-print-mime-types for the thumbnailer file.
Both depend only on the release and on the set of loader modules. The recipe
stores them per target platform in files/target-data/PLATFORM/ as
loaders.cache and mime-types.txt with an identity header:

    # EmberBSD GdkPixbuf target data 1
    # platform: NetBSD-11.0-aarch64
    # recipe: graphics/gdk-pixbuf2
    # package: gdk-pixbuf2-2.44.8
    # query: loaders
    # modules: libpixbufloader-ani.so libpixbufloader-bmp.so ...
    # data-sha256: <SHA-256 of the data below the header>
    #

Module paths in a stored loader cache read @MODULE@/<file name>; replay
writes the build paths of the requested modules instead.

EMBERBSD_GI_DUMP_MODE selects the mode, as for the GI dumps of this recipe:
replay (recipe default) answers from the stored data and refuses a request
for another platform, package or module set; live queries the target;
capture queries the target and also writes the normalized data to
EMBERBSD_GI_DUMP_CAPTURE_DIR/PLATFORM/<category>_<name>/.
"""
import hashlib
import os
import re

MAGIC = '# EmberBSD GdkPixbuf target data 1'
FIELDS = ('platform', 'recipe', 'package', 'query', 'modules', 'data-sha256')
FILES = {'loaders': 'loaders.cache', 'mime': 'mime-types.txt'}
PLACEHOLDER = '@MODULE@/'
MODULE = re.compile(r'libpixbufloader-[a-z0-9]+\.so')
MODULE_LINE = re.compile(r'^"(/[^"\n]+\.so)"$', re.MULTILINE)
MIME = re.compile(r'[a-zA-Z0-9.+_-]+/[a-zA-Z0-9.+_-]+;(?:[a-zA-Z0-9.+_-]+/[a-zA-Z0-9.+_-]+;)*')
PATTERNS = {
    'platform': re.compile(r'[A-Za-z0-9]+-[0-9][A-Za-z0-9._]*-[a-z0-9_]+'),
    'recipe': re.compile(r'[a-z0-9][a-z0-9+_-]*/[A-Za-z0-9][A-Za-z0-9+._-]*'),
    'package': re.compile(r'[A-Za-z0-9][A-Za-z0-9+._-]*-[0-9][A-Za-z0-9._]*'),
}
MODES = ('replay', 'live', 'capture')


class DataError(Exception):
    """Stored target data are absent, malformed or for another build."""


def mode(environ):
    value = environ.get('EMBERBSD_GI_DUMP_MODE', 'live')
    if value not in MODES:
        raise DataError('EMBERBSD_GI_DUMP_MODE must be replay, live or capture')
    return value


def identity(environ):
    ident = {'platform': environ.get('EMBERBSD_GI_DUMP_PLATFORM', ''),
             'recipe': environ.get('EMBERBSD_GI_DUMP_RECIPE', ''),
             'package': environ.get('EMBERBSD_GI_DUMP_PACKAGE', '')}
    for key, value in ident.items():
        if not PATTERNS[key].fullmatch(value):
            raise DataError(f'invalid {key}: {value!r}')
    return ident


def module_names(paths):
    names = sorted(os.path.basename(path) for path in paths)
    if not names or len(set(names)) != len(names) or not all(MODULE.fullmatch(name) for name in names):
        raise DataError('invalid loader module set')
    return names


def request(kind, arguments):
    """Module paths of a --loaders or --mime request (after the program)."""
    if kind == 'loaders':
        return list(arguments)
    if len(arguments) != 1:
        raise DataError('one cache required')
    with open(arguments[0], encoding='utf-8') as cache:
        return MODULE_LINE.findall(cache.read())


def normalize(kind, output, modules):
    text = output.decode('utf-8', 'strict').replace('\r\n', '\n')
    if kind == 'mime':
        if not MIME.fullmatch(text):
            raise DataError('invalid MIME query output')
        return text + '\n'
    for path in modules:
        text = text.replace(f'"{path}"', f'"{PLACEHOLDER}{os.path.basename(path)}"')
    stored = sorted(re.findall(r'^"' + re.escape(PLACEHOLDER) + r'([^"\n]+)"$', text, re.MULTILINE))
    if stored != module_names(modules) or MODULE_LINE.search(text):
        raise DataError('loader cache does not list exactly the requested modules')
    return '\n'.join(line.rstrip() for line in text.rstrip('\n').split('\n')) + '\n'


def render(ident, kind, names, data):
    values = dict(ident, query=kind, modules=' '.join(names),
                  **{'data-sha256': hashlib.sha256(data.encode('utf-8')).hexdigest()})
    return ''.join(f'{MAGIC}\n' if key is None else f'# {key}: {values[key]}\n'
                   for key in (None,) + FIELDS) + '#\n' + data


def parse(text):
    rows = text.split('\n')
    if rows[0] != MAGIC:
        raise DataError('not EmberBSD GdkPixbuf target data')
    header = {}
    for key, row in zip(FIELDS, rows[1:1 + len(FIELDS)]):
        prefix = f'# {key}: '
        if not row.startswith(prefix):
            raise DataError(f'header lacks {key}')
        header[key] = row[len(prefix):]
    if rows[1 + len(FIELDS)] != '#':
        raise DataError('header is not terminated')
    data = '\n'.join(rows[2 + len(FIELDS):])
    if header['data-sha256'] != hashlib.sha256(data.encode('utf-8')).hexdigest():
        raise DataError('data differ from their recorded checksum')
    if text != render({k: header[k] for k in ('platform', 'recipe', 'package')},
                      header['query'], header['modules'].split(' '), data):
        raise DataError('stored data are not normalized')
    return header, data


def replay(environ, kind, arguments):
    ident = identity(environ)
    directory = environ.get('EMBERBSD_PIXBUF_DATA_DIR', '')
    if not os.path.isabs(directory):
        raise DataError('EMBERBSD_PIXBUF_DATA_DIR must be absolute')
    path = os.path.join(directory, FILES[kind])
    if not os.path.isfile(path):
        raise DataError(f'No stored GdkPixbuf target data for {ident["platform"]} in {ident["recipe"]}: {path}; '
                        'capture them from an EmberBSD target (profiles/common-graphics/cross/gi-dumps.md)')
    with open(path, encoding='utf-8') as source:
        header, data = parse(source.read())
    for key in ('platform', 'recipe', 'package'):
        if header[key] != ident[key]:
            raise DataError(f'stored data are for {key} {header[key]}, not {ident[key]}: {path}')
    if header['query'] != kind:
        raise DataError(f'{path} holds {header["query"]} data')
    modules = request(kind, arguments)
    if header['modules'].split(' ') != module_names(modules):
        raise DataError(f'stored data are for loader modules {header["modules"]}, '
                        f'not {" ".join(module_names(modules))}: {path}')
    if kind == 'mime':
        return data[:-1].encode('utf-8')
    for module in modules:
        data = data.replace(f'"{PLACEHOLDER}{os.path.basename(module)}"', f'"{module}"')
    return data.encode('utf-8')


def capture(environ, kind, arguments, output):
    ident = identity(environ)
    root = environ.get('EMBERBSD_GI_DUMP_CAPTURE_DIR', '')
    if not os.path.isabs(root) or not os.path.isdir(root):
        raise DataError('EMBERBSD_GI_DUMP_CAPTURE_DIR must name an existing absolute directory')
    modules = request(kind, arguments)
    data = normalize(kind, output, modules)
    directory = os.path.join(root, ident['platform'], ident['recipe'].replace('/', '_'))
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, FILES[kind])
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as target:
        target.write(render(ident, kind, module_names(modules), data))
    return path
