#!/usr/bin/env python3
"""Execute the real MENVCFG bit helpers with simulated RV32/RV64 CSRs."""
import os
import pathlib
import subprocess
import sys
import tempfile

source = (pathlib.Path(sys.argv[1]) / 'lib/sbi/sbi_fwft.c').read_text()

def function(name):
    start = source.index('static int ' + name + '(')
    opening = source.index('{', start)
    depth = 1
    pos = opening + 1
    while depth:
        if source[pos] == '{':
            depth += 1
        elif source[pos] == '}':
            depth -= 1
        pos += 1
    return source[start:pos]

helpers = function('fwft_menvcfg_set_bit') + '\n' + function('fwft_menvcfg_read_bit')
harness = r'''
#include <assert.h>
#define SBI_OK 0
#define SBI_EINVAL -3
#define CSR_MENVCFG 0
#define CSR_MENVCFGH 1
#define _UL(x) x##UL
static unsigned long csr[2];
#define csr_set(reg, bits) (csr[reg] |= (bits))
#define csr_clear(reg, bits) (csr[reg] &= ~(bits))
#define csr_read(reg) (csr[reg])
''' + helpers + r'''
int main(void) {
  unsigned long got;
  const unsigned bits[] = {0, 31, 32, 63};
  for (unsigned i = 0; i < sizeof(bits)/sizeof(bits[0]); i++) {
    unsigned bit = bits[i];
    unsigned which = __riscv_xlen == 32 && bit >= 32;
    unsigned shift = which ? bit - 32 : bit;
    csr[0] = csr[1] = 0;
    assert(fwft_menvcfg_set_bit(1, bit) == SBI_OK);
    assert(csr[which] == (1UL << shift));
    assert(fwft_menvcfg_read_bit(&got, bit) == SBI_OK && got == 1);
    assert(fwft_menvcfg_set_bit(0, bit) == SBI_OK && csr[which] == 0);
    assert(fwft_menvcfg_read_bit(&got, bit) == SBI_OK && got == 0);
  }
  csr[0] = csr[1] = 42;
  assert(fwft_menvcfg_set_bit(1, 64) == SBI_EINVAL);
  assert(fwft_menvcfg_read_bit(&got, 64) == SBI_EINVAL);
  assert(fwft_menvcfg_set_bit(2, 0) == SBI_EINVAL);
  assert(csr[0] == 42 && csr[1] == 42);
  return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='opensbi-fwft-') as tmp:
    guard = '\tif (bit >= 64)\n\t\treturn SBI_EINVAL;\n'
    if harness.count(guard) != 2:
        raise RuntimeError('FWFT bounds guards no longer match the fault control')
    for name, body in (('real', harness), ('fault', harness.replace(guard, ''))):
        c = pathlib.Path(tmp) / (name + '.c')
        c.write_text(body)
        for xlen in ('32', '64'):
            executable = pathlib.Path(tmp) / (name + xlen)
            subprocess.run([os.environ['CC'], '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-D__riscv_xlen=' + xlen, str(c), '-o', str(executable)], check=True)
            result = subprocess.run([str(executable)], stderr=subprocess.DEVNULL)
            if (result.returncode == 0) != (name == 'real'):
                raise RuntimeError(name + ' FWFT check produced unexpected result')
print('FWFT RV32/RV64 CSR selection and bounds passed; missing-guard fault detected')
