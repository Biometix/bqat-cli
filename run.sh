#!/bin/bash

OS=$(uname)

flags="$*"
if [ -z "$flags" ]
then
    flags="--help"
fi

if [ "$flags" = "--update" -o "$flags" = "update" ]; then
    docker pull bqat-cli
    # docker bqat-cli | grep image.version
else
    [ ! -d data ] && mkdir data

    sub="\<"
    flags=${flags//</"$sub"}
    sub="\>"
    flags=${flags//>/"$sub"}

    if [ "$OS" = "Linux" -o "$OS" = "Darwin" ]; then
        docker run --rm -it \
            --shm-size=8G \
            -v "$(pwd)"/data:/app/data \
            bqat-cli \
            "python3 -m bqat -W $(pwd) $flags"

    elif [[ "$OS" =~ "MINGW64" ]]; then
        docker run --rm -it \
            --shm-size=8G \
            -v //$(PWD)/data:/app/data \
            bqat-cli \
            "python3 -m bqat -W $(pwd) $flags"
    else
        echo "Error. Unidentified Host."
    fi
fi
