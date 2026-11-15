#!/usr/bin/env python3
"""Exercise the prepared RSN M3 key-install and EAPOL authorization order."""
import argparse
from pathlib import Path
import shlex
import subprocess
import tempfile


def function_body(source, signature):
    start = source.rindex(signature)
    brace = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    i = brace
    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        if line_comment:
            if ch == "\n":
                line_comment = False
        elif block_comment:
            if ch == "*" and nxt == "/":
                block_comment = False
                i += 1
        elif quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif ch == "/" and nxt == "/":
            line_comment = True
            i += 1
        elif ch == "/" and nxt == "*":
            block_comment = True
            i += 1
        elif ch in "\"'":
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
        i += 1
    raise AssertionError(f"unterminated function: {signature}")


def rsn_install_tail(source):
    body = function_body(source, "static void wpa_supplicant_process_3_of_4(")
    start = body.index("\tif (key_info & WPA_KEY_INFO_INSTALL) {")
    ptk = body.index("wpa_supplicant_install_ptk(", start)
    secure = body.index("\tif (key_info & WPA_KEY_INFO_SECURE) {", ptk)
    end = body.index("\n\tif (mlo || ie.gtk)\n\t\twpa_sm_set_rekey_offload(sm);", start)
    tail = body[start:end]
    assert secure > ptk
    completion = tail.index("wpa_supplicant_key_neg_complete(sm, sm->bssid,")
    close = tail.index("\n\t\t\t\t\t\tkey_info & WPA_KEY_INFO_SECURE);", completion)
    return body, tail[:close + len("\n\t\t\t\t\t\tkey_info & WPA_KEY_INFO_SECURE);")]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cc", required=True)
    p.add_argument("--host-sdk", help="optional host SDK sysroot for host compilation")
    p.add_argument("--cflags", default="-O2 -g -Wall -Wextra -Werror",
                   help="additional host C flags; pass sanitizer flags explicitly")
    p.add_argument("--emit-c", help="write the extracted harness for static analysis")
    p.add_argument("--wpa-source", required=True)
    p.add_argument("--eapol-source", required=True)
    a = p.parse_args()

    wpa = Path(a.wpa_source).read_text()
    eapol = Path(a.eapol_source).read_text()
    body, tail = rsn_install_tail(wpa)
    authorized = function_body(eapol, "static void eapol_sm_set_port_authorized(")
    notify = function_body(eapol, "void eapol_sm_notify_portValid(")
    wpa1 = function_body(wpa, "static void wpa_supplicant_process_3_of_4_wpa(")
    group = function_body(wpa, "static void wpa_supplicant_process_1_of_2_wpa(")
    rsn_group = function_body(wpa, "static void wpa_supplicant_process_1_of_2(")
    complete = function_body(wpa, "static void wpa_supplicant_key_neg_complete(")
    igtk = function_body(wpa, "static int ieee80211w_set_keys(")

    # Structural controls ensure this is the owning RSN M3 function and retain
    # behavior outside its initial secure 4-way handshake.
    assert "wpa_sm_mlme_setprotection(" in tail
    assert tail.index("wpa_supplicant_pairwise_gtk(") < tail.index("ieee80211w_set_keys(sm, &ie)")
    assert tail.index("ieee80211w_set_keys(sm, &ie)") < tail.index("wpa_supplicant_key_neg_complete(")
    assert "sm->group_cipher == WPA_CIPHER_GTK_NOT_USED" in tail
    assert "goto failed;" in tail
    assert "eapol_sm_notify_portValid(sm->eapol, true);" in wpa1
    assert "!wpa_cipher_valid_mgmt_group(sm->mgmt_group_cipher)" in igtk
    assert "sm->mgmt_group_cipher == WPA_CIPHER_GTK_NOT_USED" in igtk
    assert "return 0;" in igtk[:igtk.index("if (ie->igtk)")]
    rekey = group.index("rekey = wpa_sm_get_state(sm) == WPA_COMPLETED;")
    rekey_if = group.index("if (rekey) {", rekey)
    rekey_else = group.index("} else {", rekey_if)
    assert "wpa_supplicant_key_neg_complete" not in group[rekey_if:rekey_else]
    assert "wpa_supplicant_key_neg_complete" in group[rekey_else:]
    assert "eapol_sm_notify_portValid" not in rsn_group
    assert "wpa_supplicant_key_neg_complete" not in rsn_group
    assert "wpa_sm_set_state(sm, WPA_COMPLETED);" in rsn_group
    secure = complete.index("if (secure) {")
    notify_port = complete.index("eapol_sm_notify_portValid(sm->eapol, true);", secure)
    assert notify_port > secure

    harness = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdarg.h>
