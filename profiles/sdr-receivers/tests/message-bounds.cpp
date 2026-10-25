// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD; real-source signed-field and invalid-width regressions.
#include <cassert>
#include <climits>
#include "Message.h"
int main()
{
    AIS::Message message;
    message.clear();
    message.setByteRaw(0, 0x80);
    assert(message.getInt(0, 32) == INT_MIN);
    assert(message.getInt(0, 1) == -1);
    assert(message.getUint(0, 32) == 0x80000000u);
    assert(message.getUint(0, 0) == 0);
    assert(message.getUint(0, -1) == 0);
    assert(message.getUint(0, 33) == 0);
    assert(message.getUint(INT_MAX, 1) == 0);
    assert(message.getInt(0, 0) == 0);
    assert(message.getInt(0, 33) == 0);
    assert(message.getInt(-1, 1) == 0);
    assert(message.getInt(MAX_AIS_LENGTH, 1) == 0);
    message.setByteRaw(MAX_AIS_BYTES - 1, 0x01);
    assert(message.getInt(MAX_AIS_LENGTH - 1, 1) == -1);
    return 0;
}
