# BQAT

[![PyPI - Version](https://img.shields.io/pypi/v/bqat)](https://pypi.python.org/pypi/bqat)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/bqat)](https://pypi.python.org/pypi/bqat)
[![PyPI - Format](https://img.shields.io/pypi/format/bqat)](https://pypi.python.org/pypi/bqat)
[![PyPI - License](https://img.shields.io/pypi/l/bqat)](https://pypi.python.org/pypi/bqat)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/bqat)](https://pypi.python.org/pypi/bqat)

> A command line interface to [BQAT](https://biometix.github.io/).

BQAT (Biometric Quality Assessment Tool) is an open-source tool designed for assessing the quality of biometric data. It provides evaluations for various modalities, including [face](https://biometix.github.io/modality/face.html), [fingerprint](https://biometix.github.io/modality/fingerprint.html), [iris](https://biometix.github.io/modality/iris.html), and [voice](https://biometix.github.io/modality/speech.html).

## Highlights

- 🚀 A simple Python interface for running `BQAT` workflow, and more.
- 🖥️ Supports macOS, Linux, and Windows.

## Prerequisites

- [Docker](https://www.docker.com/)
- x86-64 or ARMv9 CPU

## Quick Start

1. Install

    ```sh
    pip install bqat
    ```

2. Display version info

    ```sh
    bqat --version
    ```

3. Validate installation via benchmarking

    ```sh
    bqat --benchmark
    ```

4. Run BQAT analysis

    ```sh
    bqat --mode face --input data/face
    ```

5. Run BQAT analysis and compile a EDA report

    ```sh
    bqat --mode fingerprint --input data/fingerprint --report
    ```

## Flags for BQAT

Please refer to the documentation of [BQAT](https://biometix.github.io/) further details.

## Flags for the Python CLI

| Flag | Description |
| --- | --- |
| --help | Print help info. |
| --version, -v | Display version info. |
| --update | Update BQAT backend container. |
| --uninstall | Uninstall BQAT-CLI. |
