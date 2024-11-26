# libbitcoinkernel workshop

## Goal

The goal of this workshop is to familiarize you with the
[libbitcoinkernel library](https://github.com/bitcoin/bitcoin/pull/30595),
and the various language bindings available for it.

## Approach

`libbitcoinkernel` lends itself particularly well to being used for data
analysis tasks. Previously, one would typically use the Bitcoin Core RPC
(which can be quite slow and clunky for large volumes of data) or write
a custom `blk.data` file parser (which is brittle and error-prone since
it relies on Bitcoin Core implementation details, which change over
time).

In this workshop, we'll be building a simple backend application that
uses `libbitcoinkernel` to fetch block data from disk, and use
additional libraries to parse this data an calculate the frequency of
each [TapScript](https://bitcoinops.org/en/topics/tapscript/) OP_CODE in
a block. The project then provides a simple [frontend application](./frontend/)
to visualize OP_CODE leaderboard.

> [!NOTE] The analysis is limited to TapScript, because it simplifies
> the implementation, but you can take another approach if you wish.

> [!WARNING] libbitcoinkernel is highly experimental software under
> active development, and the language bindings are changing frequently.
> Do not use any of the code in this repository as a reference for
> building your own production code. It is meant to be a learning tool
> only.

## Prerequisites

This workshop should be well suited for you if you:
- have basic knowledge of the Bitcoin protocol and consensus rules
- have basic understanding of memory management and pointers
- are comfortable building a Python, Rust, C or C++ project from scratch

## Getting started

The workshop is aimed at using the Python language bindings. To get started,
head over to the [python](./python/) subdirectory for more instructions.

One can also implement this in [C/C++](./cpp/) or in [Rust](./rust/),
but supporting materials are currently limited.


# Frontend

The project contains an optional minimal frontend application to
visualize the JSON output from the application you've built. See
[`frontend`](./frontend/) for more information on running this.

# About libbitcoinkernel

The libbitcoinkernel project is a new attempt at extracting
Bitcoin Core's consensus engine. The kernel part of the name
highlights one of the key functional differences from the deprecated
libbitcoinconsensus and in fact, most libraries: it is a stateful
library that can spawn threads, do caching, do I/O, and many other
things that one may not normally expect from a library.
