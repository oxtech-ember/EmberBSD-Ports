The mkspecs regression invokes QtBase's actual install helper during two
in-source CMake configurations. It creates the temporary `preliminary` directory
after the first helper call, as Qt does, and checks both installation and the
`QT_WILL_INSTALL` configure-time copy. The original helper leaks the temporary
files on the second pass; the patched helper retains ordinary mkspecs and the
final `qmodule.pri` while leaving the temporary files in the build tree.

Run `python3 test-mkspecs-reconfigure.py CMAKE QTBASE_SOURCE PATCH` with the
selected CMake, an unpatched QtBase source tree and the pkgsrc patch.

## Split package revision metadata

Run with an explicit bmake and existing scratch directory:

```sh
python3 package-revisions.py --bmake /absolute/bmake --work-parent /absolute/scratch
```

This evaluates the actual runtime/devel recipe conditions, with external pkgsrc
includes stubbed. Both cross architectures, native selection, rejected revision
overrides and a simulated runtime revision edit are covered. It checks that the
exact dependency and refusal checks follow the single declaration. Native
identity and the independent devel identity stay unchanged by that edit;
publishing changed dependency metadata still requires the appropriate revision.
This is a metadata check, not a package build or lifecycle acceptance.
