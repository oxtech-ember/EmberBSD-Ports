#!/usr/bin/env python3
"""Exercise the patched BSD supplicant controlled-port callback."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

if not __debug__:
    sys.exit('this test requires Python assertions enabled')

p=argparse.ArgumentParser();p.add_argument('--cc',required=True);p.add_argument('--source',required=True);a=p.parse_args()
s=Path(a.source).read_text()
f=re.search(r'\nstatic int\nbsd_set_supp_port\(.*?\)\n\{.*?\n\}',s,re.S)
assert f
code=r'''
#include <assert.h>
#include <errno.h>
#include <string.h>
#define IEEE80211_IOC_STA_PORT 76
#define SIOCG80211 123
#define os_memset memset
struct ieee80211req { char i_name[16]; int i_type, i_val; };
struct global { int sock; };
struct bsd_driver_data { struct global *global; char ifname[16]; };
static int result,err,set_calls,set_value;
static void os_strlcpy(char *d, const char *s, unsigned n) { assert(strlen(s)<n);strcpy(d,s); }
static int ioctl(int fd,int op,struct ieee80211req *req) { assert(fd==5 && op==123 && req->i_type==76 && !strcmp(req->i_name,"espwifi0"));errno=err;if(result<0)return -1;req->i_val=result;return 0; }
static int set80211param(struct bsd_driver_data *d,int op,int v) { (void)d;assert(op==76);set_calls++;set_value=v;return 0; }
''' + f.group() + r'''
int main(void) {
 struct global g={5}; struct bsd_driver_data d={&g,"espwifi0"};
 result=-1;err=EOPNOTSUPP;assert(!bsd_set_supp_port(&d,1) && !set_calls);
 err=EINVAL;assert(!bsd_set_supp_port(&d,1) && !set_calls);
 err=EIO;assert(bsd_set_supp_port(&d,1)==-1 && !set_calls);
 result=0;assert(bsd_set_supp_port(&d,1)==-1 && !set_calls);
 result=1;assert(!bsd_set_supp_port(&d,4) && set_calls==1 && set_value==1);
 assert(!bsd_set_supp_port(&d,0) && set_calls==2 && set_value==0);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
 c=Path(td)/'port.c';out=Path(td)/'port';c.write_text(code)
 subprocess.run([a.cc,'-Werror','-fsanitize=address,undefined',
                 '-fno-sanitize-recover=all',str(c),'-o',str(out)],check=True)
 subprocess.run([str(out)],check=True)
print('actual BSD controlled-port callback and legacy fallback passed')
