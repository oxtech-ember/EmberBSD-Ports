/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD (AI-assisted), actual ConsoleKit function regression.
 * GLib is real. Only the NetBSD sysctl/KVM transport and record are modeled.
 * This host record does not prove target kinfo_proc2 layout or kernel behavior.
 */
#include <glib.h>
#include <sys/types.h>
#include <stdint.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

enum { CTL_KERN=1, KERN_PROC2=47, KERN_PROC_PID=1, KI_MAXCOMLEN=24,
       SIDL=1, SACTIVE=2, SDYING=3, SSTOP=4, SZOMB=5, SDEAD=6,
       KVM_NO_FILES=1 };
struct kinfo_proc2 {
    char p_comm[KI_MAXCOMLEN];
    int p_pid, p_ppid, p__pgid, p_sid;
    uint64_t p_vm_rssize, p_vm_vsize, p_wchan, p_realflag;
    uint64_t p_realstat;
    int64_t p_uvalid;
    uint32_t p_ustart_sec, p_ustart_usec;
    int p_stat, p_nice, p_tpgid, p_cpuid, p_nlwps, p_tdev;
    uid_t p_uid;
};
typedef struct { int token; } kvm_t;
typedef struct _CkProcessStat CkProcessStat;
static struct kinfo_proc2 record;
static enum { FULL, ZERO_LENGTH, SHORT_LENGTH, LONG_LENGTH, QUERY_ERROR,
              NO_WRITE } query_mode;
static int queries, opens, closes, env_reads, allocations, releases;
static int open_error, env_error, failures, cases;
static void *live;
static kvm_t handle;
static char entry[]="XDG_SESSION_COOKIE=untrusted-locator";
static char empty[]="";
static char *env[] = {empty, entry, NULL};
static void *tracked_alloc(size_t size)
{
    assert(live == NULL);
    live = g_malloc0(size);
    allocations++;
    return live;
}
static void tracked_free(void *p)
{
    if (p != NULL && p == live) { live = NULL; releases++; }
    g_free(p);
}
#undef g_new0
#define g_new0(type,n) tracked_alloc(sizeof(type)*(n))
#define g_free tracked_free
static int
sysctl(const int *mib, unsigned n, void *out, size_t *len,
       const void *newp, size_t newlen)
{
    assert(n==6 && mib[0]==CTL_KERN && mib[1]==KERN_PROC2 &&
           mib[2]==KERN_PROC_PID && mib[4]==(int)sizeof(record) && mib[5]==1);
    assert(*len==sizeof(record) && newp==NULL && newlen==0);
    queries++;
    if (query_mode==QUERY_ERROR) { errno=EACCES; return -1; }
    /* Complete writes make baseline short/zero-length tests deterministic. */
    if (query_mode!=NO_WRITE) memcpy(out, &record, sizeof(record));
    if (query_mode==ZERO_LENGTH) *len=0;
    if (query_mode==SHORT_LENGTH) *len=sizeof(record)-1;
    if (query_mode==LONG_LENGTH) *len=sizeof(record)+1;
    return 0;
}
static kvm_t *kvm_openfiles(const char *a, const char *b, const char *c,
                           int flags, char *errbuf)
{
    assert(a==NULL && b==NULL && c==NULL && flags==KVM_NO_FILES);
    opens++;
    if (open_error) { strcpy(errbuf,"controlled failure"); return NULL; }
    return &handle;
}
static char **kvm_getenvv2(kvm_t *kd, const struct kinfo_proc2 *p, int n)
{
    assert(kd==&handle && p->p_pid==42 && n==0);
    env_reads++;
    if (env_error) { errno=EACCES; return NULL; }
    return env;
}
static int kvm_close(kvm_t *kd) { assert(kd==&handle); closes++; return 0; }
#include "extracted.c"

