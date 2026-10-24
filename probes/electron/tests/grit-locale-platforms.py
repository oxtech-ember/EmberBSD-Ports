"""Run the production locale gather for each supported platform vocabulary."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import traceback

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    source = args.source.absolute()
    sys.path.insert(0, str(source / 'tools/grit'))
    from grit import grd_reader
    from grit.node import base
    assert Path(grd_reader.__file__).absolute().is_relative_to(source)
    # This is the existing NetBSD overlay contract. Locale conditions use it.
    for target in ('netbsd', 'freebsd', 'openbsd', 'netbsd11'):
        assert base.Node.EvaluateExpression('is_linux', {}, target)
    defines = dict(_google_chrome=False, _is_chrome_for_testing_branded=False,
                   reven=False, toolkit_views=True, use_aura=False,
                   use_ozone=False, use_titlecase=True,
                   is_desktop_android=False, scale_factors='2x')
    linux_bsd_fonts = {
        'bn': 'Lohit Bengali',
        'ja': 'VL PGothic,Sazanami Gothic,Kochi Gothic,sans-serif',
        'ko': 'Noto Sans CJK KR,NanumGothic,UnDotum,Baekmuk Gulim,sans-serif',
        'ml': 'Arial,AnjaliOldLipi,Rachana,Kartika,sans-serif',
        'th': 'Norasi,Waree,Garuda,Loma,sans-serif',
        'zh-CN': 'Noto Sans CJK SC, WenQuanYi Zen Hei, sans-serif',
        'zh-TW': 'Noto Sans CJK TC, WenQuanYi Zen Hei, sans-serif',
    }
    grd = source / 'ui/strings/app_locale_settings.grd'
    result = dict(source=str(source), grd_sha256=hashlib.sha256(grd.read_bytes()).hexdigest(),
                  method='Production grd_reader.Parse and GritNode.RunGatherers; validation enabled.',
                  platforms=[])
    for target in ('darwin', 'ios', 'chromeos', 'linux', 'netbsd', 'freebsd',
                   'openbsd', 'netbsd11', 'win32', 'android', 'sunos5', 'fuchsia'):
        row = dict(platform=target)
        try:
            root = grd_reader.Parse(str(grd), defines=defines,
                                    target_platform=target, translate_genders=True)
            root.SetOutputLanguage('en')
            root.SetAllowlistSupportEnabled(True)
            root.RunGatherers()
            if target in ('linux', 'netbsd', 'freebsd', 'openbsd', 'netbsd11'):
                clique = root.UberClique().BestClique('IDS_WEB_FONT_FAMILY')
                selected = {lang: clique.clique[(lang, 'OTHER')].GetPresentableContent()
                            for lang in linux_bsd_fonts}
                assert selected == linux_bsd_fonts
                row['selected_linux_bsd_fonts'] = selected
            row['status'] = 'PASS'
        except Exception as exc:
            row.update(status='FAIL', error_type=type(exc).__name__,
                       error=str(exc), traceback=traceback.format_exc())
        result['platforms'].append(row)
    result['status'] = 'PASS' if all(r['status'] == 'PASS' for r in result['platforms']) else 'FAIL'
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({r['platform']: r['status'] for r in result['platforms']}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
