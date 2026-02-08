add_executable(chapter_metrics chapter_metrics.cpp)

target_compile_features(chapter_metrics PRIVATE cxx_std_11)

if(MSVC)
  target_compile_options(chapter_metrics PRIVATE /W4)
  if(MSVC_VERSION GREATER_EQUAL 1910)
    target_compile_options(chapter_metrics PRIVATE /permissive-)
  endif()
else()
  target_compile_options(chapter_metrics PRIVATE -Wall -Wextra -Wpedantic)
endif()

target_compile_definitions(chapter_metrics PRIVATE
  $<$<CONFIG:Release>:NDEBUG>
)

install(TARGETS chapter_metrics RUNTIME DESTINATION bin)

add_test(NAME chapter_metrics_demo COMMAND chapter_metrics --demo)
