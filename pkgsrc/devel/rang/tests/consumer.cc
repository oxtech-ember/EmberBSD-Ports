#include <rang.hpp>
#include <sstream>
#include <string>

int main() {
    std::ostringstream out;
    rang::setControlMode(rang::control::Force);
    out << rang::fg::red << "text" << rang::fg::reset;
    return out.str() == "\x1b[31mtext\x1b[39m" ? 0 : 1;
}
