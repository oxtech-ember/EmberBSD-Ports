# SPDX-License-Identifier: MIT
BUILDLINK_TREE+= sqlite3
.if !defined(SQLITE3_BUILDLINK3_MK)
SQLITE3_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.sqlite3+= sqlite3>=3.54.0
BUILDLINK_ABI_DEPENDS.sqlite3+= sqlite3-3.54.0{,nb*}
BUILDLINK_PKGSRCDIR.sqlite3?= ../../local-robotics/sqlite3
GCC_REQD+= 16.2
.endif
BUILDLINK_TREE+= -sqlite3
