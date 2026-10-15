/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD (AI-assisted), genuine target record declarations.
 * Compile this file with the target compiler and the actual target sysroot.
 * This check does not compile ConsoleKit or replace its cross-GLib requirement.
 */
#include <sys/types.h>
#include <sys/sysctl.h>
#include <sys/proc.h>
_Static_assert(CTL_KERN == 1 && KERN_PROC2 == 47 && KERN_PROC_PID == 1,
    "The host transport model must match the target MIB constants");
_Static_assert(KI_MAXCOMLEN == 24, "The host command bound must match NetBSD");
_Static_assert(SIDL == 1 && SACTIVE == 2 && SDYING == 3 &&
    SSTOP == 4 && SZOMB == 5 && SDEAD == 6,
    "The host state model must match the target process states");
_Static_assert(sizeof(((struct kinfo_proc2 *)0)->p_uvalid) == 8,
    "NetBSD validity field size");
_Static_assert(sizeof(((struct kinfo_proc2 *)0)->p_realstat) == 8,
    "NetBSD process state field size");
_Static_assert(sizeof(((struct kinfo_proc2 *)0)->p_ustart_sec) == 4 &&
    sizeof(((struct kinfo_proc2 *)0)->p_ustart_usec) == 4,
    "NetBSD start time field sizes");
int consolekit_process_header_probe(struct kinfo_proc2 *p);
int
consolekit_process_header_probe(struct kinfo_proc2 *p)
{
    return p->p_uvalid != 0 &&
        (p->p_realstat == SACTIVE || p->p_realstat == SSTOP) &&
        p->p_ustart_sec != 0 && p->p_ustart_usec < 1000000;
}
