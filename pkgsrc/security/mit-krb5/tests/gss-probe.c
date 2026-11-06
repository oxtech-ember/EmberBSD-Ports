#include <gssapi/gssapi.h>
int main(void) { unsigned char bytes[] = {0x2b,0x06,0x01,0x04,0x01,0x83,0xb2,0x03,0x01}; gss_OID_desc oid = {sizeof(bytes),bytes}; OM_uint32 minor; gss_OID_set attrs = GSS_C_NO_OID_SET; (void)gss_inquire_attrs_for_mech(&minor,&oid,&attrs,0); if (attrs) gss_release_oid_set(&minor,&attrs); return 0; }
