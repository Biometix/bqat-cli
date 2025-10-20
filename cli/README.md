# BQAT

> BQAT-CLI

[![PyPI - Version](https://img.shields.io/pypi/v/bqat)](https://pypi.python.org/pypi/bqat)
[![PyPI - Format](https://img.shields.io/pypi/format/bqat)](https://pypi.python.org/pypi/bqat)
[![PyPI - License](https://img.shields.io/pypi/l/bqat)](https://pypi.python.org/pypi/bqat)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/bqat)](https://pypi.python.org/pypi/bqat)

A terminal interface to [BQAT](https://biometix.github.io/).

## Highlights

- 🚀 A single tool for data analysis workflow with BQAT, and more.
- 🖥️ Supports macOS, Linux, and Windows.

`bqat` is backed by [Biometix](https://www.biometix.com/).

## Prerequisites

- [Docker](https://www.docker.com/)
- x86 CPU

## Quick Start

1. Install

    ```sh
    pip install bqat
    ```

2. Display help info

    ```sh
    bqat --help
    ```

3. Validate installation via benchmarking

    ```sh
    bqat -B
    ```

4. Run BQAT analysis

    Create a `/data` folder in your working directory for input data.

    ```sh
    bqat --input data/test --mode face
    ```

## Flags for BQAT

Please refer to the documentation of [BQAT](https://biometix.github.io/).

## Flags for the CLI

| Flag | Description |
| --- | --- |
| --version, -v | Show version info. |
| --update | Update BQAT backend container. |
| --uninstall | Uninstall BQAT-CLI. |
