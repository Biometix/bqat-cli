docker run --rm -it \
    --shm-size=8G \
    --cpus=8 \
    --memory=10G \
    -v "$(pwd)"/data:/app/data \
    bqat \
    "python3.8 -m pytest tests -v"
