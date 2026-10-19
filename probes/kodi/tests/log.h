/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD (AI-assisted). Diagnostic observer for source-only tests.
 * Production logging is outside this focused RegExp contract.
 */
#pragma once
enum { LOGDEBUG, LOGINFO, LOGWARNING, LOGERROR, LOGFATAL, LOGNONE };
struct CLog
{
  inline static unsigned calls;
  template<class... Args>
  static void Log(int, const char*, Args&&...)
  {
    ++calls;
  }
};
