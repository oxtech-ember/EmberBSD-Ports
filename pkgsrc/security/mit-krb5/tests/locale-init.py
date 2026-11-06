#!/usr/bin/env python3
"""Exercise actual NLS initializer and a synthetic translation, without a full NLS build."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

p = argparse.ArgumentParser()
for flag in ('source', 'baseline', 'cc', 'msgfmt', 'intl', 'support', 'work'):
    p.add_argument('--' + flag, required=True, type=Path)
p.add_argument('--configured-locale-dir', required=True, type=Path)
p.add_argument('--locale', required=True, help='installed native locale, e.g. de_DE.UTF-8')
p.add_argument('--tool-bin', type=Path, action='append', required=True)
a = p.parse_args()
if sys.platform != 'darwin':
    p.error('this fixture uses the Darwin dynamic loader')
if any(not x.is_absolute() for x in (a.source, a.baseline, a.cc, a.msgfmt,
                                    a.intl, a.support, a.work, a.configured_locale_dir, *a.tool_bin)):
    p.error('all paths must be absolute and SDK tools explicitly selected')
if not all(x.is_file() for x in (a.source, a.baseline, a.cc, a.msgfmt, a.intl, a.support)):
    p.error('source, baseline, selected tools and libraries must exist')
if any(not x.is_dir() for x in a.tool_bin):
    p.error('tool-bin must name existing selected SDK tool directories')
if not a.locale or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.@-' for c in a.locale):
    p.error('invalid locale')
root = a.work
if root.exists() and any(root.iterdir()):
    p.error('work directory must be empty')
lib = root / 'prefix/lib'
lib.mkdir(parents=True, exist_ok=True)
shutil.copyfile(a.support, lib / a.support.name)
catalog = root / 'prefix/share/locale' / a.locale.split('.')[0] / 'LC_MESSAGES/mit-krb5.mo'
catalog.parent.mkdir(parents=True)
po = root / 'fixture.po'
po.write_text('msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n\nmsgid "ember-locale-fixture-unique"\nmsgstr "ember-verschoben"\n')
env = dict(os.environ)
env['PATH'] = os.pathsep.join(str(x) for x in a.tool_bin)
env['LC_ALL'] = a.locale
env['DYLD_LIBRARY_PATH'] = str(lib)
def run(cmd):
    return subprocess.run([str(x) for x in cmd], env=env, text=True, capture_output=True,
                          check=True, timeout=60).stdout
run([a.msgfmt, po, '-o', catalog])
header = r'''#include <stdio.h>
#include <stdlib.h>
#include <locale.h>
#define LEAN_CLIENT 1
#define ENABLE_NLS 1
#define KRB5_TEXTDOMAIN "mit-krb5"
extern char *bindtextdomain(const char *, const char *);
extern char *dgettext(const char *, const char *);
extern int k5_relocate_default(const char *, char **);
static int error_message, et_krb5_error_table, et_k5e1_error_table, et_kv5m_error_table, et_kdb5_error_table, et_asn1_error_table, et_k524_error_table, krb5int_us_time_mutex;
static void k5_set_error_info_callout_fn(int x){(void)x;}
static void add_error_table(int *x){(void)x;}
static int krb5int_cc_initialize(void){return 0;}
static int k5_mutex_finish_init(int *p){(void)p;return 0;}
'''
footer = r'''int main(void) {
 if (!setlocale(LC_ALL, "")) return 2;
 if (krb5int_lib_init()) return 3;
 printf("%s\n%s\n", bindtextdomain(KRB5_TEXTDOMAIN, NULL),
        dgettext(KRB5_TEXTDOMAIN, "ember-locale-fixture-unique"));
 return 0;
}
'''
def run_init(name, source, location):
    text = source.read_text()
    start = text.index('int krb5int_lib_init(void)\n{')
    end = text.index('\n/* Always-delayed', start)
    code = root / (name + '.c')
    code.write_text(header + text[start:end] + '\n' + footer)
    exe = root / name
    run([a.cc, '-DLOCALEDIR="' + str(location) + '"', code, a.support,
         a.intl, '-Wl,-rpath,' + str(a.intl.parent), '-o', exe])
    return run([exe]).splitlines()
old = run_init('old', a.baseline, a.configured_locale_dir)
expected_old = [str(a.configured_locale_dir), 'ember-locale-fixture-unique']
if old != expected_old:
    raise SystemExit('old initializer mismatch: %r' % old)
new = run_init('new', a.source, a.configured_locale_dir)
expected_new = [str(root / 'prefix/share/locale'), 'ember-verschoben']
if new != expected_new:
    raise SystemExit('new initializer mismatch: %r' % new)
external = Path('/opt/ember-locale-fixture-external')
if run_init('external', a.source, external)[0] != str(external):
    raise SystemExit('external locale directory was changed')
print('PASS: old binding stale, translated moved default, external path unchanged')
