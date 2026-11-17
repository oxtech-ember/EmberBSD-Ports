#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Run production WNM BTM TX-status handling with explicit result fixtures."""
import argparse
from pathlib import Path
import shlex
import subprocess
import tempfile


def extract(src, marker):
    start = src.rindex(marker)
    brace = src.index("{", start)
    depth = 0
    quote = None
    escaped = False
    line_comment = block_comment = False
    i = brace
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ""
        if line_comment:
            if ch == "\n": line_comment = False
        elif block_comment:
            if ch == "*" and nxt == "/": block_comment = False; i += 1
        elif quote:
            if escaped: escaped = False
            elif ch == "\\": escaped = True
            elif ch == quote: quote = None
        elif ch == "/" and nxt == "/": line_comment = True; i += 1
        elif ch == "/" and nxt == "*": block_comment = True; i += 1
        elif ch in "\"'": quote = ch
        elif ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0: return src[start:i + 1]
        i += 1
    raise ValueError(f"unterminated {marker}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cc", required=True)
    p.add_argument("--source", required=True, help="prepared WPA source root")
    p.add_argument("--host-sdk", required=True)
    p.add_argument("--cflags", default="-O2 -g -Wall -Wextra -Werror")
    p.add_argument("--emit-c")
    a = p.parse_args()
    source = Path(a.source) / "wpa_supplicant/wnm_sta.c"
    function = extract(source.read_text(), "int wnm_btm_resp_tx_status(")
    harness = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;
#define IEEE80211_HDRLEN 24
#define WLAN_ACTION_WNM 10
#define WNM_BSS_TRANS_MGMT_RESP 8
#define WNM_BSS_TM_ACCEPT 0
#define MSG_DEBUG 0
struct ieee80211_mgmt {
    u8 hdr[24];
    union { struct { u8 category; union {
        struct { u8 action, status_code; } bss_tm_resp;
    } u; } action; } u;
};
struct wpa_bss { int unused; };
struct wpa_ssid { int unused; };
struct wpa_supplicant {
    struct wpa_bss *wnm_target_bss;
    struct wpa_ssid *current_ssid;
};
static unsigned resets, connects;
static void wpa_printf(int level, const char *fmt, ...) { (void)level; (void)fmt; }
static void wnm_btm_reset(struct wpa_supplicant *wpa_s)
{ resets++; wpa_s->wnm_target_bss = NULL; }
static void wnm_bss_tm_connect(struct wpa_supplicant *wpa_s,
    struct wpa_bss *bss, struct wpa_ssid *ssid, int after_new_scan)
{ (void)wpa_s; (void)bss; (void)ssid; (void)after_new_scan; connects++; }
'''
    c = harness + "\n" + function + r'''
static void setup(struct wpa_supplicant *w, struct ieee80211_mgmt *f,
    struct wpa_bss *b, struct wpa_ssid *s)
{
    memset(w, 0, sizeof(*w)); memset(f, 0, sizeof(*f));
    w->wnm_target_bss = b; w->current_ssid = s;
    f->u.action.category = WLAN_ACTION_WNM;
    f->u.action.u.bss_tm_resp.action = WNM_BSS_TRANS_MGMT_RESP;
    f->u.action.u.bss_tm_resp.status_code = WNM_BSS_TM_ACCEPT;
    resets = connects = 0;
}
int main(void)
{
    struct wpa_supplicant w; struct ieee80211_mgmt f;
    struct wpa_bss b; struct wpa_ssid s;
    setup(&w, &f, &b, &s);
    if (wnm_btm_resp_tx_status(&w,(u8 *)&f,sizeof(f),5,0,0) != 0 ||
        resets != 1 || connects != 0 || w.wnm_target_bss) return 1;
    setup(&w, &f, &b, &s);
    if (wnm_btm_resp_tx_status(&w,(u8 *)&f,sizeof(f),0,1,0) != 0 ||
        resets != 1 || connects != 0 || w.wnm_target_bss) return 2;
    setup(&w, &f, &b, &s);
    if (wnm_btm_resp_tx_status(&w,(u8 *)&f,sizeof(f),0,1,1) != 0 ||
        resets || connects != 1 || w.wnm_target_bss) return 3;
    setup(&w, &f, &b, &s);
    if (wnm_btm_resp_tx_status(&w,(u8 *)&f,sizeof(f),0,0,0) != 0 ||
        resets || connects != 1 || w.wnm_target_bss) return 4;
    setup(&w, &f, &b, &s); f.u.action.u.bss_tm_resp.status_code = 1;
    if (wnm_btm_resp_tx_status(&w,(u8 *)&f,sizeof(f),0,1,1) != -1 ||
        resets || connects || !w.wnm_target_bss) return 5;
    puts("WNM BTM response TX result handling: PASS");
    return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix="wpa-wnm-tx.") as td:
        cfile = Path(td) / "check.c"
        exe = Path(td) / "check"
        cfile.write_text(c)
        if a.emit_c: Path(a.emit_c).write_text(c)
        flags = shlex.split(a.cflags)
        cc = [a.cc]
        if "darwin" in subprocess.check_output([a.cc, "-dumpmachine"], text=True).lower():
            cc += ["-isysroot", a.host_sdk]
        else:
            cc += ["--sysroot=" + a.host_sdk, "-ffunction-sections", "-fdata-sections"]
        cc += flags + [str(cfile), "-o", str(exe)]
        if "darwin" in subprocess.check_output([a.cc, "-dumpmachine"], text=True).lower():
            cc += ["-Wl,-dead_strip"]
        else:
            cc += ["-Wl,--gc-sections"]
        subprocess.run(cc, check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    main()
