# Native Windows runtime target. Uses the base engine's renderer and runtime sources.
file(GLOB BB_RUNTIME_C CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/../src/runtime*.c")
file(GLOB BB_WINDOWS_C CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/../src/win32_*.c")
file(GLOB BB_ATRAC_C CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/../third_party/LibAtrac9/C/src/*.c")
add_library(bb_atrac9 STATIC ${BB_ATRAC_C})
target_compile_options(bb_atrac9 PRIVATE -w)
add_executable(bloodborne-seamless ../src/probe.c ${BB_RUNTIME_C} ${BB_WINDOWS_C} ../src/vulkan_smoke.c)
target_include_directories(bloodborne-seamless PRIVATE .. ../src)
target_compile_definitions(bloodborne-seamless PRIVATE _FILE_OFFSET_BITS=64 _WIN32_WINNT=0x0A00)
target_compile_options(bloodborne-seamless PRIVATE -Wall -Wextra -Werror -Wno-error=unused-but-set-global)
target_link_libraries(bloodborne-seamless PRIVATE bbgpu bb_atrac9 Vulkan::Vulkan PkgConfig::SDL3
    m winmm ws2_32 psapi onecore)
target_link_options(bloodborne-seamless PRIVATE -Wl,--disable-dynamicbase,--disable-high-entropy-va)
set_target_properties(bloodborne-seamless PROPERTIES OUTPUT_NAME bb-probe
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../out")
add_executable(bb-gpu-capabilities ../tools/gpu_capabilities.c)
target_compile_definitions(bb-gpu-capabilities PRIVATE _WIN32_WINNT=0x0A00)
target_link_libraries(bb-gpu-capabilities PRIVATE Vulkan::Vulkan PkgConfig::SDL3)
set_target_properties(bb-gpu-capabilities PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../out")
