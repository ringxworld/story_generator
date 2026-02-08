#include <cctype>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {

struct Metrics {
  Metrics() : bytes(0), codepoints(0), lines(0), non_empty_lines(0), dialogue_lines(0) {}

  std::size_t bytes;
  std::size_t codepoints;
  std::size_t lines;
  std::size_t non_empty_lines;
  std::size_t dialogue_lines;
};

bool DecodeNextCodepoint(const std::string& text, std::size_t* index,
                         std::uint32_t* out_codepoint) {
  if (*index >= text.size()) {
    return false;
  }

  const auto* bytes = reinterpret_cast<const unsigned char*>(text.data());
  const unsigned char first = bytes[*index];

  if (first < 0x80) {
    ++(*index);
    *out_codepoint = static_cast<std::uint32_t>(first);
    return true;
  }

  auto fail_as_single = [&]() -> bool {
    ++(*index);
    *out_codepoint = static_cast<std::uint32_t>(first);
    return true;
  };

  auto require_continuation = [&](std::size_t pos) -> bool {
    if (pos >= text.size()) {
      return false;
    }
    return (bytes[pos] & 0xC0) == 0x80;
  };

  if ((first & 0xE0) == 0xC0) {
    if (!require_continuation(*index + 1)) {
      return fail_as_single();
    }
    const std::uint32_t value = ((first & 0x1F) << 6) | (bytes[*index + 1] & 0x3F);
    *index += 2;
    *out_codepoint = value;
    return true;
  }

  if ((first & 0xF0) == 0xE0) {
    if (!require_continuation(*index + 1) || !require_continuation(*index + 2)) {
      return fail_as_single();
    }
    const std::uint32_t value =
        ((first & 0x0F) << 12) | ((bytes[*index + 1] & 0x3F) << 6) | (bytes[*index + 2] & 0x3F);
    *index += 3;
    *out_codepoint = value;
    return true;
  }

  if ((first & 0xF8) == 0xF0) {
    if (!require_continuation(*index + 1) || !require_continuation(*index + 2) ||
        !require_continuation(*index + 3)) {
      return fail_as_single();
    }
    const std::uint32_t value = ((first & 0x07) << 18) | ((bytes[*index + 1] & 0x3F) << 12) |
                                ((bytes[*index + 2] & 0x3F) << 6) | (bytes[*index + 3] & 0x3F);
    *index += 4;
    *out_codepoint = value;
    return true;
  }

  return fail_as_single();
}

bool IsLineBlank(const std::string& line) {
  for (unsigned char c : line) {
    if (!std::isspace(c)) {
      return false;
    }
  }
  return true;
}

bool StartsWithDialogueMarker(const std::string& line) {
  std::size_t index = 0;
  while (index < line.size()) {
    const std::size_t before = index;
    std::uint32_t cp = 0;
    if (!DecodeNextCodepoint(line, &index, &cp)) {
      return false;
    }

    if (cp == static_cast<std::uint32_t>(' ') || cp == static_cast<std::uint32_t>('\t') ||
        cp == static_cast<std::uint32_t>('\r') || cp == 0x3000) {
      continue;
    }

    if (cp == static_cast<std::uint32_t>('"') || cp == static_cast<std::uint32_t>('\'') ||
        cp == 0x300C || cp == 0x300E || cp == 0x201C) {
      return true;
    }

    if (before == index) {
      return false;
    }
    return false;
  }
  return false;
}

std::size_t CountCodepoints(const std::string& text) {
  std::size_t index = 0;
  std::size_t count = 0;
  std::uint32_t cp = 0;
  while (index < text.size()) {
    DecodeNextCodepoint(text, &index, &cp);
    ++count;
  }
  return count;
}

Metrics ComputeMetrics(const std::string& text) {
  Metrics metrics;
  metrics.bytes = text.size();
  metrics.codepoints = CountCodepoints(text);

  std::istringstream input(text);
  std::string line;
  while (std::getline(input, line)) {
    if (!line.empty() && line.back() == '\r') {
      line.pop_back();
    }

    ++metrics.lines;
    if (!IsLineBlank(line)) {
      ++metrics.non_empty_lines;
    }
    if (StartsWithDialogueMarker(line)) {
      ++metrics.dialogue_lines;
    }
  }

  return metrics;
}

double DialogueDensity(const Metrics& metrics) {
  if (metrics.non_empty_lines == 0) {
    return 0.0;
  }
  return static_cast<double>(metrics.dialogue_lines) / static_cast<double>(metrics.non_empty_lines);
}

std::string ReadFileUtf8(const std::string& path) {
  std::ifstream file(path, std::ios::binary);
  if (!file) {
    throw std::runtime_error("Could not open file: " + path);
  }
  std::ostringstream buffer;
  buffer << file.rdbuf();
  return buffer.str();
}

std::string ReadStdin() {
  std::ostringstream buffer;
  buffer << std::cin.rdbuf();
  return buffer.str();
}

void PrintUsage() {
  std::cout << "chapter_metrics options:\n"
               "  --input <path>   Read UTF-8 chapter text from file\n"
               "  --demo           Run metrics on an embedded sample\n"
               "  --help           Show this message\n";
}

void PrintMetricsJson(const Metrics& metrics) {
  std::cout << "{\n"
            << "  \"bytes\": " << metrics.bytes << ",\n"
            << "  \"codepoints\": " << metrics.codepoints << ",\n"
            << "  \"lines\": " << metrics.lines << ",\n"
            << "  \"non_empty_lines\": " << metrics.non_empty_lines << ",\n"
            << "  \"dialogue_lines\": " << metrics.dialogue_lines << ",\n"
            << "  \"dialogue_density\": " << DialogueDensity(metrics) << "\n"
            << "}\n";
}

std::string DemoText() {
  return "\"First dialogue line.\"\n"
         "Narration line continues here.\n"
         "    'Another quoted line.'\n"
         "\n"
         "Final narration line.\n";
}

} // namespace

int main(int argc, char** argv) {
  std::string input_path;
  bool has_input_path = false;
  bool use_demo = false;

  for (int i = 1; i < argc; ++i) {
    const std::string arg(argv[i]);
    if (arg == "--help") {
      PrintUsage();
      return 0;
    }
    if (arg == "--demo") {
      use_demo = true;
      continue;
    }
    if (arg == "--input") {
      if (i + 1 >= argc) {
        std::cerr << "--input requires a file path\n";
        return 2;
      }
      input_path = std::string(argv[++i]);
      has_input_path = true;
      continue;
    }
    std::cerr << "Unknown argument: " << arg << "\n";
    PrintUsage();
    return 2;
  }

  try {
    std::string text;
    if (use_demo) {
      text = DemoText();
    } else if (has_input_path) {
      text = ReadFileUtf8(input_path);
    } else {
      text = ReadStdin();
    }

    const Metrics metrics = ComputeMetrics(text);
    PrintMetricsJson(metrics);
    return 0;
  } catch (const std::exception& ex) {
    std::cerr << "chapter_metrics failed: " << ex.what() << "\n";
    return 1;
  }
}
