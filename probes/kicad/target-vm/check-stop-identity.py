#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Refuse altered identity without touching the guest.
import sys
import subprocess
from vm import OWNER, canonical, entrypoint, owned_identity, parser, sdk


def main():
    args = parser(__doc__, ['work']).parse_args()
    inventory, jsonio, paths, process, identity = sdk(args.sdk_source)
    work = canonical(args.work)
    path = work / 'artifacts/run.json'
    original = path.read_bytes()
    record = jsonio.loads_json(original)
    _, current = owned_identity(work, record, identity)
    if current is None:
        raise ValueError('the recorded guest must be running')
    for label in ['argv0', 'argument', 'start-time']:
        altered = jsonio.loads_json(original)
        if label == 'argv0':
            altered['argv'][0] = '/usr/bin/true'
            altered['qemu_sha256'] = inventory.sha256_file('/usr/bin/true')
        elif label == 'argument':
            altered['argv'][-1] += '-wrong'
        else:
            altered['process_start_time'] = str(int(record['process_start_time']) + 1)
        try:
            jsonio.write_json(str(path), altered, exclusive=False)
            result = subprocess.run([sys.executable, str(OWNER / 'stop.py'), '--sdk-source', str(args.sdk_source), str(work)],
                                    stdin=subprocess.DEVNULL, capture_output=True, timeout=10)
            (work / 'logs' / ('refused-stop-' + label + '.log')).write_bytes(f'exit={result.returncode}\n'.encode() + result.stdout + result.stderr)
            if result.returncode != 1 or b'recorded PID is not the owned QEMU guest' not in result.stdout + result.stderr:
                raise ValueError(f'{label} was not refused before SSH')
        finally:
            path.write_bytes(original)
        _, current = owned_identity(work, record, identity)
        if current is None:
            raise ValueError('the correct guest exited during refusal')
    print('PASS: altered executable, exact argument and birth metadata cannot halt the correct guest')


if __name__ == '__main__':
    entrypoint(main)
