# Shared source-only Node module installation; each package owns its version,
# archive, checksums, patches and pkgsrc dependency declarations.
NO_CONFIGURE= yes
NO_ARCH= yes
USE_LANGUAGES= # JavaScript source
USE_TOOLS+= find sort
PYTHON_FOR_BUILD_ONLY= tool
JS_MODULE_DEPENDS?=
_JS_MODULE_DIR= ${PREFIX}/lib/node_modules/${JS_MODULE_NAME}
_JS_MODULE_ARGS=
.for _js_dep in ${JS_MODULE_DEPENDS}
DEPENDS+= ${_js_dep:C/^[^=]*=//}
_JS_MODULE_ARGS+= --dependency ${_js_dep:C/=.*//:Q}
.endfor

do-build:
	${TOOL_PYTHONBIN:Q} -B -I -S ${_PKGSRCDIR:Q}/mk/emberbsd-js-validate.py \
	    --source ${WRKSRC:Q} --name ${JS_MODULE_NAME:Q} --version ${PKGVERSION_NOREV:Q} ${_JS_MODULE_ARGS}

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${_JS_MODULE_DIR:H:Q}
	${CP} -R ${WRKSRC:Q} ${DESTDIR:Q}${_JS_MODULE_DIR:Q}

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} lib/node_modules/${JS_MODULE_NAME:Q} \( -type f -o -type l \) -print | ${SORT};
.include "../../lang/python/tool.mk"
