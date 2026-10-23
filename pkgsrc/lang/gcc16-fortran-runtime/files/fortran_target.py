# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); GCC16.2 NetBSD target library capability contract.
"""Select architecture capabilities, never infer them from missing files."""
import argparse

# GCC16.2 AArch64 uses IEEE binary128 long double. It does not register
# __float128, which libquadmath/configure.ac requires. The x86 port does.
QUADMATH = {'amd64': True, 'aarch64': False}


def quadmath(target):
    if target not in QUADMATH:
        raise ValueError('Unsupported Fortran target')
    return QUADMATH[target]


def components(target):
    return ('libbacktrace',) + (('libquadmath',) if quadmath(target) else ()) + ('libgfortran',)


def sonames(target):
    return ('libgfortran.so.5',) + (('libquadmath.so.0',) if quadmath(target) else ())


def aliases(target):
    return tuple(name.split('.so.')[0] + '.so' for name in sonames(target))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True, choices=tuple(QUADMATH), action='append')
    args = parser.parse_args()
    if len(args.target) != 1:
        parser.error('Use --target once')
    print(' '.join(aliases(args.target[0])))
