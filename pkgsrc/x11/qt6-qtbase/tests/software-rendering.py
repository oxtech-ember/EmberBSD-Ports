#!/usr/bin/env python3
"""Source contract for native Linux and NetBSD cross Qt software rendering."""
from pathlib import Path
import re

pkgdir = Path(__file__).resolve().parents[1]
repo = pkgdir.parents[2]
options = (pkgdir / "options.mk").read_text()
makefile = (pkgdir / "Makefile").read_text()
buildlink3 = (pkgdir / "buildlink3.mk").read_text()
plist = (pkgdir / "PLIST").read_text().splitlines()
runtime_plist = (pkgdir / "PLIST.runtime").read_text().splitlines()
netbsd_plist = (pkgdir / "PLIST.NetBSD").read_text().splitlines()
devel_plist = (pkgdir.parent / "qt6-qtbase-devel" / "PLIST").read_text().splitlines()
stage_selector = (pkgdir / "files/select-package-stage.pl").read_text()
declarative = repo / "pkgsrc/lang/qt6-qtdeclarative"
decl_make = (declarative / "Makefile").read_text()
decl_plist = (declarative / "PLIST").read_text()
def require(ok, message):
    if not ok:
        raise SystemExit("FAIL: " + message)
    print("PASS: " + message)

decl_opengl_rows = [row for row in decl_plist.splitlines() if row.endswith(("QtQuick/QQuickFramebufferObject", "QtQuick/QQuickOpenGLUtils", "QtQuick/qquickframebufferobject.h", "QtQuick/qquickopenglutils.h"))]
require(len(decl_opengl_rows) == 4 and all("${PLIST.opengl}" in row for row in decl_opengl_rows),
        "QtDeclarative OpenGL headers follow PLIST.opengl")
base_buildlink = decl_make.index('.include "../../x11/qt6-qtbase/buildlink3.mk"')
software_guard = decl_make.find(".if empty(PKG_BUILD_OPTIONS.qt6-qtbase:Msoftware-rendering)", base_buildlink)
open_gl_assignment = re.search(r"PLIST\.opengl=\s*yes", decl_make[software_guard:])
end_software_guard = decl_make.find(".endif", software_guard)
require(software_guard >= base_buildlink and open_gl_assignment is not None and end_software_guard > software_guard,
        "QtDeclarative OpenGL PLIST follows QtBase provider options")

option_guard = r'\.if \(\$\{OPSYS\} == "Linux" && \$\{USE_CROSS_COMPILE:Uno:tl\} != "yes"\) \|\| \\\s*\(\$\{OPSYS\} == "NetBSD" && \$\{USE_CROSS_COMPILE:Uno:tl\} == "yes"\)'
require(re.search(option_guard + r'\s+PKG_SUPPORTED_OPTIONS\+=\s+software-rendering\s+\.endif', options) is not None,
        "software-rendering is offered on native Linux and NetBSD cross builds")
require("software-rendering supports native Linux and NetBSD cross builds" in options,
        "software-rendering rejects unsupported host and target roles")
start = options.index(".if !empty(PKG_OPTIONS:Msoftware-rendering)\n")
block = options[start:].split("\n.else\n", 1)[0]
for flag in ("-no-opengl", "-no-feature-egl", "-no-feature-eglfs",
             "-no-feature-eglfs_egldevice", "-no-feature-vulkan",
             "-DFEATURE_egl:BOOL=OFF", "-DFEATURE_eglfs:BOOL=OFF",
             "-DFEATURE_eglfs_egldevice:BOOL=OFF", "-DFEATURE_vulkan:BOOL=OFF"):
    require(flag in block, "software mode disables " + flag)
require("PKG_FAIL_REASON" in block and "host-tools" in block,
        "software-rendering conflicts with host-tools")
require("-no-feature-testlib" not in block and "-no-gui" not in block,
        "software-rendering retains GUI and TestLib")
require(re.search(r'\.if empty\(PKG_BUILD_OPTIONS\.qt6-qtbase:Msoftware-rendering\) && empty\(PKG_BUILD_OPTIONS\.qt6-qtbase:Mvulkan-offscreen\)\s+\.include "\.\./\.\./graphics/glu/buildlink3\.mk"\s+\.endif', buildlink3) is not None,
        "QtBase omits GLU for both no-OpenGL flavors")
require(re.search(r'\.if empty\(PKG_BUILD_OPTIONS\.qt6-qtbase:Msoftware-rendering\)\s+\.include "\.\./\.\./graphics/vulkan-headers/buildlink3\.mk"\s+\.endif', buildlink3) is not None,
        "QtBase retains Vulkan headers in Vulkan offscreen mode")
