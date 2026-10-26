"""Check the real Node GYP deployment setting without external commands."""
import argparse
import ast
import os
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True,
                        help='The prepared Node source tree')
    parser.add_argument('--case', choices=('default', 'selected'), required=True,
                        help='Check the upstream default or the explicit minimum')
    args = parser.parse_args()
    source = args.source.resolve()
    selection, expected = {'default': ('unset', '13.5'),
                           'selected': ('26.0', '26.0')}[args.case]
    source_bytes = (source / 'common.gypi').read_bytes()
    sys.path.insert(0, str(source / 'tools/gyp/pylib'))
    external_commands = []

    def no_child(event, arguments):
        if event in ('subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.fork'):
            external_commands.append(event)
            raise RuntimeError('External discovery is not allowed: ' + event)

    sys.addaudithook(no_child)
    import gyp

    previous_cwd = Path.cwd()
    previous_env = {key: value for key, value in os.environ.items()
                    if key.startswith('GYP_')}
    for key in previous_env:
        os.environ.pop(key)
    with tempfile.TemporaryDirectory(prefix='node-darwin-deployment-') as tmp:
        work = Path(tmp)
        try:
            (work / 'common.gypi').write_bytes(source_bytes)
            (work / 'probe.gyp').write_text("{'includes': ['common.gypi'], 'targets': [{'target_name': 'deployment_probe', 'type': 'none'}]}\n")
            os.chdir(work)
            argv = ['-f', 'gypd', '--no-parallel', '--depth=.', '-DOS=mac',
                    '-Dtarget_arch=arm64', '-Dhost_arch=arm64', '-Denable_lto=false']
            if selection != 'unset':
                argv.append('-Dmac_deployment_target=' + selection)
            argv.append('probe.gyp')
            code = gyp.main(argv)
            settings = []
            if code == 0:
                output = ast.literal_eval((work / 'probe.gypd').read_text())
                settings = [config['xcode_settings']['MACOSX_DEPLOYMENT_TARGET']
                            for target in output['targets']
                            for config in target['configurations'].values()]
            passed = code == 0 and settings == [expected, expected] and not external_commands
            print(f'{args.case}: GYP exit {code}, expected {expected}, actual {settings}', flush=True)
            return 0 if passed else 1
        finally:
            os.chdir(previous_cwd)
            os.environ.update(previous_env)


if __name__ == '__main__':
    raise SystemExit(main())
