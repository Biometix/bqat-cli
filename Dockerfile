FROM ubuntu:22.04 AS build

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH

RUN echo "Building target ${TARGETARCH} on $(uname -m) platform."; \
    set -e && apt update && apt upgrade -y && \
    apt -y --no-install-recommends install git less vim g++ curl libopencv-dev libjsoncpp-dev qtbase5-dev build-essential libssl-dev libdb-dev libdb++-dev libopenjp2-7 libopenjp2-tools libpcsclite-dev libssl-dev libopenjp2-7-dev libjpeg-dev libpng-dev libtiff-dev zlib1g-dev libopenmpi-dev libdb++-dev libsqlite3-dev libhwloc-dev libavcodec-dev libavformat-dev libswscale-dev ca-certificates; \
    if [ "$TARGETARCH" = "arm64" ]; \
    then \
    echo "Targeting aarch64"; \
    curl -L -O https://github.com/Kitware/CMake/releases/download/v3.29.1/cmake-3.29.1-linux-aarch64.sh; \
    else \
    echo "Targeting x86_64"; \
    curl -L -O https://github.com/Kitware/CMake/releases/download/v3.29.1/cmake-3.29.1-linux-x86_64.sh; \
    fi; \
    chmod +x cmake*.sh; mkdir /opt/cmake; ./cmake*.sh --prefix=/opt/cmake --skip-license; ln -s /opt/cmake/bin/cmake /usr/local/bin/cmake;\
    mkdir /app 2>/dev/null || true; \
    cd /app; \
    git clone --verbose https://github.com/mitre/biqt --branch master biqt-pub; \
    export NUM_CORES=$(cat /proc/cpuinfo | grep -Pc "processor\s*:\s*[0-9]+\s*$"); \
    echo "Builds will use ${NUM_CORES} core(s)."; \
    cd /app/biqt-pub; \
    mkdir build; \
    cd build; \
    cmake -DBUILD_TARGET=UBUNTU -DCMAKE_BUILD_TYPE=Release -DWITH_JAVA=OFF ..; \
    make -j${NUM_CORES}; \
    make install; \
    source /etc/profile.d/biqt.sh; \
    cd /app; git clone https://github.com/mitre/biqt-iris.git; \
    cd /app/biqt-iris; \
    mkdir build; \
    cd build; \
    cmake -DBIQT_HOME=/usr/local/share/biqt -DCMAKE_BUILD_TYPE=Release ..; \
    make -j${NUM_CORES}; \
    make install; \
    cd /app; \
    git clone https://github.com/biometrics/openbr.git openbr || exit 5; \
    cd /app/openbr; \
    git checkout 1e1c8f; \
    mkdir build; \
    cd build; \
    cmake -DCMAKE_BUILD_TYPE=Release -DBR_WITH_OPENCV_NONFREE=OFF -DCMAKE_INSTALL_PREFIX=/opt/openbr ..; \
    export NUM_CORES=$(cat /proc/cpuinfo | grep -Pc "processor\s*:\s*[0-9]+\s*$"); \
    make -j${NUM_CORES}; \
    make install; \
    cd /app; \
    git clone https://github.com/mitre/biqt-face.git biqt-face --depth=1 --branch master; \
    cd /app/biqt-face; \
    mkdir build; \
    cd build; \
    cmake -DCMAKE_BUILD_TYPE=Release -DOPENBR_DIR=/opt/openbr -DBIQT_HOME=/usr/local/share/biqt ..; \
    make -j${NUM_CORES}; \
    make install; \
    cd /app; \
    git clone --recursive https://github.com/usnistgov/NFIQ2.git; \
    cd NFIQ2; \
    git checkout 76b8c4e0b0541f3deab832b1a496e524edc0b5b6; \
    mkdir build; \
    cd build; \
    cmake .. -DCMAKE_CONFIGURATION_TYPES=Release; \
    cmake --build . --config Release; \
    cmake --install .

RUN apt install -y --no-install-recommends python3-pip liblapack-dev ca-certificates; \
    pip install conan==2.0.17 cmake==3.26; \
    cd /app; mkdir ofiq; cd ofiq; \
    git clone https://github.com/BSI-OFIQ/OFIQ-Project.git; \
    cd OFIQ-Project; \
    git checkout df8fbb5e4bd8de09ae998ff69bc252f6be4367f8; \
    cd scripts; \
    chmod +x *.sh; \
    if [ "$TARGETARCH" = "arm64" ]; \
    then ./build.sh --os linux-arm64; mv /app/ofiq/OFIQ-Project/install_arm64_linux /app/ofiq/OFIQ-Project/install_linux; \
    else ./build.sh;  mv /app/ofiq/OFIQ-Project/install_x86_64_linux /app/ofiq/OFIQ-Project/install_linux; \
    fi

