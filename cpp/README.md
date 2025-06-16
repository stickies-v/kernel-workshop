# C++

C++ support for this workshop is currently limited. The included
[`bitcoinkernel_wrapper.h`](./include/bitcoinkernel_wrapper.h) provides
a C++ native wrapper for `bitcoinkernel`.

After completing [`main.cpp`](./src/main.cpp) based on the Python
workshop, you can use the provided [`CMakeLists.txt`](./CMakeLists.txt)
to compile the project with `cmake`.

```
cd cpp
cmake -B build
cmake --build build
```
