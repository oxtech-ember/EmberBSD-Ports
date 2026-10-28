#!/usr/bin/env python3
"""Exercise Waf's actual cached-answer execution from a prepared TDB source."""
import importlib.util
import pathlib
import subprocess
import sys
import tempfile

source = pathlib.Path(sys.argv[1]).resolve()
sys.path[:0] = [str(source / 'third_party/waf'), str(source / 'buildtools')]
spec = importlib.util.spec_from_file_location(
    'samba_cross_test', source / 'buildtools/wafsamba/samba_cross.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
commands = []
class SelectedPopen:
    def __init__(process, args, **kwargs):
        commands.append(args)
        subprocess.Popen.__init__(process, args, **kwargs)
module.real_Popen = SelectedPopen

with tempfile.TemporaryDirectory() as directory:
    answers = pathlib.Path(directory) / 'answers'
    answers.write_text('ok: OK\nno: NO\ntext: "NetBSD evbarm"\n')
    for name, status, expected in [('ok', 0, b''), ('no', 1, b''),
                                   ('text', 0, b'NetBSD evbarm')]:
        process = module.cross_Popen(['unused', '--cross-answers', str(answers), name],
                                     stdout=subprocess.PIPE)
        output, _ = process.communicate()
        assert (process.returncode, output) == (status, expected), name
    process = module.cross_Popen(['unused', '--cross-answers', str(answers), 'missing'],
                                 stdout=subprocess.PIPE)
    process.communicate()
    assert process.returncode == 254
    assert all(command[0] == sys.executable for command in commands)
    assert module.cross_answers_incomplete
    assert 'missing: UNKNOWN' in answers.read_text()
print('cached cross-answer routing: PASS')
