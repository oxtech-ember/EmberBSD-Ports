BUILDLINK_TREE+= tdesktop-rust
.if !defined(TDESKTOP_RUST_BUILDLINK3_MK)
TDESKTOP_RUST_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.tdesktop-rust+= tdesktop-rust>=0.1.0
BUILDLINK_PKGSRCDIR.tdesktop-rust?= ../../devel/tdesktop-rust
.endif
BUILDLINK_TREE+= -tdesktop-rust
