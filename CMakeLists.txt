cmake_minimum_required(VERSION 3.20)

project(story_gen_native VERSION 0.1.0 LANGUAGES CXX)

option(STORY_GEN_BUILD_NATIVE_TOOLS "Build native C++ tools for story_gen" ON)
option(STORY_GEN_ENABLE_CLANG_TIDY "Enable clang-tidy when available" ON)
option(STORY_GEN_ENABLE_CPPCHECK "Enable cppcheck when available" ON)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(STORY_GEN_ENABLE_CLANG_TIDY)
  find_program(CLANG_TIDY_EXE NAMES clang-tidy)
  if(CLANG_TIDY_EXE)
    set(CMAKE_CXX_CLANG_TIDY "${CLANG_TIDY_EXE}")
    message(STATUS "clang-tidy enabled: ${CLANG_TIDY_EXE}")
  else()
    message(STATUS "clang-tidy not found; skipping clang-tidy integration")
  endif()
endif()

if(STORY_GEN_ENABLE_CPPCHECK)
  find_program(CPPCHECK_EXE NAMES cppcheck)
  if(CPPCHECK_EXE)
    set(
      CMAKE_CXX_CPPCHECK
      "${CPPCHECK_EXE};--enable=warning,style,performance,portability;--error-exitcode=2"
    )
    message(STATUS "cppcheck enabled: ${CPPCHECK_EXE}")
  else()
    message(STATUS "cppcheck not found; skipping cppcheck integration")
  endif()
endif()

if(STORY_GEN_BUILD_NATIVE_TOOLS)
  include(CTest)
  enable_testing()
  add_subdirectory(cpp)
endif()
