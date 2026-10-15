// SPDX-License-Identifier: MIT
// Origin: EmberBSD (AI-assisted). Check the selected common Boost closure.
#include <boost/iostreams/copy.hpp>
#include <boost/iostreams/filter/bzip2.hpp>
#include <boost/iostreams/filter/gzip.hpp>
#include <boost/iostreams/filter/lzma.hpp>
#include <boost/iostreams/filter/zlib.hpp>
#include <boost/iostreams/filtering_stream.hpp>
#include <boost/random/random_device.hpp>

#include <cmath>
#include <exception>
#include <iostream>
#include <sstream>
#include <string>

namespace {

template <class Compressor, class Decompressor>
bool RoundTrip(const std::string& input) {
  std::ostringstream encoded;
  boost::iostreams::filtering_ostream compressor;
  compressor.push(Compressor());
  compressor.push(encoded);
  compressor.write(input.data(), static_cast<std::streamsize>(input.size()));
  compressor.reset();
  if (!encoded.good() || encoded.str().empty()) return false;

  std::istringstream source(encoded.str());
  boost::iostreams::filtering_istream decompressor;
  decompressor.push(Decompressor());
  decompressor.push(source);
  std::ostringstream decoded;
  boost::iostreams::copy(decompressor, decoded);
  return decoded.good() && decoded.str() == input;
}

}  // namespace

int main() {
  try {
    std::string input;
    for (unsigned i = 0; i < 16384; ++i) {
      input.push_back(static_cast<char>((i * 37 + i / 17) & 255));
    }
    if (!RoundTrip<boost::iostreams::zlib_compressor,
                   boost::iostreams::zlib_decompressor>(input) ||
        !RoundTrip<boost::iostreams::gzip_compressor,
                   boost::iostreams::gzip_decompressor>(input) ||
        !RoundTrip<boost::iostreams::bzip2_compressor,
                   boost::iostreams::bzip2_decompressor>(input) ||
        !RoundTrip<boost::iostreams::lzma_compressor,
                   boost::iostreams::lzma_decompressor>(input)) {
      std::cerr << "Compression round trip failed\n";
      return 1;
    }
    boost::random::random_device random;
    const double entropy = random.entropy();
    if (!std::isfinite(entropy) || entropy < 0) return 1;
    // Exercise the device API without assuming a particular random value.
    static_cast<void>(random());
    std::cout << "PASS Boost zlib, gzip, bzip2, lzma and random device\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
