docker run --rm \
    --shm-size=8G \
    ghcr.io/biometix/bqat-cli \
    "coverage run -m pytest tests"
