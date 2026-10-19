// Select only KDirWatch's existing NetBSD policy after native Qt platform setup.
#include <QtCore/qglobal.h>
#ifndef Q_OS_NETBSD
#define Q_OS_NETBSD
#endif
