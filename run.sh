#!/bin/bash

flags="$*"
if [ -z "$flags" ]
then
    flags="--help"
fi

sub="\<"
flags=${flags//</"$sub"}
sub="\>"
flags=${flags//>/"$sub"}

docker run --rm -it \
    --shm-size=8G \
    --cpus=8 \
    --memory=10G \
    -v "$(pwd)"/data:/app/data \
    bqat-cli \
    "python3.8 -m bqat -W $(pwd) $flags"
