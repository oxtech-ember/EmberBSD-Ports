The mkspecs regression invokes QtBase's actual install helper during two
in-source CMake configurations. It creates the temporary `preliminary` directory
after the first helper call, as Qt does, and checks both installation and the
`QT_WILL_INSTALL` configure-time copy. The original helper leaks the temporary
files on the second pass; the patched helper retains ordinary mkspecs and the
final `qmodule.pri` while leaving the temporary files in the build tree.

Run `python3 test-mkspecs-reconfigure.py CMAKE QTBASE_SOURCE PATCH` with the
selected CMake, an unpatched QtBase source tree and the pkgsrc patch.
