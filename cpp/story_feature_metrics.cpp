#include <algorithm>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {

struct FeatureMetrics {
  FeatureMetrics()
      : source_length_chars(0), sentence_count(0), token_count(0), non_empty_lines(0),
        dialogue_lines(0), avg_sentence_length(0.0), dialogue_line_ratio(0.0) {}

  std::size_t source_length_chars;
  std::size_t sentence_count;
  std::size_t token_count;
  std::size_t non_empty_lines;
  std::size_t dialogue_lines;
  double avg_sentence_length;
  double dialogue_line_ratio;
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

bool IsWhitespaceCodepoint(std::uint32_t cp) {
  return cp == static_cast<std::uint32_t>(' ') || cp == static_cast<std::uint32_t>('\t') ||
         cp == static_cast<std::uint32_t>('\n') || cp == static_cast<std::uint32_t>('\r') ||
         cp == static_cast<std::uint32_t>('\f') || cp == static_cast<std::uint32_t>('\v') ||
         cp == 0x3000;
}

bool IsSentenceTerminator(std::uint32_t cp) {
  return cp == static_cast<std::uint32_t>('.') || cp == static_cast<std::uint32_t>('!') ||
         cp == static_cast<std::uint32_t>('?') || cp == 0x3002 || cp == 0xFF01 || cp == 0xFF1F;
}

std::size_t CountSentences(const std::string& text) {
  std::size_t index = 0;
  std::size_t count = 0;
  bool has_sentence_content = false;

  std::uint32_t cp = 0;
  while (index < text.size()) {
    DecodeNextCodepoint(text, &index, &cp);
    if (IsSentenceTerminator(cp)) {
      if (has_sentence_content) {
        ++count;
        has_sentence_content = false;
      }
      continue;
    }
    if (IsWhitespaceCodepoint(cp)) {
      continue;
    }
    has_sentence_content = true;
  }
  if (has_sentence_content) {
    ++count;
  }
  return count;
}

bool IsLatinTokenByte(unsigned char c) { return std::isalnum(c) != 0 || c == '_' || c == '\''; }

std::size_t CountLatinTokens(const std::string& text) {
  std::size_t count = 0;
  bool in_token = false;
  for (unsigned char c : text) {
    if (IsLatinTokenByte(c)) {
      if (!in_token) {
        ++count;
        in_token = true;
      }
    } else {
      in_token = false;
    }
  }
  return count;
}

std::size_t CountWhitespaceTokens(const std::string& text) {
  std::size_t count = 0;
  std::istringstream input(text);
  std::string token;
  while (input >> token) {
    ++count;
  }
  return count;
}

bool IsLineBlank(const std::string& line) {
  return std::all_of(line.begin(), line.end(),
                     [](unsigned char c) { return std::isspace(c) != 0; });
}

bool StartsWithDialogueMarker(const std::string& line) {
  std::size_t index = 0;
  while (index < line.size()) {
    std::uint32_t cp = 0;
    if (!DecodeNextCodepoint(line, &index, &cp)) {
      return false;
    }
    if (cp == static_cast<std::uint32_t>(' ') || cp == static_cast<std::uint32_t>('\t') ||
        cp == static_cast<std::uint32_t>('\r') || cp == 0x3000) {
      continue;
    }
    if (cp == static_cast<std::uint32_t>('"') || cp == static_cast<std::uint32_t>('\'') ||
        cp == 0x201C || cp == 0x300C || cp == 0x300E) {
      return true;
    }
    return false;
  }
  return false;
}

void CountDialogueLines(const std::string& text, FeatureMetrics* metrics) {
  std::istringstream input(text);
  std::string line;
  while (std::getline(input, line)) {
    if (!line.empty() && line.back() == '\r') {
      line.pop_back();
    }
    if (IsLineBlank(line)) {
      continue;
    }
    ++(metrics->non_empty_lines);
    if (StartsWithDialogueMarker(line)) {
      ++(metrics->dialogue_lines);
    }
  }
}

FeatureMetrics ComputeFeatureMetrics(const std::string& text) {
  FeatureMetrics metrics;
  metrics.source_length_chars = CountCodepoints(text);
  metrics.sentence_count = CountSentences(text);

  const std::size_t latin_tokens = CountLatinTokens(text);
  metrics.token_count = latin_tokens > 0 ? latin_tokens : CountWhitespaceTokens(text);
  if (metrics.sentence_count > 0) {
    metrics.avg_sentence_length =
        static_cast<double>(metrics.token_count) / static_cast<double>(metrics.sentence_count);
  }

  CountDialogueLines(text, &metrics);
  if (metrics.non_empty_lines > 0) {
    metrics.dialogue_line_ratio =
        static_cast<double>(metrics.dialogue_lines) / static_cast<double>(metrics.non_empty_lines);
  }

  return metrics;
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

std::string DemoText() {
  return "\"First dialogue line.\"\n"
         "Narration line continues here. Another sentence!\n"
         "    'Another quoted line.'\n"
         "\n"
         "Final narration line.\n";
}

void PrintUsage() {
  std::cout << "story_feature_metrics options:\n"
               "  --input <path>   Read UTF-8 chapter text from file\n"
               "  --demo           Run metrics on an embedded sample\n"
               "  --help           Show this message\n";
}

void PrintMetricsJson(const FeatureMetrics& metrics) {
  std::cout << std::fixed << std::setprecision(8);
  std::cout << "{\n"
            << "  \"source_length_chars\": " << metrics.source_length_chars << ",\n"
            << "  \"sentence_count\": " << metrics.sentence_count << ",\n"
            << "  \"token_count\": " << metrics.token_count << ",\n"
            << "  \"avg_sentence_length\": " << metrics.avg_sentence_length << ",\n"
            << "  \"dialogue_line_ratio\": " << metrics.dialogue_line_ratio << "\n"
            << "}\n";
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

    const FeatureMetrics metrics = ComputeFeatureMetrics(text);
    PrintMetricsJson(metrics);
    return 0;
  } catch (const std::exception& ex) {
    std::cerr << "story_feature_metrics failed: " << ex.what() << "\n";
    return 1;
  }
}
