$flags = $args

# Check Docker is running
if ((docker ps 2>&1) -match '^(?!error)'){
    Write-Host ""
} else {
    Write-Host "Please start Docker before running this script"
    Exit
}

# Run BQAT-CLI
docker run --rm -it --shm-size=8G -v $PWD\data:/app/data ghcr.io/biometix/bqat-cli:latest "python3 -m bqat $flags"