static void check(int truth, const char *name)
{
    cases++;
    if (!truth) { fprintf(stderr,"FAIL: %s\n", name); failures++; }
}
static void reset(void)
{
    /* A rejected baseline record can leak its allocation. Keep the test finite. */
    if (live) tracked_free(live);
    memset(&record,0,sizeof(record));
    strcpy(record.p_comm,"fixture");
    record.p_pid=42; record.p_ppid=7; record.p__pgid=41; record.p_sid=40;
    record.p_uid=501; record.p_uvalid=1; record.p_realstat=SACTIVE;
    record.p_ustart_sec=1700000000; record.p_ustart_usec=123456;
    record.p_stat=3; record.p_tdev=-1; /* sleeping LWP, no controlling TTY */
    query_mode=FULL; queries=opens=closes=env_reads=allocations=releases=0;
    open_error=env_error=0;
}
static void ignored_log(const gchar *d,GLogLevelFlags f,const gchar *m,gpointer p)
{ (void)d; (void)f; (void)m; (void)p; }
static void rejected_record(const char *why)
{
    struct kinfo_proc2 out;
    memset(&out,0xa5,sizeof(out));
    check(!get_kinfo_proc2(42,&out),why);
    struct kinfo_proc2 zero={0};
    check(memcmp(&out,&zero,sizeof(out))==0,"failure output initialized");
    CkProcessStat *proc=(void *)(uintptr_t)1;
    check(!ck_process_stat_new_for_unix_pid(42,&proc,NULL),"stat rejects bad snapshot");
    check(proc==NULL,"failed stat output NULL");
    check(allocations==releases,"failed stat allocation freed");
    if (proc && proc!=(void *)(uintptr_t)1) ck_process_stat_free(proc);
    check(ck_unix_pid_get_uid(42)==(uid_t)-1,"bad snapshot has no UID");
    GHashTable *hash=ck_unix_pid_get_env_hash(42);
    check(hash==NULL && env_reads==0,"bad snapshot never reads environment");
    check(opens==closes,"rejected snapshot closes KVM handle");
    if (hash) g_hash_table_destroy(hash);
}
int main(int argc, char **argv)
{
    (void)argv;
    gboolean baseline=argc>1;
    g_log_set_handler(NULL,G_LOG_LEVEL_WARNING|G_LOG_LEVEL_CRITICAL,ignored_log,NULL);
    for(int mode=ZERO_LENGTH;mode<=QUERY_ERROR;mode++) {
        reset(); query_mode=mode; rejected_record("bad sysctl result rejected");
    }
    reset(); record.p_pid=43;
    /* Do not let old environment transport assert on the intentionally wrong PID. */
    struct kinfo_proc2 out;
    check(!get_kinfo_proc2(42,&out),"PID identity checked in shared query");
    check(ck_unix_pid_get_uid(42)==(uid_t)-1,"wrong PID cannot provide UID");
    reset(); record.p_uvalid=0; rejected_record("invalid user data rejected");
    int bad_states[]={SIDL,SDYING,SZOMB,SDEAD,0,99};
    for(unsigned i=0;i<G_N_ELEMENTS(bad_states);i++) {
        reset(); record.p_realstat=bad_states[i]; rejected_record("non-live process rejected");
    }
    reset(); record.p_ustart_sec=0; rejected_record("missing process start rejected");
    reset(); record.p_ustart_usec=1000000; rejected_record("invalid start microseconds rejected");
    /* Old code has undefined behavior on null output/no-write snapshots. */
    if (!baseline) {
        reset(); check(!get_kinfo_proc2(42,NULL) && queries==0,"null output before syscall");
        reset(); query_mode=NO_WRITE; rejected_record("zero initialized temporary rejects unwritten result");
    }
    for(int pid=-1;pid<=1;pid++) {
        reset(); memset(&out,0xa5,sizeof(out));
        check(!get_kinfo_proc2(pid,&out) && queries==0,"invalid PID before syscall");
        CkProcessStat *proc=(void *)(uintptr_t)1;
        check(!ck_process_stat_new_for_unix_pid(pid,&proc,NULL),"invalid stat PID rejected");
        check(proc==NULL && allocations==0,"invalid stat initializes output without allocation");
        check(ck_unix_pid_get_uid(pid)==(uid_t)-1,"invalid PID never UID root");
        GHashTable *hash=ck_unix_pid_get_env_hash(pid);
        check(hash==NULL && opens==0,"invalid env PID before KVM open");
        if(hash) g_hash_table_destroy(hash);
    }
    reset(); check(!ck_process_stat_new_for_unix_pid(42,NULL,NULL) && queries==0 && allocations==0,
                   "null stat output does not query or allocate");
    for(int state=SACTIVE;state<=SSTOP;state+=SSTOP-SACTIVE) {
        for(int usec=0;usec<=999999;usec+=999999) {
            reset(); record.p_realstat=state; record.p_ustart_usec=usec;
            check(get_kinfo_proc2(42,&out) && out.p_ustart_usec==(unsigned)usec,"valid full snapshot retained");
            CkProcessStat *proc=NULL;
            check(ck_process_stat_new_for_unix_pid(42,&proc,NULL) && proc,"live stat accepted");
            if(proc) {
                check(proc->pid==42 && proc->session==40 && proc->tty==-1 &&
                      proc->start_time==1700000000 && !strcmp(proc->cmd,"fixture"),"stat fields preserved");
#ifdef CHECK_START_USEC
                check(proc->start_time_usec==(unsigned)usec,"private stat preserves start microseconds");
#endif
                ck_process_stat_free(proc);
            }
            check(allocations==1 && releases==1,"successful stat released");
        }
    }
    reset(); check(ck_unix_pid_get_uid(42)==501,"valid user UID");
    record.p_uid=0; check(ck_unix_pid_get_uid(42)==0,"valid root UID remains accepted");
    reset(); GHashTable *hash=ck_unix_pid_get_env_hash(42);
    check(hash && !strcmp(g_hash_table_lookup(hash,"XDG_SESSION_COOKIE"),"untrusted-locator"),"environment value retained");
    check(opens==1 && closes==1 && env_reads==1,"valid environment closes KVM");
    if(hash) g_hash_table_destroy(hash);
    reset(); env_error=1; hash=ck_unix_pid_get_env_hash(42);
    check(!hash && opens==1 && closes==1 && env_reads==1,"environment read failure closes KVM");
    reset(); open_error=1; hash=ck_unix_pid_get_env_hash(42);
    check(!hash && opens==1 && closes==0 && env_reads==0,"KVM open failure has no close/read");
    if(live) tracked_free(live);
    printf("%d cases, %d failures\n",cases,failures);
    return failures?1:0;
}
