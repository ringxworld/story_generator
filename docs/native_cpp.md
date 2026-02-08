# Native C++ Path

This project includes an optional native toolchain for high-performance sections.

## Why this exists

Python remains the orchestration layer. C++ is used for hotspots where throughput matters (large text scans, metrics, or heavy parsing loops).

## Current native tool

- `chapter_metrics` (C++11+)
  - Computes UTF-8 text metrics quickly:
    - bytes
    - codepoints
    - lines
    - non-empty lines
    - dialogue lines
    - dialogue density

## Build with CMake

```bash
cmake -S . -B build/cpp
cmake --build build/cpp --config Release
```

## Run demo

```bash
ctest --test-dir build/cpp -C Release -R chapter_metrics_demo --output-on-failure
```

## Example usage

```bash
chapter_metrics --input chapter.txt
```

Or pipe from stdin:

```bash
cat chapter.txt | chapter_metrics
```

## Prerequisites

- CMake 3.20+
- A C++11+ compiler (MSVC Build Tools, clang++, or g++)

## Make targets

- `make cpp-configure`
- `make cpp-build`
- `make cpp-test`
- `make cpp-demo`
