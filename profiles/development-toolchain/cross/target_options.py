# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; target and build mode policy for Python host controllers.
from host import TARGETS, require


def parse(args, kernel_allowed=False, bootstrap_allowed=False):
    args = list(args)
    target, mode, seen = 'aarch64', 'applications', False
    bootstrap = False
    while args and args[0].startswith('--'):
        option = args.pop(0)
        if option == '--target':
            require(args and not seen, 'Duplicate or missing target')
            target, seen = args.pop(0), True
        elif option == '--kernel':
            require(kernel_allowed and mode == 'applications', 'Unknown build mode')
            mode = 'kernel'
        elif option == '--bootstrap-libgcc':
            require(bootstrap_allowed and not bootstrap, 'Unknown or repeated --bootstrap-libgcc')
            bootstrap = True
        else:
            require(False, 'Unknown build mode: ' + option)
    require(target in TARGETS, 'Unsupported target: ' + target)
    require(not bootstrap or mode == 'kernel', '--bootstrap-libgcc requires --kernel')
    if bootstrap:
        mode = 'kernel-bootstrap'
    return target, mode, args
