# PO/QM tool wrapper regression

`poqm-wrapper.py` applies the package patch to the selected upstream ECM module
and builds a small real translation in both direct and wrapped Qt 6 modes.
Pass the selected native CMake, Ninja, C++ compiler, Qt host prefix, unpatched
ECM module directory, patch, gpatch, SDK Python, SDK runtime launcher and runtime
view, Darwin SDK and deployment target as absolute arguments (see `--help`).
The caller keeps the shared SDK locks for the selected Qt work and dependencies
through the test. The test requires no target execution and does not modify Qt.
