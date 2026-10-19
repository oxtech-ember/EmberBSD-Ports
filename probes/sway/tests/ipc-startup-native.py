#!/usr/bin/env python3
"""Fault-test actual Sway IPC startup and rollback with native sockets."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse
import json
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ['baseline', 'patched', 'wayland', 'wayland-include', 'work']:
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
assert all(x.is_absolute() for x in vars(a).values()) and not a.work.exists()
a.work.mkdir(parents=True)
records = []

def function(text, signature):
    start = text.index(signature + ' {')
    brace = text.index('{', start)
    end, depth = brace + 1, 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end] + '\n'

fixture = Path(__file__).with_suffix('.c').read_text()
prefix, body = fixture.split('/* ACTUAL SOURCE */\n')
for label, source in [('baseline', a.baseline), ('patched', a.patched)]:
    text = (source / 'sway/ipc-server.c').read_text()
    main = (source / 'sway/main.c').read_text()
    boolean = 'bool ipc_init(' in text
    declarations = text[text.index('static int ipc_socket'):text.index('static const char ipc_magic')]
    declarations += text[text.index('struct ipc_client {'):text.index('int ipc_handle_connection')]
    chunks = [function(text, signature) for signature in (
        'static bool ipc_has_event_listeners(enum ipc_command_type event)',
        'static void handle_display_destroy(struct wl_listener *listener, void *data)',
        ('bool' if boolean else 'void') + ' ipc_init(struct sway_server *server)',
        'struct sockaddr_un *ipc_user_sockaddr(void)',
        'int ipc_client_handle_writable(int client_fd, uint32_t mask, void *data)',
        'void ipc_client_disconnect(struct ipc_client *client)')]
    chunks += [function(main, 'void sway_terminate(int exit_code)')]
    generated = a.work / (label + '.c')
    generated.write_text(('#define TEST_BOOL_INIT 1\n' if boolean else '') + prefix +
        declarations + '#define malloc test_malloc\n#define free test_free\n' +
        '#define setenv test_setenv\n#define bind test_bind\n#define listen test_listen\n' +
        (source / 'common/list.c').read_text() + '\n'.join(chunks) +
        '#undef malloc\n#undef free\n#undef setenv\n#undef bind\n#undef listen\n' + body)
    binary = a.work / label
    command = ['/usr/bin/cc', '-std=c11', '-O1', '-g', '-D_DARWIN_C_SOURCE',
        '-D_POSIX_C_SOURCE=200809L', '-Wall', '-Wextra', '-Werror',
        '-Wno-unused-parameter', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
        '-I' + str(source / 'include'), '-I' + str(a.wayland_include),
        '-I' + str(a.wayland / 'src'), str(generated), str(source / 'common/log.c'),
        str(a.wayland / 'src/wayland-util.c'), '-o', str(binary)]
    built = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (a.work / (label + '-build.log')).write_text(built.stdout + built.stderr)
    assert built.returncode == 0, built.stderr
    for case in ['success', 'before', 'after', 'alloc1', 'alloc2', 'alloc3',
                 'event', 'env1', 'env2', 'path', 'bind', 'listen']:
        directory = a.work / (label + '-' + case)
        directory.mkdir()
        result = subprocess.run([str(binary), case, str(directory)],
            env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0:abort_on_error=1',
                 'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'},
            capture_output=True, text=True, timeout=10)
        records.append(dict(source=label, case=case, status=result.returncode,
                            stdout=result.stdout, stderr=result.stderr))
        (a.work / 'receipt.json').write_text(json.dumps(records, indent=2) + '\n')
        assert (result.returncode == 0) == (label == 'patched' or case == 'success'), records[-1]
        if label == 'patched':
            assert 'AddressSanitizer' not in result.stderr and 'runtime error:' not in result.stderr
print('PASS: 11 original lifecycle failures; 12 patched startup/rollback/teardown cases under ASan/UBSan')
