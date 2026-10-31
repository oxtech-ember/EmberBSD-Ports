/* Toy DH parameter ownership fixture. ASN.1 decoding and group-policy
 * checks are stubs; this is not a protocol or group-strength test. */
#include <openssl/bn.h>
#include <openssl/dh.h>
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef void *krb5_context;
typedef int krb5_error_code;
typedef struct { size_t length; void *data; int negative; } heim_integer;
typedef struct { heim_integer p, g; heim_integer *q; } DomainParameters;
typedef struct { size_t length; void *data; } blob;
typedef struct { struct { blob *parameters; } algorithm; blob subjectPublicKey; } SubjectPublicKeyInfo;
typedef struct { int pkinit_dh_min_bits; } krb5_kdc_configuration;
typedef struct { struct { struct { DH *key; BIGNUM *public_key; } dh; } u; char *dh_group_name; } pk_client_params;

#define HEIMDAL_OPAQUE_DH 1
#define KRB5_BADMSGTYPE 9
static void *moduli;
static int with_q, fail_bn, bn_calls, fail_set0, fail_decode, fail_dh;
static int domain_alloc, domain_free, dh_alloc, dh_free, bn_alloc, bn_free;

static void
krb5_set_error_message(krb5_context c, int e, const char *f, ...)
{
	(void)c;
	(void)e;
	(void)f;
}

static void
krb5_clear_error_message(krb5_context c)
{
	(void)c;
}

static int
make_int(heim_integer *i, unsigned char b)
{
	i->data = malloc(1);
	if (i->data == NULL)
		return ENOMEM;
	domain_alloc++;
	*(unsigned char *)i->data = b;
	i->length = 1;
	i->negative = 0;
	return 0;
}

static int
decode_DomainParameters(const void *p, size_t n, DomainParameters *d, size_t *s)
{
	(void)p;
	(void)n;
	(void)s;
	if (make_int(&d->p, 23) || make_int(&d->g, 2))
		return ENOMEM;
	if (with_q) {
		d->q = calloc(1, sizeof(*d->q));
		if (d->q == NULL)
			return ENOMEM;
		domain_alloc++;
		if (make_int(d->q, 11))
			return ENOMEM;
	}
	return 0;
}

static void
free_domain_item(void *p)
{
	if (p != NULL) {
		domain_free++;
		free(p);
	}
}

static void
free_DomainParameters(DomainParameters *d)
{
	free_domain_item(d->p.data);
	free_domain_item(d->g.data);
	if (d->q != NULL) {
		free_domain_item(d->q->data);
		free_domain_item(d->q);
	}
}

static int
_krb5_dh_group_ok(krb5_context c, int min, heim_integer *p, heim_integer *g,
    heim_integer *q, void *m, char **name)
{
	(void)c;
	(void)min;
	(void)p;
	(void)g;
	(void)q;
	(void)m;
	(void)name;
	return 0;
}

static int
decode_DHPublicKey(const void *p, size_t n, heim_integer *v, size_t *s)
{
	(void)p;
	(void)n;
	(void)s;
	if (fail_decode)
		return 77;
	return make_int(v, 8);
}

static void
der_free_heim_integer(heim_integer *v)
{
	free_domain_item(v->data);
}

static BIGNUM *
test_bin2bn(const unsigned char *p, int n, BIGNUM *v)
{
	BIGNUM *out;

	if (fail_bn && ++bn_calls == fail_bn)
		return NULL;
	out = BN_bin2bn(p, n, v);
	if (out != NULL)
		bn_alloc++;
	return out;
}

static void
test_bn_free(BIGNUM *p)
{
	if (p != NULL)
		bn_free++;
	BN_free(p);
}

static DH *
test_dh_new(void)
{
	DH *d;

	if (fail_dh)
		return NULL;
	d = DH_new();
	if (d != NULL)
		dh_alloc++;
	return d;
}

static void
test_dh_free(DH *d)
{
	const BIGNUM *p, *q, *g;

	if (d != NULL) {
		DH_get0_pqg(d, &p, &q, &g);
		bn_free += (p != NULL) + (q != NULL) + (g != NULL);
		dh_free++;
	}
	DH_free(d);
}

static int
test_set0(DH *d, BIGNUM *p, BIGNUM *q, BIGNUM *g)
{
	return fail_set0 ? 0 : DH_set0_pqg(d, p, q, g);
}

#define BN_bin2bn test_bin2bn
#define BN_free test_bn_free
#define DH_new test_dh_new
#define DH_free test_dh_free
#define DH_set0_pqg test_set0
#include "pkinit.inc"

static int
run(int q, int bn, int set0, int dec, int fail_new, int expected)
{
	unsigned char input = 0;
	blob alg = { 1, &input };
	SubjectPublicKeyInfo info = { { &alg }, { 8, &input } };
	krb5_kdc_configuration cfg = { 0 };
	pk_client_params cp = { 0 };
	const BIGNUM *p, *g, *order;
	int ret, result = 0;

	with_q = q;
	fail_bn = bn;
	bn_calls = 0;
	fail_set0 = set0;
	fail_decode = dec;
	fail_dh = fail_new;
	domain_alloc = domain_free = dh_alloc = dh_free = bn_alloc = bn_free = 0;
	ret = get_dh_param(NULL, &cfg, &info, &cp);
	if (ret != expected)
		result = 1;
	else if (expected == 0) {
		if (cp.u.dh.key == NULL || cp.u.dh.public_key == NULL)
			result = 2;
		else {
			DH_get0_pqg(cp.u.dh.key, &p, &order, &g);
			if (p == NULL || g == NULL || (!!order != !!q) ||
			    BN_get_word(p) != 23 || BN_get_word(g) != 2 ||
			    (q && BN_get_word(order) != 11) ||
			    BN_get_word(cp.u.dh.public_key) != 8)
				result = 3;
		}
	} else if (cp.u.dh.key != NULL || cp.u.dh.public_key != NULL)
		result = 4;
	DH_free(cp.u.dh.key);
	BN_free(cp.u.dh.public_key);
	if (domain_alloc != domain_free || dh_alloc != dh_free || bn_alloc != bn_free)
		result = 5;
	return result;
}

int
main(void)
{
	if (run(1, 0, 0, 0, 0, 0) || run(0, 0, 0, 0, 0, 0))
		return 1;
	for (int i = 1; i <= 4; i++) {
		if (run(1, i, 0, 0, 0, KRB5_BADMSGTYPE))
			return 2;
	}
	if (run(1, 0, 1, 0, 0, KRB5_BADMSGTYPE) ||
	    run(1, 0, 0, 1, 0, 77) || run(1, 0, 0, 0, 1, ENOMEM))
		return 3;
	puts("KDC DH selected group, ownership, failures PASS");
	return 0;
}
