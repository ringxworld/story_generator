cmake_minimum_required(VERSION 3.20)

project(story_gen_native VERSION 0.1.0 LANGUAGES CXX)

option(STORY_GEN_BUILD_NATIVE_TOOLS "Build native C++ tools for story_gen" ON)

if(STORY_GEN_BUILD_NATIVE_TOOLS)
  include(CTest)
  enable_testing()
  add_subdirectory(cpp)
endif()
