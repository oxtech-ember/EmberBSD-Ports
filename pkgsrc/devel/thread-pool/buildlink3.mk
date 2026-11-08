# $NetBSD$

BUILDLINK_TREE+=	thread-pool

.if !defined(THREAD_POOL_BUILDLINK3_MK)
THREAD_POOL_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.thread-pool+=	thread-pool>=5.1.0nb1
BUILDLINK_PKGSRCDIR.thread-pool?=	../../devel/thread-pool
BUILDLINK_DEPMETHOD.thread-pool?=	build
.endif

BUILDLINK_TREE+=	-thread-pool
