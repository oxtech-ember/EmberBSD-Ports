#include <config.h>
#include "dbus/dbus-string.h"
#include "dbus/dbus-sysdeps.h"
#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
  const char *paths[] = {DBUS_PREFIX "/share/dbus-1/session.conf", DBUS_PREFIX "-other/file", DBUS_PREFIX "/../escape", DBUS_PREFIX "/share//bad", "/etc/external.conf"};
  DBusString x; char expected[4096]; int i;
  if (argc != 3) return 2;
  for (i=0;i<5;i++) {
    if (!_dbus_string_init(&x) || !_dbus_string_append(&x, paths[i]) || !_dbus_relocate_install_prefix(&x)) return 3;
    if (i==0 && strcmp(argv[2],"moved")==0) snprintf(expected,sizeof(expected),"%s/share/dbus-1/session.conf",argv[1]);
    else snprintf(expected,sizeof(expected),"%s",paths[i]);
    if (strcmp(_dbus_string_get_const_data(&x),expected)) {fprintf(stderr,"case %d got %s expected %s\n",i,_dbus_string_get_const_data(&x),expected);return 4;}
    _dbus_string_free(&x);
  }
  puts("prefix boundary, explicit external and noncanonical path cases PASS"); return 0;
}
