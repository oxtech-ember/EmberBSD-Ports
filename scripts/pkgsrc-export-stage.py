#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Keep one pkgsrc export per Git fingerprint of its inputs.

The fingerprint is a hash of Git object ids: the pinned upstream/pkgsrc
gitlink and the committed objects of every overlay input that
scripts/prepare-pkgsrc.py reads (pkgsrc/export.conf with its recipes,
patches, files and manifests, and the exporter itself), plus the patch tool.
The Ports commit is not part of it, so a Ports change outside those inputs
reuses the stage. Inputs must be committed: an uncommitted change has no Git
object id, and the stage is refused instead of being keyed wrongly; so is an
untracked or ignored file inside an input.

  pkgsrc-export-stage.py fingerprint --git GIT --patch PATCH
  pkgsrc-export-stage.py prepare ROOT --git GIT --patch PATCH

prepare prints the stage directory ROOT/FINGERPRINT. It creates the stage in
a private directory and renames it into place, or verifies an existing one.
Consumers read DIRECTORY/pkgsrc and never write into it.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PORTS = Path(__file__).resolve().parents[1]
FORMAT = 'emberbsd-pkgsrc-export-stage'
VERSION = 1
RECEIPT = 'pkgsrc-stage.json'


def _executable(path, role):
    if not path or not os.path.isabs(path) or not os.path.isfile(path) or not os.access(path, os.X_OK):
        raise ValueError(f'{role} must be an absolute executable')
    return path


def _environment(*tools):
    """Run only the selected tools, with no inherited search path."""
    env = {name: os.environ[name] for name in ('HOME', 'TMPDIR') if name in os.environ}
    env.update(LC_ALL='C', GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1',
               GIT_CONFIG_NOSYSTEM='1', PATCH_VERSION_CONTROL='none',
               PATH=os.pathsep.join(dict.fromkeys(os.path.dirname(tool) for tool in tools)))
    return env


def _git(git, root, *args):
    return subprocess.run([git, '-C', str(root), *args], check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=_environment(git)).stdout


