# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run

args = arguments('Check S31 NOR JEDEC capacity decoding')
path = args.source / 'board/espressif/esp32s31/spl.c'
text = path.read_text()
start = text.index('static u32 s31_nor_capacity(u32 id)')
brace = text.index('{', start)
depth = 1
end = brace + 1
while depth:
    if text[end] == '{':
        depth += 1
    elif text[end] == '}':
        depth -= 1
    end += 1
function = text[start:end]

source = r'''
#include <stdint.h>
#include <stdio.h>
typedef uint32_t u32;
''' + function + r'''
int main(void)
{
    static const struct { u32 density, bytes; } valid[] = {
        { 0x14, 1U << 20 },
        { 0x15, 1U << 21 },
        { 0x16, 1U << 22 },
        { 0x17, 1U << 23 },
        { 0x18, 1U << 24 },
    };
    static const u32 invalid_density[] = { 0x19, 0x1a, 0x20 };
    const u32 manufacturer = 0xef;

    for (unsigned i = 0; i < sizeof(valid) / sizeof(valid[0]); i++) {
        u32 id = (manufacturer << 16) | valid[i].density;
        if (s31_nor_capacity(id) != valid[i].bytes)
            return 1;
    }
    for (unsigned i = 0; i < sizeof(invalid_density) / sizeof(invalid_density[0]); i++) {
        u32 id = (manufacturer << 16) | invalid_density[i];
        if (s31_nor_capacity(id) != 0)
            return 2;
    }
    if (s31_nor_capacity(0) != 0 ||
        s31_nor_capacity(0x00ffffff) != 0 ||
        s31_nor_capacity(0x00000018) != 0 ||
        s31_nor_capacity(0x00ff0018) != 0 ||
        s31_nor_capacity(0x01ef0018) != 0)
        return 3;

    puts("S31 NOR JEDEC capacity decoding passed");
    return 0;
}
'''
compile_and_run(args, source)
