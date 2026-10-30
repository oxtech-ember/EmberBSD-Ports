#include <config.h>
#include <roken.h>
#include <evp.h>
int main(void) { return EVP_sha256() == 0; }
