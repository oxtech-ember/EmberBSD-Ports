#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check the common GNU utility source delta. Do not run release scripts."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location('ports_exporter', ROOT / 'scripts/prepare-pkgsrc.py')
EXPORTER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(EXPORTER)
RELEASES = (("devel/diffutils", "diffutils-3.12"),
            ("sysutils/findutils", "findutils-4.11.0"))
GUARD_FROM = 'e) if test "`echo 1 2 3 | xargs -n2 echo`" = "1 2\n3"'
GUARD_TO = ('e) if command -v xargs >/dev/null 2>&1 && '
            'test "`echo 1 2 3 | xargs -n2 echo`" = "1 2\n3"')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def patch_run(patch_tool, patch, work, *options):
    command = [str(patch_tool), "-f", "-F", "0", "-V", "none",
               "-p0", *options, "-i", str(patch)]
    return subprocess.run(command, cwd=work, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, check=False)


def diagnostic_checks(args, work, hook, recipe):
    """Run only the actual diagnostic hook, never configure or a compiler."""
    helper = ROOT / 'profiles/common-build-tools/files/emberbsd-configure-diagnostics.sh'
    (work / helper.name).write_bytes(helper.read_bytes())
    export = (ROOT / 'pkgsrc/export.conf').read_text()
    require(f'file\t{helper.relative_to(ROOT)}\t{recipe}/files/{helper.name}' in export,
            'Export must stage the single common diagnostic owner')
    for tool in (args.shell, args.uname):
        require(tool.is_absolute() and tool.is_file() and os.access(tool, os.X_OK),
                'Select executable SDK shell and uname paths')
    script = 'srcdir=' + shlex.quote(str(work)) + '\n' + hook
    script += 'emberbsd_host_diagnostic "$@"\n'
    env = {'PATH': str(work), 'LC_ALL': 'C',
           'EMBERBSD_CONFIGURE_SDK': 'yes',
           'EMBERBSD_CONFIGURE_UNAME': str(args.uname)}
    def invoke(command, selected):
        return subprocess.run([str(args.shell), '-c', script, 'diagnostic-test', *command],
                              cwd=work, env=selected, capture_output=True)
    expected = subprocess.run([str(args.uname), '-p'], env=env,
                              capture_output=True, check=True)
    actual = invoke(['/usr/bin/uname', '-p'], env)
    require(actual.returncode == 0 and actual.stdout == expected.stdout
            and not actual.stderr, 'Selected uname diagnostic changed')
    for command in (['/bin/uname', '-X'], ['/bin/arch'], ['/usr/bin/arch', '-k'],
                    ['/usr/convex/getsysinfo'], ['/usr/bin/hostinfo'],
                    ['/bin/machine'], ['/usr/bin/oslevel'], ['/bin/universe']):
        result = invoke(command, env)
        require(result.returncode == 1
                and result.stdout == b'unavailable (selected SDK profile)\n'
                and not result.stderr, 'Legacy diagnostic reached a host command')
    for value in (None, 'uname', '/usr/bin/uname', '/bin/uname', str(work / 'absent')):
        bad = dict(env)
        if value is None:
            del bad['EMBERBSD_CONFIGURE_UNAME']
        else:
            bad['EMBERBSD_CONFIGURE_UNAME'] = value
        result = invoke(['/usr/bin/uname', '-p'], bad)
        require(result.returncode != 0 and not result.stdout
                and b'configure:' in result.stderr,
                'Missing or outside selected uname must refuse before diagnostics')
    bad = dict(env, EMBERBSD_CONFIGURE_SDK='no')
    require(invoke(['/usr/bin/uname', '-p'], bad).returncode != 0,
            'An invalid explicit SDK mode must refuse')
    ordinary = {'PATH': str(work), 'LC_ALL': 'C'}
    result = invoke(['echo', 'ordinary diagnostic'], ordinary)
    require(result.returncode == 0 and result.stdout == b'ordinary diagnostic\n',
            'Unset SDK mode must preserve the original diagnostic invocation')
    (work / helper.name).unlink()


