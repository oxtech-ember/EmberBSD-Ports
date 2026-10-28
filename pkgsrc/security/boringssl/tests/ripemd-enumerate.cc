// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
#include <openssl/digest.h>
#include <openssl/evp.h>
#include <assert.h>
#include <string.h>
struct State { const char *previous; bool found; };
static void visit(const EVP_MD *md, const char *name, const char *, void *arg) {
  State *state = static_cast<State *>(arg);
  if (state->previous) assert(strcmp(state->previous, name) <= 0);
  state->previous = name;
  if (strcmp(name, "ripemd160") == 0 && md == EVP_ripemd160()) state->found = true;
}
int main() { State state = {nullptr, false}; EVP_MD_do_all_sorted(visit, &state); assert(state.found); }
