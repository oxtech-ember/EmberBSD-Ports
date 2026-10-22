// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted). Installed OCCT8 STEP geometry contract.
#include <BRepBndLib.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <Bnd_Box.hxx>
#include <GProp_GProps.hxx>
#include <IFSelect_ReturnStatus.hxx>
#include <STEPControl_Reader.hxx>
#include <STEPControl_Writer.hxx>
#include <Standard_Failure.hxx>
#include <TopAbs_ShapeEnum.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS_Shape.hxx>
#include <cerrno>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <unistd.h>

static void require(bool condition, const char* message)
{
  if (!condition)
    throw std::runtime_error(message);
}

static void checkGeometry(const TopoDS_Shape& shape, double expectedVolume,
                          double volumeTolerance, const char* stage)
{
  require(!shape.IsNull(), "Geometry is null");
  require(BRepCheck_Analyzer(shape, true).IsValid(), "BRep validity failed");
  int solids = 0;
  for (TopExp_Explorer it(shape, TopAbs_SOLID); it.More(); it.Next())
    ++solids;
  require(solids == 1, "Expected exactly one solid");
  GProp_GProps properties;
  BRepGProp::VolumeProperties(shape, properties, true, false, false);
  const double volume = properties.Mass();
  std::printf("%s volume=%.17g expected=%.17g tolerance=%.17g\n",
              stage, volume, expectedVolume, volumeTolerance);
  require(std::isfinite(volume) && std::abs(volume - expectedVolume) <= volumeTolerance,
          "Geometry volume differs from the independent expected value");
  Bnd_Box bounds;
  BRepBndLib::AddOptimal(shape, bounds, false, false);
  require(!bounds.IsVoid() && !bounds.IsOpen(), "Geometry bounds are unavailable");
  double x0, y0, z0, x1, y1, z1;
  bounds.Get(x0, y0, z0, x1, y1, z1);
  constexpr double tolerance = 1e-7;
  const double actual[] = {x0, y0, z0, x1, y1, z1};
  const double expected[] = {0.0, 0.0, 0.0, 1.0, 2.0, 3.0};
  for (unsigned i = 0; i < 6; ++i)
    require(std::isfinite(actual[i]) && std::abs(actual[i] - expected[i]) <= tolerance,
            "Geometry bounds differ from the independent expected values");
}

static void roundTrip(const char* path, double expectedVolume)
{
  const TopoDS_Shape original = BRepPrimAPI_MakeBox(1.0, 2.0, 3.0).Shape();
  checkGeometry(original, 6.0, 1e-12, "SOURCE");
  {
    STEPControl_Writer writer;
    require(writer.Transfer(original, STEPControl_ManifoldSolidBrep) == IFSelect_RetDone,
            "STEP writer transfer failed");
    require(writer.Write(path) == IFSelect_RetDone, "STEP file write failed");
  }
  STEPControl_Reader reader;
  require(reader.ReadFile(path) == IFSelect_RetDone, "STEP file read failed");
  require(reader.NbRootsForTransfer() == 1, "STEP root count differs");
  require(reader.TransferRoots() == 1 && reader.NbShapes() == 1,
          "STEP reader transfer count differs");
  std::puts("STEP_TRANSFER_DONE roots=1 shapes=1");
  checkGeometry(reader.OneShape(), expectedVolume, 1e-8, "READBACK");
  std::puts("STEP_ROUNDTRIP_PASS");
}

int main(int argc, char** argv)
{
  const bool roundtrip = argc >= 2 && std::strcmp(argv[1], "roundtrip") == 0;
  const bool malformed = argc == 2 && std::strcmp(argv[1], "malformed") == 0;
  const bool missing = argc == 2 && std::strcmp(argv[1], "missing") == 0;
  if ((!roundtrip && !malformed && !missing) || (roundtrip && argc != 3))
  {
    std::fputs("Usage: occt-step roundtrip EXPECTED_VOLUME | malformed | missing\n", stderr);
    return 2;
  }
  double expected = 6.0;
  if (roundtrip)
  {
    char* tail = nullptr;
    errno = 0;
    expected = std::strtod(argv[2], &tail);
    if (errno || tail == argv[2] || *tail != '\0' || !std::isfinite(expected) || expected <= 0)
      return 2;
  }
  char directory[] = "./occt-step-XXXXXX";
  if (::mkdtemp(directory) == nullptr)
  {
    std::perror("mkdtemp");
    return 1;
  }
  char path[sizeof(directory) + sizeof("/shape.step")];
  std::snprintf(path, sizeof(path), "%s/shape.step", directory);
  int result = 0;
  try
  {
    if (roundtrip)
      roundTrip(path, expected);
    else
    {
      if (malformed)
      {
        std::ofstream file(path, std::ios::binary);
        file << "This is not an ISO-10303-21 STEP file.\n";
        file.close();
        require(file.good(), "Cannot write malformed STEP fixture");
      }
      STEPControl_Reader reader;
      const IFSelect_ReturnStatus status = reader.ReadFile(path);
      require(status != IFSelect_RetDone, "Invalid or missing STEP input was accepted");
      std::printf("STEP_READ_REFUSED mode=%s status=%d\n", argv[1], static_cast<int>(status));
    }
  }
  catch (const Standard_Failure& error)
  {
    std::fprintf(stderr, "OCCT failure: %s\n", error.what());
    result = 1;
  }
  catch (const std::exception& error)
  {
    std::fprintf(stderr, "Contract failure: %s\n", error.what());
    result = 1;
  }
  const bool fileRemoved = ::unlink(path) == 0 || errno == ENOENT;
  const bool directoryRemoved = ::rmdir(directory) == 0;
  const bool cleaned = fileRemoved && directoryRemoved;
  std::printf("owned_fixture_cleanup=%d\n", cleaned ? 0 : 1);
  return cleaned ? result : 1;
}
