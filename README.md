# Biometric Quality Assessment Tool (BQAT)

BQAT is a biometric quality assessment tool for generating and analysing biometric sample quality to international standards and supporting customized metrics. It takes as input directory of biometric images/data in standard formats (e.g. wsq,png,jpg) and output both the raw quality information as well as an analysis report. 

It is available to be run from a docker image. 

+ ### Fingerprint
    The analysis of fingerprint engine based on NIST/NFIQ2 quality features. The quality score links image quality of optical and ink 500 PPI fingerprints to operational recognition performance.

+ ### Face
    The face image assessment provides metrics includes head pose, smile detection, inter-eye-distance, closed eyes, etc.

+ ### Iris
    The face image assessment provides various quality attributes, features, and ISO metrics.

## Installation

This tool is designed to be run as container.

### Build the Image

```sh
# Build the image
docker build -t bqat:latest .
```

## Usage

The tool is designed to be executed on a directory of /data. You will need to mount the primary working directory (where all the images are stored) into the container. The default directory in the container for mounting the work directory is `/app/data`, this can be done using the `-v` option in Docker.

The tool does require additional shared memory and this can be set by using the `--shm-size` option in Docker. Generally setting this to 8G works well.

### Quick start

The `run.sh` is a convenience script for running BQAT.

Example:
``` sh
# Run samples in /input with fingerprint mode as default
./run.sh --input data/input/

# Run benchmarking task
./run.sh --input data/input/ --benchmarking

# Run samples in /input with iris mode
./run.sh --input data/input/ --mode iris

# Search the file with name pattern in the input folder
./run.sh --input data/input/ --mode iris --filename "*FINGER*"

# Search the file with specific format in the input folder
./run.sh --input data/input/ --mode iris --search "jp2 pgm bmp"

# Convert the files with specific formats before scanning
./run.sh --input data/input/ --mode fingerprint --convert "jp2 jpeg"

# Specify the file format to convert to
./run.sh --input data/input/ --mode fingerprint --target wsq

# Run samples in /input with face mode, extension function enabled, limit to 100k scan
./run.sh --input data/input/ --mode face --extension --limit 100000
```

Alternate interface:
``` sh
# Enter interactive CLI
./run.sh --interactive
```

### Optional Flags
You can append optional flags as follows:
* -M, --mode         (REQUIRED)  Specify assessment mode (Fingerprint, Face, IRIS).
* -I, --input        (REQUIRED)  Specify input directory
* -O, --output       (OPTIONAL)  Specify output csv file or directory
* -B, --benchmark    (OPTIONAL)  Run system benchmarking analysis
* -L, --limit        (OPTIONAL)  Set a limit for number of files to scan
* -F, --filename     (OPTIONAL)  Specify filename pattern for searching in the folder
* -S, --search       (OPTIONAL)  Specify file types to search within the input folder
* -C, --convert      (OPTIONAL)  Specify file types to convert before processing
* -T, --target       (OPTIONAL)  Specify target type to convert to
* -E, --extension    (OPTIONAL)  Enable customized extension function
* -A, --arm          (OPTIONAL)  Disable multithreading (For ARM64 platform)
* -X, --interactive  (OPTIONAL)  Enter terminal interactive ui
* --help             Show a help message

If the output or log options are not specified then the tool will use a default value.

> For powershell (windows) replace this line
``` sh
-v ${PWD}/data:/app/data
```

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

## Setup validation OR Benchmarking

The tool has a benchmark module to profile the host machine. It will go through a dataset of 1000 files which consist of multiple formats and even corrupted files. The output also includes simple spec of the host machine.

```sh
# Use run.sh
./run.sh --benchmarking

# OR in CLI
docker run --rm -it --shm-size=8G bqat --benchmarking
```

## Licence

The source code for the site is licensed under the MIT license - it is planned for full release as an Open Source project

## Limitations
Please note that only the following file extensions (file types) are supported:
* `.jpeg`
* `.jpg`
* `.bmp`
* `.png`
* `.jp2`
* `.wsq` (fingerprint only)
> For fingerprint, by default, all input types will be converted to `.png`.

For iris samples, if the resolution of the input is higher than 640 by 480, it will be resized.

## Known Issues
+ For large dataset on Linux, in the runtime, when the memory is exhausted, the kernel will try to reclaim some memory, which could freeze the system if critical system process was killed. This may not affect the final output because the docker runtime are still alive. This will not happen on MacOS or windows. Try to limit the memory or cpu available to Docker runtime or increase physical memory. Modify `--cpus` or `--memory` flags in `run.sh` or in the vanilla docker command.

## Offline Deployment
``` sh
# Build the image with version tag
docker build -t bqat:v0.1.0 .

# Save the image as tar file
docker save -o bqat-v0.1.0.tar bqat:v0.1.0
```