def run(args):
    require(args.patch.is_absolute() and args.patch.is_file(),
            "Pass an explicit selected SDK patch for source-data checks")
    require(args.work.is_absolute() and not args.work.exists(),
            "Use a new absolute caller-owned source work directory")
    args.work.mkdir()
    reports = []
    for (recipe, release), archive in zip(RELEASES, args.archives):
        path = ROOT / "pkgsrc" / recipe
        info = (path / "distinfo").read_text()
        require(archive.is_absolute(), "Use an absolute source archive path")
        size = re.search(r"^Size \(" + re.escape(release)
                         + r"\.tar\.xz\) = ([0-9]+) bytes$", info, re.M)
        require(size and archive.stat().st_size == int(size[1]),
                "Archive size differs")
        data = archive.read_bytes()
        for algorithm, constructor in (("BLAKE2s", hashlib.blake2s),
                                       ("SHA512", hashlib.sha512),
                                       ("SHA256", hashlib.sha256)):
            expected = re.search(r"^" + algorithm + r" \(" + re.escape(release)
                                 + r"\.tar\.xz\) = ([0-9a-f]+)$", info, re.M)
            require(expected and constructor(data).hexdigest() == expected[1],
                    f"Archive {algorithm} differs: {release}")
        size = re.search(r"^Size \(" + re.escape(release)
                         + r"\.tar\.xz\) = ([0-9]+) bytes$", info, re.M)
        require(size and len(data) == int(size[1]), "Archive size differs")
        patches = sorted((path / "patches").glob("patch-*"))
        source_files = {"po/LINGUAS"}
        for patch in patches:
            expected = re.search(r"^SHA1 \(" + re.escape(patch.name)
                                 + r"\) = ([0-9a-f]+)$", info, re.M)
            require(expected and EXPORTER.patch_sha1(patch)
                    == expected[1], f"Patch hash differs: {patch.name}")
            old_paths = re.findall(r"^--- (\S+)\.orig$", patch.read_text(), re.M)
            require(len(old_paths) == 1, "Each source patch has one fixed file")
            source_files.update(old_paths)
        source_files.update({"configure", "src/Makefile.in"} if release.startswith(
            "diffutils") else {"gnulib-tests/localename.c"})
        work = args.work / release
        work.mkdir()
        original = {}
        with tarfile.open(archive) as tar:
            for relative in sorted(source_files):
                require(not PurePosixPath(relative).is_absolute()
                        and ".." not in PurePosixPath(relative).parts,
                        "Unsafe source path")
                member = tar.getmember(release + "/" + relative)
                require(member.isfile() and member.size < 4 * 1024 * 1024,
                        "Source member is not a bounded regular file")
                contents = tar.extractfile(member).read()
                original[relative] = contents
                destination = work / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(contents)
        for patch in patches:
            result = patch_run(args.patch, patch, work)
            require(result.returncode == 0, result.stdout.decode(errors="replace"))
            require(b"offset" not in result.stdout and b"fuzz" not in result.stdout,
                    "Source patch needs an exact refreshed hunk")
            reports.append({"patch": str(patch.relative_to(ROOT)),
                            "exit": result.returncode,
                            "output": result.stdout.decode()})
        expected_configure = original["configure"].decode()
        require(expected_configure.count(GUARD_FROM) == 1, "xargs probe changed")
        expected_configure = expected_configure.replace(GUARD_FROM, GUARD_TO)
        if release.startswith("diffutils"):
            expected_configure, count = re.subn(r"(?m)^(\s*(?:if )?)diff ",
                                               r"\1cmp -s ", expected_configure)
            require(count == 6, "Require all six equality checks")
        else:
            require(b"extern char * getlocalename_l(int, locale_t);"
                    not in original["gnulib-tests/localename.c"],
                    "The removed Solaris patch is still needed")
        hook = ('# EmberBSD: use the common selected diagnostic helper in explicit SDK mode.\n'
                'if test "${EMBERBSD_CONFIGURE_SDK+set}" = set; then\n'
                '  . "${srcdir}/emberbsd-configure-diagnostics.sh" || exit 1\n'
                'else\n'
                '  emberbsd_host_diagnostic () { "$@"; }\n'
                'fi\n')
        expected_configure = expected_configure.replace(
            'exec 5>>config.log\n', 'exec 5>>config.log\n' + hook, 1)
        start = expected_configure.index('cat <<_ASUNAME\n')
        end = expected_configure.index('\n_ASUNAME\n', start)
        body = expected_configure[start:end]
        require(body.count('`(/') == 9, 'Require all nine absolute diagnostic probes')
        expected_configure = (expected_configure[:start]
                              + body.replace('`(/', '`(emberbsd_host_diagnostic /')
                              + expected_configure[end:])
        require((work / "configure").read_text() == expected_configure,
                "Configure patch changes more than the finite source delta")
        ac = (work / 'configure.ac').read_text()
        require(hook.replace('$@', '$[]@') in ac
                and '[(/], [(emberbsd_host_diagnostic /]' in ac,
                'Regenerated configure must use the same selected diagnostic hook')
        recipe_text = (path / 'Makefile').read_text()
        require('EMBERBSD_CONFIGURE_UNAME=${EMBERBSD_GCC16_UNAME:Q}' in recipe_text
                and 'EMBERBSD_CONFIGURE_SDK=yes' in recipe_text
                and '${CP} ${FILESDIR}/emberbsd-configure-diagnostics.sh ${WRKSRC}/' in recipe_text,
                'Ordinary recipe must stage the common helper and bind SDK diagnostics')
        diagnostic_checks(args, work, hook, recipe)
        locales = set(original["po/LINGUAS"].decode().split())
        plist = (path / "PLIST").read_text()
        installed = set(re.findall(r"share/locale/([^/]+)/LC_MESSAGES/", plist))
        require(locales == installed, "PLIST must keep all release translations")
        for patch in reversed(patches):
            result = patch_run(args.patch, patch, work, "-R")
            require(result.returncode == 0, "Patch reverse failed")
        require(all((work / k).read_bytes() == v for k, v in original.items()),
                "Source patches do not reverse to the exact release")
    # Causal control: a changed old equality command must reject at zero fuzz.
    source = args.work / "diffutils-3.12"
    configure = source / "configure"
    configure.write_bytes(configure.read_bytes().replace(
        b'diff "conftest.out" "conftest.nl"',
        b'changed_source "conftest.out" "conftest.nl"', 1))
    patch = ROOT / "pkgsrc/devel/diffutils/patches/patch-configure"
    refusal = patch_run(args.patch, patch, source, "-C")
    require(refusal.returncode != 0, "Changed source was silently accepted")
    require("--disable-nls" not in (ROOT / "pkgsrc/sysutils/findutils/Makefile").read_text(),
            "The ordinary findutils recipe must retain NLS")
    require("PKG_SUGGESTED_OPTIONS=\tnls" in
            (ROOT / "pkgsrc/devel/diffutils/options.mk").read_text(),
            "The ordinary diffutils recipe must retain default NLS")
    for name in ("diffutils", "findutils"):
        manifest = json.loads((ROOT / "profiles/common-build-tools/bootstrap"
                               / ("gnu-" + name + ".json")).read_text())
        require(manifest["format"] == "emberbsd-native-bootstrap-program"
                and manifest["version"] == 1 and manifest["initial_only"] is True,
                "The finite manifest must keep the existing initial envelope")
        require(manifest["configure_args"] == ["--disable-nls"],
                "Initial configure arguments changed")
        require(all(c.get("command_role", "sh") == "sh"
                    for c in manifest["runtime_cases"]),
                "Only the fixed selected-shell child binding is defined")
    result = {"status": "SOURCE_CHECKS_PASSED", "patches": reports,
              "changed_source_control": {"exit": refusal.returncode,
                                         "output": refusal.stdout.decode()},
              "configure_or_compiler_executed": False,
              "diagnostic_hook_executed": True}
    (args.work / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PASS: exact reversible patches, release hashes and locales, "
          "six equality checks, two xargs guards, source-change refusal, NLS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diffutils-archive", type=Path, required=True)
    parser.add_argument("--findutils-archive", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--shell", type=Path, required=True)
    parser.add_argument("--uname", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    options = parser.parse_args()
    options.archives = [options.diffutils_archive, options.findutils_archive]
    run(options)
