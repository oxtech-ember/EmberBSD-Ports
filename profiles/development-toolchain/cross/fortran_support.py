# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); GCC16 application Fortran capability policy.
"""Qualify a new host frontend generation. Do not link or run target programs."""
import os
from pathlib import Path
import platform
import re
import shutil

import sdk_source
from emberbsd_sdk import elf, inventory, jsonio, paths, provenance
from emberbsd_sdk.errors import ProcessOwnershipError, SDKError
from emberbsd_sdk.stream import PRODUCER_STREAM_API, capture_streamed
from host import PROFILE, TARGETS, VERSION, QUARANTINE, audit_source, environment, logged, new_path, require

PORTS = PROFILE.parents[1]
F77 = """      subroutine emberbsd_fortran_add(a, b, result)
      integer a, b, result
      result = a + b
      end
"""
C_BINDING = """subroutine emberbsd_fortran_c_add(a, b, result) bind(C)
  use iso_c_binding, only: c_int
  implicit none
  integer(c_int), value :: a, b
  integer(c_int), intent(out) :: result
  result = a + b
end subroutine
"""


def query(argv):
    require(type(PRODUCER_STREAM_API) is int and PRODUCER_STREAM_API == 1,
            'SDK producer stream API1 is required')
    result = capture_streamed(list(map(str, argv)), env=environment(),
                              stdout_limit=1024 * 1024, stderr_limit=1024 * 1024, timeout=120)
    require(not result.stderr_truncated, 'Fortran query stderr exceeds the capture limit')
    return result.value.decode('utf-8', 'strict'), result.stderr.decode('utf-8', 'strict')


def source_state(pkgsrc, archive):
    """Require complete clean explicit sources before starting this generation."""
    return {'ports': provenance.git_source(PORTS, kind='ports', env=environment()),
            'sdk': provenance.git_source(sdk_source.load(), env=environment()),
            'archive_sha256': inventory.sha256_file(archive),
            'recipe': inventory.snapshot_tree(Path(pkgsrc) / 'lang/gcc16')}


def reports(target, version, triplet, verbose):
    require(target in TARGETS, 'Unsupported Fortran target')
    require(version.strip() == VERSION, 'Fortran must use GCC ' + VERSION)
    require(triplet.strip() == TARGETS[target][0], 'Fortran target triplet mismatch')
    require(re.findall(r'^Target: (.+)$', verbose, re.M) == [TARGETS[target][0]],
            'Fortran verbose target report mismatch or duplicate')
    require(re.findall(r'^Thread model: (.+)$', verbose, re.M) == ['posix'],
            'Fortran must report one POSIX thread model')


def executable(path, prefix):
    require(Path(path).is_absolute(), 'Fortran executable path must be absolute')
    path = Path(paths.canonical_existing(path))
    paths.regular_file(path)
    require(paths.inside(path, prefix) and os.access(path, os.X_OK),
            'Fortran executable is missing or escapes the compiler prefix')
    return path


def host_image(path):
    """Use the host inspector; never infer host execution from target triplet."""
    file = shutil.which('file')
    require(file is not None, 'Host file inspector is required')
    out, err = query([file, '-b', path])
    require(not err, 'Host file inspector reported a diagnostic')
    host = platform.system(), platform.machine()
    if host[0] == 'Darwin':
        arch = {'arm64': 'arm64', 'x86_64': 'x86_64'}.get(host[1])
        require(arch is not None and out.strip() == 'Mach-O 64-bit executable ' + arch,
                'Fortran frontend must be a native Mach-O executable')
    elif host[0] == 'Linux':
        machine = {'aarch64': 183, 'x86_64': 62}.get(host[1])
        require(machine is not None and elf.read_elf_header(path, machine=machine) is not None,
                'Fortran frontend must be a native ELF executable')
        require(re.search(r'ELF 64-bit LSB (?:pie )?executable', out) is not None,
                'Fortran frontend is not a host executable')
    else:
        raise SDKError('Unsupported Fortran build host')
    return {'format': out.strip(), 'inspector': str(Path(file).resolve(strict=True)),
            'inspector_sha256': inventory.sha256_file(file)}


def inspect(prefix, target):
    prefix = Path(paths.canonical_existing(prefix))
    paths.real_directory(prefix)
    require(target in TARGETS, 'Unsupported Fortran target')
    driver = executable(prefix / 'bin' / (TARGETS[target][0] + '-gfortran'), prefix)
    version, _ = query([driver, '-dumpfullversion'])
    triplet, _ = query([driver, '-dumpmachine'])
    out, err = query([driver, '-v'])
    reports(target, version, triplet, out + err)
    reported, diagnostic = query([driver, '-print-prog-name=f951'])
    require(not diagnostic and len(reported.splitlines()) == 1, 'Invalid f951 path report')
    frontend = executable(reported.strip(), prefix)
    require(frontend.name == 'f951', 'Fortran backend must be f951')
    nm = executable(prefix / 'bin' / (TARGETS[target][0] + '-nm'), prefix)
    nm_out, nm_err = query([nm, '--version'])
    require(not nm_err and re.match(r'GNU nm .* 2[.]47(?:[.\s]|$)', nm_out) is not None,
            'The selected GNU nm2.47 is required')
    tools = {}
    for name, path in (('gfortran', driver), ('f951', frontend), ('nm', nm)):
        tools[name] = {'path': str(path), 'sha256': inventory.sha256_file(path),
                       'host_image': host_image(path)}
    return {'version': version.strip(), 'triplet': triplet.strip(), 'threads': 'posix',
            'host': {'system': platform.system(), 'machine': platform.machine()}, 'tools': tools,
            'reports': {'version': version, 'triplet': triplet, 'verbose_stdout': out,
                        'verbose_stderr': err, 'f951': reported, 'nm_version': nm_out}}


