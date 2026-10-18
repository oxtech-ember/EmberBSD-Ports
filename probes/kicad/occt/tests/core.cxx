// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Installed core API, locale, path and exception checks.
#include <NCollection_Array1.hxx>
#include <OSD_Path.hxx>
#include <Standard_CLocaleSentry.hxx>
#include <Standard_CString.hxx>
#include <Standard_Failure.hxx>
#include <Standard_OutOfRange.hxx>
#include <TCollection_AsciiString.hxx>
#include <clocale>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <string>

static void require(bool condition, const char* message)
{
  if (!condition)
    throw std::runtime_error(message);
}

int main(int argc, char** argv)
{
  if (argc != 2)
    return 2;
  try
  {
    require(std::setlocale(LC_ALL, argv[1]) != nullptr, "Requested locale is unavailable");
    const std::string original = std::setlocale(LC_ALL, nullptr);
    char nativeBefore[64], nativeAfter[64], value[64];
    std::snprintf(nativeBefore, sizeof(nativeBefore), "%.2f", 12.5);
    require(Standard_CLocaleSentry::GetCLocale() != nullptr, "No explicit C locale");
    Sprintf(value, "%.2f", 12.5);
    require(std::strcmp(value, "12.50") == 0, "OCCT formatting used the process locale");
    char* tail = nullptr;
    require(std::abs(Strtod("12.50end", &tail) - 12.5) < 1e-12 && std::strcmp(tail, "end") == 0,
            "OCCT parsing did not use the C locale");
    std::snprintf(nativeAfter, sizeof(nativeAfter), "%.2f", 12.5);
    require(std::strcmp(nativeBefore, nativeAfter) == 0 && original == std::setlocale(LC_ALL, nullptr),
            "OCCT conversion changed the process locale");
    {
      Standard_CLocaleSentry sentry;
      require(std::abs(std::strtod("12.50", nullptr) - 12.5) < 1e-12, "C locale sentry failed");
    }
    require(original == std::setlocale(LC_ALL, nullptr), "C locale sentry did not restore the locale");
    OSD_Path path(TCollection_AsciiString("/usr/pkg/share/fixture.step"));
    OSD_Path copied = path;
    TCollection_AsciiString result;
    copied.SystemName(result);
    require(result.IsEqual("/usr/pkg/share/fixture.step"), "Unix path round trip failed");
    bool caught = false;
    try { throw Standard_Failure("occt8 exception contract"); }
    catch (const Standard_Failure& failure)
    { caught = std::strcmp(failure.what(), "occt8 exception contract") == 0; }
    require(caught, "Standard_Failure what() contract failed");
    NCollection_Array1<int> array(1, 2);
    caught = false;
    try { (void)array.Value(0); }
    catch (const Standard_OutOfRange&) { caught = true; }
    require(caught, "Range checks were disabled by No_Exception");
    std::printf("OCCT core locale=%s process-number=%s: PASS\n", argv[1], nativeAfter);
    return 0;
  }
  catch (const std::exception& failure)
  {
    std::fprintf(stderr, "%s\n", failure.what());
    return 1;
  }
}
