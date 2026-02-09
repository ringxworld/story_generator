add_executable(chapter_metrics chapter_metrics.cpp)
add_executable(story_feature_metrics story_feature_metrics.cpp)

target_compile_features(chapter_metrics PRIVATE cxx_std_11)
target_compile_features(story_feature_metrics PRIVATE cxx_std_11)

if(MSVC)
  target_compile_options(chapter_metrics PRIVATE /W4)
  target_compile_options(story_feature_metrics PRIVATE /W4)
  if(MSVC_VERSION GREATER_EQUAL 1910)
    target_compile_options(chapter_metrics PRIVATE /permissive-)
    target_compile_options(story_feature_metrics PRIVATE /permissive-)
  endif()
else()
  target_compile_options(chapter_metrics PRIVATE -Wall -Wextra -Wpedantic)
  target_compile_options(story_feature_metrics PRIVATE -Wall -Wextra -Wpedantic)
endif()

target_compile_definitions(chapter_metrics PRIVATE
  $<$<CONFIG:Release>:NDEBUG>
)
target_compile_definitions(story_feature_metrics PRIVATE
  $<$<CONFIG:Release>:NDEBUG>
)

install(TARGETS chapter_metrics story_feature_metrics RUNTIME DESTINATION bin)

add_test(NAME chapter_metrics_demo COMMAND chapter_metrics --demo)
add_test(NAME story_feature_metrics_demo COMMAND story_feature_metrics --demo)
