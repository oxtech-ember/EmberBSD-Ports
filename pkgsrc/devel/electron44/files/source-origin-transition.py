# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Guard an incremental source-view replacement under the caller's locks."""
from pathlib import Path
import os
import shutil
import tempfile

MARKER = 'GN reconfiguration incomplete\nsource-origin-v1\n'


def require(test, message):
    if not test:
        raise ValueError(message)


def entry(path):
    return os.path.lexists(path)


def real_directory(path):
    return path.is_dir() and not path.is_symlink()


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def transition(work, *, saved_configuration, config_is_new, verify_old, verify_new,
               build_new, commit_config):
    """Switch an owned view; verify callbacks must check all selected providers.

    The existing reconfigure guard protects the whole operation. The retained
    previous configuration is temporary proof for the old view after commit.
    Partial cleanup remains fail-closed and never removes unverified content.
    """
    work = Path(work)
    require(work.is_absolute() and real_directory(work), 'invalid producer work')
    require(type(saved_configuration) is bytes and saved_configuration,
            'saved configuration must be nonempty bytes')
    view = work / 'source-view'
    candidate = work / '.source-view-origin-candidate'
    backup = work / '.source-view-origin-backup'
    previous = work / '.source-view-origin-old-configuration.json'
    current = work / 'configuration.json'
    marker = work / 'reconfigure-incomplete'
    for path in (view, candidate, backup):
        require(not entry(path) or real_directory(path), 'unexpected source view entry: ' + str(path))
    require(not entry(previous) or (previous.is_file() and not previous.is_symlink() and
                                   previous.read_bytes() == saved_configuration),
            'previous configuration changed')

    def cleanup():
        verify_new(view)
        if entry(backup):
            require(entry(previous), 'old view lacks previous configuration')
            verify_old(backup)
            shutil.rmtree(backup)
            sync_directory(work)
        if entry(previous):
            require(previous.read_bytes() == saved_configuration, 'previous configuration changed')
            previous.unlink()
            sync_directory(work)
        marker.unlink()
        sync_directory(work)

    if entry(marker):
        require(marker.is_file() and not marker.is_symlink() and marker.read_text() == MARKER,
                'invalid source-origin reconfigure marker')
        if config_is_new():
            require(entry(view) and not entry(candidate), 'invalid committed transition state')
            cleanup()
            return
        require(current.is_file() and not current.is_symlink() and
                current.read_bytes() == saved_configuration and entry(previous),
                'saved configuration changed before commit')
        if not entry(backup):
            require(entry(view) and entry(candidate), 'invalid pre-swap transition state')
            verify_old(view)
            verify_new(candidate)
            view.rename(backup)
            sync_directory(work)
        verify_old(backup)
        if entry(view):
            require(not entry(candidate), 'unexpected candidate with new stable view')
            verify_new(view)
        else:
            require(entry(candidate), 'missing new candidate')
            verify_new(candidate)
            candidate.rename(view)
            sync_directory(work)
    else:
        require(not config_is_new() and entry(view) and not entry(backup) and
                current.is_file() and not current.is_symlink() and
                current.read_bytes() == saved_configuration,
                'unexpected initial transition state')
        verify_old(view)
        if entry(candidate):
            verify_new(candidate)
        else:
            scratch = Path(tempfile.mkdtemp(prefix='.source-view-origin-factory-', dir=work))
            staged = scratch / 'source-view'
            build_new(staged)
            require(real_directory(staged), 'factory did not create candidate')
            verify_new(staged)
            staged.rename(candidate)
            scratch.rmdir()
            sync_directory(work)
        if not entry(previous):
            fd, name = tempfile.mkstemp(prefix='.source-view-origin-config-', dir=work)
            try:
                with os.fdopen(fd, 'wb') as handle:
                    handle.write(saved_configuration)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.link(name, previous, follow_symlinks=False)
                sync_directory(work)
            finally:
                os.unlink(name)
        require(previous.read_bytes() == saved_configuration, 'previous configuration changed')
        with marker.open('x') as handle:
            handle.write(MARKER)
            handle.flush()
            os.fsync(handle.fileno())
        sync_directory(work)
        view.rename(backup)
        sync_directory(work)
        candidate.rename(view)
        sync_directory(work)
        verify_new(view)
    commit_config()
    require(config_is_new(), 'configuration did not commit')
    cleanup()
