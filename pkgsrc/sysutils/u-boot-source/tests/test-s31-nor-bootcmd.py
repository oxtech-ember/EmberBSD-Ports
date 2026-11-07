# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check NOR autoboot loadable metadata')
s = (args.source / 'board/espressif/esp32s31/board.c').read_text()
a = s.index('static bool s31_fit_payload_ready(')
b = s.index('\n#endif', a)
c = s.index('int board_late_init(void)', b)
late = s[c:s.index('\n}', c) + 2]
source = r'''
#include <stdbool.h>
#include <stdint.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <libfdt.h>
typedef uint32_t u32;
struct global_data { void *fdt_blob; } data, *gd = &data;
static int sets;
static const char *want_cmd;
static const char *want_args;
static int env_set(const char *name, const char *value) {
 if (!strcmp(name, "bootargs")) {
  if (!want_args || strcmp(value, want_args)) return -1;
  sets++; return 0;
 }
 if (strcmp(name, "bootcmd") || !want_cmd || strcmp(value, want_cmd)) return -1;
 sets++; return 0;
}
#define CONFIG_ESP32S31_NOR_BOOT 1
#define IS_ENABLED(x) (x)
''' + s[a:b] + '\n' + late + r'''
int main(void) {
 char blob[4096]; int node, images; fdt32_t load[2]; gd->fdt_blob=blob;
 if (fdt_create_empty_tree(blob,sizeof(blob))) return 1;
 if (s31_fit_payload_ready(blob,"/fit-images/root",0x50000000,0x400000,0x400000)) return 2;
 if (board_late_init() || sets) return 12;
 images=fdt_add_subnode(blob,0,"fit-images"); if(images<0) return 3;
 node=fdt_add_subnode(blob,images,"root"); if(node<0) return 4;
 load[0]=cpu_to_fdt32(0); load[1]=cpu_to_fdt32(0x50000000);
 if (fdt_setprop(blob,node,"load",load,sizeof(load)) || fdt_setprop_u32(blob,node,"size",0x400000)) return 5;
 if (!s31_fit_payload_ready(blob,"/fit-images/root",0x50000000,0x400000,0x400000)) return 6;
 if (fdt_setprop_u32(blob,node,"size",0x3fffff)) return 7;
 if (s31_fit_payload_ready(blob,"/fit-images/root",0x50000000,0x400000,0x400000)) return 8;
 if (fdt_setprop_u32(blob,node,"size",0x400000)) return 9;
 load[0]=cpu_to_fdt32(1);
 if (fdt_setprop(blob,node,"load",load,sizeof(load))) return 10;
 if (s31_fit_payload_ready(blob,"/fit-images/root",0x50000000,0x400000,0x400000)) return 11;
 load[0]=0; if (fdt_setprop(blob,node,"load",load,sizeof(load))) return 13;
 images=fdt_path_offset(blob,"/fit-images"); node=fdt_add_subnode(blob,images,"kernel"); if(node<0) return 14;
 load[1]=cpu_to_fdt32(0x50c00000);
 if(fdt_setprop(blob,node,"load",load,sizeof(load)) || fdt_setprop_u32(blob,node,"size",1000)) return 15;
 want_cmd="setenv initrd_high ffffffff; setenv fdt_high 50500000; setenv bootargs -s; setenv verify yes; bootm 50c00000 50000000:400000";
 if (board_late_init() || sets!=1) return 16;
 if (fdt_setprop_u32(blob,node,"size",0)) return 17;
 sets=0; if (board_late_init() || sets) return 18;
 if (fdt_setprop_u32(blob,node,"size",1000)) return 19;
 node=fdt_path_offset(blob,"/chosen");
 if (node < 0) node=fdt_add_subnode(blob,0,"chosen");
 if (node < 0 || fdt_setprop_string(blob,node,"emberbsd,root-mode","broken")) return 24;
 sets=0;
 if (board_late_init() != -EINVAL || sets) return 25;
 if (fdt_delprop(blob,node,"emberbsd,root-mode")) return 26;
 node=fdt_path_offset(blob,"/chosen");
 if (node < 0 || fdt_setprop_string(blob,node,"emberbsd,root-mode","nor") ||
     fdt_setprop_string(blob,node,"bootargs",
       "root=flash1 mtdparts=espnor0:6M@0(boot)ro,10M@6M(root)")) return 20;
 want_cmd="setenv fdt_high 50500000; setenv verify yes; bootm 50c00000";
 want_args="root=flash1 mtdparts=espnor0:6M@0(boot)ro,10M@6M(root)";
 sets=0;
 if (board_late_init() || sets != 2) return 21;
 if (fdt_setprop_u32(blob,fdt_path_offset(blob,"/fit-images/kernel"),"size",0)) return 22;
 sets=0;
 if (board_late_init() != -EINVAL || sets) return 23;
 puts("NOR autoboot: missing, valid and invalid loadables passed"); return 0;
}
'''
compile_and_run(args, source, include=(args.host_prefix / 'include',), libraries=('fdt',))
