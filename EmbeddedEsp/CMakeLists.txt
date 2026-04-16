cmake_minimum_required(VERSION 3.16)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(EmbeddedEsp)

# Fix ESP-IDF v6.0 framework warning treated as error
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wno-error=implicit-fallthrough")
 