// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted), public JPEG transform coefficient contract.
#include <algorithm>
#include <array>
#include <cassert>
#include <climits>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <new>
#include <vector>
#include <jpeglib.h>
#include "FreeImage.h"

static char message[512];
static bool failAllocation;
// Wrap the call instead of replacing new/delete. Memcheck keeps ownership
// of the actual allocator and the allocation failure still reaches the TU.
extern "C" void *__real__Znwm(std::size_t);
extern "C" void *__wrap__Znwm(std::size_t size) {
    if(failAllocation) {
        failAllocation = false;
        throw std::bad_alloc();
    }
    return __real__Znwm(size);
}
extern "C" void DLL_CALLCONV
FreeImage_OutputMessageProc(int, const char *format, ...) {
    va_list args;
    va_start(args, format);
    vsnprintf(message, sizeof(message), format, args);
    va_end(args);
}

struct Stream {
    std::vector<unsigned char> bytes;
    size_t position = 0;
    unsigned readLimit = UINT_MAX;
    bool shortWrite = false, throwRead = false, throwWrite = false;
    bool badSeek = false, badTell = false, oversizedRead = false, throwTell = false, throwSeek = false;
};
static unsigned DLL_CALLCONV readBytes(void *buffer, unsigned size, unsigned count, fi_handle handle) {
    Stream &s = *static_cast<Stream *>(handle);
    assert(size == 1);
    if(s.throwRead) throw std::runtime_error("read");
    if(s.oversizedRead) return count + 1;
    const unsigned n = static_cast<unsigned>(std::min({size_t(count), size_t(s.readLimit), s.bytes.size() - s.position}));
    if(n) memcpy(buffer, s.bytes.data() + s.position, n);
    s.position += n;
    return n;
}
static unsigned DLL_CALLCONV writeBytes(void *buffer, unsigned size, unsigned count, fi_handle handle) {
    Stream &s = *static_cast<Stream *>(handle);
    assert(size == 1);
    if(s.throwWrite) throw std::runtime_error("write");
    if(s.shortWrite) return count - 1;
    s.bytes.resize(std::max(s.bytes.size(), s.position + count));
    memcpy(s.bytes.data() + s.position, buffer, count);
    s.position += count;
    return count;
}
static int DLL_CALLCONV seekBytes(fi_handle handle, long offset, int origin) {
    Stream &s = *static_cast<Stream *>(handle);
    if(s.throwSeek) throw std::runtime_error("seek");
    if(s.badSeek || origin != SEEK_SET || offset < 0 || size_t(offset) > s.bytes.size()) return -1;
    s.position = static_cast<size_t>(offset);
    return 0;
}
static long DLL_CALLCONV tellBytes(fi_handle handle) {
    Stream &s = *static_cast<Stream *>(handle);
    if(s.throwTell) throw std::runtime_error("tell");
    return s.badTell ? -1 : static_cast<long>(s.position);
}
static FreeImageIO io = {readBytes, writeBytes, seekBytes, tellBytes};

static Stream makeJPEG(int width, int height, int horizontal = 1, int vertical = 1, bool gray = false) {
    jpeg_compress_struct c{};
    jpeg_error_mgr e;
    c.err = jpeg_std_error(&e);
    jpeg_create_compress(&c);
    unsigned char *buffer = nullptr;
    unsigned long length = 0;
    jpeg_mem_dest(&c, &buffer, &length);
    c.image_width = width;
    c.image_height = height;
    c.input_components = gray ? 1 : 3;
    c.in_color_space = gray ? JCS_GRAYSCALE : JCS_RGB;
    jpeg_set_defaults(&c);
    c.comp_info[0].h_samp_factor = horizontal;
    c.comp_info[0].v_samp_factor = vertical;
    jpeg_set_quality(&c, 93, TRUE);
    jpeg_start_compress(&c, TRUE);
    const unsigned char exif[] = {'E','x','i','f',0,0,'f','i','x','t','u','r','e'};
    const unsigned char comment[] = "lossless coefficient oracle";
    jpeg_write_marker(&c, JPEG_APP0 + 1, exif, sizeof(exif));
    jpeg_write_marker(&c, JPEG_COM, comment, sizeof(comment));
    std::vector<unsigned char> row(size_t(width) * c.input_components);
    while(c.next_scanline < c.image_height) {
        for(size_t i = 0; i < row.size(); ++i) row[i] = (i * 37 + c.next_scanline * 19 + (i / 7) * 11) % 256;
        JSAMPROW p = row.data();
        jpeg_write_scanlines(&c, &p, 1);
    }
    jpeg_finish_compress(&c);
    Stream result;
    result.bytes.assign(buffer, buffer + length);
    free(buffer);
    jpeg_destroy_compress(&c);
    return result;
}

