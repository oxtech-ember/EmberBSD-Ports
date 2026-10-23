#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; real GCC16 frontend capability selection for pkgsrc.
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime/recipe/files'))
import sdk_source
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main(args):
    from fortran_support import inspect
    from host import require
    from emberbsd_sdk import paths, provenance, jsonio
    from host import PROFILE, environment
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True, choices=('amd64', 'aarch64'), action='append')
    parser.add_argument('--capability', type=Path, required=True, action='append')
    parser.add_argument('--compiler', type=Path, required=True, action='append')
    options = parser.parse_args(args)
    for name in ('target', 'capability', 'compiler'):
        value = getattr(options, name)
        require(len(value) == 1, 'Use each capability option once')
        setattr(options, name, value[0])
    receipt = Path(paths.canonical_existing(options.capability))
    paths.regular_file(receipt)
    value = jsonio.read_json(receipt)
    require(value['format'] == 'emberbsd-gcc16-fortran-capability' and
            type(value['version']) is int and value['version'] == 1 and
            value['status'] == 'PASS' and value['target'] == options.target,
            'A matching completed Fortran capability receipt is required')
    provenance.git_source(PROFILE.parents[1], kind='ports', env=environment())
    driver = Path(paths.canonical_existing(options.compiler))
    require(str(driver) == value['compiler']['tools']['gfortran']['path'],
            'The selected Fortran driver differs from the capability receipt')
    require(inspect(driver.parent.parent, options.target) == value['compiler'],
            'The selected real Fortran frontend identity changed')
    print('verified-gcc16-fortran')


if __name__ == '__main__':
    try:
        sdk_source.install_signal_handlers()
        main(sdk_source.arguments(sys.argv[1:]))
    except Exception as error:
        errors = sys.modules.get('emberbsd_sdk.errors')
        if errors is not None:
            if isinstance(error, errors.ProcessOwnershipError):
                from fortran_support import lease_hold
                lease_hold(error)
        print('Fortran capability: ' + str(error), file=sys.stderr)
        status = getattr(error, 'returncode', None)
        sys.exit((128 - status if status < 0 else status) if status else 2)
