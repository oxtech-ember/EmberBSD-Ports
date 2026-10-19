/* SPDX-License-Identifier: GPL-2.0-or-later
 * Origin: EmberBSD (AI-assisted). Exercise the real Kodi CRegExp consumer.
 */
#include "RegExp.h"
#include "log.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <string>

static unsigned checks;
static unsigned skips;

#if defined(KODI_PCRE2_FAULT_TESTS)
extern "C" bool kodi_pcre2_fail_compile_context;
extern "C" bool kodi_pcre2_fail_match_context;
extern "C" bool kodi_pcre2_fail_match_data;
extern "C" unsigned int kodi_pcre2_match_context_attempts;
#endif

static void check(bool result, const char* message)
{
  ++checks;
  if (!result)
  {
    std::fprintf(stderr, "FAIL: %s\n", message);
    std::exit(1);
  }
}

static void functional()
{
  CRegExp re;
  check(re.RegFind("x") == -1, "reject matching before compilation");
  check(CLog::calls > 0, "report matching error");
  check(re.RegComp("(?<word>[a-z]+)-(\\d+)"), "compile named captures");
  check(re.RegFind("++abc-42!") == 2, "match at independent expected offset");
  check(re.GetFindLen() == 6, "full capture length");
  check(re.GetMatch() == "abc-42", "full capture bytes");
  check(re.GetMatch(1) == "abc", "first capture bytes");
  check(re.GetMatch(2) == "42", "second capture bytes");
  check(re.GetSubStart(3) == -1, "reject capture index equal to match count");
  check(re.GetMatch("word") == "abc", "named capture bytes");
  check(re.GetReplaceString("\\1/\\2") == "abc/42", "capture replacement");
  check(re.RegFind("abc-42", 20) == -1, "reject offset beyond subject");
  check(re.RegFind(nullptr) == -1, "reject null subject");
  check(!re.RegComp("("), "reject malformed pattern");
  check(!re.IsCompiled(), "failed compilation clears state");
  check(re.GetMatch().empty(), "failed compilation exposes no captures");
  check(re.RegComp("^$"), "compile empty pattern match");
  check(re.RegFind(std::string()) == 0, "empty subject matches");
  check(re.GetFindLen() == 0, "empty capture length");
  check(re.RegComp("a.b"), "compile binary subject pattern");
  const std::string binary("a\0b", 3);
  check(re.RegFind(binary) == 0, "match subject containing NUL");
  check(re.GetMatch() == binary, "retain embedded NUL capture");
  CRegExp utf8(false, CRegExp::forceUtf8);
  check(utf8.RegComp("^\\p{L}+$"), "compile Unicode property pattern");
  check(utf8.RegFind("Привет") == 0, "match Unicode letters");
  check(utf8.GetMatch() == "Привет", "retain Unicode capture bytes");
  check(utf8.RegFind("Привет2") == -1, "reject non-letter suffix");
  const std::string malformed("\xff", 1);
  check(utf8.RegFind(malformed) == -1, "reject malformed UTF-8");
  CRegExp freshUtf8(false, CRegExp::forceUtf8);
  check(freshUtf8.RegComp("^\\p{L}+$"), "compile Unicode pattern for first malformed subject");
  check(freshUtf8.RegFind(malformed) == -1, "reject malformed UTF-8 on first match");
  check(freshUtf8.GetMatch().empty(), "first malformed subject exposes no captures");
}

