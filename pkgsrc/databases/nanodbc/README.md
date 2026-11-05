# nanodbc

The common provider follows the [upstream 3.0.8 release](https://github.com/nanodbc/nanodbc/releases/tag/v3.0.8).
It installs `nanodbc::nanodbc` and `<nanodbc/nanodbc.h>`. The CMake target
exports its Unicode ABI flags and shared unixODBC/Boost.Locale dependencies.
Consumers use `nanodbc::string` and the target interface rather than choosing
a conflicting character ABI locally.

The SDK selects the compiler and C++ runtime; the library's automatic libc++
selection is disabled. Tests and examples are separate from the library.
The packaging patch makes the installed CMake config import its dependencies
and assigns the library's major-version SONAME.
