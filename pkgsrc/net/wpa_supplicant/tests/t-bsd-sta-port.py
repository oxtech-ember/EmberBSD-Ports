#!/usr/bin/env python3
"""Exercise production BSD legacy and SAE controlled-port callbacks."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

if not __debug__:
    sys.exit('this test requires Python assertions enabled')
p = argparse.ArgumentParser()
p.add_argument('--cc', required=True)
p.add_argument('--source', required=True)
a = p.parse_args()
s = Path(a.source).read_text()
f = re.search(r'\nstatic int\nbsd_set_supp_port\(.*?\)\n\{.*?\n\}', s, re.S)
assert f, 'missing production BSD port callback'
code = r'''
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
#define IEEE80211_IOC_SAE 75
#define CONFIG_SAE 1
#define IEEE80211_SAE_CAP_KEY_EPOCH 1
#define IEEE80211_SAE_SET_PORT 42
#define IEEE80211_IOC_STA_PORT 76
#define SIOCG80211 123
#define os_memset memset
struct ieee80211req { char i_name[16]; int i_type, i_val; };
struct global { int sock; };
struct bsd_driver_data {
 struct global *global; char ifname[16];
 int sae_active, sae_blocked, sae_key_epoch;
};
static int result, err, set_result, set_calls, set_value, query_calls;
static int sae_result, sae_calls, sae_op, sae_value, sae_len;
static void os_strlcpy(char *d, const char *s, size_t n) { assert(strlen(s)<n);strcpy(d,s); }
static int ioctl(int fd,int op,struct ieee80211req *req) {
 assert(fd==5 && op==123 && req->i_type==76 && !strcmp(req->i_name,"espwifi0"));
 query_calls++;errno=err;if(result<0)return -1;req->i_val=result;return 0;
}
static int set80211param(struct bsd_driver_data *d,int op,int v) {
 (void)d;assert(op==76);set_calls++;set_value=v;return set_result;
}
static int bsd_sae_request(struct bsd_driver_data *d,u16 op,const void *data,size_t len) {
 (void)d;sae_calls++;sae_op=op;sae_len=(int)len;sae_value=*(const u8 *)data;return sae_result;
}
''' + f.group() + r'''
int main(void) {
 struct global g={5}; struct bsd_driver_data d={.global=&g,.ifname="espwifi0",.sae_key_epoch=1};
 /* Ordinary non-SAE profile: capability absence is optional; transport errors fail. */
 int before;
 before=query_calls;assert(bsd_set_supp_port(&d,2)==-1 && bsd_set_supp_port(&d,-1)==-1);
 assert(query_calls==before && !set_calls);
 result=-1;err=EOPNOTSUPP;assert(!bsd_set_supp_port(&d,1) && !set_calls);
 err=ENOTTY;assert(!bsd_set_supp_port(&d,1) && !set_calls);
 err=EINVAL;assert(!bsd_set_supp_port(&d,1) && !set_calls);
 err=EIO;assert(bsd_set_supp_port(&d,1)==-1 && !set_calls);
 result=0;assert(bsd_set_supp_port(&d,1)==-1 && !set_calls);
 result=1;assert(!bsd_set_supp_port(&d,1) && set_calls==1 && set_value==1);
 set_result=-1;assert(bsd_set_supp_port(&d,0)==-1 && set_calls==2 && set_value==0);
 /* SAE epoch profile: SET_PORT owns authorization and never falls back to legacy. */
 d.sae_active=1;d.sae_blocked=0;sae_result=0;
 int queries=query_calls, setters=set_calls, completions=sae_calls;
 assert(bsd_set_supp_port(&d,2)==-1 && bsd_set_supp_port(&d,-1)==-1);
 assert(sae_calls==completions && query_calls==queries && set_calls==setters);
 assert(!bsd_set_supp_port(&d,0) && sae_calls==1 && sae_op==42 && sae_value==0 && sae_len==1);
 sae_result=-1;assert(bsd_set_supp_port(&d,1)==-1 && sae_calls==2);
 assert(query_calls==queries && set_calls==setters);
 d.sae_active=0;d.sae_blocked=1;
 assert(bsd_set_supp_port(&d,1)==-1 && sae_calls==2 && query_calls==queries && set_calls==setters);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
 c=Path(td)/'port.c'; out=Path(td)/'port'; c.write_text(code)
 subprocess.run([a.cc,'-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(c),'-o',str(out)],check=True)
 subprocess.run([str(out)],check=True)
print('actual BSD legacy and SAE key-epoch port callbacks passed')
