"""Browser-owned WebApp launch and profile cleanup using a stable BSD flock."""
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
from contextlib import ExitStack

LAYOUT = json.loads(Path(__file__).with_name('webapp-layout.json').read_text())
IDENT = re.compile(r'[A-Za-z0-9_-]{1,64}')
SINGLETON = ('SingletonLock', 'SingletonSocket', 'SingletonCookie')


def checked_directory(fd):
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise ValueError('WebApp directory must be owned by this user and not writable by others')
    return fd


def directory(stack, parent, name, create=False):
    if create:
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent)
        except FileExistsError:
            pass
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    stack.callback(os.close, fd)
    return checked_directory(fd)


def main(argv):
    if len(argv) < 3:
        raise ValueError('expected Electron executable, application and WebApp arguments')
    command, options = argv[:2], argv[2:]
    clears = [a.removeprefix('--webapp-clear=') for a in options if a.startswith('--webapp-clear=')]
    ids = [a.removeprefix('--webapp-id=') for a in options if a.startswith('--webapp-id=')]
    clear = bool(clears)
    if clear:
        if len(clears) != 1 or ids or any(a != '--webapp-clear=' + clears[0] and
                a not in ('--ozone-platform=x11', '--in-process-gpu') for a in options):
            raise ValueError('clear accepts only one WebApp ID')
        ident = clears[0]
    else:
        if len(ids) != 1:
            raise ValueError('launch requires exactly one WebApp ID')
        ident = ids[0]
    if not IDENT.fullmatch(ident):
        raise ValueError('invalid WebApp ID')
    config_path = os.environ.get('XDG_CONFIG_HOME')
    if not config_path:
        home = os.environ.get('HOME')
        if not home or not Path(home).is_absolute():
            raise ValueError('HOME or an absolute XDG_CONFIG_HOME is required')
        config_path = str(Path(home) / '.config')
    config = Path(config_path)
    if not config.is_absolute():
        raise ValueError('XDG_CONFIG_HOME must be absolute')
    # The explicitly selected XDG location is trusted, as in Electron. All
    # Browser-owned directories beneath its resolved root are opened no-follow.
    config = config.resolve()
    config.mkdir(mode=0o700, parents=True, exist_ok=True)
    with ExitStack() as stack:
        base = directory(stack, None, str(config))
        app = directory(stack, base, LAYOUT['application'], create=True)
        locks = directory(stack, app, LAYOUT['locks'], create=True)
        fd = os.open(ident, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=locks)
        stack.callback(os.close, fd)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
            raise ValueError('unsafe WebApp lock file')
        try:
            fcntl.flock(fd, (fcntl.LOCK_EX | fcntl.LOCK_NB) if clear else fcntl.LOCK_SH)
        except BlockingIOError:
            raise ValueError('Close this web app before deleting it') from None
        current = os.stat(ident, dir_fd=locks, follow_symlinks=False)
        if (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino):
            raise ValueError('WebApp lock file changed')
        if not clear:
            # The browser owns this open description until it exits. The target
            # acceptance test verifies that Electron retains it through exec.
            os.set_inheritable(fd, True)
            os.execv(command[0], command + options)
        if not shutil.rmtree.avoids_symlink_attacks:
            raise ValueError('safe directory-relative cleanup is unavailable')
        profiles = []
        # Check both profiles before deleting either. Never follow profile or
        # namespace symlinks; use the same directory descriptors for removal.
        for name in (LAYOUT['normal'], LAYOUT['private']):
            try:
                namespace = directory(stack, app, name)
                profile = directory(stack, namespace, ident)
            except FileNotFoundError:
                continue
            for entry in SINGLETON:
                try:
                    os.stat(entry, dir_fd=profile, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                raise ValueError('Browser profile has an active or stale process lock; open and close the web app, then retry')
            profiles.append(namespace)
        for namespace in profiles:
            shutil.rmtree(ident, dir_fd=namespace)
        # Keep the stable lock inode: unlinking it would let concurrent clients
        # acquire different locks for the same ID.
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except (OSError, ValueError) as exc:
        print('WebApp: ' + str(exc), file=sys.stderr)
        sys.exit(1)
