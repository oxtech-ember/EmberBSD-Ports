#include "k5-int.h"
#include <stdio.h>
int main(void) {
 krb5_context ctx = NULL; char name[4096]; int rc=krb5_init_context(&ctx);
 if (rc) { printf("init=%d\n",rc); return 1; }
 rc=krb5_kt_default_name(ctx,name,sizeof(name));
 printf("keytab=%s rc=%d\nplugin=%s\n",rc?"(error)":name,rc,ctx->plugin_base_dir?ctx->plugin_base_dir:"(null)");
 krb5_free_context(ctx); return !!rc;
}
