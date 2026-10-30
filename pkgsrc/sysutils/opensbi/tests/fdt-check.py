#!/usr/bin/env python3
"""Exercise S31's actual FDT handoff with the upstream libfdt implementation."""
import os
import pathlib
import subprocess
import sys
import tempfile

src = pathlib.Path(sys.argv[1]).resolve()
text = (src / 'platform/generic/espressif/esp32s31/esp32s31.c').read_text()
start = text.index('static unsigned long s31_uboot_dtb;')
end = text.index('/* Vendor SBI extension:', start)
functions = text[start:end]
helper = (src / 'lib/utils/fdt/fdt_helper.c').read_text()
helper = helper[helper.index('/* Optional bounds for the single cold-boot'):helper.index('#define DEFAULT_UART_FREQ')]
harness = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <libfdt.h>
#define S31_FIXUP_FDT_SIZE 0x3000
#define SBI_ENOSPC -1
#define SBI_ENOMEM -2
#define SBI_EINVAL -3
struct domain { unsigned long next_arg1; } root;
struct scratch { unsigned long next_arg1; } scratch;
static int fail_malloc, fail_growth, make_large, freed;
static unsigned char large_value[3000];
static void *sbi_malloc(unsigned n) { return fail_malloc ? NULL : malloc(n); }
static void sbi_free(void *p) { freed++; free(p); }
static void s31_pma_init(void) {}
static int generic_early_init(bool cold) { (void)cold; return 0; }
static void sbi_printf(const char *s) { (void)s; }
static void s31_apm_init(void) {}
static void sbi_system_reset_add_device(void *p) { (void)p; }
static int s31_reset;
static void s31_hsm_register(void) {}
static void s31_tee_supervisor_priv_sel_to_m(void) {}
static struct scratch *sbi_scratch_thishart_ptr(void) { return &scratch; }
static int generic_final_init(bool cold);
''' + helper + functions + r'''
static int generic_final_init(bool cold) {
  if (!cold) return 0;
  void *tree = (void *)root.next_arg1;
  if (fail_growth) {
    /* Mimic a generic helper which ignores the failed expansion. */
    (void)fdt_fixup_open_into(tree, tree, S31_FIXUP_FDT_SIZE + 1);
    return 0;
  }
  if (fdt_fixup_open_into(tree, tree, fdt_totalsize(tree) + 4096)) return -9;
  int node = fdt_add_subnode(tree, 0, "reserved-memory");
  assert(node >= 0);
  assert(fdt_setprop_empty(tree, node, "no-map") == 0);
  if (make_large) assert(fdt_setprop(tree, node, "test-padding", large_value, sizeof(large_value)) == 0);
  return 0;
}
int main(void) {
  unsigned char original[4096];
  assert(fdt_create_empty_tree(original, sizeof(original)) == 0);
  assert(fdt_fixup_open_into(original, original, sizeof(original)) == 0);
  fdt_fixup_buffer_begin(original, sizeof(original));
  assert(fdt_fixup_open_into(original, original, -1) == -FDT_ERR_NOSPACE);
  assert(fdt_fixup_buffer_end());
  assert(!fdt_fixup_buffer_end());
  root.next_arg1 = (unsigned long)original;
  fail_malloc = 1;
  assert(esp32s31_early_init(true) == SBI_ENOMEM);
  fail_malloc = 0;
  assert(esp32s31_early_init(true) == 0);
  assert(esp32s31_final_init(true) == 0);
  assert(root.next_arg1 == (unsigned long)original && scratch.next_arg1 == root.next_arg1);
  assert(fdt_path_offset(original, "/reserved-memory") >= 0 && freed == 1);
  assert(fdt_create_empty_tree(original, 512) == 0);
  root.next_arg1 = (unsigned long)original; make_large = 1;
  assert(esp32s31_early_init(true) == 0);
  assert(esp32s31_final_init(true) == SBI_ENOSPC && freed == 2);
  assert(root.next_arg1 == (unsigned long)original);
  assert(fdt_create_empty_tree(original, sizeof(original)) == 0);
  root.next_arg1 = (unsigned long)original; make_large = 0; fail_growth = 1;
  assert(esp32s31_early_init(true) == 0);
  assert(esp32s31_final_init(true) == SBI_ENOSPC && freed == 3);
  assert(root.next_arg1 == (unsigned long)original);
  return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='opensbi-fdt-') as tmp:
    stubs = pathlib.Path(tmp) / 'sbi'
    stubs.mkdir()
    (stubs / 'sbi_types.h').write_text(
        '#include <stdint.h>\n#include <stddef.h>\n#include <stdbool.h>\n'
        'typedef uint16_t be16_t; typedef uint32_t be32_t; typedef uint64_t be64_t;\n')
    lib = src / 'lib/utils/libfdt'
    library = [str(p) for p in lib.glob('*.c') if p.name != 'fdt_overlay.c']
    guard = 'fixup_buffer && buf == fixup_buffer &&\n\t    (size < 0 || size > fixup_capacity)'
    if harness.count(guard) != 1:
        raise RuntimeError('FDT capacity guard no longer matches the fault control')
    for name, body in (('real', harness),
                       ('fault', harness.replace(guard, '(fixup_capacity && 0)'))):
        c = pathlib.Path(tmp) / (name + '.c')
        c.write_text(body)
        exe = pathlib.Path(tmp) / name
        subprocess.run([os.environ['CC'], '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', '-Wno-macro-redefined', '-D__riscv_xlen=64', '-I' + tmp,
                        '-I' + str(src / 'include'), '-I' + str(lib), str(c), *library,
                        str(src / 'lib/sbi/sbi_string.c'), '-o', str(exe)], check=True)
        result = subprocess.run([str(exe)], stderr=subprocess.DEVNULL)
        if (result.returncode == 0) != (name == 'real'):
            raise RuntimeError(name + ' FDT check produced unexpected result')
print('S31 fixed-up FDT handoff and limits passed; capacity fault detected')
