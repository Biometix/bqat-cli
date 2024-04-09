FROM ubuntu:20.04 AS build

SHELL ["/bin/bash", "-c"] 

ARG WITH_BIQT_FACE=ON
ENV WITH_BIQT_FACE ${WITH_BIQT_FACE}

ARG WITH_BIQT_IRIS=ON
ENV WITH_BIQT_IRIS ${WITH_BIQT_IRIS}

ARG WITH_BIQT_CONTACT_DETECTOR=ON
ENV WITH_BIQT_CONTACT_DETECTOR ${WITH_BIQT_CONTACT_DETECTOR}

ARG BIQT_COMMIT=master
ENV BIQT_COMMIT ${BIQT_COMMIT}

ARG BIQT_FACE_COMMIT=master
ENV BIQT_FACE_COMMIT ${BIQT_FACE_COMMIT}

COPY bqat/core/bqat_core/misc/BIQT-Iris /app/biqt-iris/

RUN set -e && \
    apt update && \
    apt upgrade -y; \
    DEBIAN_FRONTEND=noninteractive apt -y install git less vim cmake g++ curl libopencv-dev libjsoncpp-dev pip qtbase5-dev && \
    apt -y install cmake build-essential libssl-dev libdb-dev libdb++-dev libopenjp2-7 libopenjp2-tools libpcsclite-dev libssl-dev libopenjp2-7-dev libjpeg-dev libpng-dev libtiff-dev zlib1g-dev libopenmpi-dev libdb++-dev libsqlite3-dev libhwloc-dev libavcodec-dev libavformat-dev libswscale-dev; \
    echo "BIQT_COMMIT=${BIQT_COMMIT}" ; \
    mkdir /app 2>/dev/null || true; \
    cd /app; \
    git clone --verbose https://github.com/mitre/biqt --branch "${BIQT_COMMIT}" biqt-pub; \
    export NUM_CORES=$(cat /proc/cpuinfo | grep -Pc "processor\s*:\s*[0-9]+\s*$"); \
    echo "Builds will use ${NUM_CORES} core(s)."; \
    cd /app/biqt-pub; \
    mkdir build; \
    cd build; \
    cmake -DBUILD_TARGET=UBUNTU -DCMAKE_BUILD_TYPE=Release -DWITH_JAVA=OFF ..; \
    make -j${NUM_CORES}; \
    make install; \
    source /etc/profile.d/biqt.sh; \
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
    git clone https://github.com/mitre/biqt-face.git biqt-face --depth=1 --branch "${BIQT_FACE_COMMIT}"; \
    cd /app/biqt-face; \
    mkdir build; \
    cd build; \
    cmake -DCMAKE_BUILD_TYPE=Release -DOPENBR_DIR=/opt/openbr ..; \
    make -j${NUM_CORES}; \
    make install

RUN apt install -y python3-pip liblapack-dev; \
    pip install conan cmake; \
    cd /app; mkdir ofiq; cd ofiq; \
    git clone https://github.com/BSI-OFIQ/OFIQ-Project.git; \
    cd OFIQ-Project/scripts; \
    chmod +x *.sh; \
    ./build.sh

# RUN cd /app; \
#     git clone --recursive https://github.com/usnistgov/NFIQ2.git; \
#     cd NFIQ2; \
#     mkdir build; \
#     cd build; \
#     cmake .. -DCMAKE_CONFIGURATION_TYPES=Release; \
#     cmake --build . --config Release; \
#     cmake --install .


FROM ubuntu:20.04 AS release

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

COPY bqat/core/bqat_core/misc/BQAT/haarcascade_smile.xml bqat_core/misc/haarcascade_smile.xml
COPY bqat/core/bqat_core/misc/NISQA/conda-lock.yml .
COPY bqat/core/bqat_core/misc/NISQA /app/
COPY bqat/core/bqat_core/misc/OFIQ /app/OFIQ/
COPY Pipfile /app/

ENV PATH=/app/mamba/bin:${PATH}
RUN apt update && apt -y install curl ca-certificates libblas-dev liblapack-dev; curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh" && \
    ( echo yes ; echo yes ; echo mamba ; echo yes ) | bash Mambaforge-$(uname)-$(uname -m).sh && \
    mamba install --channel=conda-forge --name=base conda-lock=1.4 && \
    conda-lock install --name nisqa conda-lock.yml && \
    mamba clean -afy && \
    useradd assessor && chown -R assessor /app && \
    python3 -m pip install pipenv && \
    pipenv lock && \
    pipenv requirements > requirements.txt && \
    python3 -m pip uninstall -y pipenv && \
    python3 -m pip install -r requirements.txt

RUN cd /app; mkdir misc; cd misc; curl -L -O https://github.com/usnistgov/NFIQ2/releases/download/v2.2.0/nfiq2_2.2.0-1_amd64.deb; \
    apt install -y ./*amd64.deb

# RUN curl -L -O https://github.com/usnistgov/NFIQ2/releases/download/v2.2.0/nfiq2_2.2.0-1_amd64.deb --create-dirs --output-dir /app/misc/ && \
#     cd /app/misc; apt install -y ./*amd64.deb

# # RUN mkdir -p /root/.deepface/weights && \
# #     wget https://github.com/serengil/deepface_models/releases/download/v1.0/facial_expression_model_weights.h5 -P /root/.deepface/weights/ && \
# #     wget https://github.com/serengil/deepface_models/releases/download/v1.0/age_model_weights.h5 -P /root/.deepface/weights/ && \
# #     wget https://github.com/serengil/deepface_models/releases/download/v1.0/gender_model_weights.h5 -P /root/.deepface/weights/ && \
# #     wget https://github.com/serengil/deepface_models/releases/download/v1.0/race_model_single_batch.h5 -P /root/.deepface/weights/

USER assessor

COPY bqat /app/bqat/

COPY --from=build /app/ofiq/OFIQ-Project/install_x86_64_linux/Release/bin ./OFIQ/bin
COPY --from=build /app/ofiq/OFIQ-Project/install_x86_64_linux/Release/lib ./OFIQ/lib
COPY --from=build /app/ofiq/OFIQ-Project/data/models ./OFIQ/models

ARG VER_CORE
ARG VER_API
LABEL BQAT.core.version=$VER_CORE
LABEL BQAT.api.version=$VER_API

ENTRYPOINT [ "/bin/bash", "-l", "-c" ]
CMD [ "python3 -m bqat --help" ]