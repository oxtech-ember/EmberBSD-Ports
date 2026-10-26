#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), explicit Perl Darwin install-name selection.
"""Check the real installperl fragment. Runtime requires an explicit Perl.

Source-only checks run no child program. Runtime cases use a recording tool,
not a Mach-O editor. Run this fixture through the SDK owned-process interface.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

NAME = 'EMBERBSD_DARWIN_INSTALL_NAME_TOOL'
SELECTION = '''    my $install_name_tool = "install_name_tool";
    if (exists $ENV{EMBERBSD_DARWIN_INSTALL_NAME_TOOL}) {
        $install_name_tool = $ENV{EMBERBSD_DARWIN_INSTALL_NAME_TOOL};
        die "EMBERBSD_DARWIN_INSTALL_NAME_TOOL must name an absolute executable file\\n"
          unless $install_name_tool =~ m{\\A/}
            && -f $install_name_tool && -x $install_name_tool;
    }
'''
CALL = '    system { $install_name_tool } $install_name_tool, @opts\n'
GUARD = '''    $^O eq "darwin" && $Config{osvers} =~ /^(1[5-9]|[2-9])/
      && $Config{useshrplib}
      or return;
'''
ENVIRONMENT = '''.if ${OPSYS} == "Darwin" && defined(EMBERBSD_DARWIN_INSTALL_NAME_TOOL)
MAKE_ENV+=\t\tEMBERBSD_DARWIN_INSTALL_NAME_TOOL=${EMBERBSD_DARWIN_INSTALL_NAME_TOOL:Q}
.endif
'''


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def fragment(text):
    start = text.index('sub fix_dep_names {\n')
    end = text.index('\n}\n', start) + 3
    return text[start:end]


def check_source(text, makefile):
    body = fragment(text)
    require(body.count(SELECTION) == 1, 'Explicit selection or validation changed')
    require(body.count(GUARD) == 1 and body.index(GUARD) < body.index(SELECTION),
            'Keep the original platform guard before selection')
    require(body.count(CALL) == 1 and body.count('system ') == 1,
            'Use one indirect list-form system call')
    require('push @opts, -id => $libperl;' in body and
            'push @opts, -change => getcwd . "/libperl.$so", $libperl;' in body and
            'push @opts, $file;' in body, 'Keep both upstream operand lists')
    require('and die "Cannot update $file dependency paths\\n";' in body,
            'Keep command failure propagation')
    require('$opts{verbose} and print "  $install_name_tool @opts\\n";' in body,
            'Report the actual selected tool')
    require(makefile.count(ENVIRONMENT) == 1 and
            re.search(r'^PKGREVISION=\s*8$', makefile, re.M),
            'Forward the quoted Darwin environment and use effective revision 8')


def source_mutations(text, makefile):
    check_source(text, makefile)
    mutations = [
        (text.replace('exists $ENV{' + NAME + '}', '$ENV{' + NAME + '}'), makefile),
        (text.replace('m{\\A/}', 'm{.}'), makefile),
        (text.replace('&& -f $install_name_tool', ''), makefile),
        (text.replace('&& -x $install_name_tool', ''), makefile),
        (text.replace(CALL, '    system "install_name_tool", @opts\n'), makefile),
        (text.replace('push @opts, -id => $libperl;', 'push @opts, -id => $file;'), makefile),
        (text.replace('getcwd . "/libperl.$so", $libperl', '$libperl, $libperl'), makefile),
        (text.replace('and die "Cannot update $file dependency paths\\n";', ';'), makefile),
        (text.replace('or return;', 'or die "wrong platform";'), makefile),
        (text, makefile.replace('${' + NAME + ':Q}', '${' + NAME + '}')),
        (text, makefile.replace('defined(' + NAME + ')', '!empty(' + NAME + ')')),
    ]
    for number, (bad_text, bad_makefile) in enumerate(mutations):
        require((bad_text, bad_makefile) != (text, makefile), 'Inert mutation')
        try:
            check_source(bad_text, bad_makefile)
        except AssertionError:
            continue
        raise AssertionError('Source mutation was accepted: ' + str(number))
    return len(mutations)


def runtime(text, perl, work):
    require(perl.is_absolute() and perl.is_file() and os.access(perl, os.X_OK),
            'Select an absolute executable Perl')
    require(not any(c.isspace() for c in str(perl)),
            'The recording fixture shebang requires a one-word Perl path')
    require(work.is_absolute() and not os.path.lexists(work), 'Use new absolute work')
    work.mkdir(mode=0o700)
    tools = work / 'selected tools'; tools.mkdir()
    path = work / 'path'; path.mkdir()
    selected = tools / 'install-name-tool ; $literal'
    default = path / 'install_name_tool'
    trace = work / 'tool-arguments'
    recorder = ('#!' + str(perl) + '\n'
                'open my $out, ">", $ENV{TEST_TRACE} or die $!;\n'
                'print {$out} join "\\0", $0, @ARGV; close $out or die $!;\n'
                'exit $ENV{TEST_TOOL_EXIT};\n')
    for tool in (selected, default):
        tool.write_text(recorder); tool.chmod(0o700)
    noexec = tools / 'not-executable'; noexec.write_text(recorder)
    badexec = tools / 'broken-interpreter'
    badexec.write_text('#!' + str(tools / 'missing-interpreter') + '\n')
    badexec.chmod(0o700)
    link = tools / 'selected-link'; link.symlink_to(selected)
    body = fragment(text)
    require(body.count('$^O') == 1, 'Expected one platform operand')
    # Only the OS operand is parameterized. Selection, argument construction,
    # filesystem validation, system execution and failure handling are unchanged.
    body = body.replace('$^O', '$fixture_os')
    harness = work / 'fragment.pl'
    harness.write_text('sub getcwd { return $ENV{TEST_CWD}; }\n'
        'my $fixture_os = $ENV{TEST_OS};\n'
        'my %Config = (osvers => $ENV{TEST_OSVERS}, useshrplib => $ENV{TEST_SHARED},\n'
        '    so => "dylib", archlibexp => "/target runtime/lib/perl5");\n'
        'my %opts = (verbose => 1);\n' + body + '\nfix_dep_names($ARGV[0]);\n')
    records = []
    library = '/target runtime/lib/perl5/CORE/libperl.dylib'
    shared = '/stage directory/libperl.dylib'
    program = '/stage directory/perl ; $literal'
    id_args = ['-id', library, shared]
    change_args = ['-change', str(work) + '/libperl.dylib', library, program]

    def run(name, value, file=program, expected=None, error=None, *, status=0,
            platform='darwin', osvers='26.0', shared_library='1', refused=False):
        trace.unlink(missing_ok=True)
        env = dict(PATH=str(path), LC_ALL='C', TZ='UTC', TMPDIR=str(work),
                   TEST_TRACE=str(trace), TEST_TOOL_EXIT=str(status),
                   TEST_OS=platform, TEST_OSVERS=osvers, TEST_SHARED=shared_library,
                   TEST_CWD=str(work))
        if value is not None:
            env[NAME] = value
        argv = [str(perl), str(harness), file]
        result = subprocess.run(argv, cwd=work, env=env, capture_output=True, timeout=30)
        (work / (name + '.stdout')).write_bytes(result.stdout)
        (work / (name + '.stderr')).write_bytes(result.stderr)
        actual = trace.read_bytes().decode().split('\0') if trace.exists() else None
        records.append(dict(case=name, argv=argv, env=env, actual_exit=result.returncode,
                            observed_tool_argv=actual,
                            stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),
                            stderr_sha256=hashlib.sha256(result.stderr).hexdigest()))
        (work / 'commands.json').write_text(json.dumps(records, indent=2) + '\n')
        require(actual == expected, name + ': wrong tool or operands')
        require((result.returncode != 0) == (error is not None), name + ': wrong status')
        if error is not None:
            require(error.encode() in result.stderr, name + ': wrong error')
        else:
            require(result.stderr == b'', name + ': unexpected diagnostic')
        if refused:
            require(result.stdout == b'', name + ': selected tool must fail before dispatch')
        elif expected is not None:
            displayed = value if value is not None else 'install_name_tool'
            require(result.stdout == ('  ' + displayed + ' ' + ' '.join(expected[1:]) + '\n').encode(),
                    name + ': wrong verbose tool or arguments')
        elif error is None:
            require(result.stdout == b'', name + ': inapplicable platform performed work')

    run('selected-id', str(selected), shared, [str(selected), *id_args])
    run('selected-change', str(selected), expected=[str(selected), *change_args])
    run('selected-symlink', str(link), expected=[str(link), *change_args])
    run('unset-id', None, shared, [str(default), *id_args])
    run('unset-change', None, expected=[str(default), *change_args])
    run('selected-failure', str(selected), expected=[str(selected), *change_args],
        error='Cannot update ', status=7)
    run('unset-failure', None, expected=[str(default), *change_args],
        error='Cannot update ', status=7)
    run('selected-exec-failure', str(badexec), error='Cannot update ')
    for name, value in [('empty', ''), ('relative', 'install_name_tool'),
                        ('missing', str(tools / 'missing')), ('directory', str(tools)),
                        ('not-executable', str(noexec))]:
        run(name, value, error=NAME + ' must name an absolute executable file', refused=True)
    run('netbsd-inapplicable', '', platform='netbsd')
    run('old-darwin-inapplicable', '', osvers='14.0')
    run('static-inapplicable', '', shared_library='0')
    return len(records)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--installperl', type=Path, required=True)
    cli.add_argument('--makefile', type=Path, required=True)
    cli.add_argument('--perl', type=Path)
    cli.add_argument('--new-work', type=Path)
    args = cli.parse_args()
    require((args.perl is None) == (args.new_work is None), 'Pair --perl and --new-work')
    text, makefile = args.installperl.read_text(), args.makefile.read_text()
    mutations = source_mutations(text, makefile)
    cases = runtime(text, args.perl, args.new_work) if args.perl is not None else None
    print(json.dumps(dict(status='PASS', source_mutations_rejected=mutations,
        runtime_cases=cases,
        scope='Source checks only' if cases is None else 'Real Perl fragment with recording tools; no Mach-O edit')))


if __name__ == '__main__':
    main()