def _exporter(root):
    spec = importlib.util.spec_from_file_location('emberbsd_pkgsrc_export', root / 'scripts/prepare-pkgsrc.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def input_paths(root):
    """Return the Ports-relative paths that the exporter reads."""
    recipes, patches, files, _, manifests = _exporter(root).configuration(root, include_manifests=True)
    sources = {root / 'scripts/prepare-pkgsrc.py', root / 'pkgsrc'}
    sources.update(source for _, source in recipes)
    sources.update(source for _, source, _, _ in patches)
    sources.update(source for source, _ in files)
    sources.update(manifests)
    result = set()
    for source in sources:
        relative = Path(os.path.normpath(source)).relative_to(root).as_posix()
        if relative.startswith('upstream/'):
            raise ValueError(f'export input inside the upstream checkout: {relative}')
        result.add(relative)
    # A path inside another listed directory is covered by that tree's id.
    return sorted(path for path in result
                  if not any(path.startswith(other + '/') for other in result))


def fingerprint_inputs(git, patch, root=PORTS):
    root = Path(root).resolve(strict=True)
    git, patch = _executable(git, 'git'), _executable(patch, 'patch')
    paths = input_paths(root)
    # The exporter copies files from the checkout, so ignored files count too.
    changed = _git(git, root, 'status', '--porcelain=v1', '-z', '--untracked-files=all',
                   '--ignored=matching', '--', *paths)
    if changed:
        names = sorted({entry[3:] for entry in changed.decode('utf-8', 'surrogateescape').split('\0')
                        if len(entry) > 3})
        raise ValueError('uncommitted pkgsrc export inputs have no Git fingerprint: ' + ', '.join(names[:5]))
    pin = _git(git, root, 'ls-files', '--stage', '--', 'upstream/pkgsrc').split()
    if len(pin) != 4 or pin[0] != b'160000' or pin[2] != b'0':
        raise ValueError('expected one pinned pkgsrc gitlink')
    objects = {}
    for path in paths:
        objects[path] = _git(git, root, 'rev-parse', '--verify', 'HEAD:' + path).decode('ascii').strip()
    with open(patch, 'rb') as stream:
        patch_sha256 = hashlib.sha256(stream.read()).hexdigest()
    return {'format': FORMAT, 'version': VERSION, 'upstream': pin[1].decode('ascii'),
            'objects': objects, 'patch': {'path': patch, 'sha256': patch_sha256}}


def fingerprint(inputs):
    encoded = json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode('ascii')
    return hashlib.sha256(encoded).hexdigest()


def verify(directory, git, patch, root=PORTS):
    """Return DIRECTORY/pkgsrc when the stage matches the current inputs."""
    directory = Path(directory)
    if not directory.is_absolute() or directory.is_symlink() or not directory.is_dir():
        raise ValueError('pkgsrc export stage must be an absolute real directory')
    inputs = fingerprint_inputs(git, patch, root)
    key = fingerprint(inputs)
    if directory.name != key:
        raise ValueError('pkgsrc export stage was made from different inputs')
    receipt = directory / RECEIPT
    if receipt.is_symlink() or not receipt.is_file():
        raise ValueError('pkgsrc export stage has no receipt')
    recorded = json.loads(receipt.read_text(encoding='ascii'))
    if recorded != {'fingerprint': key, 'inputs': inputs}:
        raise ValueError('pkgsrc export stage receipt differs from its inputs')
    exported = directory / 'pkgsrc'
    revision = exported / 'EMBERBSD-PKGSRC-REVISION'
    if (exported.is_symlink() or not exported.is_dir() or revision.is_symlink() or not revision.is_file() or
            revision.read_text(encoding='ascii') != inputs['upstream'] + '\n'):
        raise ValueError('pkgsrc export stage tree differs from its receipt')
    return exported


def prepare(root_directory, git, patch, root=PORTS):
    """Create or reuse ROOT/FINGERPRINT; return (directory, reused)."""
    stages = Path(root_directory)
    if not stages.is_absolute():
        raise ValueError('pkgsrc export stage root must be absolute')
    stages.mkdir(parents=True, exist_ok=True)
    inputs = fingerprint_inputs(git, patch, root)
    key = fingerprint(inputs)
    final = stages / key
    if os.path.lexists(final):
        verify(final, git, patch, root)
        return final, True
    partial = stages / f'.partial-{key}-{os.getpid()}'
    partial.mkdir(mode=0o755)
    try:
        subprocess.run([sys.executable, '-B', str(Path(root) / 'scripts/prepare-pkgsrc.py'),
                        str(partial / 'pkgsrc'), '--git', git, '--patch', patch],
                       check=True, env=_environment(git, patch), stdout=sys.stderr)
        if fingerprint_inputs(git, patch, root) != inputs:
            raise ValueError('pkgsrc export inputs changed during the export')
        with open(partial / RECEIPT, 'x', encoding='ascii') as output:
            output.write(json.dumps({'fingerprint': key, 'inputs': inputs}, sort_keys=True) + '\n')
        try:
            os.rename(partial, final)
        except OSError:
            # Another run published the same fingerprint first.
            if not os.path.lexists(final):
                raise
            verify(final, git, patch, root)
            return final, True
    finally:
        if os.path.lexists(partial):
            shutil.rmtree(partial)
    verify(final, git, patch, root)
    return final, False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('fingerprint', 'prepare'):
        command = commands.add_parser(name)
        if name == 'prepare':
            command.add_argument('root', help='absolute directory holding the stages')
        command.add_argument('--git', required=True, help='absolute Git executable')
        command.add_argument('--patch', required=True, help='absolute patch tool')
    args = parser.parse_args(argv)
    try:
        if args.command == 'fingerprint':
            inputs = fingerprint_inputs(args.git, args.patch)
            result = {'fingerprint': fingerprint(inputs), 'inputs': inputs}
        else:
            directory, reused = prepare(args.root, args.git, args.patch)
            result = {'directory': str(directory), 'fingerprint': directory.name, 'reused': reused}
        sys.stdout.write(json.dumps(result, sort_keys=True) + '\n')
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        detail = getattr(error, 'stderr', None)
        if detail:
            error = f'{error}: {detail.decode("utf-8", "replace").strip()}'
        print('pkgsrc export stage: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
