/* SPDX-License-Identifier: BSD-2-Clause
 * Controlled registration boundary for the complete original launcher main.
 * GLib, libdbus errors, fork/wait and child execution remain real.
 */
#include "ck-connector.h"
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
struct _CkConnector { int unused; };
static CkConnector connector;
static dbus_bool_t result(DBusError *error)
{
        const char *mode = getenv("CK_REGISTRATION_MODE");
        if (mode && strcmp(mode, "error") == 0) {
                dbus_set_error_const(error, "org.freedesktop.ConsoleKit.Manager.InsufficientPermission", "Registration denied by fixture");
                return FALSE;
        }
        return !(mode && strcmp(mode, "noerror") == 0);
}
CkConnector *ck_connector_new(void)
{
        const char *mode = getenv("CK_REGISTRATION_MODE");
        return mode && strcmp(mode, "null") == 0 ? NULL : &connector;
}
void ck_connector_unref(CkConnector *ckc) { (void)ckc; }
dbus_bool_t ck_connector_open_session(CkConnector *ckc, DBusError *error)
{ (void)ckc; return result(error); }
dbus_bool_t ck_connector_open_session_with_parameters(CkConnector *ckc,
    DBusError *error, const char *name, ...)
{
        va_list args;
        const char **value;
        const char *end;
        (void)ckc;
        va_start(args, name);
        value = va_arg(args, const char **);
        end = va_arg(args, const char *);
        va_end(args);
        if (!name || strcmp(name, "session-service") || !value || !*value || end)
                abort();
        return result(error);
}
const char *ck_connector_get_cookie(CkConnector *ckc)
{ (void)ckc; return "fixture-cookie"; }
const char *ck_connector_get_runtime_dir(CkConnector *ckc, DBusError *error)
{ (void)ckc; (void)error; return "/fixture-runtime"; }
