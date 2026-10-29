// Origin: EmberBSD contributors (AI-assisted); ordinary mesh codec regression.
#include <Open3DGC/o3dgcSC3DMCEncoder.h>
#include <Open3DGC/o3dgcSC3DMCDecoder.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <vector>

int main() {
    using namespace o3dgc;
    Real coordinates[] = {0,0,0, 1,0,0, 0,1,0, 0,0,1};
    unsigned long triangles[] = {0,2,1, 0,1,3, 1,2,3, 2,0,3};
    IndexedFaceSet<unsigned long> input;
    input.SetNCoord(4);
    input.SetCoord(coordinates);
    input.SetNCoordIndex(4);
    input.SetCoordIndex(triangles);
    input.ComputeMinMax(O3DGC_SC3DMC_MAX_ALL_DIMS);
    SC3DMCEncodeParams params;
    params.SetStreamType(O3DGC_STREAM_TYPE_BINARY);
    params.SetCoordQuantBits(12);
    params.SetCoordPredMode(O3DGC_SC3DMC_PARALLELOGRAM_PREDICTION);
    BinaryStream stream;
    SC3DMCEncoder<unsigned long> encoder;
    if (encoder.Encode(params, input, stream) != O3DGC_OK || stream.GetSize() == 0) return 1;
    IndexedFaceSet<unsigned long> output;
    SC3DMCDecoder<unsigned long> decoder;
    if (decoder.DecodeHeader(output, stream) != O3DGC_OK ||
        output.GetNCoord() != 4 || output.GetNCoordIndex() != 4) return 2;
    std::vector<Real> decoded(output.GetNCoord() * 3);
    std::vector<unsigned long> indices(output.GetNCoordIndex() * 3);
    output.SetCoord(decoded.data());
    output.SetCoordIndex(indices.data());
    if (decoder.DecodePayload(output, stream) != O3DGC_OK) return 3;
    std::vector<std::array<int, 3>> points;
    for (size_t i = 0; i < decoded.size(); i += 3) {
        std::array<int, 3> point;
        for (size_t j = 0; j < 3; ++j) {
            if (std::fabs(decoded[i+j] - std::round(decoded[i+j])) > 0.001) return 4;
            point[j] = static_cast<int>(std::round(decoded[i+j]));
        }
        points.push_back(point);
    }
    std::sort(points.begin(), points.end());
    const std::vector<std::array<int, 3>> expected = {{{0,0,0}}, {{0,0,1}}, {{0,1,0}}, {{1,0,0}}};
    if (points != expected) return 5;
    for (auto index : indices) if (index >= 4) return 6;
    return 0;
}