static void copied_match()
{
  std::unique_ptr<CRegExp> copied;
  {
    CRegExp source;
    check(source.RegComp("([a-z]+)-(\\d+)"), "compile source for copy");
    check(source.RegFind("++abc-42!") == 2, "match source for copy");
    copied = std::make_unique<CRegExp>(source);
  }
  check(copied->GetMatch(1) == "abc", "copy owns captures after source destruction");
  check(copied->GetMatch(2) == "42", "copy retains second capture");
  *copied = *copied;
  check(copied->GetMatch(1) == "abc", "self-assignment preserves captures");
  check(copied->RegFind("xy-9") == 0, "copied expression matches independently");
  check(copied->GetMatch(1) == "xy", "copied match updates only its own data");
  CRegExp assigned;
  assigned = *copied;
  check(copied->RegComp("z"), "recompile copied source");
  check(assigned.GetMatch(2) == "9", "assignment owns capture state");
  check(assigned.RegFind("q-7") == 0, "assigned expression retains code");
  CRegExp empty;
  assigned = empty;
  check(!assigned.IsCompiled(), "assignment from empty clears pattern");
  check(assigned.GetMatch().empty(), "assignment from empty clears captures");
}

static void named_lookup_after_failed_compile()
{
  CRegExp re;
  check(!re.RegComp("("), "compile malformed pattern before named lookup");
  check(re.GetMatch("missing").empty(), "reject named match without compiled code");
  check(re.GetSubStart("missing") == -1, "reject named start without compiled code");
  check(re.GetSubLength("missing") == -1, "reject named length without compiled code");
  std::string match = "stale";
  check(!re.GetNamedSubPattern("missing", match) && match.empty(),
        "reject named pattern without compiled code");
  check(re.GetNamedSubPatternNumber("missing") < 0,
        "reject named number without compiled code");
}

#if defined(KODI_PCRE2_FAULT_TESTS)
static void allocation_failures()
{
  CRegExp compile;
  kodi_pcre2_fail_compile_context = true;
  check(!compile.RegComp("a"), "report compile-context allocation failure");
  check(!compile.IsCompiled(), "failed compile-context allocation leaves no pattern");
  check(compile.GetMatch("missing").empty(),
        "reject named match after compile-context allocation failure");
  kodi_pcre2_fail_compile_context = false;

  CRegExp match;
  check(match.RegComp("a"), "compile before match-data allocation failure");
  kodi_pcre2_fail_match_data = true;
  check(match.RegFind("a") == -1, "report match-data allocation failure");
  check(match.GetMatch().empty(), "match-data failure exposes no capture");
  kodi_pcre2_fail_match_data = false;

  if (CRegExp::IsJitSupported())
  {
    CRegExp jit;
    check(jit.RegComp("a", CRegExp::StudyWithJitComp), "compile JIT allocation case");
    const unsigned int attempts = kodi_pcre2_match_context_attempts;
    kodi_pcre2_fail_match_context = true;
    const int result = jit.RegFind("a");
    kodi_pcre2_fail_match_context = false;
    if (kodi_pcre2_match_context_attempts == attempts)
      ++skips;
    else
    {
      check(result == -1, "report match-context allocation failure");
      check(jit.GetMatch().empty(), "match-context failure exposes no capture");
    }
  }
  else
    ++skips;
}
#endif

int main(int argc, char** argv)
{
  PCRE2_UCHAR version[32]{};
  const int configResult = pcre2_config(PCRE2_CONFIG_VERSION, version);
  check(configResult >= 0 && version[0] != 0, "read PCRE2 runtime version");
  check(std::strncmp(reinterpret_cast<const char*>(version), "10.49", 5) == 0,
        "use selected PCRE2 10.49 provider");
  std::printf("PCRE2 runtime: %s\n", reinterpret_cast<const char*>(version));
  if (argc == 2 && std::strcmp(argv[1], "--copy") == 0)
    copied_match();
  else if (argc == 2 && std::strcmp(argv[1], "--named-after-failure") == 0)
    named_lookup_after_failed_compile();
  else
  {
    functional();
    copied_match();
    named_lookup_after_failed_compile();
#if defined(KODI_PCRE2_FAULT_TESTS)
    allocation_failures();
#endif
  }
  std::printf("PASS: %u Kodi RegExp checks; skips=%u\n", checks, skips);
  return 0;
}