for dep, guard in (("graphics/glu/buildlink3.mk", ".if empty(PKG_OPTIONS:Msoftware-rendering) && empty(PKG_OPTIONS:Mvulkan-offscreen)"),
                   ("graphics/vulkan-headers/buildlink3.mk", ".if empty(PKG_OPTIONS:Msoftware-rendering)")):
    pos = makefile.index('.include "../../' + dep + '"')
    start_guard = makefile.rfind(guard, 0, pos)
    end_guard = makefile.find(".endif", start_guard)
    require(start_guard >= 0 and end_guard > pos, dep + " follows its feature guard")

def unprefixed(path):
    return re.sub(r"^(?:\$\{PLIST\.[^}]+\})+", "", path)

opengl = [s for s in plist if any(x in unprefixed(s) for x in
          ("/QtOpenGL/", "/QtOpenGLWidgets/", "Qt6OpenGL", "OpenGLWidgets", "libQt6OpenGL"))]
vulkan = [s for s in plist if any(x in unprefixed(s).lower() for x in (
           "qvulkan", "qbasicvulkan", "qrhivulkan", "qplatformvulkan",
           "qwaylandvulkan", "qvulkanserverbufferplugin", "libvulkan-server.so"))]
egl = [s for s in plist if "mkspecs/devices/" not in s and any(x in s for x in ("QtEglFS", "QtEglFs", "qeglfs", "libQt6EglFS", "libQt6EglFs"))]
require(bool(opengl) and all("PLIST.opengl" in s for s in opengl),
        "OpenGL/OpenGLWidgets files follow PLIST.opengl")
require(bool(vulkan) and all("PLIST.vulkan" in s for s in vulkan),
        "Vulkan plugin files follow PLIST.vulkan")
require(bool(egl) and all("PLIST.egl" in s for s in egl),
        "EGL/EGLFS files follow PLIST.egl")

def require_rows(source, fragments, features, label, count=None):
    rows=[row for row in source if any(fragment in unprefixed(row) for fragment in fragments)]
    require(bool(rows) and (count is None or len(rows)==count) and
            all(all("${PLIST."+feature+"}" in row for feature in features) for row in rows), label)

require_rows(plist, ["/QtGui/${PKGVERSION}/QtGui/private/"+name for name in
    ("qeglconvenience_p.h","qeglpbuffer_p.h","qeglplatformcontext_p.h","qeglstreamconvenience_p.h","qt_egl_p.h")],
    ("egl","x11"), "EGL private headers follow PLIST.egl and PLIST.x11", 5)
require_rows(plist, ["/QtGui/${PKGVERSION}/QtGui/private/qglxconvenience_p.h"],
    ("opengl","x11"), "GLX private header follows PLIST.opengl and PLIST.x11", 1)
require_rows(plist, ["/QtGui/${PKGVERSION}/QtGui/private/"+name for name in
    ("qopengl_p.h","qopenglcontext_p.h","qopenglextensions_p.h","qopenglprogrambinarycache_p.h","qrhigles2_p.h")] +
    ["qt6/include/QtGui/qopenglcontext_platform.h"],
    ("opengl",), "OpenGL private headers follow PLIST.opengl", 6)
require_rows(plist, ["qt6/metatypes/qt6opengl_metatypes.json","qt6/metatypes/qt6openglwidgets_metatypes.json"],
    ("opengl",), "OpenGL metatypes follow PLIST.opengl", 2)
cmake_families = (
    ("Qt6DmaBufServerBufferPlugin", ("wayland","x11","egl","opengl")),
    ("Qt6DrmEglServerBufferPlugin", ("wayland","x11","egl","opengl")),
    ("Qt6QVkKhrDisplayIntegrationPlugin", ("vulkan","x11")),
    ("Qt6QWaylandEglClientBufferPlugin", ("wayland","x11","egl","opengl")),
    ("Qt6QXcbEglIntegrationPlugin", ("egl","x11")),
    ("Qt6QXcbGlxIntegrationPlugin", ("opengl","x11")),
    ("Qt6ShmServerBufferPlugin", ("wayland","x11","opengl")),
)
for family, features in cmake_families:
    require_rows(plist, ["qt6/lib/cmake/Qt6Gui/"+family], features,
                 family+" CMake files follow its plugin feature guard", 7)
require_rows(plist, ["qt6/include/QtGui/${PKGVERSION}/QtGui/private/qxdgdesktopportalfiletransfer_p.h"],
    ("dbus","wayland"), "QtGui portal transfer header remains declared for DBus and Wayland", 1)
require("QT_FEATURE_xdg_desktop_portal_file_transfer:INTERNAL=" in stage_selector and
        "qxdgdesktopportalfiletransfer_p" in stage_selector,
        "QtGui portal header selection follows the generated CMake feature")
