# Biometric Quality Assessment Tool (BQAT)

[![Build Status](https://github.com/Biometix/bqat-cli/actions/workflows/build.yml/badge.svg)](https://github.com/Biometix/bqat-cli/actions/workflows/build.yml)
[![Test Status](https://github.com/Biometix/bqat-cli/actions/workflows/test.yml/badge.svg)](https://github.com/Biometix/bqat-cli/actions/workflows/test.yml)
[![Release Status](https://github.com/Biometix/bqat-cli/actions/workflows/release.yml/badge.svg)](https://github.com/Biometix/bqat-cli/actions/workflows/release.yml)
[![Tests Status](./reports/junit/tests-badge.svg?dummy=8585744)](https://htmlpreview.github.io/?https://github.com/Biometix/bqat-cli/blob/main/reports/junit/report.html)
[![Coverage Status](./reports/coverage/coverage-badge.svg?dummy=8585744)](https://htmlpreview.github.io/?https://github.com/Biometix/bqat-cli/blob/main/reports/coverage/index.html)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

<img alt="GitHub tag (latest by date)" src="https://img.shields.io/github/v/tag/biometix/bqat-cli">
<img alt="GitHub last commit" src="https://img.shields.io/github/last-commit/biometix/bqat-cli">
<img alt="GitHub issues" src="https://img.shields.io/github/issues-raw/biometix/bqat-cli">
<img alt="GitHub commit activity" src="https://img.shields.io/github/commit-activity/m/biometix/bqat-cli">
<img alt="GitHub" src="https://img.shields.io/github/license/biometix/bqat-cli">

![PyPI downloads](https://img.shields.io/badge/dynamic/json?label=downloads&query=total_downloads&url=https%3A%2F%2Fpypistats.org%2Fapi%2Fpackages%2Fbqat%2Foverall&color=blue)
[![PyPI - Version](https://img.shields.io/pypi/v/bqat)](https://pypi.python.org/pypi/bqat)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/bqat)](https://pypi.python.org/pypi/bqat)
[![PyPI - Format](https://img.shields.io/pypi/format/bqat)](https://pypi.python.org/pypi/bqat)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/bqat)](https://pypi.python.org/pypi/bqat)
[![PyPI - License](https://img.shields.io/pypi/l/bqat)](https://pypi.python.org/pypi/bqat)

BQAT is a biometric quality assessment tool for generating and analysing biometric sample quality to international standards and supporting customized metrics. It takes as input directory of biometric images/data in standard formats (e.g. wsq,png,jpg) and output both the raw quality information as well as an analysis report.

+ `Fingerprint`

    The analysis of fingerprint engine based on NIST/NFIQ2 quality features. The quality score links image quality of optical and ink 500 PPI fingerprints to operational recognition performance.

+ `Face`

    The face image assessment provides metrics includes head pose, smile detection, inter-eye-distance, closed eyes, etc.

+ `Iris`

    The face image assessment provides various quality attributes, features, and ISO metrics.

+ `Speech`

    The speech assessment provides various quality metrics, including naturalness, coloration, noisiness, etc.

## Quick start

Install BQAT-CLI:

```sh
pip install bqat
```

Example Usage:

``` sh
# Print help information
bqat --help

# Print version information
bqat --version

# Run benchmarking task
bqat --benchmark

# Run samples in `data` with fingerprint mode as default
bqat --input data

# Run samples in `data` with iris mode
bqat --input data --mode iris

# Run samples in `data` with iris mode and generate EDA report
bqat --input data --mode iris --report

# Search the file with name pattern in the input folder
bqat --input data --mode iris --filename "*FINGER*"

# Search the file with specific format in the input folder
bqat --input data --mode iris --type "jp2,pgm,bmp"

# Convert the files with specific formats before scanning
bqat --input data --mode fingerprint --convert "jp2,jpeg"

# Specify the file format to convert to
bqat --input data --mode fingerprint --target wsq

# Run samples in `data` with face mode, extension function enabled, limit to 100k scan
bqat --input data --mode face --extension --limit 100000
```

<!-- Alternate interface:
``` sh
# Enter interactive CLI
./run.sh --interactive
``` -->

### Optional Flags

You can append optional flags as follows:

+ -M, --mode         (REQUIRED)  Specify assessment mode (Fingerprint, Face, Iris).
+ -I, --input        (REQUIRED)  Specify input directory
+ -O, --output       (OPTIONAL)  Specify output csv file or directory
+ -B, --benchmark    (OPTIONAL)  Run system benchmarking analysis
+ -L, --limit        (OPTIONAL)  Set a limit for number of files to scan
+ -F, --filename     (OPTIONAL)  Specify filename pattern for searching in the folder
+ -S, --search       (OPTIONAL)  Specify file types to search within the input folder
+ -C, --convert      (OPTIONAL)  Specify file types to convert before processing
+ -T, --target       (OPTIONAL)  Specify target type to convert to
+ -E, --extension    (OPTIONAL)  Enable customized extension function
+ --help             Show a help message

If the output or log options are not specified then the tool will use a default value.

## Input & Output

### Input Format

For fingerprints the tool works with image formats WSQ and PNG. For both of these formats the image will be run directly through NFIQ2. The image formats JPG and BMP are also supported but will be converted to WSQ first before being run through NFIQ2.

NFIQ2 expects images to have a resolution of at least 500 PPI. The tool will force NFIQ2 to run on images of lower resolution but the result may be inaccurate.

### Output Format

The tool will produce a csv with all the quality scores generated by the engines and some additional columns.

#### _Fingerprint_

| Column Name | Description |
|---|----|
| Filename | Filename of the image, including the directory path |
| FingerCode | NFIQ2 Output |
| QualityScore | NFIQ2 Output |
| OptionalError | NFIQ2 Output |
| Quantized | NFIQ2 Output |
| Resampled | NFIQ2 Output |
| UniformImage | NFIQ2 Output |
| EmptyImageOrContrastTooLow | NFIQ2 Output |
| FingerprintImageWithMinutiae | NFIQ2 Output |
| SufficientFingerprintForeground | NFIQ2 Output |
| EdgeStd | Metric to identify malformed images |
| Width | Width of the image in pixels |
| Height | Height of the image in pixels |
| uuid | The unique id assigned to this image |

#### _Face_

| Column Name | Description |
|---|----|
| Filename | Filename of the image, including the directory path |
| IPD | Inter-pupillary distance |
| Closed eye left | Bool value |
| Closed eye right | Bool value |
| Head pose yaw | Direction and degree |
| Head pose pitch | Direction and degree |
| Head pose roll | Direction and degree |
| Expression smile | Bool value |
| Face recognition confidence level | Percentage |

#### _Iris_

| Column Name | Description |
|---|----|
| quality | An overall quality score that leverages several statistics together |
| contrast | Raw score quantifying overall image contrast |
| sharpness | Raw score quantifying the sharpness of the image |
| iris_diameter | Raw diameter of the iris measured in pixels |
| percent_visible_iris | Percentage of visible iris area |
| iris_pupil_gs | Raw measure quantifying how distinguishable the boundary is between the pupil and the iris |
| iris_sclera_gs | Raw measure quantifying how distinguishable the boundary is between the iris and the sclera |

#### _Report_

A overview statistical report on each of the column. 

#### _Log_

The log file will show some information on the process, including errors, warnings, and the total execution time of the job.

## Limitations

Please note that only the following file extensions (file types) are supported:

+ `.jpeg`
+ `.jpg`
+ `.bmp`
+ `.png`
+ `.jp2`
+ `.wsq` (fingerprint only)

> For fingerprint, by default, all input types will be converted to `.png`.

For iris samples, if the resolution of the input is higher than 640 by 480, it will be resized.

> When calling `bqat` from PowerShell, use "/" instead of "\" in the path.

> When calling `bqat` from Command Prompt, wrap the path with "" (--input "path/to/folder").

## Offline Deployment

``` sh
# Build the image
docker build --build-arg VER_CORE=0.1.0 --build-arg VER_CLI=0.1.0 -t bqat-cli:latest .

# Save the image as tarball
docker save bqat-cli:latest | zstd > bqat-cli.tar.zst

# Load the image from tarball
zstd -d -c bqat-cli.tar.zst | docker load
```

## Backend Deployment

This backend is designed to be run as container.

### Build the Image

```sh
# Build the image
docker build -t bqat-cli:latest .
```

## Note

The tool is designed to be executed on a directory of /data. You will need to mount the primary working directory (where all the images are stored) into the container. The default directory in the container for mounting the work directory is `/app/data`, this can be done using the `-v` option in Docker.

The tool does require additional shared memory and this can be set by using the `--shm-size` option in Docker. Generally setting this to 8G works well.

## CLI Development

Run package:

```sh
uv run bqat --help
```

Build python wheel:

```sh
uv build
```

Build binary exe:

```sh
uv run pyinstaller -F src/bqat/cli.py -n bqat
```

## Multi-platform Build

+ Run build step on each machine; collect the printed digests (or run docker inspect to read them).

``` sh
./build-and-publish-multiarch.sh build <OWNER> <REPO> <TAG> <VER_CORE> <VER_CLI>
```

+ Run merge step once (on any machine) with the two full digest strings.

``` sh
./build-and-publish-multiarch.sh merge <OWNER> <REPO> <TAG> <AMD64_DIGEST> <ARM64_DIGEST>
```

> Make sure docker login ghcr.io is completed beforehand.
