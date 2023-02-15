docker run --rm \
    --shm-size=8G \
    -v "$(pwd)"/data:/app/data \
    bqat-cli \
    "python3.8 -m pytest tests"