#include <errno.h>

enum { Unauthorized, Authorized, WPA_GROUP_HANDSHAKE, WPA_PROTO_RSN,
       WPA_CIPHER_GTK_NOT_USED, WPA_KEY_INFO_SECURE = 1, WPA_KEY_INFO_INSTALL = 2,
       MSG_DEBUG, MLME_SETPROTECTION_PROTECT_TYPE_RX,
       MLME_SETPROTECTION_KEY_TYPE_PAIRWISE, KEY_FLAG_RX_TX, MSG_INFO,
       WLAN_REASON_UNSPECIFIED };
struct eapol_ctx { void (*port_cb)(void *, int); void *ctx; };
struct eapol_sm { bool portValid; int suppPortStatus; bool force_authorized_update; struct eapol_ctx *ctx; };
struct wpa_ctx { void *msg_ctx; };
struct wpa_sm { struct eapol_sm *eapol; struct wpa_ctx *ctx; unsigned char *bssid; int group_cipher; int proto; int use_ext_key_id; };
struct wpa_eapol_ie_parse { unsigned char *gtk; size_t gtk_len; };
static int events[16], n_events, ptk_error, gtk_error, igtk_error, ioctl_error, callback_count;
static void event(int value) { assert(n_events < 16); events[n_events++] = value; }
static void port_cb(void *ctx, int authorized) {
    (void)ctx; assert(authorized == 1); callback_count++;
    if (ioctl_error) assert(ioctl_error == EACCES);
    event(5); /* driver callback attempted; ioctl_error models EACCES */
}
static void wpa_printf(int level, const char *fmt, ...) { (void)level; (void)fmt; }
static void eapol_sm_step(struct eapol_sm *sm);
''' + authorized + '\n' + notify + r'''
static void eapol_sm_step(struct eapol_sm *sm) {
    if (sm->portValid)
        eapol_sm_set_port_authorized(sm);
}
static void wpa_sm_mlme_setprotection(struct wpa_sm *sm, unsigned char *bssid,
                                      int type, int key_type) {
    (void)sm; (void)bssid; (void)type; (void)key_type; event(1);
}
static void wpa_sm_set_state(struct wpa_sm *sm, int state) {
    (void)sm; (void)state;
}
static int wpa_supplicant_pairwise_mlo_gtk(struct wpa_sm *sm, void *key,
                                           struct wpa_eapol_ie_parse *ie,
                                           int key_info) {
    (void)sm; (void)key; (void)ie; (void)key_info; return gtk_error;
}
static int wpa_supplicant_pairwise_gtk(struct wpa_sm *sm, void *key,
                                       unsigned char *gtk, size_t len,
                                       int key_info) {
    (void)sm; (void)key; (void)gtk; (void)len; (void)key_info;
    event(2); return gtk_error;
}
static int wpa_supplicant_activate_ptk(struct wpa_sm *sm) {
    (void)sm; return ptk_error;
}
static int wpa_supplicant_install_ptk(struct wpa_sm *sm, void *key, int flags) {
    (void)sm; (void)key; (void)flags; return ptk_error;
}
static int mlo_ieee80211w_set_keys(struct wpa_sm *sm,
                                   struct wpa_eapol_ie_parse *ie) {
    (void)sm; (void)ie; event(3); return igtk_error;
}
static int ieee80211w_set_keys(struct wpa_sm *sm,
                               struct wpa_eapol_ie_parse *ie) {
    (void)sm; (void)ie; event(3); return igtk_error;
}
static void wpa_msg(void *ctx, int level, const char *fmt, ...) {
    (void)ctx; (void)level; (void)fmt;
}
static void wpa_supplicant_key_neg_complete(struct wpa_sm *sm,
                                             unsigned char *bssid, int secure) {
    (void)bssid;
    if (!secure) return;
    event(4);
    eapol_sm_notify_portValid(sm->eapol, true);
}
static void run_tail(int no_gtk, int fail_ptk, int fail_gtk, int fail_igtk, int fail_ioctl) {
    unsigned char bssid[6] = {0}, gtk[16] = {0};
    struct eapol_ctx ctx = { port_cb, 0 };
    struct eapol_sm eapol = { false, Unauthorized, false, &ctx };
    struct wpa_ctx wctx = { 0 };
    struct wpa_sm sm_data = { &eapol, &wctx, bssid,
                              no_gtk ? WPA_CIPHER_GTK_NOT_USED : 1,
                              WPA_PROTO_RSN, 0 };
    struct wpa_sm *sm = &sm_data;
    struct wpa_eapol_ie_parse ie = { no_gtk ? 0 : gtk, no_gtk ? 0 : sizeof(gtk) };
    int key_info = WPA_KEY_INFO_SECURE;
    int mlo = 0;
    void *key = 0;
    n_events = callback_count = 0;
    ptk_error = fail_ptk ? -1 : 0;
    gtk_error = fail_gtk ? -1 : 0;
    igtk_error = fail_igtk ? -1 : 0;
    ioctl_error = fail_ioctl ? EACCES : 0;
    key_info = WPA_KEY_INFO_SECURE | WPA_KEY_INFO_INSTALL;
''' + tail + r'''
    if (fail_ioctl)
        eapol_sm_notify_portValid(sm->eapol, true);
failed:
    return;
}
static int event_index(int value) {
    for (int i = 0; i < n_events; i++) if (events[i] == value) return i;
    return -1;
}
int main(void) {
    run_tail(0, 0, 0, 0, 0); /* strict PMF success */
    assert(callback_count == 1 && event_index(1) >= 0 && event_index(2) > event_index(1));
    assert(event_index(3) > event_index(2) && event_index(4) > event_index(3));
    assert(event_index(5) > event_index(4));
    run_tail(0, 0, 0, 1, 0); /* IGTK failure keeps controlled port closed */
    assert(callback_count == 0 && event_index(4) < 0);
    run_tail(0, 0, 1, 0, 0); /* GTK failure keeps controlled port closed */
    assert(callback_count == 0 && event_index(4) < 0);
    run_tail(0, 1, 0, 0, 0); /* PTK failure keeps controlled port closed */
    assert(callback_count == 0 && event_index(2) < 0 && event_index(4) < 0);
    run_tail(1, 0, 0, 0, 0); /* no-GTK success still completes */
    assert(callback_count == 1 && event_index(2) < 0 && event_index(3) >= 0);
    run_tail(0, 0, 0, 0, 1); /* even if ioctl fails, EAPOL does not retry same state */
    assert(callback_count == 1);
    return 0;
}
'''
    if a.emit_c:
        Path(a.emit_c).write_text(harness)
    with tempfile.TemporaryDirectory() as td:
        c = Path(td) / "rsn-port-order.c"
        out = Path(td) / "rsn-port-order"
        c.write_text(harness)
        command = [a.cc, *shlex.split(a.cflags)]
        if a.host_sdk:
            command.append(f"--sysroot={a.host_sdk}")
        command.extend([str(c), "-o", str(out)])
        subprocess.run(command, check=True)
        subprocess.run([str(out)], check=True)
    assert "eapol_sm_notify_portValid" not in body
    print("RSN GTK/IGTK authorization order and one-shot EAPOL callback: PASS")


if __name__ == "__main__":
    main()
