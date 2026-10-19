#!/usr/bin/env python3
"""Check actual Sway IPC teardown with native sockets and ASan/UBSan."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse
import json
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--baseline', type=Path, required=True)
p.add_argument('--patched', type=Path, required=True)
p.add_argument('--wayland', type=Path, required=True)
p.add_argument('--wayland-include', type=Path, required=True)
p.add_argument('--work', type=Path, required=True)
a = p.parse_args()
assert not a.work.exists()
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


for label, source in [('baseline', a.baseline), ('patched', a.patched)]:
    text = (source / 'sway/ipc-server.c').read_text()
    # Keep the actual client structure, globals, writer and disconnect path.
    declarations = text[text.index('static int ipc_socket'):text.index('static const char ipc_magic')]
    declarations += text[text.index('struct ipc_client {'):text.index('int ipc_handle_connection')]
    chunks = [function(text, signature) for signature in (
        'static void handle_display_destroy(struct wl_listener *listener, void *data)',
        'int ipc_client_handle_writable(int client_fd, uint32_t mask, void *data)',
        'void ipc_client_disconnect(struct ipc_client *client)')]
    header = '''#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <wayland-server-core.h>
#include "ipc.h"
#include "list.h"
#include "log.h"
struct ipc_client;
int ipc_client_handle_writable(int, uint32_t, void *);
void ipc_client_disconnect(struct ipc_client *);
'''
    test = a.work / (label + '.c')
    test.write_text(header + declarations + '\n'.join(chunks) +
                    Path(__file__).with_suffix('.c').read_text())
    binary = a.work / label
    command = ['/usr/bin/cc', '-O1', '-g', '-D_DARWIN_C_SOURCE', '-D_POSIX_C_SOURCE=200809L',
        '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
        '-I' + str(source / 'include'), '-I' + str(a.wayland_include),
        '-I' + str(a.wayland / 'src'), str(test), str(source / 'common/list.c'),
        str(source / 'common/log.c'), str(a.wayland / 'src/wayland-util.c'), '-o', str(binary)]
    result = subprocess.run(command, capture_output=True, text=True)
    (a.work / (label + '-build.log')).write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    for case in ('reply', 'closed', 'blocked'):
        directory = a.work / (label + '-' + case)
        directory.mkdir()
        result = subprocess.run([str(binary), case, str(directory)],
            env={**os.environ, 'ASAN_OPTIONS': 'abort_on_error=1:detect_leaks=0',
                 'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'},
            capture_output=True, text=True, timeout=10)
        record = dict(source=label, case=case, status=result.returncode,
                      stdout=result.stdout, stderr=result.stderr)
        records.append(record)
        (a.work / 'receipt.json').write_text(json.dumps(records, indent=2) + '\n')
        expected = 1 if label == 'baseline' and case == 'reply' else 0
        assert result.returncode == expected, record
        assert 'AddressSanitizer' not in result.stderr and 'runtime error:' not in result.stderr, record
print('PASS: original reply loss reproduced; patched reply/closed/blocked socket teardown passes ASan/UBSan')
