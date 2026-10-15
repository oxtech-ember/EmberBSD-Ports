/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 EmberBSD contributors (AI-assisted).
 * Exercise installed C++ runtime ownership, unwinding, threads and DSO TLS.
 */
#include "cxx-runtime.hpp"

#include <array>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <thread>

struct worker_result {
	unsigned int first = 0, second = 0;
	bool text_valid = false, caught = false, unexpected = false;
};

static bool
valid_text(const std::string &text)
{
	return text.size() == 4099 && text.find_first_not_of('q') == 4096 &&
	    text.compare(4096, 3, "E35") == 0;
}

static bool
catch_error()
{
	try {
		e35::throw_error();
	} catch (const std::runtime_error &error) {
		return std::strcmp(error.what(), "E35 cross-DSO runtime_error") == 0;
	}
}

int
main(int argc, char **)
{
	std::array<worker_result, 2> results;
	std::array<std::thread, 2> workers;
	unsigned int checks = 0;
	bool ok = argc == 1, started = true;
	const unsigned int dso_major = e35::compiler_major();
	auto check = [&ok, &checks](bool condition) {
		checks++;
		if (!condition)
			ok = false;
	};
	auto job = [&results](std::size_t index) {
		worker_result &result = results[index];

		try {
			result.first = e35::next_tls();
			{
				const std::string text = e35::make_text();
				result.text_valid = valid_text(text);
			}
			result.caught = catch_error();
			result.second = e35::next_tls();
		} catch (...) {
			result.unexpected = true;
		}
	};

	check(__GNUC__ == 16);
	check(dso_major == 16);
	try {
		{
			const std::string text = e35::make_text();
			check(valid_text(text));
		}
		check(catch_error());
		check(e35::next_tls() == 1);
		try {
			for (std::size_t i = 0; i < workers.size(); i++)
				workers[i] = std::thread(job, i);
		} catch (...) {
			started = false;
		}
		for (std::thread &worker : workers) {
			if (worker.joinable())
				worker.join();
		}
		check(started);
		for (const worker_result &result : results) {
			check(!result.unexpected);
			check(result.first == 1 && result.second == 2);
			check(result.text_valid);
			check(result.caught);
		}
		check(e35::next_tls() == 2);
	} catch (...) {
		ok = false;
	}
	if (std::printf("{\"ok\":%s,\"gcc_major\":%u,\"dso_gcc_major\":%u,"
	    "\"checks\":%u}\n", ok ? "true" : "false", __GNUC__, dso_major,
	    checks) < 0)
		return 1;
	return ok ? 0 : 1;
}
