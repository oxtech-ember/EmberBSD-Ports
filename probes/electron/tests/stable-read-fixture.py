# SPDX-License-Identifier: BSD-2-Clause
"""Inject file replacement after read while keeping the SDK inspector real."""
import os
from pathlib import Path
from unittest.mock import patch
from emberbsd_sdk.errors import SDKError

def race(paths, target, action):
    target = Path(target).resolve(); original = paths.open_regular; fired = []
    class Stream:
        def __init__(self, source): self.source = source
        def __enter__(self): return self
        def __exit__(self, *args): self.source.close()
        def fileno(self): return self.source.fileno()
        def read(self, *args):
            data = self.source.read(*args)
            if not fired:
                fired.append(True)
                replacement = target.with_suffix(target.suffix + '.replacement')
                replacement.write_bytes(data); os.replace(replacement, target)
            return data
    def select(path):
        stream, before = original(path)
        return (Stream(stream), before) if Path(path) == target else (stream, before)
    with patch.object(paths, 'open_regular', side_effect=select):
        try: action()
        except (SDKError, ValueError) as error:
            assert 'changed during' in str(error), str(error)
        else: raise AssertionError('replacement during read accepted')
    assert fired, 'test did not reach selected file'

def age(path):
    stat = path.stat(); os.utime(path, ns=(1_000_000_000, stat.st_mtime_ns))
