#!/usr/bin/env python3
"""Execute the production CLIC implementation against a small fake MMIO bank."""
import os
import pathlib
import subprocess
import sys
import tempfile

source = pathlib.Path(sys.argv[1]).resolve()
cc = pathlib.Path(os.environ['CC']).resolve()
test = pathlib.Path(__file__).with_name('clic.c').resolve()
common = r'''
#include <stdint.h>
typedef uint8_t u8;
typedef uint32_t u32;
struct fdt_match { const char *compatible; const void *data; };
struct hartmask { unsigned long bits; };
struct sbi_irqchip_device { unsigned id, num_hwirq; struct hartmask target_harts;
  int (*warm_init)(struct sbi_irqchip_device *); };
struct fdt_driver { const struct fdt_match *match_table;
  int (*init)(const void *, int, const struct fdt_match *); };
#define SBI_EINVAL -3
#define SBI_ENOTSUPP -2
#define sbi_for_each_hartindex(i) for (u32 i = 0; i < 2; i++)
static inline void sbi_hartmask_set_hartindex(u32 i, struct hartmask *m)
{ m->bits |= 1UL << i; }
u32 readl(const void *p);
void writel(u32 v, void *p);
u8 readb(const void *p);
void writeb(u8 v, void *p);
int fdt_get_node_addr_size(const void *, int, int, uint64_t *, uint64_t *);
int sbi_irqchip_add_device(struct sbi_irqchip_device *);
'''
with tempfile.TemporaryDirectory(prefix='opensbi-clic-') as tmp:
    base = pathlib.Path(tmp)
    (base / 'common.h').write_text('#pragma once\n' + common)
    for header in ('sbi/riscv_io.h', 'sbi/sbi_error.h', 'sbi/sbi_irqchip.h',
                   'sbi/sbi_scratch.h', 'sbi/sbi_types.h',
                   'sbi_utils/fdt/fdt_helper.h', 'sbi_utils/irqchip/fdt_irqchip.h'):
        path = base / header
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#include <common.h>\n')
    actual = source / 'lib/utils/irqchip/fdt_irqchip_clic.c'
    original = actual.read_text()
    needle = 'return sbi_irqchip_add_device(&clic_device);'
    if original.count(needle) != 1:
        raise RuntimeError('CLIC registration no longer matches this fault control')
    faulty = base / 'faulty.c'
    faulty.write_text(original.replace(needle, '(void)sbi_irqchip_add_device(&clic_device); return 0;'))
    for label, candidate in (('real', actual), ('fault', faulty)):
        output = base / ('clic-check-' + label)
        subprocess.run([str(cc), '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', '-I' + str(base),
                        '-I' + str(source / 'include'),
                        '-DSOURCE_FILE="' + str(candidate) + '"',
                        str(test), '-o', str(output)], check=True)
        result = subprocess.run([str(output)], stderr=subprocess.DEVNULL)
        if (result.returncode == 0) != (label == 'real'):
            raise RuntimeError(label + ' CLIC check produced unexpected result')
print('S31 CLIC registration, error propagation and source routing passed; fault detected')
