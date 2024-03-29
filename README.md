Biometric Quality Assessment Tool (BQAT) - CLI
==============================================

[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](code_of_conduct.md)
<img alt="GitHub tag (latest by date)" src="https://img.shields.io/github/v/tag/biometix/bqat-cli">
<img alt="GitHub last commit" src="https://img.shields.io/github/last-commit/biometix/bqat-cli">
<img alt="GitHub issues" src="https://img.shields.io/github/issues-raw/biometix/bqat-cli">
<img alt="GitHub commit activity" src="https://img.shields.io/github/commit-activity/m/biometix/bqat-cli">
<img alt="GitHub" src="https://img.shields.io/github/license/biometix/bqat-cli">
[![Build Status](https://github.com/Biometix/bqat-cli/actions/workflows/build.yml/badge.svg)](https://github.com/Biometix/bqat-cli/actions/workflows/build.yml)
[![Test Status](https://github.com/Biometix/bqat-cli/actions/workflows/test.yml/badge.svg)](https://github.com/Biometix/bqat-cli/actions/workflows/test.yml)
[![Release Status](https://github.com/Biometix/bqat-cli/actions/workflows/release.yml/badge.svg)](https://github.com/Biometix/bqat-cli/actions/workflows/release.yml)
[![Tests Status](./reports/junit/tests-badge.svg?dummy=8585744)](https://htmlpreview.github.io/?https://github.com/Biometix/bqat-cli/blob/main/reports/junit/report.html)
[![Coverage Status](./reports/coverage/coverage-badge.svg?dummy=8585744)](https://htmlpreview.github.io/?https://github.com/Biometix/bqat-cli/blob/main/reports/coverage/index.html)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> [biometix.github.io](https://biometix.github.io/)

BQAT is a biometric quality assessment tool for generating and analysing given biometric samples’ quality to international standards as well as to customized metrics. The BQAT tool functions by taking an input directory of biometric data and will produce both the raw quality information as well as an analysis report.

## __Modules__

### Fingerprint:

The analysis of fingerprint engine based on NIST/NFIQ2 quality features. The quality score links image quality of optical and ink 500 PPI fingerprints to operational recognition performance.

### Face:

The face image assessment provides metrics includes head pose, smile detection, inter-eye-distance, closed eyes, etc.

### Iris:

The iris sample assessment module provides various quality attributes, features, and ISO metrics.

### Speech:

The speech assessment provides various quality metrics, including naturalness, coloration, noisiness, etc.

## __Contributing__

We welcome all kinds of contributions, including but not limited to bug reports, proposals and requests of new features, and of course pull requests.

We use GitHub issues for tracking requests and bugs. Contributors are expected to adhere to the [Contributor Covenant](http://contributor-covenant.org) code of conduct.

### Submit changes:

- Open an [Issue](https://github.com/Biometix/bqat-cli/issues) with description of motivates.

- Discuss the proposed changes with other users and the maintainers

- Open a [Pull Request](https://github.com/Biometix/bqat-cli/pulls)

- Ensure all CI tests pass

- Provide instructions to demo the changes

- It will be accepted after code review!

## __License__

The project is available as open source under the terms of the [Apache-2.0 license](https://www.apache.org/licenses/LICENSE-2.0.html).
