#include <openssl/err.h>
#include <stdlib.h>
#include <string.h>
extern const void *hc_EVP_ossl_rc2_cbc(void);
extern const void *hc_EVP_hcrypto_rc2_cbc(void);
int main(int argc,char **argv) {
 unsigned long e; const void *result; if(argc!=2) return 2;
 if (strcmp(argv[1],"empty-mixed")!=0) ERR_raise(ERR_LIB_EVP,ERR_R_UNSUPPORTED); e=ERR_peek_last_error();
 if (!strcmp(argv[1],"single-mark") && !ERR_set_mark()) return 3;
 setenv("FETCH_CASE", !strcmp(argv[1],"empty-mixed") ? "mixed" : !strcmp(argv[1],"single-mark") ? "single" : argv[1], 1); result=hc_EVP_ossl_rc2_cbc();
 if (!strcmp(argv[1],"empty-mixed")) return result!=NULL || ERR_GET_REASON(ERR_peek_error())!=ERR_R_MALLOC_FAILURE || ERR_GET_REASON(ERR_peek_last_error())!=ERR_R_UNSUPPORTED;
 if (!strcmp(argv[1],"single-mark")) { if (result!=hc_EVP_hcrypto_rc2_cbc() || ERR_peek_last_error()!=e) return 4; ERR_raise(ERR_LIB_USER,321); return !ERR_pop_to_mark() || ERR_peek_last_error()!=e; }
 if (!strcmp(argv[1],"single")) return result!=hc_EVP_hcrypto_rc2_cbc() || ERR_peek_last_error()!=e;
 return result!=NULL || ERR_peek_error()!=e || (strcmp(argv[1],"mixed")==0 && ERR_peek_last_error()!=e);
}
