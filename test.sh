docker run --rm \
    --shm-size=8G \
    ghcr.io/biometix/bqat-cli \
    "python3 -m pytest tests -v"
