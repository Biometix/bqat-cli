#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage:
  $0 build <OWNER> <REPO> <TAG> <VER_CORE> <VER_CLI>
    Builds for local architecture and pushes ghcr.io/OWNER/REPO:ARCH-TAG
    Prints the image digest (ghcr.io/OWNER/REPO@sha256:<digest>)

  $0 merge <OWNER> <REPO> <TAG> <AMD64_DIGEST> <ARM64_DIGEST>
    Creates and pushes multi-arch image ghcr.io/OWNER/REPO:TAG using the two digests.
    DIGEST arguments must be full ghcr.io/OWNER/REPO@sha256:<digest> form.

Examples:
  ./build-and-publish-multiarch.sh build myuser myrepo v1.0
  ./build-and-publish-multiarch.sh merge myuser myrepo v1.0 \
    ghcr.io/myuser/myrepo@sha256:... amd64 \
    ghcr.io/myuser/myrepo@sha256:... arm64
EOF
  exit 1
}

if [ "$#" -lt 6 ]; then
  usage
fi

cmd=$1
OWNER=$2
REPO=$3
TAG=$4
VER_CORE=$5
VER_CLI=$6

IMAGE_BASE="ghcr.io/${OWNER}/${REPO}"

detect_arch() {
  case "$(uname -m)" in
    x86_64|amd64) echo "amd64" ;;
    arm64|aarch64) echo "arm64" ;;
    *) echo "unknown" ;;
  esac
}

if [ "$cmd" = "build" ]; then
  ARCH=$(detect_arch)
  if [ "$ARCH" = "unknown" ]; then
    echo "Unsupported architecture: $(uname -m)" >&2
    exit 2
  fi

  IMAGE_TAG="${IMAGE_BASE}:${TAG}-${ARCH}"
  echo "Building for arch=${ARCH} -> ${IMAGE_TAG}"
  echo "BQAT-Core version: ${VER_CORE}"
  echo "BQAT-CLI version: ${VER_CLI}"

  # Build using the Dockerfile expecting ARG TARGETARCH VER_CORE VER_CLI
  docker build --build-arg TARGETARCH="${ARCH}" --build-arg VER_CORE="${VER_CORE}" --build-arg VER_CLI="${VER_CLI}" -t "${IMAGE_TAG}" .

  echo "Pushing ${IMAGE_TAG} to GHCR..."
  docker push "${IMAGE_TAG}"

  echo "Pulling back to get digest..."
  # Pull and get repo digest
  docker pull --quiet "${IMAGE_TAG}" >/dev/null
  DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "${IMAGE_TAG}" 2>/dev/null || true)

  if [ -z "$DIGEST" ]; then
    # Fallback: try using the registry API via skopeo if available (optional)
    echo "Warning: could not determine digest from local inspect." >&2
    echo "You can run: docker inspect --format='{{index .RepoDigests 0}}' ${IMAGE_TAG}"
  else
    echo "Pushed image digest: ${DIGEST}"
  fi

  exit 0
fi

if [ "$cmd" = "merge" ]; then
  if [ "$#" -ne 6 ]; then
    echo "merge requires 2 digest args: <AMD64_DIGEST> <ARM64_DIGEST>" >&2
    usage
  fi

  AMD64_DIGEST=$5
  ARM64_DIGEST=$6

  # Validate digest format
  for d in "$AMD64_DIGEST" "$ARM64_DIGEST"; do
    if [[ ! "$d" =~ ^ghcr\.io/.+@sha256:[0-9a-fA-F]{64}$ ]]; then
      echo "Digest '$d' does not appear to be in the form ghcr.io/OWNER/REPO@sha256:<digest>" >&2
      exit 2
    fi
  done

  FINAL_TAG="${IMAGE_BASE}:${TAG}"
  LATEST_TAG="${IMAGE_BASE}:latest"

  echo "Creating multi-arch image ${FINAL_TAG}"
  echo "amd64 -> ${AMD64_DIGEST}"
  echo "arm64 -> ${ARM64_DIGEST}"

  # Preferred: docker buildx imagetools create with explicit platform mapping
  # ensure buildx is available
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker CLI not found" >&2
    exit 2
  fi

  # Create and push manifest
  docker buildx imagetools create \
    --tag "${FINAL_TAG}" \
    --tag "${LATEST_TAG}" \
    "${AMD64_DIGEST}" \
    "${ARM64_DIGEST}"

  echo "Multi-arch image pushed: ${FINAL_TAG}"
  echo "Verify with: docker buildx imagetools inspect ${FINAL_TAG}"
  exit 0
fi

usage
