#pragma once

#include <QString>
#include <cstdint>

namespace KSysGuard
{
class SensorProperty
{
public:
    void setValue(quint64 value) { number = value; }
    void setValue(const QString &value) { text = value.toStdString(); }
    quint64 number = 0;
    std::string text;
};
}
