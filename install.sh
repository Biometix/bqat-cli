#!/bin/bash

if curl -o bqat-cli https://raw.githubusercontent.com/Biometix/bqat-cli/refs/tags/v1.7.0-beta/run.sh; then
    printf "\n"
else
    printf "\nDownload failed!\n"
    exit 0
fi

LOCATION="/usr/local/bin"

if chmod +x bqat-cli && sudo mv bqat-cli $LOCATION; then
    printf "Installation finished ($(which bqat-cli))!\n\nTry 'bqat-cli --help' for more information.\n"
else
    printf "Installation failed!\n"
    exit 0
fi