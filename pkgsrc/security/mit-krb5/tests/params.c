#include <krb5.h>
#include <kadm5/admin.h>
#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
    krb5_context ctx; kadm5_config_params in, out; krb5_error_code ret;
    memset(&in, 0, sizeof(in)); memset(&out, 0, sizeof(out));
    in.mask = KADM5_CONFIG_REALM; in.realm = "TEST.INVALID";
    if (argc > 1) { in.mask |= KADM5_CONFIG_DBNAME | KADM5_CONFIG_ACL_FILE; in.dbname = "/tmp/explicit-db"; in.acl_file = "/tmp/explicit-acl"; }
    ret = krb5_init_context(&ctx); if (ret) return 2;
    ret = kadm5_get_config_params(ctx, 0, &in, &out); if (ret) { printf("error %d\n", ret); return 3; }
    printf("%s\n%s\n", out.dbname, out.acl_file);
    kadm5_free_config_params(ctx, &out); krb5_free_context(ctx); (void)argv; return 0;
}
