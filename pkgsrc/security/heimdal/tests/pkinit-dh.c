#include <openssl/bn.h>
#include <openssl/dh.h>
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
typedef void *krb5_context;
typedef int krb5_error_code;
typedef struct { size_t length; void *data; int negative; } heim_integer;
struct krb5_dh_moduli { char *name; unsigned long bits; heim_integer p, g, q; };
#define N_(x,y) x
#define HEIMDAL_OPAQUE_DH 1
static void krb5_clear_error_message(krb5_context c) { (void)c; }
static void krb5_set_error_message(krb5_context c, int e, const char *s, ...) { (void)c;(void)e;(void)s; }
static int inject, calls;
static BIGNUM *test_bin2bn(const unsigned char *p, int n, BIGNUM *a) { if (inject && ++calls == inject) return NULL; return BN_bin2bn(p,n,a); }
#define BN_bin2bn test_bin2bn
#include "pkinit.inc"
int main(void) {
    unsigned char bp[] = { 23 }, bg[] = { 2 }, bq[] = { 11 };
    struct krb5_dh_moduli group = { .bits = 8, .p = {1,bp,0}, .g = {1,bg,0}, .q = {1,bq,0} };
    struct krb5_dh_moduli *groups[] = { &group, NULL };
    const BIGNUM *p, *q, *g;
    DH *dh = DH_new(); if (!dh) return 1;
    if (select_dh_group(NULL, dh, 0, groups)) return 2;
    DH_get0_pqg(dh, &p, &q, &g);
    if (!p || !q || !g || BN_get_word(p)!=23 || BN_get_word(q)!=11 || BN_get_word(g)!=2) return 3;
    DH_free(dh);
    dh = DH_new(); if (!dh) return 4; inject = 3; calls = 0;
    if (select_dh_group(NULL, dh, 0, groups) != ENOMEM) return 5;
    DH_get0_pqg(dh, &p, &q, &g); if (p || q || g) return 6;
    DH_free(dh);
    BIGNUM *prime = BN_get_rfc3526_prime_2048(NULL);
    BIGNUM *order = BN_dup(prime);
    if (!prime || !order || !BN_sub_word(order, 1) || !BN_rshift1(order, order)) return 7;
    unsigned char prime_bytes[256], order_bytes[256];
    if (BN_bn2binpad(prime, prime_bytes, sizeof prime_bytes) != sizeof prime_bytes ||
        BN_bn2binpad(order, order_bytes, sizeof order_bytes) != sizeof order_bytes) return 8;
    BN_free(prime); BN_free(order);
    group.bits = 2048; group.p.data = prime_bytes; group.p.length = sizeof prime_bytes;
    group.q.data = order_bytes; group.q.length = sizeof order_bytes;
    DH *one = DH_new(), *two = DH_new(); inject = 0;
    if (!one || !two || select_dh_group(NULL, one, 0, groups) ||
        select_dh_group(NULL, two, 0, groups) || !DH_generate_key(one) || !DH_generate_key(two)) return 9;
    const BIGNUM *pub1, *pub2; DH_get0_key(one, &pub1, NULL); DH_get0_key(two, &pub2, NULL);
    unsigned char shared1[256], shared2[256];
    int n1 = DH_compute_key(shared1, pub2, one), n2 = DH_compute_key(shared2, pub1, two);
    if (n1 <= 0 || n1 != n2 || memcmp(shared1, shared2, n1)) return 10;
    DH_free(one); DH_free(two);
    puts("PKINIT DH exchange, ownership and allocation failure PASS"); return 0;
}
