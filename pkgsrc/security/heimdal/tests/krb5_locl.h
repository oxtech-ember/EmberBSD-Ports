#include <openssl/evp.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdarg.h>
typedef void *krb5_context;
typedef int krb5_boolean;
typedef int krb5_error_code;
struct data { void *data; size_t length; };
struct block { struct data keyvalue; int keytype; };
struct _krb5_key_data { struct block *key; struct data *schedule; };
struct _krb5_key_type { const EVP_CIPHER *(*evp)(void); void (*schedule)(krb5_context, struct _krb5_key_type *, struct _krb5_key_data *); size_t schedule_size; };
struct _krb5_evp_schedule { EVP_CIPHER_CTX *ectx, *dctx; krb5_error_code error; };
#define HEIMDAL_OPAQUE_EVP 1
#define HEIM_EVP_SCHEDULE_CTX(s, f) ((s)->f)
#define HEIM_EVP_SCHEDULE_ERROR(s, c) ((s)->error)
#define HEIM_EVP_TRY(expr) do { if ((expr) <= 0) return EINVAL; } while (0)
static int krb5_enomem(krb5_context c) { (void)c; return ENOMEM; }
static void krb5_set_error_message(krb5_context c, int e, const char *s, ...) { (void)c; (void)e; (void)s; }
static int inject, calls;
static EVP_CIPHER_CTX *test_new(void) { if (inject && ++calls == inject) return NULL; return EVP_CIPHER_CTX_new(); }
#define EVP_CIPHER_CTX_new test_new

static int fail_init, init_calls;
static int test_cipher_init(EVP_CIPHER_CTX *ctx, const EVP_CIPHER *cipher,
                            ENGINE *engine, const unsigned char *key,
                            const unsigned char *iv, int encrypt) {
    if (fail_init && ++init_calls == fail_init) return 0;
    return EVP_CipherInit_ex(ctx, cipher, engine, key, iv, encrypt);
}
#define EVP_CipherInit_ex test_cipher_init