def symbol_report(text, expected):
    matches = re.findall(r'^([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+T\s+(\S+)$', text, re.M)
    require(len(matches) == 1 and matches[0][2] == expected and int(matches[0][1], 16) > 0,
            'Fortran object must contain exactly its nonempty probe routine')


def quarantine_work(owned, error):
    """Mark only the exact new generation after an unproven producer drain."""
    try:
        work = Path(owned['path'])
        identity = paths.real_directory(work)
        require((identity.st_dev, identity.st_ino) == (owned['device'], owned['inode']),
                'The owned Fortran work directory identity changed')
        marker = work / QUARANTINE
        if paths.entry(marker) is None:
            jsonio.write_json(marker, {'state': 'producer-ownership-unproven', 'work': str(work),
                'phase': 'fortran-build', 'session': error.sid, 'reason': error.reason,
                'log': str(error.log) if error.log is not None else None,
                'device': identity.st_dev, 'inode': identity.st_ino}, exclusive=True)
        else:
            paths.regular_file(marker)
    except Exception as marker_error:
        raise ProcessOwnershipError(error.sid, error.reason + '; cannot persist the Fortran quarantine: ' + str(marker_error), error.log) from error


def qualify(prefix, target, output, sources, pkgsrc, archive, *, quarantine):
    """Compile two real objects; leave all failed work and evidence in place."""
    output = new_path(output)
    paths.reject_overlap(prefix, output)
    try:
        require(source_state(pkgsrc, archive) == sources, 'Fortran sources changed during the compiler build')
        expected_archive, patches = audit_source(pkgsrc, archive, runtime=False)
        before = inspect(prefix, target)
        output.mkdir()
        objects = {}
        driver = before['tools']['gfortran']['path']
        for name, suffix, text, symbol in (('f77', 'f', F77, 'emberbsd_fortran_add_'),
                                           ('c-binding', 'f90', C_BINDING, 'emberbsd_fortran_c_add')):
            source, obj = output / (name + '.' + suffix), output / (name + '.o')
            source.write_text(text)
            log = output / (name + '.log')
            argv = [driver, '-O2', '-fPIC', '-c', source, '-o', obj]
            logged(argv, log, quarantine=quarantine)
            header = elf.read_elf_header(obj, machine=TARGETS[target][1], required_type=1)
            require(header is not None, 'Fortran probe did not produce a target ELF object')
            nm_argv = [before['tools']['nm']['path'], '-g', '--defined-only', '-S', obj]
            symbols, diagnostics = query(nm_argv)
            require(not diagnostics, 'Fortran object symbol inspection reported a diagnostic')
            symbol_report(symbols, symbol)
            objects[name] = {'source': str(source), 'source_sha256': inventory.sha256_file(source),
                             'object': str(obj), 'object_sha256': inventory.sha256_file(obj),
                             'header': header, 'argv': list(map(str, argv)),
                             'symbols': {'argv': list(map(str, nm_argv)), 'stdout': symbols, 'stderr': diagnostics},
                             'log_sha256': inventory.sha256_file(log)}
        require(inspect(prefix, target) == before, 'Fortran compiler changed during qualification')
        require(source_state(pkgsrc, archive) == sources, 'Fortran sources changed before capability publication')
        require(inventory.sha256_file(archive) == expected_archive, 'Fortran source archive changed')
        recipe = Path(pkgsrc) / 'lang/gcc16'
        # Revalidate all audited recipe/patch inputs after the actual compiler runs.
        require(audit_source(pkgsrc, archive, runtime=False) == (expected_archive, patches),
                'Fortran source recipe changed')
        receipt = output / 'capability.json'
        jsonio.write_json(receipt, {'format': 'emberbsd-gcc16-fortran-capability', 'version': 1,
            'status': 'PASS', 'target': target, 'scope': 'host-frontends-and-target-compile-only',
            'compiler': before, 'sources': sources, 'archive_sha256': expected_archive,
            'recipe_distinfo_sha256': inventory.sha256_file(recipe / 'distinfo'),
            'patches': {name: inventory.sha256_file(recipe / 'patches' / name) for name in patches},
            'probes': objects, 'limits': ['No target runtime was built, linked, installed or executed.',
            'This is not a libgfortran, FFTW, Libtool or target-system acceptance.']}, exclusive=True)
        return receipt
    except ProcessOwnershipError as error:
        marker = Path(quarantine) / QUARANTINE
        if paths.entry(marker) is None:
            jsonio.write_json(marker, {'state': 'producer-ownership-unproven', 'work': str(quarantine),
                                      'phase': 'fortran-capability', 'error': str(error)}, exclusive=True)
        raise


def lease_hold(error):
    """Do not release caller leases after unproven Fortran query drainage."""
    import signal
    import sys
    import time
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, signal.SIG_IGN)
    try:
        print('Fortran ownership HOLD: ' + str(error), file=sys.stderr, flush=True)
    except BaseException:
        pass
    while True:
        try:
            time.sleep(30)
        except BaseException:
            pass
