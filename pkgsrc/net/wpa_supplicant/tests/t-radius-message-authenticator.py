#!/usr/bin/env python3
"""Exercise actual RADIUS Message-Authenticator validation and bounds."""
import argparse
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--cc", required=True, help="Clang from the selected native prefix")
p.add_argument("--host-sdk", help="optional host SDK sysroot for native compilation")
p.add_argument("--source", required=True, type=Path,
               help="actual src/radius/radius.c from the prepared WPA source")
p.add_argument("--cflags", default="-O2 -g -Wall -Wextra -Werror",
               help="additional native C flags; pass sanitizer flags explicitly")
p.add_argument("--emit-c", type=Path, help="write the C test harness for static analysis")
a = p.parse_args()

radius = a.source.resolve()
src = radius.parents[1]
if radius.name != "radius.c" or not (src / "utils/wpabuf.c").is_file():
    p.error("--source must be the prepared src/radius/radius.c")

harness = r'''
#include "utils/includes.h"
#include "utils/common.h"
#include "utils/trace.h"
#include "utils/wpabuf.h"
#include "utils/wpa_debug.h"
#include "crypto/crypto.h"
#include "crypto/md5.h"
#include "radius/radius.h"

#include <assert.h>
#include <stdarg.h>

void wpa_printf(int level, const char *fmt, ...)
{
    (void) level;
    (void) fmt;
}

void * __hide_aliasing_typecast(void *ptr)
{
    return ptr;
}

static const u8 secret[] = { 0x72, 0x61, 0x64, 0x69, 0x75, 0x73 };
static const u8 request_auth[MD5_MAC_LEN] = {
    0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38,
    0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f, 0x40
};
static int failures;

enum verification_kind { VERIFY_MESSAGE_AUTH, VERIFY_DAS_REQUEST };

static u8 *make_packet(size_t attr_len, enum verification_kind kind,
                       size_t *packet_len)
{
    struct radius_hdr *hdr;
    u8 *packet, *attr, digest[MD5_MAC_LEN], zero[MD5_MAC_LEN];
    const u8 *addr[4];
    size_t len[4], body_len;

    *packet_len = sizeof(*hdr) + attr_len;
    packet = os_zalloc(*packet_len);
    assert(packet != NULL);
    hdr = (struct radius_hdr *) packet;
    hdr->code = kind == VERIFY_DAS_REQUEST ?
        RADIUS_CODE_DISCONNECT_REQUEST : RADIUS_CODE_ACCESS_ACCEPT;
    hdr->identifier = 9;
    hdr->length = host_to_be16(*packet_len);
    if (kind == VERIFY_MESSAGE_AUTH)
        os_memcpy(hdr->authenticator, request_auth, sizeof(request_auth));

    attr = packet + sizeof(*hdr);
    attr[0] = RADIUS_ATTR_MESSAGE_AUTHENTICATOR;
    attr[1] = attr_len;
    body_len = attr_len - sizeof(struct radius_attr_hdr);
    if (body_len > MD5_MAC_LEN)
        os_memset(attr + sizeof(struct radius_attr_hdr) + MD5_MAC_LEN,
                  0x5a, body_len - MD5_MAC_LEN);

    /* Build a correct HMAC for the exact size and for overlong attributes.
     * Short values retain only the digest bytes that physically fit. */
    os_memset(attr + sizeof(struct radius_attr_hdr), 0,
              body_len < MD5_MAC_LEN ? body_len : MD5_MAC_LEN);
    if (kind == VERIFY_MESSAGE_AUTH)
        os_memcpy(hdr->authenticator, request_auth, sizeof(request_auth));
    assert(hmac_md5(secret, sizeof(secret), packet, *packet_len, digest) == 0);
    if (body_len > MD5_MAC_LEN)
        os_memset(attr + sizeof(struct radius_attr_hdr) + MD5_MAC_LEN,
                  0x5a, body_len - MD5_MAC_LEN);
    if (body_len < MD5_MAC_LEN)
        os_memcpy(attr + sizeof(struct radius_attr_hdr), digest, body_len);
    else
        os_memcpy(attr + sizeof(struct radius_attr_hdr), digest, MD5_MAC_LEN);

    if (kind == VERIFY_DAS_REQUEST) {
        /* Response Authenticator = MD5(Code+ID+Length+zero Authenticator+
         * Attributes+secret), the precondition checked before the vulnerable
         * Message-Authenticator copy in radius_msg_verify_das_req(). */
        os_memset(zero, 0, sizeof(zero));
        addr[0] = (const u8 *) hdr;
        len[0] = sizeof(*hdr) - MD5_MAC_LEN;
        addr[1] = zero;
        len[1] = sizeof(zero);
        addr[2] = (const u8 *) (hdr + 1);
        len[2] = *packet_len - sizeof(*hdr);
        addr[3] = secret;
        len[3] = sizeof(secret);
        assert(md5_vector(4, addr, len, digest) == 0);
        os_memcpy(hdr->authenticator, digest, sizeof(digest));
    }

    return packet;
}

static int verify(struct radius_msg *msg, enum verification_kind kind)
{
    if (kind == VERIFY_DAS_REQUEST)
        return radius_msg_verify_das_req(msg, secret, sizeof(secret), 1);
    return radius_msg_verify_msg_auth(msg, secret, sizeof(secret),
                                      request_auth);
}

static void check_one(size_t attr_len, enum verification_kind kind,
                      int should_verify)
{
    struct radius_msg *msg;
    u8 *packet;
    size_t packet_len;
    int result;

    packet = make_packet(attr_len, kind, &packet_len);
    msg = radius_msg_parse(packet, packet_len);
    assert(msg != NULL);
    result = verify(msg, kind);
    if ((result == 0) != should_verify) {
        fprintf(stderr, "Message-Authenticator length %zu, verifier %d: result %d, expected %s\n",
                attr_len, kind, result, should_verify ? "valid" : "reject");
        failures++;
    }
    radius_msg_free(msg);
    os_free(packet);
}

static void check_parser_bounds(void)
{
    struct radius_hdr hdr;
    struct radius_msg *msg;
    u8 packet[sizeof(hdr) + sizeof(struct radius_attr_hdr)] = { 0 };

    memset(&hdr, 0, sizeof(hdr));
    hdr.length = host_to_be16(sizeof(packet));
    memcpy(packet, &hdr, sizeof(hdr));
    packet[sizeof(hdr)] = RADIUS_ATTR_MESSAGE_AUTHENTICATOR;
    packet[sizeof(hdr) + 1] = 1;
    msg = radius_msg_parse(packet, sizeof(packet));
    assert(msg == NULL);

    packet[sizeof(hdr) + 1] = sizeof(struct radius_attr_hdr);
    msg = radius_msg_parse(packet, sizeof(packet) - 1);
    assert(msg == NULL);
}

int main(void)
{
    static const size_t lengths[] = { 2, 17, 18, 19, 255 };
    size_t i;

    check_parser_bounds();
    for (i = 0; i < sizeof(lengths) / sizeof(lengths[0]); i++) {
        int valid = lengths[i] == sizeof(struct radius_attr_hdr) + MD5_MAC_LEN;

        check_one(lengths[i], VERIFY_MESSAGE_AUTH, valid);
        check_one(lengths[i], VERIFY_DAS_REQUEST, valid);
    }
    return failures ? 1 : 0;
}
'''

with tempfile.TemporaryDirectory(prefix="radius-message-authenticator-") as td:
    work = Path(td)
    cfile = work / "radius-message-authenticator.c"
    exe = work / "radius-message-authenticator"
    cfile.write_text(harness)
    if a.emit_c:
        a.emit_c.write_text(harness)

    command = [a.cc, *shlex.split(a.cflags), "-std=gnu11",
               "-Wno-unused-parameter", "-ffunction-sections", "-fdata-sections",
               "-I", str(src), "-I", str(src / "utils")]
    if a.host_sdk:
        command.extend(["-isysroot", a.host_sdk])
    linker_gc = "-Wl,-dead_strip" if sys.platform == "darwin" else "-Wl,--gc-sections"
    command.extend([
        str(radius),
        str(src / "utils/wpabuf.c"),
        str(src / "utils/os_unix.c"),
        str(src / "crypto/md5.c"),
        str(src / "crypto/md5-internal.c"),
        str(cfile), linker_gc, "-o", str(exe),
    ])
    subprocess.run(command, check=True)
    subprocess.run([str(exe)], check=True)

print("actual RADIUS Message-Authenticator validation passed")