using Block = std::array<JCOEF, DCTSIZE2>;
struct Plane {
    int width, height, horizontal, vertical, table;
    std::vector<Block> blocks;
};
struct Image {
    int width, height, maxH, maxV;
    std::vector<Plane> planes;
    std::array<std::array<unsigned, DCTSIZE2>, NUM_QUANT_TBLS> tables{};
    std::vector<std::vector<unsigned char>> markers;
};
static Image coefficients(const Stream &stream, size_t offset = 0) {
    jpeg_decompress_struct c{};
    jpeg_error_mgr e;
    c.err = jpeg_std_error(&e);
    jpeg_create_decompress(&c);
    jpeg_mem_src(&c, stream.bytes.data() + offset, stream.bytes.size() - offset);
    jpeg_save_markers(&c, JPEG_APP0 + 1, 65535);
    jpeg_save_markers(&c, JPEG_COM, 65535);
    assert(jpeg_read_header(&c, TRUE) == JPEG_HEADER_OK);
    Image image{int(c.image_width), int(c.image_height), c.max_h_samp_factor, c.max_v_samp_factor, {}, {}, {}};
    for(auto marker = c.marker_list; marker; marker = marker->next) {
        image.markers.emplace_back(marker->data, marker->data + marker->data_length);
    }
    for(int t = 0; t < NUM_QUANT_TBLS; ++t) if(c.quant_tbl_ptrs[t]) {
        std::copy(c.quant_tbl_ptrs[t]->quantval, c.quant_tbl_ptrs[t]->quantval + DCTSIZE2, image.tables[t].begin());
    }
    auto arrays = jpeg_read_coefficients(&c);
    for(int i = 0; i < c.num_components; ++i) {
        const auto &info = c.comp_info[i];
        Plane plane{int(info.width_in_blocks), int(info.height_in_blocks), info.h_samp_factor, info.v_samp_factor, info.quant_tbl_no, {}};
        for(JDIMENSION y = 0; y < info.height_in_blocks; ++y) {
            JBLOCKARRAY row = (*c.mem->access_virt_barray)(reinterpret_cast<j_common_ptr>(&c), arrays[i], y, 1, FALSE);
            for(JDIMENSION x = 0; x < info.width_in_blocks; ++x) {
                Block block;
                std::copy(row[0][x], row[0][x] + DCTSIZE2, block.begin());
                plane.blocks.push_back(block);
            }
        }
        image.planes.push_back(plane);
    }
    jpeg_finish_decompress(&c);
    jpeg_destroy_decompress(&c);
    return image;
}

static bool swapped(int op) { return op == 3 || op == 4 || op == 5 || op == 7; }
static bool flipH(int op) { return op == 1 || op == 4 || op == 5 || op == 6; }
static bool flipV(int op) { return op == 2 || op == 4 || op == 6 || op == 7; }

// Check the independent DCT identity, including signs and quantization tables.
// Source block coordinates are calculated from the inverse pixel transform.
static void exact(const Image &source, const Image &output, int op, int x = 0, int y = 0) {
    assert(output.markers == source.markers);
    assert(output.planes.size() == source.planes.size());
    for(size_t component = 0; component < source.planes.size(); ++component) {
        const auto &s = source.planes[component];
        const auto &d = output.planes[component];
        assert(d.horizontal == (swapped(op) ? s.vertical : s.horizontal));
        assert(d.vertical == (swapped(op) ? s.horizontal : s.vertical));
        int sw = s.width, sh = s.height;
        if((op == 1 || op == 4 || op == 6 || op == 7) && source.width >= source.maxH * 8) sw = source.width / (source.maxH * 8) * s.horizontal;
        if((op == 2 || op == 4 || op == 5 || op == 6) && source.height >= source.maxV * 8) sh = source.height / (source.maxV * 8) * s.vertical;
        const int cropX = x * d.horizontal / (output.maxH * 8);
        const int cropY = y * d.vertical / (output.maxV * 8);
        for(int dy = 0; dy < d.height; ++dy) for(int dx = 0; dx < d.width; ++dx) {
            const int tx = dx + cropX, ty = dy + cropY;
            int sx = tx, sy = ty;
            switch(op) {
                case 1: sx = sw - 1 - tx; break;
                case 2: sy = sh - 1 - ty; break;
                case 3: sx = ty; sy = tx; break;
                case 4: sx = sw - 1 - ty; sy = sh - 1 - tx; break;
                case 5: sx = ty; sy = sh - 1 - tx; break;
                case 6: sx = sw - 1 - tx; sy = sh - 1 - ty; break;
                case 7: sx = sw - 1 - ty; sy = tx; break;
            }
            assert(sx >= 0 && sx < s.width && sy >= 0 && sy < s.height);
            for(int v = 0; v < 8; ++v) for(int u = 0; u < 8; ++u) {
                const int original = swapped(op) ? u * 8 + v : v * 8 + u;
                const int sign = ((flipH(op) && (u & 1)) != (flipV(op) && (v & 1))) ? -1 : 1;
                assert(d.blocks[dy * d.width + dx][v * 8 + u] == sign * s.blocks[sy * s.width + sx][original]);
                assert(output.tables[d.table][v * 8 + u] == source.tables[s.table][original]);
            }
        }
    }
}

