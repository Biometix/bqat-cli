$flags = $args

# Check if docker is running
if ((docker ps 2>&1) -match '^(?!error)') {
    Write-Host ""
} else {
    Write-Host "Please start Docker before running this script"
    Exit
}

$update_cmds = @(
    "--update",
    "update"
)

if ($flags -in $update_cmds) {
    # Pull latest container
    docker pull ghcr.io/biometix/bqat-cli:latest
    docker inspect ghcr.io/biometix/bqat-cli:latest | Out-String -Stream | Select-String -Pattern 'image.version' -AllMatches
} else {
    # Run BQAT-CLI
    docker run --rm -it --shm-size=8G -v $PWD\data:/app/data ghcr.io/biometix/bqat-cli:latest "python3 -m bqat $flags"
}