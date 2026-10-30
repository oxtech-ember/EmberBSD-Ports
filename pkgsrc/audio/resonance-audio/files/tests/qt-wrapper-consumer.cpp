#include "resonance_audio.h"
#include "graph/resonance_audio_api_impl.h"
#include <array>
#include <cmath>
#include <iostream>

int main()
{
    constexpr size_t frames = 256;
    vraudio::ResonanceAudio audio(2, frames, 48000);
    auto id = audio.api->CreateSoundObjectSource(vraudio::kBinauralHighQuality);
    if (id == vraudio::ResonanceAudioApi::kInvalidSourceId)
        return 1;
    audio.api->SetSourcePosition(id, 0.0f, 0.0f, -1.0f);
    std::array<float, frames> input{};
    for (size_t i = 0; i < frames; ++i)
        input[i] = 0.5f * std::sin(float(i) * 0.1f);
    std::array<float, 2 * frames> stereo{};
    bool rendered = false;
    for (int n = 0; n < 8; ++n) {
        audio.api->SetInterleavedBuffer(id, input.data(), 1, frames);
        if (audio.api->FillInterleavedOutputBuffer(2, frames, stereo.data()))
            for (float sample : stereo)
                rendered |= std::isfinite(sample) && std::abs(sample) > 1e-7f;
    }
    const float *channels[32]{};
    const float *reverb[2]{};
    audio.api->SetInterleavedBuffer(id, input.data(), 1, frames);
    auto *impl = static_cast<vraudio::ResonanceAudioApiImpl *>(audio.api.get());
    impl->ProcessNextBuffer();
    const auto *ambisonic = impl->GetAmbisonicOutputBuffer();
    if (!ambisonic || ambisonic->num_channels() > 32)
        return 3;
    const int nchannels = int(ambisonic->num_channels());
    audio.api->SetInterleavedBuffer(id, input.data(), 1, frames);
    if (audio.getAmbisonicOutput(channels, reverb, nchannels) != int(frames)
        || channels[0] == nullptr || reverb[0] == nullptr || reverb[1] == nullptr)
        return 4;
    audio.api->DestroySource(id);
    if (!rendered)
        return 2;
    std::cout << "Resonance Qt wrapper and spatial render PASS\n";
}
