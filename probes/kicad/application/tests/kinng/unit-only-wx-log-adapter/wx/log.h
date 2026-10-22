/* SPDX-License-Identifier: BSD-2-Clause */
/* Unit-test logging adapter only. Never use this header in KiCad builds. */
#ifndef EMBERBSD_KINNG_UNIT_LOG_ADAPTER_H
#define EMBERBSD_KINNG_UNIT_LOG_ADAPTER_H
using wxChar = char;
#define wxT(text) text
#define wxS(text) text
class wxString
{
public:
    template<typename... Arguments>
    static const char* Format( const char* text, Arguments... ) { return text; }
};
inline void wxLogTrace( const char*, const char* ) {}
#endif
