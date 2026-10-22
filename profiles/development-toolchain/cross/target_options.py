# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; target and build mode policy for Python host controllers.
from host import TARGETS, require


def parse(args, kernel_allowed=False, bootstrap_allowed=False, fortran_allowed=False):
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
        elif option == '--with-fortran':
            require(fortran_allowed and mode == 'applications', 'Fortran requires application mode and cannot be repeated')
            mode = 'applications-fortran'
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


# Firmware policy does not extend application or kernel targets.
FIRMWARE_TARGETS = {'arm-none-eabi': 'arm-none-eabi'}


def parse_firmware(args):
    args = list(args)
    require(len(args) >= 2 and args[0] == '--target', 'An explicit firmware --target is required')
    target = args[1]
    require(target in FIRMWARE_TARGETS, 'Unsupported firmware target: ' + target)
    args = args[2:]
    require(not any(value.startswith('--') for value in args), 'Unknown or repeated firmware option')
    return target, args
