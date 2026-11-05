#include "wallet_engine.hpp"
#include <iostream>
int main() {
    auto words = wallet_engine::mnemonic_wordlist();
    if (words.size() != 2048 || words.front() != "abandon" || words.back() != "zoo") return 1;
    if (wallet_engine::is_valid_ton_address("not an address")) return 2;
    std::cout << "wallet FFI wordlist and invalid address: PASS\n";
}
