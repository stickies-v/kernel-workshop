cmake_minimum_required(VERSION 3.10)

# Set the project name
project(kernel-cpp-workshop)

# Specify the C++ standard
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Add the executable
add_executable(kernel-cpp-workshop src/main.cpp)

# Find the libbitcoinkernel library
find_library(BITCOINKERNEL_LIBRARY NAMES bitcoinkernel)

# Include the directory containing both bitcoinkernel_wrapper.h and bitcoinkernel.h
target_include_directories(kernel-cpp-workshop PRIVATE include)

# Link the libbitcoinkernel library
target_link_libraries(kernel-cpp-workshop PRIVATE ${BITCOINKERNEL_LIBRARY})
