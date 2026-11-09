// Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT
// Exercise the installed shared provider, including ownership on failed reads.
#include <dl_dxf.h>
#include <dl_creationadapter.h>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <fcntl.h>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

static void check(bool ok, const char* message)
{
    if (!ok)
    {
        std::fprintf(stderr, "FAIL: %s\n", message);
        std::exit(1);
    }
}

static const char input[] =
    "0\nSECTION\n2\nENTITIES\n"
    "0\nPOINT\n10\n1.25\n20\n-2.5\n30\n3.75\n39\n0.75\n"
    "0\nPOINT\n10\n4\n20\n5\n30\n6\n"
    "0\nPOLYLINE\n66\n1\n70\n0\n"
    "0\nVERTEX\n10\n1\n20\n2\n30\n3\n42\n0.5\n40\n250\n41\n375\n"
    "0\nVERTEX\n10\n4\n20\n5\n30\n6\n"
    "0\nSEQEND\n0\nENDSEC\n0\nEOF\n";

struct Capture : DL_CreationAdapter
{
    std::vector<DL_PointData> points;
    std::vector<DL_VertexData> vertices;
    unsigned pairs = 0;
    void processCodeValuePair(unsigned, const std::string&) override { ++pairs; }
    void addPoint(const DL_PointData& point) override { points.push_back(point); }
    void addVertex(const DL_VertexData& vertex) override { vertices.push_back(vertex); }
    void verify() const
    {
        check(points.size() == 2 && vertices.size() == 2, "entity callbacks");
        check(points[0].x == 1.25 && points[0].y == -2.5 && points[0].z == 3.75 &&
              points[0].thickness == 0.75, "POINT coordinates and group 39");
        check(points[1].thickness == 0.0, "missing POINT thickness defaults to zero");
        check(vertices[0].x == 1 && vertices[0].y == 2 && vertices[0].z == 3 &&
              vertices[0].bulge == 0.5 && vertices[0].startWidth == 250 &&
              vertices[0].endWidth == 375, "VERTEX groups 40/41 and existing data");
        check(vertices[1].startWidth == 0 && vertices[1].endWidth == 0,
              "missing VERTEX widths default to zero");
    }
};

static void check_closed(int fd)
{
    errno = 0;
    check(fcntl(fd, F_GETFD) == -1 && errno == EBADF, "reader closes owned FILE");
}

struct CommaDecimal : std::numpunct<char>
{
    char do_decimal_point() const override { return ','; }
};

struct ThrowingCapture : DL_CreationAdapter
{
    void addPoint(const DL_PointData&) override { throw std::runtime_error("callback"); }
};

int main(int argc, char** argv)
{
    check(argc == 2, "provide a writable test directory");
    const std::string path = std::string(argv[1]) + u8"/DXF-кириллица-線.dxf";
    FILE* fp = std::fopen(path.c_str(), "wb");
    check(fp != nullptr, "create Unicode filename");
    check(std::fwrite(input, 1, sizeof(input) - 1, fp) == sizeof(input) - 1,
          "write fixture");
    check(std::fclose(fp) == 0, "close fixture writer");

    const std::locale prior = std::locale();
    const std::locale comma(prior, new CommaDecimal);
    std::locale::global(comma);
    DL_Dxf reader;
    Capture capture;
    fp = std::fopen(path.c_str(), "rb");
    check(fp != nullptr, "open Unicode file outside parser");
    const int fd = fileno(fp);
    check(reader.in(fp, &capture), "owned FILE import");
    check_closed(fd);
    check(std::locale() == comma, "restore caller locale after import");
    capture.verify();

    Capture by_path;
    check(reader.in(path, &by_path), "existing path overload");
    by_path.verify();
    check(std::locale() == comma, "restore caller locale after path import");
    check(!reader.in(static_cast<FILE*>(nullptr), &capture), "null FILE refusal");
    check(!reader.in(path + ".missing", &capture), "missing path refusal");

    ThrowingCapture throwing;
    fp = std::fopen(path.c_str(), "rb");
    check(fp != nullptr, "open callback failure fixture");
    const int throwing_fd = fileno(fp);
    bool caught = false;
    try { reader.in(fp, &throwing); }
    catch (const std::runtime_error&) { caught = true; }
    check(caught, "callback exception propagates");
    check_closed(throwing_fd);
    check(std::locale() == comma, "restore caller locale after callback exception");

    // Reading a write-only stream reports ferror without necessarily setting
    // EOF. The parser must terminate, return false, and close it exactly once.
    fp = std::fopen(path.c_str(), "wb");
    check(fp != nullptr, "open write-only fixture");
    const int error_fd = fileno(fp);
    const unsigned pairs_before_error = capture.pairs;
    check(!reader.in(fp, &capture), "I/O failure is not successful EOF");
    check(capture.pairs == pairs_before_error, "I/O failure emits no stale group callback");
    check_closed(error_fd);
    check(std::locale() == comma, "restore caller locale after I/O failure");

    std::istringstream stream(input);
    Capture borrowed;
    check(reader.in(stream, &borrowed), "borrowed stream import");
    borrowed.verify();
    check(std::locale() == comma, "restore caller locale after stream import");
    stream.clear();
    stream.seekg(0);
    check(stream.peek() == '0', "borrowed stream remains usable");
    caught = false;
    try { reader.in(stream, &throwing); }
    catch (const std::runtime_error&) { caught = true; }
    check(caught && std::locale() == comma, "stream callback exception restores locale");
    stream.clear();
    stream.seekg(0);
    check(stream.peek() == '0', "stream exception does not consume ownership");
    std::istringstream oversized(std::string(DL_DXF_MAXLINE + 2, '0'));
    check(!reader.in(oversized, &borrowed), "oversized stream line terminates with failure");
    std::istringstream throwing_stream(std::string(DL_DXF_MAXLINE + 2, '0'));
    throwing_stream.exceptions(std::ios::failbit | std::ios::badbit);
    caught = false;
    try { reader.in(throwing_stream, &borrowed); }
    catch (const std::ios_base::failure&) { caught = true; }
    check(caught && std::locale() == comma, "stream read exception restores locale");
    std::locale::global(prior);
    check(std::remove(path.c_str()) == 0, "remove fixture");
    std::puts("dxflib FILE ownership and entity fields PASS");
}
