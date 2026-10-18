# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; target and build mode policy for Python host controllers.
from host import TARGETS, require


def parse(args, kernel_allowed=False):
    args = list(args)
    target, mode, seen = 'aarch64', 'applications', False
    while args and args[0].startswith('--'):
        option = args.pop(0)
        if option == '--target':
            require(args and not seen, 'Duplicate or missing target')
            target, seen = args.pop(0), True
        elif option == '--kernel':
            require(kernel_allowed and mode == 'applications', 'Unknown build mode')
            mode = 'kernel'
        else:
            require(False, 'Unknown build mode: ' + option)
    require(target in TARGETS, 'Unsupported target: ' + target)
    return target, mode, args
