#!/usr/bin/env python3
"""Exercise the production BSD connected-scan request and event paths."""
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
p.add_argument('--host-sdk', required=True)
p.add_argument('--source', required=True,
               help='effective driver_bsd.c with the Ports patch applied')
a = p.parse_args()
source = Path(a.source).read_text()


def function(name):
    match = re.search(rf'\nstatic (?:void|int)\n{name}\(', source)
    assert match, f'missing production function {name}'
    start = match.start() + 1
    brace = source.index('{', match.end())
    depth = 0
    for end in range(brace, len(source)):
        if source[end] == '{':
            depth += 1
        elif source[end] == '}':
            depth -= 1
            if depth == 0:
                return source[start:end + 1]
    raise AssertionError(f'unclosed production function {name}')


def connected_scan_block():
    marker = 'if (drv->sta_enabled && drv->sta_scan) {'
    start = source.index(marker)
    brace = source.index('{', start)
    depth = 0
    for end in range(brace, len(source)):
        if source[end] == '{':
            depth += 1
        elif source[end] == '}':
            depth -= 1
            if depth == 0:
                return source[start:end + 1]
    raise AssertionError('unclosed production connected-scan block')


scan_clear = function('bsd_sta_scan_clear')
abort_scan = function('bsd_sta_abort_scan')
disconnected = function('bsd_sta_disconnected')
sta_event = function('bsd_sta_event')
scan_block = connected_scan_block()
assert 'IEEE80211_STA_CAP_SCAN' in source
assert 'what == RTM_IEEE80211_STA_SCAN && !drv->sta_scan' in sta_event
assert 'req.freq = ' not in abort_scan

