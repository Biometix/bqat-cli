docker run --rm \
    --shm-size=8G \
    ghcr.io/biometix/bqat-cli \
    "python3.8 -m pytest tests"
