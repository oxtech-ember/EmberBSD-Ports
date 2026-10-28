// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#ifdef NDEBUG
#error "LIEF consumer checks require assertions"
#endif
#include <LIEF/PE.hpp>
#include <LIEF/utils.hpp>
#include <cassert>
#include <iomanip>
#include <fstream>
#include <iterator>
#include <sstream>
#include <string>
#include <vector>

static std::string hex(const std::vector<uint8_t>& bytes) {
  std::ostringstream out;
  for (auto byte : bytes) out << std::hex << std::setfill('0') << std::setw(2) << unsigned(byte);
  return out.str();
}
int main(int argc, char** argv) {
  assert(argc == 3);
  // Exercise initialization through the memory API before any digest operation.
  std::ifstream certificate(argv[1], std::ios::binary);
  assert(certificate);
  std::vector<uint8_t> pem((std::istreambuf_iterator<char>(certificate)), {});
  pem.push_back(0); // The provider's PEM parser requires a terminating NUL.
  auto memory_certs = LIEF::PE::x509::parse(pem);
  assert(memory_certs.size() == 1);
  using LIEF::PE::ALGORITHMS;
  const std::vector<uint8_t> input{'a','b','c'};
  auto hash = [&](ALGORITHMS algorithm) { return hex(LIEF::PE::Signature::hash(input, algorithm)); };
  assert(hash(ALGORITHMS::MD5) == "900150983cd24fb0d6963f7d28e17f72");
  assert(hash(ALGORITHMS::SHA_1) == "a9993e364706816aba3e25717850c26c9cd0d89d");
  assert(hash(ALGORITHMS::SHA_256) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  assert(hash(ALGORITHMS::SHA_384) == "cb00753f45a35e8bb5a03d699ac65007272c32ab0eded1631a8b605a43ff5bed8086072ba1e7cc2358baeca134c825a7");
  assert(hash(ALGORITHMS::SHA_512) == "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f");
  auto utf = LIEF::u8tou16("A\xf0\x9f\x90\x88");
  assert(utf && *utf == u"A\U0001f408");
  assert(!LIEF::u8tou16("\xc0\xaf"));
  using Date = LIEF::PE::x509::date_t;
  const Date before{2026, 10, 28, 12, 30, 45};
  assert(LIEF::PE::x509::check_time(before, before));
  assert(LIEF::PE::x509::check_time(before, Date{2026, 10, 28, 12, 30, 46}));
  assert(!LIEF::PE::x509::check_time(before, Date{2026, 10, 28, 12, 30, 44}));
  auto certs = LIEF::PE::x509::parse(std::string(argv[1]));
  assert(certs.size() == 1);
  assert(certs[0].key_type() == LIEF::PE::x509::KEY_TYPES::RSA);
  auto rsa = certs[0].rsa_info();
  assert(rsa && rsa->has_public_key() && rsa->key_size() == 2048);
  std::ifstream file(argv[2], std::ios::binary);
  assert(file);
  std::vector<uint8_t> signature((std::istreambuf_iterator<char>(file)), {});
  auto digest = LIEF::PE::Signature::hash(input, ALGORITHMS::SHA_256);
  assert(certs[0].check_signature(digest, signature, ALGORITHMS::SHA_256));
  auto copy = *rsa;
  assert(copy.has_public_key() && copy.N() == rsa->N() && copy.E() == rsa->E());
}
