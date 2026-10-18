// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Exercise actual exception trace allocation.
#include <Standard_Failure.hxx>
#include <climits>
#include <cstdio>
#include <cstring>

int main(int argc, char** argv)
{
  if (argc != 2)
    return 2;
  int frames = 0;
  if (std::strcmp(argv[1], "negative") == 0)
    frames = -1;
  else if (std::strcmp(argv[1], "zero") == 0)
    frames = 0;
  else if (std::strcmp(argv[1], "small") == 0)
    frames = 1;
  else if (std::strcmp(argv[1], "below-cap") == 0)
    frames = 327;
  else if (std::strcmp(argv[1], "above-cap") == 0)
    frames = 328;
  else if (std::strcmp(argv[1], "overflow") == 0)
    frames = INT_MAX;
  else
    return 2;
  const int previous = Standard_Failure::DefaultStackTraceLength();
  Standard_Failure::SetDefaultStackTraceLength(frames);
  const Standard_Failure failure("bounded failure");
  Standard_Failure::SetDefaultStackTraceLength(previous);
  if (std::strcmp(failure.what(), "bounded failure") != 0)
    return 1;
  const bool trace = failure.GetStackString()[0] != '\0';
  if (trace != (frames > 0 && frames != INT_MAX))
    return 1;
  std::puts("Exception message and bounded trace: PASS");
  return 0;
}
