# $NetBSD$
BUILDLINK_TREE+= sha1collisiondetection

.if !defined(SHA1COLLISIONDETECTION_BUILDLINK3_MK)
SHA1COLLISIONDETECTION_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.sha1collisiondetection+= sha1collisiondetection>=1.0.3nb3
BUILDLINK_PKGSRCDIR.sha1collisiondetection?= ../../devel/sha1collisiondetection
.endif

BUILDLINK_TREE+= -sha1collisiondetection