## BIQT Contact Detector
# RUN set -e; \
#     source /etc/profile.d/biqt.sh; \
#     if [ "${WITH_BIQT_CONTACT_DETECTOR}" == "ON" ]; then \
#     ( mkdir /app 2>/dev/null || true ); \
#     cd /app; \
#     git clone https://github.com/mitre/biqt-contact-detector biqt-contact-detector --branch "master --depth 1; \
#     cd biqt-contact-detector; \
#     pip install -r requirements.txt; \
#     export NUM_CORES=$(cat /proc/cpuinfo | grep -Pc "processor\s*:\s*[0-9]+\s*$"); \
#     mkdir build; \
#     cd build; \
#     cmake -DCMAKE_BUILD_TYPE=Release ..; \
#     make -j${NUM_CORES}; \
#     make install; \
#     fi;


FROM ubuntu:22.04 AS release

WORKDIR /app

COPY --from=build /usr/local /usr/local
COPY --from=build /etc/profile.d/biqt.sh /etc/profile.d/biqt.sh
COPY --from=build /opt/openbr /opt/openbr

COPY --from=build /usr/lib /usr/lib

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=off
ENV MPLCONFIGDIR=/app/temp
# ENV RAY_USE_MULTIPROCESSING_CPU_COUNT=1
ENV RAY_DISABLE_DOCKER_CPU_WARNING=1
ENV RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO=0
ENV YDATA_PROFILING_NO_ANALYTICS=True
# ENV YOLO_CONFIG_DIR=/tmp/yolo
ENV DEBIAN_FRONTEND=noninteractive
ENV OPENCV_LOG_LEVEL=ERROR
ENV NUMBA_CACHE_DIR=/tmp

COPY bqat/core/bqat_core/misc/BQAT /app/BQAT/
COPY bqat/core/bqat_core/misc/NISQA /app/NISQA/
COPY bqat/core/bqat_core/misc/OFIQ /app/OFIQ/
COPY Pipfile Pipfile.lock /app/

COPY tests /app/tests/

RUN apt update && apt -y --no-install-recommends install python3-pip libblas-dev liblapack-dev libsndfile1 build-essential cmake python3-dev ninja-build && \
    python3 -m pip install pipenv && \
    if [ "${DEV}" == "true" ]; \
    then pipenv requirements --dev > requirements.txt; \
    else pipenv requirements > requirements.txt; \
    fi; \
    if [ "$ARCH" = "arm64" ]; \
    then \
    git clone https://github.com/KaveIO/PhiK.git && cd PhiK && git checkout tags/v0.12.5 && cd .. && python3 -m pip install PhiK/ && \
    python3 -m pip install BQAT/wsq*.whl; \
    fi; \
    python3 -m pip uninstall -y pipenv && \
    python3 -m pip install -r requirements.txt && \
    python3 -m pip cache purge; python3 -m compileall . && \
    apt remove -y --purge python3-pip build-essential cmake python3-dev ninja-build && \
    rm -rf /var/lib/apt/lists/*

# RUN mkdir -p /root/.deepface/weights && \
#     wget https://github.com/serengil/deepface_models/releases/download/v1.0/facial_expression_model_weights.h5 -P /root/.deepface/weights/ && \
#     wget https://github.com/serengil/deepface_models/releases/download/v1.0/age_model_weights.h5 -P /root/.deepface/weights/ && \
#     wget https://github.com/serengil/deepface_models/releases/download/v1.0/gender_model_weights.h5 -P /root/.deepface/weights/ && \
#     wget https://github.com/serengil/deepface_models/releases/download/v1.0/race_model_single_batch.h5 -P /root/.deepface/weights/

RUN mkdir data temp

RUN groupadd -r assessors && useradd -M -g assessors -s /bin/false assessor
RUN chown -R assessor /app/data /app/temp /app/tests
USER assessor

COPY  --chown=assessor:assessors bqat /app/bqat/

COPY --from=build /app/ofiq/OFIQ-Project/install_linux/Release/bin ./OFIQ/bin
COPY --from=build /app/ofiq/OFIQ-Project/install_linux/Release/lib ./OFIQ/lib
COPY --from=build /app/ofiq/OFIQ-Project/data/models ./OFIQ/models

ARG VER_CORE
ARG VER_CLI
LABEL bqat.core.version=$VER_CORE
LABEL bqat.cli.version=$VER_CLI

ENTRYPOINT [ "/bin/bash", "-l", "-c" ]
CMD [ "python3 -m bqat --help" ]