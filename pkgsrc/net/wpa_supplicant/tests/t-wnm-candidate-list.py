#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the prepared WPA WNM candidate-list serializer and common mapper."""
import argparse
from pathlib import Path
import shlex
import subprocess
import tempfile


def body(src, marker):
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
    p.add_argument("--host-sdk", required=True, help="selected native host sysroot")
    p.add_argument("--cflags", default="-O2 -g -Wall -Wextra -Werror -Wno-enum-conversion -Wno-unused-parameter")
    p.add_argument("--emit-c")
    a = p.parse_args()
    root = Path(a.source)
    wnm = (root / "wpa_supplicant/wnm_sta.c").read_text()
    common = (root / "src/common/ieee802_11_common.c").read_text()
    wnm_funcs = [
        body(wnm, "static u32 wnm_get_bss_info("),
        body(wnm, "static int wnm_add_nei_rep("),
        body(wnm, "static int wnm_nei_rep_add_bss("),
        body(wnm, "static void wnm_add_cand_list("),
        body(wnm, "int wnm_send_bss_transition_mgmt_query("),
    ]
    common_funcs = [
        body(common, "enum hostapd_hw_mode\nieee80211_freq_to_channel_ext(unsigned int freq"),
        body(common, "int ieee80211_chaninfo_to_channel(unsigned int freq"),
    ]
    # The width parser and IE parser below are bounded fixture doubles; the
    # actual production path under test is the WNM query/IE52 serializer and
    # common enum-to-operating-class mapper.
    harness = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <time.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#define CONFIG_NO_STDOUT_DEBUG
#include "utils/common.h"
#include "common/defs.h"
#include "common/ieee802_11_defs.h"
#include "common/ieee802_11_common.h"
#include "utils/wpabuf.h"

#define MSG_WARNING 1
#define BTM_QUERY_MIN_SIZE 4
struct wpa_ssid { int unused; };
struct wpa_bss {
    u8 bssid[ETH_ALEN];
    const u8 *ies;
    size_t ie_len;
    unsigned int freq;
    unsigned int caps;
};
struct wpa_supplicant {
    struct wpa_ssid *current_ssid;
    struct wpa_bss *current_bss;
    struct wpa_bss **last_scan_res;
    unsigned int last_scan_res_used;
    struct os_reltime last_scan;
    unsigned int assoc_freq;
    u8 bssid[ETH_ALEN], own_addr[ETH_ALEN];
};
static u8 tx[IEEE80211_MAX_MMPDU_SIZE];
static size_t tx_len;
static u8 ht_ie[24];

