PKG_OPTIONS_VAR=	PKG_OPTIONS.rust-bin
PKG_SUPPORTED_OPTIONS=	doc

.include "../../mk/bsd.options.mk"

.if empty(PKG_OPTIONS:Mdoc)
# The installer removes component names by substring; remove the longer
# overlapping component first.
RUST_INSTALLER_ARGS+=	--without=rust-docs-json-preview,rust-docs
.endif