protocol_xml="qt6/share/qt6/wayland/extensions/qt-vulkan-server-buffer-unstable-v1.xml"
protocol_rows=[row for row in plist if unprefixed(row)==protocol_xml]
require(len(protocol_rows)==1 and "${PLIST.vulkan}" not in protocol_rows[0],
        "Vulkan-named protocol XML follows upstream unconditional Wayland extension install")
provider_rows = {
    "libqvkkhrdisplay.so": ("vulkan", "x11"),
    "libdmabuf-server.so": ("wayland", "x11", "egl", "opengl"),
    "libdrm-egl-server.so": ("wayland", "x11", "egl", "opengl"),
    "libqt-plugin-wayland-egl.so": ("wayland", "x11", "egl", "opengl"),
    "libshm-emulation-server.so": ("wayland", "x11", "opengl"),
    "libqxcb-glx-integration.so": ("opengl",),
}
for plist_name, source_plist in (("native PLIST", plist), ("target runtime PLIST", runtime_plist)):
    for filename, features in provider_rows.items():
        rows=[row for row in source_plist if unprefixed(row).endswith(filename)]
        require(len(rows)==1 and all("${PLIST."+feature+"}" in rows[0] for feature in features),
                plist_name+": "+filename+" follows "+"/".join("PLIST."+f for f in features))
require(not any("qxdgdesktopportalfiletransfer_p.h" in row for row in runtime_plist),
        "runtime PLIST remains free of QtGui development private headers")
require("PLIST.opengl" not in protocol_rows[0], "Wayland protocol XML is not hidden by software-rendering OpenGL selection")

require("full-tools-required.mk" in decl_make and "QtQuickTest/" in decl_plist,
        "full QtDeclarative retains QuickTest")

def manifest_rows(rows):
    return [row for row in rows if row and not row.startswith("@comment")]
def guards(row):
    return re.findall(r"\$\{PLIST\.([^}]+)\}", row)
def path(row):
    return re.sub(r"^(?:\$\{PLIST\.[^}]+\})+", "", row)
full_rows = manifest_rows(netbsd_plist + plist)
full_guards = {}
for row in full_rows:
    key = path(row)
    if key in full_guards and full_guards[key] != guards(row):
        raise SystemExit("FAIL: complete PLIST has ambiguous feature guards: " + key)
    full_guards[key] = guards(row)
runtime_rows = manifest_rows(runtime_plist)
devel_rows = manifest_rows(devel_plist)
runtime_paths = {path(row) for row in runtime_rows}
devel_paths = {path(row) for row in devel_rows}
require(not runtime_paths & devel_paths and runtime_paths | devel_paths == set(full_guards),
        "target runtime and SDK PLISTs form the complete independent NetBSD manifest")
guard_errors = []
for label, rows in (("target runtime", runtime_rows), ("target SDK", devel_rows)):
    for row in rows:
        key = path(row)
        if key not in full_guards or guards(row) != full_guards[key]:
            guard_errors.append(label + ": " + key)
require(not guard_errors,
        "target partitions preserve complete-PLIST guards" +
        (" (" + str(len(guard_errors)) + " mismatches: " + ", ".join(guard_errors[:3]) + ")" if guard_errors else ""))
# Native generator GUI keeps Unix support while opting out of X11/XCB.
require("headless-generators" in options, "native GUI generator role is explicit")
require("-DFEATURE_xcb:BOOL=OFF" in options and "-DFEATURE_xlib:BOOL=OFF" in options,
        "headless generator disables XCB and Xlib")
headless_guard = makefile.index('.if empty(PKG_OPTIONS:Mheadless-generators) && empty(PKG_OPTIONS:Mvulkan-offscreen)')
headless_end = makefile.index('\n.endif', headless_guard)
headless_block = makefile[headless_guard:headless_end]
for dependency in ('libxcb', 'libX11', 'libXext', 'libXcursor', 'libXft', 'libXi',
                   'libXmu', 'libXrandr', 'libXrender', 'libxkbcommon'):
    require('/' + dependency + '/buildlink3.mk' in headless_block,
            dependency + ' stays outside the headless generator dependency graph')
require('PLIST.xcb=\tyes' in headless_block and 'PLIST.x11=\tyes' in makefile[:headless_guard],
        'default retains XCB and headless keeps Unix-specific PLIST entries')
for label, rows in (("full", plist), ("runtime", runtime_plist), ("devel", devel_plist)):
    for row in rows:
        clean = unprefixed(row).lower()
        if any(x in clean for x in ("qt6qxcbintegrationplugin", "qt6qxcbeglintegrationplugin",
                                     "qt6qxcbglxintegrationplugin", "qt6xcbqpa", "libqxcb",
                                     "/xcbglintegrations/", "xcbqpaprivate", "qt_lib_xcb_qpa")):
            require("${PLIST.xcb}" in row, label + " XCB file lacks XCB guard: " + clean)
print("PASS: software-rendering recipe contract")
