#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
"""Check OpenSBI counter scaling, FDT fallback, and the old NULL failure."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def function(path, signature):
    text = path.read_text()
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'missing production function: {signature}')
    brace = text.find('{', start)
    depth = 0
    for end in range(brace, len(text)):
        if text[end] == '{':
            depth += 1
        elif text[end] == '}':
            depth -= 1
            if depth == 0:
                return text[start:end + 1]
    raise SystemExit(f'unterminated production function: {signature}')


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path,
                    help='patched OpenSBI 1.9 source directory')
parser.add_argument('base', type=Path,
                    help='unpatched OpenSBI 1.9 source/archive directory')
parser.add_argument('--static-analysis', action='store_true',
                    help='run Cppcheck and Clang Static Analyzer on the host harness')
args = parser.parse_args()
source = args.source.resolve(strict=True)
base = args.base.resolve(strict=True)
current_timer = source / 'lib/sbi/sbi_timer.c'
base_timer = base / 'lib/sbi/sbi_timer.c'
current_fdt_timer = source / 'lib/utils/timer/fdt_timer.c'

current_functions = '\n\n'.join(function(current_timer, signature) for signature in (
    'u64 sbi_timer_compute_delta(',
    'void sbi_timer_delay_loop(',
    'bool sbi_timer_waitms_until(',
    'u64 sbi_timer_value(',
    'const struct sbi_timer_device *sbi_timer_get_device(',
    'unsigned long sbi_timer_get_frequency(',
    'int sbi_timer_set_frequency(',
    'void sbi_timer_set_device(',
))
fdt_function = function(current_fdt_timer, 'int fdt_timer_init(')
baseline_function = function(base_timer, 'u64 sbi_timer_compute_delta(')

prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

typedef uint64_t u64;
typedef unsigned long ulong;
#define SBI_EINVAL (-3)
#define SBI_ENOENT (-2)
#define SBI_HART_CSR_TIME 1

struct sbi_timer_device {
    char name[32];
    unsigned long timer_freq;
    u64 (*timer_value)(void);
    void (*timer_event_start)(u64);
    void (*timer_event_stop)(void);
    int (*warm_init)(void);
};
struct sbi_scratch { int unused; };
struct fdt_driver { int unused; };

static unsigned long timer_freq;
static u64 (*get_time_val)(void);
static const struct sbi_timer_device *timer_dev;
static int printf_calls;
static void sbi_printf(const char *fmt, ...) { (void)fmt; printf_calls++; }
static void cpu_relax(void) {}
static void nop_delay_fn(void *opaque) { (void)opaque; cpu_relax(); }

static const struct sbi_timer_device *sbi_timer_get_device(void);
static unsigned long sbi_timer_get_frequency(void);
static int sbi_timer_set_frequency(unsigned long);
static void sbi_timer_set_device(const struct sbi_timer_device *);
static u64 sbi_timer_value(void);

static const struct fdt_driver *const fdt_timer_drivers[] = { NULL };
static int csr_time_available;
static int driver_init_result;
static int parse_frequency_result;
static unsigned long parse_frequency_value;
static const struct sbi_timer_device *device_from_fdt;
static int parse_frequency_calls;
static struct sbi_scratch scratch;

static struct sbi_scratch *sbi_scratch_thishart_ptr(void) { return &scratch; }
static bool sbi_hart_has_csr(struct sbi_scratch *s, int csr)
{
    (void)s; (void)csr; return csr_time_available != 0;
}
static const void *fdt_get_address(void) { return &scratch; }
static int fdt_driver_init_all(const void *fdt,
    const struct fdt_driver *const *drivers)
{
    (void)fdt; (void)drivers;
    if (driver_init_result)
        return driver_init_result;
    if (device_from_fdt)
        sbi_timer_set_device(device_from_fdt);
    return 0;
}
static int fdt_parse_timebase_frequency(const void *fdt, unsigned long *freq)
{
    (void)fdt; parse_frequency_calls++;
    if (parse_frequency_result)
        return parse_frequency_result;
    *freq = parse_frequency_value;
    return 0;
}
'''

checks = r'''
static u64 counter_value;
static u64 read_counter(void) { return ++counter_value; }
static bool false_predicate(void *arg) { (void)arg; return false; }
static bool true_predicate(void *arg) { (void)arg; return true; }

int main(void)
{
    struct sbi_timer_device device = { .timer_freq = 1000000,
                                       .timer_value = read_counter };
    int rc;

    /* CSR-only counter: no machine-mode event device is registered. */
    timer_dev = NULL;
    timer_freq = 0;
    get_time_val = read_counter;
    rc = sbi_timer_set_frequency(320000000);
    assert(rc == 0);
    assert(sbi_timer_get_device() == NULL);
    assert(sbi_timer_get_frequency() == 320000000);
    assert(sbi_timer_compute_delta(100, 1000) == 32000000);

    /* A rejected zero must preserve the last valid frequency. */
    rc = sbi_timer_set_frequency(0);
    assert(rc == SBI_EINVAL);
    assert(sbi_timer_get_frequency() == 320000000);

    /* Existing MMIO event-device registration still supplies its frequency. */
    timer_dev = NULL;
    timer_freq = 0;
    get_time_val = NULL;
    sbi_timer_set_device(&device);
    assert(sbi_timer_get_device() == &device);
    assert(sbi_timer_get_frequency() == 1000000);
    assert(sbi_timer_value() != 0);

    /* Missing readable counter is safe for wait/delay helpers. */
    timer_dev = NULL;
    timer_freq = 320000000;
    get_time_val = NULL;
    assert(!sbi_timer_waitms_until(false_predicate, NULL, 1));
    assert(sbi_timer_waitms_until(true_predicate, NULL, 1));
    sbi_timer_delay_loop(1, 1000, NULL, NULL);
    assert(printf_calls == 1);

    /* FDT timer device keeps the normal backend and bypasses CSR fallback. */
    timer_dev = NULL; timer_freq = 0; get_time_val = read_counter;
    device_from_fdt = &device; driver_init_result = 0;
    csr_time_available = 1; parse_frequency_calls = 0;
    assert(fdt_timer_init() == 0);
    assert(sbi_timer_get_device() == &device);
    assert(sbi_timer_get_frequency() == 1000000);
    assert(parse_frequency_calls == 0);

    /* CSR-only FDT fallback installs the shared counter frequency. */
    timer_dev = NULL; timer_freq = 0; device_from_fdt = NULL;
    csr_time_available = 1; parse_frequency_calls = 0;
    parse_frequency_result = 0; parse_frequency_value = 320000000;
    assert(fdt_timer_init() == 0);
    assert(sbi_timer_get_device() == NULL);
    assert(sbi_timer_get_frequency() == 320000000);
    assert(parse_frequency_calls == 1);

    /* Missing FDT frequency is returned; zero frequency is rejected. */
    timer_freq = 0; parse_frequency_calls = 0;
    parse_frequency_result = SBI_ENOENT;
    assert(fdt_timer_init() == SBI_ENOENT);
    assert(sbi_timer_get_frequency() == 0);
    parse_frequency_result = 0; parse_frequency_value = 0;
    assert(fdt_timer_init() == SBI_EINVAL);
    assert(sbi_timer_get_frequency() == 0);

    /* No event device and no TIME CSR needs no FDT frequency. */
    csr_time_available = 0; parse_frequency_calls = 0;
    assert(fdt_timer_init() == 0);
    assert(parse_frequency_calls == 0);
    return 0;
}
'''

baseline_harness = r'''
#include <stdint.h>
typedef uint64_t u64;
typedef unsigned long ulong;
struct sbi_timer_device { unsigned long timer_freq; };
static const struct sbi_timer_device *timer_dev;
''' + baseline_function + r'''
int main(void) { timer_dev = 0; return sbi_timer_compute_delta(100, 1000) != 0; }
'''

current_harness = prefix + current_functions + '\n\n' + fdt_function + checks
cc = os.environ.get('CC')
if not cc:
    raise SystemExit('set CC to the selected native Clang compiler')
common_flags = ['-std=gnu11', '-Wall', '-Wextra', '-Werror',
                '-fsanitize=address,undefined', '-fno-sanitize-recover=all']

with tempfile.TemporaryDirectory(prefix='opensbi-timer-') as temporary:
    tmp = Path(temporary)
    baseline_c, baseline_bin = tmp / 'baseline.c', tmp / 'baseline'
    current_c, current_bin = tmp / 'current.c', tmp / 'current'
    baseline_c.write_text(baseline_harness)
    current_c.write_text(current_harness)
    subprocess.run([cc, *common_flags, str(baseline_c), '-o', str(baseline_bin)],
                   check=True)
    red = subprocess.run([str(baseline_bin)], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    diagnostic = red.stderr.decode(errors='replace').lower()
    if red.returncode == 0 or not any(token in diagnostic for token in
                                      ('null pointer', 'runtime error', 'segv')):
        raise SystemExit('baseline failed to reproduce the old NULL timer_dev dereference')
    subprocess.run([cc, *common_flags, str(current_c), '-o', str(current_bin)],
                   check=True)
    subprocess.run([str(current_bin)], check=True)
    if args.static_analysis:
        cppcheck = os.environ.get('CPPCHECK')
        analyzer = os.environ.get('CLANG_ANALYZER')
        if not cppcheck or not analyzer:
            raise SystemExit('set CPPCHECK and CLANG_ANALYZER for --static-analysis')
        subprocess.run([cppcheck, '--enable=warning,performance,portability',
                        '--error-exitcode=1', '--std=c11', str(current_c)], check=True)
        subprocess.run([analyzer, '--analyze', '-std=gnu11', str(current_c)], check=True)

print('baseline NULL dereference reproduced; current timer/FDT cases passed')
