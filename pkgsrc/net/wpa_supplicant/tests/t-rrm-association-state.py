#!/usr/bin/env python3
"""Exercise RRM association state using the prepared WPA source snippets."""
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
    line_comment = block_comment = False
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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cc", required=True)
    p.add_argument("--host-sdk")
    p.add_argument("--cflags", default="-O2 -g -Wall -Wextra -Werror")
    p.add_argument("--no-rrm", action="store_true",
                   help="compile the extracted paths with CONFIG_NO_RRM")
    p.add_argument("--emit-c")
    p.add_argument("--wpa-source", required=True)
    p.add_argument("--events-source", required=True)
    p.add_argument("--rrm-source", required=True)
    p.add_argument("--sme-source", required=True)
    a = p.parse_args()

    wpa = Path(a.wpa_source).read_text()
    events = Path(a.events_source).read_text()
    rrm = Path(a.rrm_source).read_text()
    sme = Path(a.sme_source).read_text()
    # Execute the real FullMAC association IE block without extracting the
    # rest of the larger association builder and its unrelated dependencies.
    fullmac_start = wpa.index(
        "\t/* A full-MAC driver may expose host-managed neighbor reports. */")
    fullmac_end = wpa.index("#endif /* CONFIG_NO_RRM */", fullmac_start)
    fullmac_rrm = wpa[fullmac_start:fullmac_end]
    associate = function_body(wpa, "static void wpas_start_assoc_cb(struct wpa_radio_work *work, int deinit)")
    parser = function_body(events, "static void wpas_parse_connection_info(")
    command = function_body(rrm, "int wpas_rrm_send_neighbor_rep_request(")
    sme_rrm = function_body(sme, "static void sme_auth_handle_rrm(")
    assert "params.rrm_used = wpa_s->rrm.rrm_used;" in sme

    # Extract and execute the actual non-SME association reset/build/handoff
    # sequence. Population is stubbed only at its boundary.
    populate = associate.index("wpas_populate_assoc_ies(wpa_s, bss, ssid, &params")
    handoff = associate.index("if (bss &&", populate)
    assoc_start = associate.rindex("wpa_s->rrm.rrm_used = 0;", 0, populate)
    assoc_slice = associate[assoc_start:handoff]
    # EVENT_ASSOC request IEs are authoritative when present; response IEs
    # are optional. Missing request IEs preserve the association-param value.
    parse = parser.index("wpa_s->connection_set = 0;")
    parsed = parser.index("wpa_s->connection_set = 1;", parse)
    prefix = parser[parse:parsed]

    # Confirm the actual neighbor-report command still gates on the persistent
    # connection state, so the test covers the user-visible symptom.
    gate_start = command.index("if (wpa_s->wpa_state != WPA_COMPLETED")
    gate_end = command.index("rrm_ie = wpa_bss_get_ie", gate_start)
    gate = command[gate_start:gate_end]
    assert "if (!wpa_s->rrm.rrm_used)" in gate
    assert "return -EOPNOTSUPP;" in gate

    harness = r'''
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdbool.h>
#include <string.h>
typedef unsigned char u8;
enum { WPA_COMPLETED = 9, WPA_DISCONNECTED = 0, ParseFailed = -1,
       ParseOK = 0, MSG_DEBUG = 1, MSG_INFO = 2 };
enum { IEEE80211_CAP_RRM = 1, WPA_DRIVER_FLAGS_SUPPORT_RRM = 1,
       WPA_DRIVER_FLAGS_RRM_NEIGHBOR_REPORT_ONLY = 2,
       WPA_DRIVER_FLAGS_TX_POWER_INSERTION = 4,
       WPA_DRIVER_FLAGS_DS_PARAM_SET_IE_IN_PROBES = 8,
       WPA_DRIVER_FLAGS_QUIET = 16,
       WPA_DRIVER_FLAGS_RRM_NEIGHBOR_REPORT = 32,
       WLAN_EID_RRM_ENABLED_CAPABILITIES = 70,
       WLAN_RRM_CAPS_LINK_MEASUREMENT = 1,
       WLAN_RRM_CAPS_NEIGHBOR_REPORT = 2,
       WLAN_RRM_CAPS_BEACON_REPORT_PASSIVE = 4,
       WLAN_RRM_CAPS_BEACON_REPORT_ACTIVE = 8,
       WLAN_RRM_CAPS_BEACON_REPORT_TABLE = 16,
       WLAN_RRM_CAPS_LCI_MEASUREMENT = 32 };
struct ieee802_11_elems { const unsigned char *rrm_enabled; };
struct rrm_state { int rrm_used; };
struct sme_state { unsigned char assoc_req_ie[32]; size_t assoc_req_ie_len; };
struct wpa_supplicant {
    int connection_set;
    struct rrm_state rrm;
    int wpa_state;
    void *current_ssid;
    int mscs_setup_done;
    unsigned int drv_flags;
    unsigned int drv_rrm_flags;
    struct sme_state sme;
    void *lci;
};
enum { WPA_DRIVER_FLAGS_SME = 1 };
struct wpa_bss { unsigned int caps; };
struct wpa_driver_associate_params { int rrm_used; };
struct wpa_ssid_value { int unused; };
struct wpabuf { int unused; };
static int parse_fail;
static int populate_rrm, populate_fail;
static unsigned char assoc_ie;
#ifndef CONFIG_NO_RRM
static unsigned char test_rrm_ie[7];
static int test_rrm_ie_present;
static const unsigned char *wpa_bss_get_ie(struct wpa_bss *bss, int eid) {
    (void) bss; (void) eid; return test_rrm_ie_present ? test_rrm_ie : 0;
}
static void wpa_printf(int level, const char *fmt, ...) { (void)level; (void)fmt; }
#define os_memset memset
#endif
#ifndef CONFIG_NO_RRM
static unsigned char fullmac_ie[16];
static size_t fullmac_ie_len;
#endif
static int parse_elems(const unsigned char *buf, size_t len,
                       struct ieee802_11_elems *elems, int flags) {
    (void) flags;
    memset(elems, 0, sizeof(*elems));
    if (parse_fail) return ParseFailed;
    if (buf && len && buf[0]) elems->rrm_enabled = buf;
    return ParseOK;
}
#define ieee802_11_parse_elems parse_elems
static unsigned char *wpas_populate_assoc_ies(struct wpa_supplicant *wpa_s,
        void *bss, void *ssid, struct wpa_driver_associate_params *params,
        void *mask) {
    (void) wpa_s; (void) bss; (void) ssid; (void) mask;
    params->rrm_used = populate_rrm;
    return populate_fail ? 0 : &assoc_ie;
}
static void wpas_connect_work_done(struct wpa_supplicant *wpa_s) { (void)wpa_s; }
static void wpa_dbg(struct wpa_supplicant *w, int level, const char *msg) {
    (void) w; (void) level; (void) msg;
}
static int nr_command(struct wpa_supplicant *wpa_s) {
    const unsigned char *req_ies = 0, *resp_ies = 0;
    size_t req_ies_len = 0, resp_ies_len = 0;
    struct ieee802_11_elems req_elems, resp_elems;
    struct wpabuf *buf;
    const unsigned char *rrm_ie;
    (void) req_ies; (void) resp_ies; (void) req_ies_len; (void) resp_ies_len;
    (void) req_elems; (void) resp_elems; (void) buf; (void) rrm_ie;
''' + gate + r'''
    return 0;
}
#ifndef CONFIG_NO_RRM
static void fullmac_assoc_rrm(struct wpa_supplicant *wpa_s,
        struct wpa_bss *bss, struct wpa_driver_associate_params *params) {
    unsigned char *wpa_ie = fullmac_ie;
    size_t wpa_ie_len = 0, max_wpa_ie_len = sizeof(fullmac_ie);
''' + fullmac_rrm + r'''
    fullmac_ie_len = wpa_ie_len;
}
#endif
static void associate_once(struct wpa_supplicant *wpa_s) {
    void *bss = 0, *ssid = 0;
    struct wpa_driver_associate_params params = { 0 };
    unsigned char *wpa_ie;
''' + assoc_slice + r'''
}
static void parse_assoc(struct wpa_supplicant *wpa_s,
                        const unsigned char *req_ies, size_t req_ies_len,
                        const unsigned char *resp_ies, size_t resp_ies_len) {
    struct ieee802_11_elems req_elems, resp_elems;
''' + prefix + r'''
}
#ifndef CONFIG_NO_RRM
''' + sme_rrm + r'''
#endif
int main(void) {
    struct wpa_supplicant w = { 0 };
    unsigned char rrm[] = { 1 }, no_rrm[] = { 0 };
    w.wpa_state = WPA_COMPLETED; w.current_ssid = &w;
    populate_rrm = 1; populate_fail = 0;
    associate_once(&w);
#ifndef CONFIG_NO_RRM
    assert(w.rrm.rrm_used == 1 && nr_command(&w) == 0);
#else
    assert(w.rrm.rrm_used == 0 && nr_command(&w) == -EOPNOTSUPP);
#endif
    populate_fail = 1;
    associate_once(&w);
    assert(w.rrm.rrm_used == 0 && nr_command(&w) == -EOPNOTSUPP);
    populate_fail = 0; populate_rrm = 0;
    associate_once(&w);
    assert(w.rrm.rrm_used == 0 && nr_command(&w) == -EOPNOTSUPP);
#ifndef CONFIG_NO_RRM
    /* No request IEs: retain the value derived from association params. */
    w.rrm.rrm_used = 1;
    parse_assoc(&w, 0, 0, 0, 0);
    assert(w.rrm.rrm_used == 1);
    /* Request IE data is authoritative even when response IEs are absent. */
    parse_fail = 0;
    parse_assoc(&w, rrm, sizeof(rrm), 0, 0);
    assert(w.rrm.rrm_used == 1);
    parse_assoc(&w, no_rrm, sizeof(no_rrm), 0, 0);
    assert(w.rrm.rrm_used == 0 && nr_command(&w) == -EOPNOTSUPP);
    w.rrm.rrm_used = 1; parse_fail = 1;
    parse_assoc(&w, rrm, sizeof(rrm), 0, 0);
    assert(w.rrm.rrm_used == 0);
    parse_fail = 0;
    parse_assoc(&w, rrm, sizeof(rrm), no_rrm, sizeof(no_rrm));
    assert(w.rrm.rrm_used == 1);
    /* The SME path keeps its existing persistent-state and IE behavior. */
    {
        struct wpa_bss bss = { IEEE80211_CAP_RRM };
        struct wpa_driver_associate_params params = { 0 };
        w.drv_rrm_flags = WPA_DRIVER_FLAGS_SUPPORT_RRM |
            WPA_DRIVER_FLAGS_RRM_NEIGHBOR_REPORT_ONLY;
        test_rrm_ie_present = 1;
        test_rrm_ie[0] = WLAN_EID_RRM_ENABLED_CAPABILITIES;
        test_rrm_ie[1] = 5;
        sme_auth_handle_rrm(&w, &bss);
        assert(w.rrm.rrm_used == 1);
        assert(w.sme.assoc_req_ie[0] == WLAN_EID_RRM_ENABLED_CAPABILITIES);
        assert(w.sme.assoc_req_ie[2] == WLAN_RRM_CAPS_NEIGHBOR_REPORT);
        assert((w.sme.assoc_req_ie[3] | w.sme.assoc_req_ie[4] |
            w.sme.assoc_req_ie[5] | w.sme.assoc_req_ie[6]) == 0);
        test_rrm_ie_present = 0;
        sme_auth_handle_rrm(&w, &bss);
        assert(w.rrm.rrm_used == 0);

        /* AIC's RX/TX measurement-action transport has no declared
         * measurement-type capability, so its association IE is NR only. */
        test_rrm_ie_present = 1;
        w.sme.assoc_req_ie_len = 0;
        w.drv_rrm_flags = WPA_DRIVER_FLAGS_SUPPORT_RRM |
            WPA_DRIVER_FLAGS_RRM_NEIGHBOR_REPORT;
        sme_auth_handle_rrm(&w, &bss);
        assert(w.rrm.rrm_used == 1 &&
            w.sme.assoc_req_ie[2] == WLAN_RRM_CAPS_NEIGHBOR_REPORT);
        assert((w.sme.assoc_req_ie[3] | w.sme.assoc_req_ie[4] |
            w.sme.assoc_req_ie[5] | w.sme.assoc_req_ie[6]) == 0);

        w.drv_rrm_flags = WPA_DRIVER_FLAGS_SUPPORT_RRM |
            WPA_DRIVER_FLAGS_RRM_NEIGHBOR_REPORT_ONLY;
        fullmac_assoc_rrm(&w, &bss, &params);
        assert(fullmac_ie_len == 7 && params.rrm_used == 1 &&
            fullmac_ie[0] == WLAN_EID_RRM_ENABLED_CAPABILITIES &&
            fullmac_ie[2] == WLAN_RRM_CAPS_NEIGHBOR_REPORT &&
            (fullmac_ie[3] | fullmac_ie[4] | fullmac_ie[5] |
             fullmac_ie[6]) == 0);
        params.rrm_used = 0;
        w.drv_rrm_flags = WPA_DRIVER_FLAGS_SUPPORT_RRM |
            WPA_DRIVER_FLAGS_RRM_NEIGHBOR_REPORT;
        fullmac_assoc_rrm(&w, &bss, &params);
        assert(fullmac_ie_len == 7 && params.rrm_used == 1 &&
            fullmac_ie[2] == WLAN_RRM_CAPS_NEIGHBOR_REPORT &&
            (fullmac_ie[3] | fullmac_ie[4] | fullmac_ie[5] |
             fullmac_ie[6]) == 0);
        params.rrm_used = 0;
        w.drv_rrm_flags = 0;
        fullmac_assoc_rrm(&w, &bss, &params);
        assert(fullmac_ie_len == 0 && params.rrm_used == 0);
    }
#else
    assert(w.rrm.rrm_used == 0 && nr_command(&w) == -EOPNOTSUPP);
    parse_assoc(&w, rrm, sizeof(rrm), 0, 0);
    assert(w.rrm.rrm_used == 0);
    parse_assoc(&w, no_rrm, sizeof(no_rrm), 0, 0);
    assert(w.rrm.rrm_used == 0);
#endif
    /* A non-completed connection is rejected regardless of RRM state. */
    w.wpa_state = WPA_DISCONNECTED; w.rrm.rrm_used = 1;
    assert(nr_command(&w) == -ENOTCONN);
    return 0;
}
'''
    if a.emit_c:
        Path(a.emit_c).write_text(harness)
    with tempfile.TemporaryDirectory() as td:
        c = Path(td) / "rrm-association-state.c"
        out = Path(td) / "rrm-association-state"
        c.write_text(harness)
        command_line = [a.cc, *shlex.split(a.cflags)]
        if a.no_rrm:
            command_line.append("-DCONFIG_NO_RRM")
        if a.host_sdk:
            command_line.append(f"--sysroot={a.host_sdk}")
        command_line.extend([str(c), "-o", str(out)])
        subprocess.run(command_line, check=True)
        subprocess.run([str(out)], check=True)
    print("RRM params/EVENT_ASSOC/neighbor command lifecycle: PASS")


if __name__ == "__main__":
    main()