static const u8 *wpa_bss_ie_ptr(struct wpa_bss *bss) { return bss->ies; }
int ieee802_11_parse_elems(const u8 *ies, size_t len,
                                  struct ieee802_11_elems *e, int rx)
{
    size_t pos = 0;
    (void) rx;
    memset(e, 0, sizeof(*e));
    while (pos < len) {
        u8 id, n;
        if (len - pos < 2) return ParseFailed;
        id = ies[pos++]; n = ies[pos++];
        if (n > len - pos) return ParseFailed;
        if (id == WLAN_EID_HT_OPERATION && n == 22) e->ht_operation = ies + pos;
        if (id == WLAN_EID_VHT_OPERATION && n == 5) e->vht_operation = ies + pos;
        pos += n;
    }
    return ParseOK;
}
/* Test double keeps the source header enum ABI and derives HT20/40 only. */
enum chan_width get_operation_channel_width(struct ieee802_11_elems *e)
{
    struct ieee80211_ht_operation *ht;
    if (!e->ht_operation) return CHAN_WIDTH_UNKNOWN;
    ht = (struct ieee80211_ht_operation *) e->ht_operation;
    return (ht->ht_param & HT_INFO_HT_PARAM_SECONDARY_CHNL_OFF_MASK) ?
        CHAN_WIDTH_40 : CHAN_WIDTH_20;
}
enum phy_type ieee80211_get_phy_type(int freq, bool ht, bool vht, bool he)
{
    (void) freq; (void) he;
    if (vht) return PHY_TYPE_VHT;
    return ht ? PHY_TYPE_HT : PHY_TYPE_UNSPECIFIED;
}
static int wpa_scan_res_match(struct wpa_supplicant *w, unsigned int i,
    struct wpa_bss *b, struct wpa_ssid *s, int a, int c, bool d)
{ (void) w; (void) i; (void) b; (void) s; (void) a; (void) c; (void) d; return 1; }
int os_get_reltime(struct os_reltime *t) { t->sec = 20; t->usec = 0; return 0; }
static int wpa_drv_send_action(struct wpa_supplicant *w, unsigned int f,
    unsigned int wait, const u8 *dst, const u8 *src, const u8 *bssid,
    const u8 *data, size_t len, int no_cck)
{ (void) w; (void) f; (void) wait; (void) dst; (void) src; (void) bssid; (void) no_cck; memcpy(tx, data, len); tx_len = len; return 0; }
int ieee802_11_parse_candidate_list(const char *pos, u8 *nei_rep, size_t len)
{ (void) pos; (void) nei_rep; (void) len; return -1; }
static int wpa_bss_ies_eq(struct wpa_bss *a, struct wpa_bss *b, u8 eid)
{ (void) a; (void) b; (void) eid; return 0; }
'''
    helpers = '\n'.join(common_funcs)
    functions = '\n\n'.join(wnm_funcs)
    # Compile actual serializer functions. Suppress enum conversion warnings so
    # the old source reaches the behavioral assertion instead of failing early.
    main = r'''
static void run_candidate(unsigned int freq, u8 ht_param, int include_ht,
                          int malformed, size_t expect_len,
                          u8 expect_opclass, u8 expect_chan)
{
    struct wpa_supplicant w;
    struct wpa_bss b;
    struct wpa_bss *scan[1];
    struct wpa_ssid ssid;
    memset(&w, 0, sizeof(w)); memset(&b, 0, sizeof(b));
    memset(&ssid, 0, sizeof(ssid)); memset(ht_ie, 0, sizeof(ht_ie));
    ht_ie[0] = WLAN_EID_HT_OPERATION; ht_ie[1] = 22; ht_ie[3] = ht_param;
    b.ies = include_ht ? ht_ie : NULL;
    b.ie_len = include_ht ? sizeof(ht_ie) - (malformed ? 1 : 0) : 0;
    b.freq = freq;
    b.bssid[0] = 0x02; b.bssid[5] = (u8) (freq / 5);
    scan[0] = &b; w.current_ssid = &ssid; w.last_scan_res = scan;
    w.last_scan_res_used = 1; w.last_scan.sec = 20;
    assert(wnm_send_bss_transition_mgmt_query(&w, 0, NULL, 1) == 0);
    assert(tx_len == expect_len);
    if (expect_len == 22) {
        assert(tx[0] == WLAN_ACTION_WNM && tx[1] == WNM_BSS_TRANS_MGMT_QUERY);
        assert(tx[2] == 1 && tx[3] == 0);
        assert(tx[4] == WLAN_EID_NEIGHBOR_REPORT && tx[5] == 16);
        {
            u8 expected_bssid[ETH_ALEN] = { 0x02, 0, 0, 0, 0, (u8) (freq / 5) };
            assert(memcmp(tx + 6, expected_bssid, sizeof(expected_bssid)) == 0);
        }
        assert(tx[12] == 2 && tx[13] == 0 && tx[14] == 0 && tx[15] == 0);
        assert(tx[16] == expect_opclass && tx[17] == expect_chan);
        assert(tx[18] == PHY_TYPE_HT && tx[19] == 3 && tx[20] == 1 && tx[21] == 255);
    } else {
        assert(tx[0] == WLAN_ACTION_WNM && tx[1] == WNM_BSS_TRANS_MGMT_QUERY);
        assert(tx[2] == 1 && tx[3] == 0);
    }
}
static void run_size_boundary(void)
{
    struct wpa_supplicant w;
    struct wpa_bss bss[127];
    struct wpa_bss *scan[127];
    struct wpa_ssid ssid;
    size_t i, pos;
    memset(&w, 0, sizeof(w)); memset(bss, 0, sizeof(bss));
    memset(&ssid, 0, sizeof(ssid)); memset(ht_ie, 0, sizeof(ht_ie));
    ht_ie[0] = WLAN_EID_HT_OPERATION; ht_ie[1] = 22;
    for (i = 0; i < 127; i++) {
        bss[i].ies = ht_ie; bss[i].ie_len = sizeof(ht_ie);
        bss[i].freq = 2422; bss[i].bssid[0] = 0x02;
        bss[i].bssid[5] = (u8) i; scan[i] = &bss[i];
    }
    w.current_ssid = &ssid; w.last_scan_res = scan;
    w.last_scan_res_used = 127; w.last_scan.sec = 20;
    assert(wnm_send_bss_transition_mgmt_query(&w, 0, NULL, 1) == 0);
    assert(tx_len == 4 + 126 * 18);
    for (pos = 4; pos < tx_len; pos += 18) {
        assert(tx[pos] == WLAN_EID_NEIGHBOR_REPORT && tx[pos + 1] == 16);
    }
}

