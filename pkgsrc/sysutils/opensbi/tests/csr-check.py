#!/usr/bin/env python3
"""Exercise counter 31 in the real CSR dispatch macro under UBSan."""
import os
import pathlib
import subprocess
import sys
import tempfile

source = (pathlib.Path(sys.argv[1]) / 'lib/sbi/sbi_emulate_csr.c').read_text()
start = source.index('#define switchcase_hpm(')
end = source.index('#define switchcase_hpm_2(', start)
macro = source[start:end]
if macro.count('1U << (__csr - __uref)') != 1:
    raise RuntimeError('CSR counter mask no longer matches this regression')
hart = (pathlib.Path(sys.argv[1]) / 'lib/sbi/sbi_hart.c').read_text()
start = hart.index('#define __check_hpm_csr(')
end = hart.index('#define __check_hpm_csr_2(', start)
probe_macro = hart[start:end]
if probe_macro.count('1U << (__csr - CSR_MCYCLE)') != 1:
    raise RuntimeError('CSR probe mask no longer matches this regression')
prefix = r'''
#include <assert.h>
#define SBI_ENOTSUPP -2
static unsigned int mask;
static unsigned int sbi_hart_mhpm_mask(void *scratch) { (void)scratch; return mask; }
static int hpm_allowed(int c, int p, int v) { (void)c; (void)p; (void)v; return 1; }
#define csr_read(n) (n)
#define CSR_MCYCLE 0
#define csr_read_allowed(n, t) ((void)(n), (void)(t), 0UL)
#define csr_write_allowed(n, t, v) ((void)(n), (void)(t), (void)(v))
#define csr_swap(n, v) ((void)(n), (void)(v), 1UL)
'''
suffix = r'''
static unsigned int probe(void) {
    struct { unsigned int mask; } features = {0}, *hfeatures = &features;
    struct { int cause; } trap = {0};
    unsigned long oldval;
    __check_hpm_csr(31, mask)
    return features.mask;
}
static int dispatch(int csr_num) {
    void *scratch = 0;
    int prev_mode = 0, virt = 0, csr_val_store = 0, *csr_val = &csr_val_store;
    switch (csr_num) {
        switchcase_hpm(0, 100, 31)
    }
    return csr_val_store;
}
int main(void) {
    assert(probe() == 0x80000000U);
    mask = 0;
    assert(dispatch(31) == 131);
    mask = 0x80000000U;
    assert(dispatch(31) == SBI_ENOTSUPP);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='opensbi-csr-') as tmp:
    cases = (('real', macro + probe_macro),
             ('dispatch_fault', macro.replace('1U <<', '1 <<') + probe_macro),
             ('probe_fault', macro + probe_macro.replace('1U <<', '1 <<')))
    for name, code in cases:
        c = pathlib.Path(tmp) / (name + '.c')
        exe = pathlib.Path(tmp) / name
        c.write_text(prefix + code + suffix)
        subprocess.run([os.environ['CC'], '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=undefined', '-fno-sanitize-recover=all',
                        str(c), '-o', str(exe)], check=True)
        result = subprocess.run([str(exe)], stderr=subprocess.DEVNULL)
        if (result.returncode == 0) != (name == 'real'):
            raise SystemExit(name + ' counter 31 regression failed')
print('CSR counter 31 regression and signed-shift fault control passed')
