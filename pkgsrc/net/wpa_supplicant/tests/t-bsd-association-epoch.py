#!/usr/bin/env python3
"""Exercise actual patched BSD MLME and association-event helpers."""
import argparse
from pathlib import Path
import re
import shlex
import subprocess
import tempfile


def function(source, name):
    match = re.search(r"(?m)^static (?:int|void)[ \n]+" + name +
                      r"\([^;]*?\)\n\{[\s\S]+?^}", source)
    if not match:
        raise SystemExit(f"missing production function: {name}")
    return match.group(0)


p = argparse.ArgumentParser()
p.add_argument("--cc", required=True)
p.add_argument("--host-sdk", required=True)
p.add_argument("--source", required=True)
p.add_argument("--cflags", default="-O2 -g -Wall -Wextra -Werror")
a = p.parse_args()
source = Path(a.source).read_text()
helpers = "\n".join(function(source, name) for name in (
    "bsd_set_mlme", "bsd_sta_epoch_reset", "bsd_sta_assoc_event",
    "bsd_sta_disassoc_event"))
code = r'''
#define __NetBSD__ 1
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
typedef unsigned char u8;
#define ETH_ALEN 6
#define IEEE80211_MLME_VERSION 1
#define IEEE80211_ASSOC_EVENT_VERSION 1
#define IEEE80211_IOC_MLME 44
#define IEEE80211_IOC_SAE 45
#define CONFIG_SAE 1
struct ieee80211req_mlme {
    uint8_t im_op;
    uint32_t im_version;
    uint64_t im_assoc_epoch;
    uint8_t im_macaddr[6];
};
struct ieee80211_assoc_event {
    uint32_t iae_version;
    uint32_t iae_reserved;
    uint64_t iae_assoc_epoch;
    uint8_t iae_bssid[6];
    uint8_t iae_reserved2[2];
};
struct bsd_driver_data {
    uint64_t sta_assoc_epoch, sta_assoc_retired_epoch;
    u8 sta_assoc_bssid[ETH_ALEN];
    int sta_assoc_versioned;
    int sae_active;
};
static int bsd_set80211(struct bsd_driver_data *d, int op, int val,
                        const void *arg, int len) {
    struct ieee80211req_mlme *mlme = (void *)arg;
    (void)d; (void)val;
    assert(op == IEEE80211_IOC_MLME && len == (int)sizeof(*mlme));
    assert(mlme->im_version == IEEE80211_MLME_VERSION);
    assert(mlme->im_assoc_epoch == 0);
    mlme->im_assoc_epoch = 41;
    { const u8 selected[ETH_ALEN] = { 2, 9, 8, 7, 6, 5 };
      memcpy(mlme->im_macaddr, selected, sizeof(selected)); }
    return 0;
}
static void os_memcpy(void *d, const void *s, size_t n) { memcpy(d, s, n); }
static void os_memset(void *d, int c, size_t n) { memset(d, c, n); }
static int os_memcmp(const void *a, const void *b, size_t n) { return memcmp(a,b,n); }
static int is_multicast_ether_addr(const u8 *a) { return (a[0] & 1) != 0; }
static int is_zero_ether_addr(const u8 *a) {
    static const u8 z[ETH_ALEN]; return memcmp(a,z,ETH_ALEN)==0;
}
''' + helpers + r'''
static struct ieee80211_assoc_event event(uint64_t epoch, const u8 *bssid) {
    struct ieee80211_assoc_event e;
    memset(&e, 0, sizeof(e)); e.iae_version = IEEE80211_ASSOC_EVENT_VERSION;
    e.iae_assoc_epoch = epoch; memcpy(e.iae_bssid, bssid, ETH_ALEN); return e;
}
int main(void) {
    const u8 bssid[6] = { 2, 1, 2, 3, 4, 5 };
    const u8 other_bssid[6] = { 2, 5, 4, 3, 2, 1 };
    struct bsd_driver_data d = {0};
    struct ieee80211req_mlme mlme = {0};
    struct ieee80211_assoc_event e, malformed;
    u8 unaligned[sizeof(e) + 1];
    assert(bsd_set_mlme(&d, &mlme) == 0 && mlme.im_assoc_epoch == 41 &&
           mlme.im_macaddr[1] == 9);
    d.sta_assoc_epoch = 41; d.sta_assoc_versioned = 1;
    memcpy(d.sta_assoc_bssid, bssid, ETH_ALEN); d.sae_active = 1;
    e = event(40, bssid);
    assert(!bsd_sta_disassoc_event(&d, &e, sizeof(e)) && d.sta_assoc_epoch == 41);
    e = event(41, bssid);
    memcpy(unaligned + 1, &e, sizeof(e));
    assert(bsd_sta_assoc_event(&d, unaligned + 1, sizeof(e)));
    assert(bsd_sta_assoc_event(&d, unaligned + 1, sizeof(e)));
    malformed = e; malformed.iae_version++;
    assert(!bsd_sta_disassoc_event(&d, &malformed, sizeof(malformed)));
    malformed = e; malformed.iae_reserved = 1;
    assert(!bsd_sta_disassoc_event(&d, &malformed, sizeof(malformed)));
    malformed = e; malformed.iae_assoc_epoch = 0;
    assert(!bsd_sta_disassoc_event(&d, &malformed, sizeof(malformed)));
    assert(!bsd_sta_disassoc_event(&d, &e, sizeof(e) - 1));
    assert(d.sta_assoc_epoch == 41 && d.sae_active);
    assert(bsd_sta_disassoc_event(&d, unaligned + 1, sizeof(e)));
    assert(!d.sta_assoc_epoch && d.sta_assoc_retired_epoch == 41 &&
           !d.sae_active);
    assert(!bsd_sta_disassoc_event(&d, &e, sizeof(e)));
    assert(!bsd_sta_assoc_event(&d, &e, sizeof(e)));
    e = event(40, bssid);
    assert(!bsd_sta_assoc_event(&d, &e, sizeof(e)));
    /* Autonomous joins can retire before their ASSOC route event. */
    e = event(43, other_bssid);
    assert(bsd_sta_disassoc_event(&d, &e, sizeof(e)) == 2 &&
           d.sta_assoc_epoch == 0 && d.sta_assoc_retired_epoch == 43);
    assert(!bsd_sta_assoc_event(&d, &e, sizeof(e)));
    /* A late older disconnect cannot close a newer selected BSS. */
    e = event(50, bssid);
    assert(bsd_sta_assoc_event(&d, &e, sizeof(e)));
    e = event(51, other_bssid);
    assert(bsd_sta_assoc_event(&d, &e, sizeof(e)));
    e = event(50, bssid);
    assert(!bsd_sta_disassoc_event(&d, &e, sizeof(e)) &&
           d.sta_assoc_epoch == 51);
    e = event(51, bssid);
    assert(!bsd_sta_assoc_event(&d, &e, sizeof(e)) &&
           d.sta_assoc_epoch == 51);
    bsd_sta_epoch_reset(&d);
    e = event(1, bssid);
    assert(bsd_sta_assoc_event(&d, &e, sizeof(e)) && d.sta_assoc_epoch == 1);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="bsd-association-epoch-") as td:
    c = Path(td) / "contract.c"
    exe = Path(td) / "contract"
    c.write_text(code)
    command = [a.cc, f"--sysroot={a.host_sdk}", *shlex.split(a.cflags),
               "-std=c99"]
    command.extend([str(c), "-o", str(exe)])
    subprocess.run(command, check=True)
    subprocess.run([str(exe)], check=True)
print("actual BSD association epoch helpers passed")
