/* SPDX-License-Identifier: GPL-2.0-or-later
 * Origin: EmberBSD (AI-assisted). Inject deterministic PCRE2 allocation failures.
 */

extern "C" {
bool kodi_pcre2_fail_compile_context = false;
bool kodi_pcre2_fail_match_context = false;
bool kodi_pcre2_fail_match_data = false;
unsigned int kodi_pcre2_match_context_attempts = 0;

void* __real_pcre2_compile_context_create_8(void*);
void* __real_pcre2_match_context_create_8(void*);
void* __real_pcre2_match_data_create_8(unsigned int, void*);

void* __wrap_pcre2_compile_context_create_8(void* context)
{
  if (kodi_pcre2_fail_compile_context)
    return nullptr;
  return __real_pcre2_compile_context_create_8(context);
}

void* __wrap_pcre2_match_context_create_8(void* context)
{
  ++kodi_pcre2_match_context_attempts;
  if (kodi_pcre2_fail_match_context)
    return nullptr;
  return __real_pcre2_match_context_create_8(context);
}

void* __wrap_pcre2_match_data_create_8(unsigned int count, void* context)
{
  if (kodi_pcre2_fail_match_data)
    return nullptr;
  return __real_pcre2_match_data_create_8(count, context);
}
}
