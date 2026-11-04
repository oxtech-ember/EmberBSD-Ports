# Shared source-only Node module installation; each package owns its version,
# archive, checksums, patches and pkgsrc dependency declarations.
# Executable scripts need a fixed interpreter in the selected package prefix.
.if !empty(REPLACE_NODEJS:U)
DEPENDS+= nodejs>=26:../../lang/nodejs
.include "../../lang/nodejs/application.mk"
do-configure:
	${DO_NADA}
.else
NO_CONFIGURE= yes
.endif
NO_ARCH= yes
USE_LANGUAGES= # JavaScript source
USE_TOOLS+= find sort
PYTHON_FOR_BUILD_ONLY= tool
JS_MODULE_DEPENDS?=
# Mandatory peers supplied by the consuming runtime, not this source package.
# The consumer must validate the installed package.json peer ranges.
JS_MODULE_EXTERNAL_PEERS?=
.if !empty(JS_MODULE_EXTERNAL_PEERS)
BUILD_DEFS+= JS_MODULE_EXTERNAL_PEERS
.endif
_JS_MODULE_DIR= ${PREFIX}/lib/node_modules/${JS_MODULE_NAME}
_JS_MODULE_ARGS=
.for _js_dep in ${JS_MODULE_DEPENDS}
DEPENDS+= ${_js_dep:C/^[^=]*=//}
_JS_MODULE_ARGS+= --dependency ${_js_dep:C/=.*//:Q}
.endfor
.for _js_peer in ${JS_MODULE_EXTERNAL_PEERS}
_JS_MODULE_ARGS+= --external-peer ${_js_peer:Q}
.endfor

do-build:
	${TOOL_PYTHONBIN:Q} -B -I -S ${_PKGSRCDIR:Q}/mk/emberbsd-js-validate.py \
	    --source ${WRKSRC:Q} --name ${JS_MODULE_NAME:Q} --version ${PKGVERSION_NOREV:Q} ${_JS_MODULE_ARGS}

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${_JS_MODULE_DIR:H:Q}
	${CP} -R ${WRKSRC:Q} ${DESTDIR:Q}${_JS_MODULE_DIR:Q}

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} lib/node_modules/${JS_MODULE_NAME:Q} \( -type f -o -type l \) -print | ${SORT};
.include "../../lang/python/tool.mk"
