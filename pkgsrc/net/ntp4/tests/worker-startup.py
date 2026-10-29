#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check ordinary deferred worker pipe setup using the actual NTP function."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'compiler', 'linker', 'host-sysroot'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--sanitizers', action='store_true')
a = p.parse_args()
text = (a.source / 'libntp/work_fork.c').read_text()
start = text.index('static void\nfork_blocking_child(\n')
end = text.index('\n\t/*\n\t * The parent gets the child pid', start)
function = text[start:end] + '\n}\n'
prefix = r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define HAVE_DROPROOT 1
#define FALSE 0
#define TRUE 1
#define LOG_ERR 3
#define TRACE(a,b) ((void)0)
#define INSIST(x) do { if (!(x)) abort(); } while (0)
#define fork mock_fork
#define close mock_close
typedef struct { int req_write_pipe, resp_read_pipe, pid, ispipe; } blocking_child;
static int droproot=1, root_dropped=0, selected, callback_pipe=-1;
static FILE *syslog_file;
static int pipe_socketpair(int *p, int *kind) { static int fd=10; p[0]=fd++; p[1]=fd++; *kind=selected; return 0; }
static int move_fd(int fd) { return fd; }
static void send_worker_home_atexit(void) {}
static int mock_fork(void) { return 123; }
static int mock_close(int fd) { (void)fd; return 0; }
static void msyslog(int level, const char *fmt) { (void)level; (void)fmt; }
static size_t netread(int fd, void *out, size_t n) { (void)fd; memset(out, 0, n); return n; }
static void addremove(int fd, int kind, int remove) { (void)fd; (void)remove; callback_pipe=kind; }
static void (*addremove_io_fd)(int,int,int)=addremove;
'''
suffix = r'''
int main(int argc, char **argv) {
    blocking_child child = { .req_write_pipe=-1, .resp_read_pipe=-1, .pid=0, .ispipe=-1 };
    selected = argc > 1 ? atoi(argv[1]) : 0;
    fork_blocking_child(&child);
    if (child.ispipe != selected || child.pid != 0) return 1;
    root_dropped = 1;
    fork_blocking_child(&child);
    return child.pid != 123 || child.ispipe != selected || callback_pipe != selected;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / 'worker.c'
    exe = Path(tmp) / 'worker'
    c.write_text(prefix + function + suffix)
    command = [str(a.compiler), '-isysroot', str(a.host_sysroot), '--ld-path=' + str(a.linker)]
    if a.sanitizers:
        command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    subprocess.run([*command, str(c), '-o', str(exe)], check=True)
    for kind in ('0', '1'):
        subprocess.run([str(exe), kind], check=True)
print('deferred worker preserves pipe type: PASS')