static BOOL transform(Stream &source, Stream *destination, int op, int *l = nullptr, int *t = nullptr, int *r = nullptr, int *b = nullptr, BOOL perfect = FALSE) {
    source.position = 0;
    return FreeImage_JPEGTransformFromHandle(&io, &source, destination ? &io : nullptr, destination,
        static_cast<FREE_IMAGE_JPEG_OPERATION>(op), l, t, r, b, perfect);
}

int main() {
    auto baseline = makeJPEG(40, 56);
    Stream first;
    if(!transform(baseline, &first, FIJPEG_OP_FLIP_V, nullptr, nullptr, nullptr, nullptr, TRUE)) {
        fprintf(stderr, "FAIL: valid perfect vertical transform: %s\n", message);
        return 1;
    }
    unsigned cases = 0;
    // All operations, subsampling orientations, grayscale and partial edges.
    for(const auto sample : {std::array<int, 3>{1,1,0}, {2,1,0}, {2,2,0}, {1,2,0}, {4,1,0}, {1,4,0}, {4,2,0}, {2,4,0}, {1,1,1}}) {
        for(bool partial : {false, true}) {
            auto input = makeJPEG(partial ? 67 : 64, partial ? 99 : 96, sample[0], sample[1], sample[2]);
            const Image original = coefficients(input);
            for(int op = 0; op != 8; ++op) {
                const bool swap = swapped(op);
                const int fw = swap ? original.height : original.width;
                const int fh = swap ? original.width : original.height;
                const int mw = 8 * (swap ? original.maxV : original.maxH);
                const int mh = 8 * (swap ? original.maxH : original.maxV);
                const int trimX = flipH(op) ? fw % mw : 0;
                const int trimY = flipV(op) ? fh % mh : 0;
                const bool isPerfect = !trimX && !trimY;
                Stream perfect;
                assert(bool(transform(input, &perfect, op, nullptr, nullptr, nullptr, nullptr, TRUE)) == isPerfect);
                if(!isPerfect) assert(perfect.bytes.empty());
                Stream output;
                assert(transform(input, &output, op));
                const Image actual = coefficients(output);
                assert(actual.width == fw - trimX && actual.height == fh - trimY);
                exact(original, actual, op);
                ++cases;

                int l = mw + 3, t = mh + 1, r = fw - 1, b = fh - 2;
                const int expectedX = l / mw * mw, expectedY = t / mh * mh;
                int expectedW = r - expectedX, expectedH = b - expectedY;
                if(flipH(op) && (expectedX + expectedW) / mw == fw / mw) expectedW = expectedW / mw * mw;
                if(flipV(op) && (expectedY + expectedH) / mh == fh / mh) expectedH = expectedH / mh * mh;
                int ql = l, qt = t, qr = r, qb = b;
                assert(transform(input, nullptr, op, &ql, &qt, &qr, &qb));
                assert(ql == expectedX + trimX && qt == expectedY + trimY);
                assert(qr - ql == expectedW && qb - qt == expectedH);
                Stream cropped;
                assert(transform(input, &cropped, op, &l, &t, &r, &b));
                assert(l == ql && t == qt && r == qr && b == qb);
                const Image cropImage = coefficients(cropped);
                assert(cropImage.width == expectedW && cropImage.height == expectedH);
                exact(original, cropImage, op, expectedX, expectedY);
                ++cases;
            }
        }
    }
    // Rectangle normalization, edge-relative coordinates, and full-image no-ops.
    for(auto rect : {std::array<int,4>{-9,-8,0,0}, {29,35,11,9}, {11,9,-3,-4}, {10,9,10,35}, {0,0,40,56}}) {
        auto input = makeJPEG(40,56);
        int l=rect[0], t=rect[1], r=rect[2], b=rect[3];
        Stream output;
        assert(transform(input, &output, 0, &l, &t, &r, &b));
        const auto actual = coefficients(output);
        assert(actual.width == r-l && actual.height == b-t);
        exact(coefficients(input), actual, 0, l,t);
        ++cases;
    }
    // An unusual 3:1 sampling ratio can transform. TurboJPEG's public API
    // rejects its crops. Rectangle-only calls must report the same limit.
    auto unusual = makeJPEG(72,96,3,1);
    const Image unusualOriginal = coefficients(unusual);
    for(int op = 0; op < 8; ++op) {
        Stream output;
        assert(transform(unusual, &output, op));
        exact(unusualOriginal, coefficients(output), op);
        int l=1,t=1,r=50,b=50;
        assert(!transform(unusual, nullptr, op, &l,&t,&r,&b));
        l=1;t=1;r=50;b=50;
        Stream cropped;
        assert(!transform(unusual, &cropped, op, &l,&t,&r,&b));
        assert(cropped.bytes.empty());
        cases += 3;
    }
    // Short reads are valid; a destination can omit tell/seek when distinct.
    auto input = makeJPEG(40,56);
    input.readLimit = 7;
    Stream output;
    assert(transform(input, &output, 5));
    exact(coefficients(input), coefficients(output), 5);
    auto writeOnly = io;
    writeOnly.tell_proc = nullptr;
    writeOnly.seek_proc = nullptr;
    input.position = 0;
    Stream separate;
    assert(FreeImage_JPEGTransformFromHandle(&io,&input,&writeOnly,&separate,FIJPEG_OP_NONE,nullptr,nullptr,nullptr,nullptr,FALSE));
    exact(coefficients(input), coefficients(separate), 0);
    // Same-handle transformation starts and writes at the existing offset.
    Stream same = makeJPEG(40,56);
    const Image original = coefficients(same);
    same.bytes.insert(same.bytes.begin(), 17, 0xa5);
    same.position = 17;
    assert(FreeImage_JPEGTransformFromHandle(&io,&same,&io,&same,FIJPEG_OP_ROTATE_90,nullptr,nullptr,nullptr,nullptr,TRUE));
    assert(std::all_of(same.bytes.begin(),same.bytes.begin()+17,[](unsigned char b){return b==0xa5;}));
    exact(original, coefficients(same,17),5);
    // Callback errors, malformed input, and ownership paths must fail cleanly.
    for(int fault = 0; fault < 7; ++fault) {
        auto source = makeJPEG(40,56);
        Stream destination;
        if(fault == 0) source.throwRead = true;
        if(fault == 1) source.oversizedRead = true;
        if(fault == 2) destination.shortWrite = true;
        if(fault == 3) destination.throwWrite = true;
        if(fault == 4) source.bytes.clear();
        if(fault == 5) source.bytes.assign(64, 0xff);
        if(fault == 6) source.bytes.resize(10);
        assert(!transform(source,&destination,0));
        ++cases;
    }
    for(int fault = 0; fault < 4; ++fault) {
        auto source = makeJPEG(40,56);
        if(fault == 0) source.badTell = true;
        if(fault == 1) source.badSeek = true;
        if(fault == 2) source.throwTell = true;
        if(fault == 3) source.throwSeek = true;
        assert(!transform(source,&source,0));
        ++cases;
    }
    auto allocation = makeJPEG(40,56);
    Stream allocationOutput;
    failAllocation = true;
    assert(!transform(allocation,&allocationOutput,0));
    assert(!failAllocation && allocationOutput.bytes.empty());
    ++cases;
    assert(!FreeImage_JPEGTransformFromHandle(nullptr,nullptr,nullptr,nullptr,FIJPEG_OP_NONE,nullptr,nullptr,nullptr,nullptr,FALSE));
    printf("PASS: %u transform/crop/error cases; exact DCT coefficients, quantization tables, markers, short I/O and same-handle offsets.\n", cases + 5);
}