int main(void)
{
    run_candidate(2422, 0, 1, 0, 22, 81, 3);
    run_candidate(2427, 0, 1, 0, 22, 81, 4);
    run_candidate(2422, HT_INFO_HT_PARAM_SECONDARY_CHNL_ABOVE, 1, 0, 22, 83, 3);
    run_candidate(2437, HT_INFO_HT_PARAM_SECONDARY_CHNL_BELOW, 1, 0, 22, 84, 6);
    run_candidate(5180, 0, 1, 0, 22, 115, 36);
    run_candidate(2414, 0, 1, 0, 4, 0, 0);
    run_candidate(2422, 0, 1, 1, 4, 0, 0);
    run_candidate(2422, 0, 0, 0, 4, 0, 0);
    run_size_boundary();
    return 0;
}
'''
    # The compiler fixture uses source-provided headers for enum declarations;
    # wpabuf operations are provided by a small in-memory implementation.
    buf_impl = r'''
struct wpabuf *wpabuf_alloc(size_t n) { struct wpabuf *b=calloc(1,sizeof(*b)); if (!b) return NULL; b->buf=calloc(1,n?n:1); b->size=n; return b; }
void wpabuf_free(struct wpabuf *b) { if (b) { free(b->buf); free(b); } }
int wpabuf_resize(struct wpabuf **bp, size_t n) { struct wpabuf *b=*bp; u8 *p=realloc(b->buf,b->used+n); if (!p) return -1; b->buf=p; b->size=b->used+n; return 0; }
void *wpabuf_put(struct wpabuf *b, size_t n) { void *p=b->buf+b->used; assert(b->used+n<=b->size); b->used+=n; return p; }
'''
    text = harness + '\n' + buf_impl + '\n' + helpers + '\n' + functions + '\n' + main
    with tempfile.TemporaryDirectory(prefix="wnm-candidate-") as td:
        cfile = Path(td) / "test.c"
        exe = Path(td) / "test"
        cfile.write_text(text)
        if a.emit_c:
            Path(a.emit_c).write_text(text)
        inc = [f"-I{root}", f"-I{root / 'src'}"]
        cmd = shlex.split(a.cc) + [f"--sysroot={a.host_sdk}"] + shlex.split(a.cflags) + inc + [str(cfile), "-o", str(exe)]
        subprocess.run(cmd, check=True)
        subprocess.run([str(exe)], check=True)

if __name__ == "__main__":
    main()
