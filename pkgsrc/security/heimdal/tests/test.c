#include "crypto-evp.c"
#include <stdio.h>
struct _krb5_encryption_type { struct _krb5_key_type *keytype; };
static struct _krb5_key_type *selected_type;
static struct _krb5_encryption_type * _krb5_find_enctype(int t) { static struct _krb5_encryption_type et; (void)t; et.keytype=selected_type; return &et; }
static int unsupported_enctype(krb5_context c, int t) { (void)c; (void)t; return EINVAL; }
#define ALLOC(p,n) ((p) = calloc((n), sizeof(*(p))))
static int krb5_data_alloc(struct data *d, size_t n) { d->data=calloc(1,n); d->length=n; return d->data ? 0 : ENOMEM; }
static void krb5_free_data(krb5_context c, struct data *d) { (void)c; free(d->data); free(d); }
#include "key-schedule.inc"
int main(void) {
    unsigned char k[16] = {0}, original[32], buffer[32];
    for (int i = 0; i < 32; i++) original[i] = (unsigned char)i;
    struct block block = { .keyvalue = { k, sizeof(k) } };
    struct _krb5_evp_schedule schedule = {0};
    struct data data = { &schedule, sizeof(schedule) };
    struct _krb5_key_data key = { &block, &data };
    struct _krb5_key_type type = { EVP_aes_128_cbc, _krb5_evp_schedule, sizeof(schedule) };
    _krb5_evp_schedule(NULL, &type, &key);
    if (schedule.error || !schedule.ectx || !schedule.dctx) return 1;
    memcpy(buffer, original, sizeof buffer);
    if (_krb5_evp_encrypt(NULL, &key, buffer, sizeof buffer, 1, 0, NULL)) return 2;
    if (!memcmp(buffer, original, sizeof buffer)) return 3;
    if (_krb5_evp_encrypt(NULL, &key, buffer, sizeof buffer, 0, 0, NULL)) return 4;
    if (memcmp(buffer, original, sizeof buffer)) return 5;
    fail_init = 1; init_calls = 0;
    if (_krb5_evp_encrypt(NULL, &key, buffer, sizeof buffer, 1, 0, NULL) != EINVAL) return 12;
    fail_init = 0;
    _krb5_evp_cleanup(NULL, &key);
    memset(&schedule, 0, sizeof schedule); inject = 2; calls = 0;
    _krb5_evp_schedule(NULL, &type, &key);
    if (schedule.error != ENOMEM || schedule.ectx || schedule.dctx) return 6;
    if (_krb5_evp_encrypt(NULL, &key, buffer, sizeof buffer, 1, 0, NULL) != ENOMEM) return 7;
    _krb5_evp_cleanup(NULL, &key);
    struct _krb5_key_data lazy = { &block, NULL };
    selected_type = &type; inject = 2; calls = 0;
    if (_key_schedule(NULL, &lazy) != ENOMEM || lazy.schedule != NULL) return 8;
    inject = 0; calls = 0;
    if (_key_schedule(NULL, &lazy) != 0 || lazy.schedule == NULL) return 9;
    _krb5_evp_cleanup(NULL, &lazy);
    krb5_free_data(NULL, lazy.schedule);
    lazy.schedule = NULL; fail_init = 2; init_calls = 0;
    if (_key_schedule(NULL, &lazy) != EINVAL || lazy.schedule != NULL) return 10;
    fail_init = 0;
    if (_key_schedule(NULL, &lazy) != 0 || lazy.schedule == NULL) return 11;
    _krb5_evp_cleanup(NULL, &lazy);
    krb5_free_data(NULL, lazy.schedule);
    puts("keyed EVP roundtrip and retry after allocation failure PASS");
    return 0;
}
