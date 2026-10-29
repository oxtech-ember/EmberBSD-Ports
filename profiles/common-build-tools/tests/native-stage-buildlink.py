#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise native stage buildlink selection with a disposable package DB."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', required=True)
    parser.add_argument('--pkgsrc-root', type=Path, required=True)
    parser.add_argument('--native-makeconf', required=True)
    parser.add_argument('--cross-makeconf', required=True)
    parser.add_argument('--initial-mk', required=True)
    args = parser.parse_args()
    package = args.pkgsrc_root/'devel/ada-idna'
    with tempfile.TemporaryDirectory(prefix='ember-stage-routing-') as tmp:
        base = Path(tmp).resolve()
        host = base/'host'; host.mkdir()
        stage = base/'stage'; stage.mkdir()
        staged = stage/str(host).lstrip('/')
        db = staged/'pkgdb'; db.mkdir(parents=True)
        (staged/'nested').mkdir()
        outside = base/'outside'; outside.mkdir()
        (staged/'escape').symlink_to(outside, target_is_directory=True)
        entry = db/'simdutf-9.3.3nb1'; entry.mkdir()
        (entry/'+CONTENTS').write_text('@name simdutf-9.3.3nb1\n')
        info = entry/'+BUILD_INFO'
        common = [args.bmake, '-m', args.initial_mk, '-C', str(package),
                  'MAKECONF='+args.native_makeconf, 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
                  '_PKGSRC_BARRIER=yes', 'PKG_DBDIR='+str(db),
                  'EMBERBSD_NATIVE_STAGE_ROOT='+str(stage),
                  'EMBERBSD_NATIVE_STAGE_PREFIX='+str(host)]
        def query(logical, *extra):
            info.write_text('LOCALBASE='+str(logical)+'\n')
            result = subprocess.run(common+list(extra)+[
                '-V', '${BUILDLINK_PREFIX.simdutf}', '-V', '${PKG_FAIL_REASON}',
                '-V', '${_BLNK_PKG_DBDIR.simdutf}'], check=True,
                text=True, capture_output=True)
            return result.stdout.splitlines()
        for logical, expected in ((host, staged), (host/'nested', staged/'nested'),
                                  (Path('/usr'), Path('/usr')),
                                  (Path(str(host)+'-other'), Path(str(host)+'-other'))):
            prefix, failure, selected = query(logical)
            assert prefix == str(expected) and not failure, (prefix, failure)
            assert Path(selected).parent == db, selected
        prefix, failure, _ = query(host, 'BUILDLINK_PREFIX.simdutf=/explicit/override')
        assert prefix == '/explicit/override' and not failure
        prefix, failure, _ = query(host, 'USE_BUILTIN.simdutf=yes')
        assert prefix.endswith('/usr') and str(stage) not in prefix and not failure
        _, failure, _ = query(host/'missing')
        assert 'missing or escapes the selected stage' in failure
        _, failure, _ = query(host/'escape')
        assert 'escapes the selected stage' in failure
        result = subprocess.run(common+['_cbbh'], text=True, capture_output=True)
        assert result.returncode and 'escapes the selected stage' in result.stderr + result.stdout
        cross = [args.bmake, '-m', args.initial_mk, '-C', str(package),
                 'MAKECONF='+args.cross_makeconf, '_PKGSRC_BARRIER=yes']
        def cross_prefix(extra):
            return subprocess.run(cross+extra+['-V', '${BUILDLINK_PREFIX.simdutf}'],
                                  check=True, text=True, capture_output=True).stdout
        assert cross_prefix([]) == cross_prefix(['EMBERBSD_NATIVE_STAGE_ROOT='+str(stage),
                                                 'EMBERBSD_NATIVE_STAGE_PREFIX='+str(host)])
    print('native stage, prefix boundaries, override, builtin and cross: PASS')


if __name__ == '__main__':
    main()
