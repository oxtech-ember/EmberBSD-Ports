BUILDLINK_TREE+= tdesktop-rust
.if !defined(TDESKTOP_RUST_BUILDLINK3_MK)
TDESKTOP_RUST_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.tdesktop-rust+= tdesktop-rust>=0.1.0
BUILDLINK_PKGSRCDIR.tdesktop-rust?= ../../devel/tdesktop-rust
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && \
    (!empty(EMBER_LLVM_CXX_STAGE:U) || !empty(EMBER_LLVM_CXX_SYSROOT:U))
.include "../../lang/libunwind/buildlink3.mk"
.endif
.endif
BUILDLINK_TREE+= -tdesktop-rust
