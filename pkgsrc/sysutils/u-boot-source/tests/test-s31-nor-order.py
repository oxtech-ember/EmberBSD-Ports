# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check S31 NOR boot order and range')
s = (args.source / 'board/espressif/esp32s31/spl.c').read_text()
a = s.index('#if CONFIG_IS_ENABLED(NOR_SUPPORT)')
b = s.index("/* SPL's control dtb", a)
source = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
typedef unsigned long ulong;
typedef uint32_t u32;
#define CONFIG_IS_ENABLED(x) NOR_SUPPORT
#define IS_ENABLED(x) (x)
#define BOOT_DEVICE_NOR 5
#define BOOT_DEVICE_UART 7
''' + s[a:b] + r'''
int main(void) {
 u32 list[3]={0,0,42}; board_boot_order(list);
#if NOR_SUPPORT && CONFIG_ESP32S31_NOR_BOOT
 ulong start=0,size=0;
 if (list[0]!=5 || list[1]!=7 || list[2]!=42) return 1;
 if (!spl_nor_get_bounds(&start,&size) || start!=0x40000000UL || size!=0x1000000UL) return 2;
 if (spl_nor_get_uboot_base()!=0x40020000UL) return 3;
#else
 if (list[0]!=7 || list[1]!=0 || list[2]!=42) return 4;
#endif
 puts("S31 boot order passed"); return 0;
}
'''
for support, boot in ((0, 0), (1, 0), (1, 1)):
    compile_and_run(args, source, cflags=(f'-DNOR_SUPPORT={support}',
                      f'-DCONFIG_ESP32S31_NOR_BOOT={boot}'))