code = r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ETH_ALEN 6
#define IEEE80211_STA_VERSION 1
#define IEEE80211_STA_ASSOCIATED 0x0002
#define IEEE80211_STA_CAP_BTM 0x0001
#define IEEE80211_STA_CAP_SCAN 0x0040
#define IEEE80211_STA_CAP_RRM 0x0008
#define IEEE80211_STA_SCAN 5
#define IEEE80211_STA_CANCEL_SCAN 6
#define IEEE80211_STA_SCAN_ABORTED 0x0020
#define IEEE80211_STA_MAX_CHANNELS 32
#define IEEE80211_STA_MAX_BODY 1024
#define IEEE80211_STA_TX 4
#define IEEE80211_STA_GET 1
#define IEEE80211_STA_TX_ACK 0x0001
#define RTM_IEEE80211_STA_RX 112
#define RTM_IEEE80211_STA_TX 113
#define RTM_IEEE80211_STA_SCAN 114
#define WLAN_FC_STYPE_ACTION 13
#define EVENT_SCAN_RESULTS 1
#define EVENT_DISASSOC 2
#define EVENT_TX_STATUS 3
#define EVENT_RX_MGMT 4
#define ELOOP_ALL_CTX ((void *)-1)
#define os_memset memset
#define os_memcpy memcpy
#define os_memcmp memcmp
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint64_t u64;
struct os_reltime { unsigned sec, usec; };
struct bsd_driver_data {
 void *ctx;
 int sta_scan, sta_btm, sta_rrm, sta_enabled, sta_scan_pending;
 uintptr_t sta_scan_generation;
 uint32_t sta_scan_cookie, sta_scan_epoch;
 u16 sta_scan_freq;
 u8 sta_scan_bssid[ETH_ALEN], sta_addr[ETH_ALEN];
 u8 *sta_tx_frame; size_t sta_tx_len;
 uint32_t sta_cookie, sta_tx_generation;
 u16 sta_tx_freq;
 struct os_reltime sta_scan_completed;
};
'''
code += r'''
struct ieee80211req_sta_mgmt {
 uint32_t version, reserved, op, flags, cookie, generation;
 uint16_t freq;
 size_t len;
 u8 bssid[ETH_ALEN];
 u8 data[IEEE80211_STA_MAX_BODY];
};
struct wpa_driver_scan_params { int *freqs; };
union wpa_event_data {
 struct { int aborted; } scan_info;
 struct { int type, stype, ack, link_id; const u8 *dst, *data; size_t data_len; } tx_status;
 struct { const u8 *frame; size_t frame_len; unsigned freq; int link_id; } rx_mgmt;
};
static struct ieee80211req_sta_mgmt current, issued, started;
static int info_error, set_error, timer_error;
static unsigned set_calls, scan_events, disconnect_events, timers;
static int last_aborted;
static void bsd_sta_scan_timeout(void *a, void *b)
{ (void)a; (void)b; }
static void bsd_sta_tx_status(struct bsd_driver_data *d, int ack, int notify)
{ (void)d; (void)ack; (void)notify; }
static int bsd_sta_info(struct bsd_driver_data *d,
    struct ieee80211req_sta_mgmt *info)
{ (void)d; *info = current; return info_error; }
static int bsd_sta_set(struct bsd_driver_data *d,
    struct ieee80211req_sta_mgmt *req, unsigned op)
{
 (void)d; issued = *req; issued.op = op; set_calls++;
 if (op == IEEE80211_STA_SCAN) { started = issued; }
 return set_error;
}
static void eloop_cancel_timeout(void (*fn)(void *, void *), void *d, void *ctx)
{ (void)fn; (void)d; (void)ctx; if (timers) timers--; }
static int eloop_register_timeout(unsigned sec, unsigned usec,
    void (*fn)(void *, void *), void *d, void *ctx)
{ (void)fn; (void)d; (void)ctx; assert(sec == 15 && usec == 0); timers++; return timer_error; }
static void os_get_reltime(struct os_reltime *t) { t->sec = 1; t->usec = 0; }
static int bsd_sta_rx_body(struct bsd_driver_data *d, const u8 *p, size_t n)
{ (void)d; (void)p; (void)n; return 0; }
static void wpa_supplicant_event(void *ctx, int event,
    union wpa_event_data *data)
{
 (void)ctx;
 if (event == EVENT_SCAN_RESULTS) { scan_events++; last_aborted = data->scan_info.aborted; }
 else if (event == EVENT_DISASSOC) disconnect_events++;
}
'''
code += '\n' + scan_clear + '\n' + abort_scan + '\n' + disconnected + '\n' + sta_event
code += '\nstatic int scan_dispatch(struct bsd_driver_data *drv, struct wpa_driver_scan_params *params) {\n'
code += scan_block + '\n return -2;\n}\n'
code += r'''
static void setup(struct bsd_driver_data *d)
{
 memset(d, 0, sizeof(*d)); memset(&current, 0, sizeof(current));
 memset(&issued, 0, sizeof(issued)); memset(&started, 0, sizeof(started));
 d->sta_scan = d->sta_enabled = 1;
 d->sta_scan_cookie = 40; d->sta_scan_generation = 10;
 current.version = IEEE80211_STA_VERSION;
 current.flags = IEEE80211_STA_ASSOCIATED | IEEE80211_STA_CAP_SCAN;
 current.generation = 50; current.freq = 5180; current.bssid[0] = 2;
 d->sta_scan_freq = current.freq;
 d->sta_scan_epoch = current.generation; memcpy(d->sta_scan_bssid, current.bssid, ETH_ALEN);
 info_error = set_error = timer_error = 0;
 set_calls = scan_events = disconnect_events = timers = 0;
 last_aborted = 0;
}
int main(void)
{
 struct bsd_driver_data d;
 struct wpa_driver_scan_params params = {0};
 struct ieee80211req_sta_mgmt event;
 size_t header = offsetof(struct ieee80211req_sta_mgmt, data);
 setup(&d); d.sta_btm = d.sta_rrm = 0;
 assert(scan_dispatch(&d, &params) == 0 && set_calls == 1 &&
     issued.op == IEEE80211_STA_SCAN && issued.cookie != 0 &&
     issued.generation == current.generation &&
     issued.freq == current.freq && !memcmp(issued.bssid, current.bssid, ETH_ALEN));
 assert(d.sta_scan_pending && timers == 1);
 event = issued; event.len = 0; event.flags = 0;
 event.cookie++;
 bsd_sta_event(&d, RTM_IEEE80211_STA_SCAN, &event, header);
 assert(scan_events == 0 && d.sta_scan_pending);
 event.cookie--;
 event.freq++;
 bsd_sta_event(&d, RTM_IEEE80211_STA_SCAN, &event, header);
 assert(scan_events == 0 && d.sta_scan_pending);
 event.freq--;
 bsd_sta_event(&d, RTM_IEEE80211_STA_SCAN, &event, header);
 assert(scan_events == 1 && !last_aborted && !d.sta_scan_pending && timers == 0);
 bsd_sta_event(&d, RTM_IEEE80211_STA_SCAN, &event, header);
 assert(scan_events == 1);

 /* Timer failure rolls back the accepted request using the cancel tuple. */
 setup(&d); timer_error = -1;
 assert(scan_dispatch(&d, &params) == -1 && set_calls == 2 &&
     started.op == IEEE80211_STA_SCAN && issued.op == IEEE80211_STA_CANCEL_SCAN &&
     issued.freq == 0 && issued.cookie == started.cookie &&
     issued.generation == started.generation &&
     !memcmp(issued.bssid, started.bssid, ETH_ALEN) && !d.sta_scan_pending);

 /* A scan-only adapter can cancel; cancellation frequency is unspecified. */
 setup(&d); d.sta_btm = d.sta_rrm = 0; d.sta_scan_pending = 1;
 d.sta_scan_cookie = 41; d.sta_scan_epoch = current.generation;
 assert(bsd_sta_abort_scan(&d, 0) == 0 && issued.op == IEEE80211_STA_CANCEL_SCAN &&
     issued.cookie == 41 && issued.generation == current.generation &&
     issued.freq == 0 && !memcmp(issued.bssid, current.bssid, ETH_ALEN));
 event = current; event.op = IEEE80211_STA_SCAN; event.len = 0;
 event.cookie = 41; event.flags = IEEE80211_STA_SCAN_ABORTED;
 bsd_sta_event(&d, RTM_IEEE80211_STA_SCAN, &event, header);
 assert(scan_events == 1 && last_aborted && !d.sta_scan_pending);

 /* Either arrival order releases radio work once. */
 setup(&d); d.sta_scan_pending = 1; event = current;
 event.op = IEEE80211_STA_SCAN; event.cookie = d.sta_scan_cookie;
 event.flags = IEEE80211_STA_SCAN_ABORTED; event.len = 0;
 current.flags = 0; current.generation++;
 bsd_sta_event(&d, RTM_IEEE80211_STA_SCAN, &event, header);
 bsd_sta_disconnected(&d);
 assert(scan_events == 1 && disconnect_events == 1 && !d.sta_scan_pending);
 setup(&d); d.sta_scan_pending = 1; event = current;
 event.op = IEEE80211_STA_SCAN; event.cookie = d.sta_scan_cookie;
 event.flags = IEEE80211_STA_SCAN_ABORTED; event.len = 0;
 current.flags = 0; current.generation++;
 bsd_sta_disconnected(&d);
 bsd_sta_event(&d, RTM_IEEE80211_STA_SCAN, &event, header);
 assert(scan_events == 1 && last_aborted && disconnect_events == 1 &&
     !d.sta_scan_pending);

 /* BTM/RRM alone must not enable connected scans or accept scan events. */
 setup(&d); d.sta_scan = 0; d.sta_btm = d.sta_rrm = 1;
 current.flags = IEEE80211_STA_ASSOCIATED | IEEE80211_STA_CAP_BTM |
     IEEE80211_STA_CAP_RRM;
 assert(scan_dispatch(&d, &params) == -2 && set_calls == 0);
 d.sta_scan_pending = 1; event = current;
 event.op = IEEE80211_STA_SCAN; event.cookie = d.sta_scan_cookie;
 event.flags = IEEE80211_STA_SCAN_ABORTED; event.len = 0;
 bsd_sta_event(&d, RTM_IEEE80211_STA_SCAN, &event, header);
 assert(scan_events == 0 && d.sta_scan_pending);
 puts("PASS: production BSD scan request, completion, cancellation and disconnect paths");
 return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
    c = Path(td) / 'scan.c'
    out = Path(td) / 'scan'
    c.write_text(code)
    subprocess.run([a.cc, f'--sysroot={a.host_sdk}', '-std=c11',
                    '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    str(c), '-o', str(out)], check=True)
    subprocess.run([str(out)], check=True)
