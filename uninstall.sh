#!/bin/bash

if ! which bqat-cli; then
    printf "Failed! BQAT-CLI not found in your system.\n"
    exit 0
fi

FILE="$(which bqat-cli)"

if sudo rm "$FILE"; then
    printf "Success! BQAT-CLI removed from your system ($FILE).\n"
else
    printf "Failed!\n"
fi


confirm() {
    while true; do
        read -p "Do you want to remove BQAT-CLI docker container as well? (yes/no) " yn
        case $yn in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

if confirm; then
    docker rmi ghcr.io/biometix/bqat-cli:latest
    printf "BQAT-CLI Docker container removed."
fi