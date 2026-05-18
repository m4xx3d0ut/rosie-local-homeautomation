FROM ubuntu:18.04

ARG DEBIAN_FRONTEND=noninteractive
ARG ANDROID_SDK_ROOT=/opt/android-sdk
ARG CMDLINE_TOOLS_VERSION=6609375
ARG ANDROID_EMULATOR_ZIP=emulator-linux_x64-7425822.zip

RUN apt-get update && apt-get install -y --no-install-recommends \
    adb \
    bc \
    bison \
    build-essential \
    ca-certificates \
    ccache \
    curl \
    fastboot \
    flex \
    g++-multilib \
    gcc-multilib \
    git-lfs \
    git-core \
    gnupg \
    gperf \
    imagemagick \
    lib32ncurses5-dev \
    lib32readline-dev \
    lib32z1-dev \
    libgl1 \
    libnss-wrapper \
    libxkbfile1 \
    liblz4-tool \
    libncurses5-dev \
    libssl-dev \
    libxml2 \
    libxml2-utils \
    lzop \
    openjdk-8-jdk \
    pngcrush \
    python \
    python3 \
    python3-yaml \
    repo \
    rsync \
    schedtool \
    squashfs-tools \
    unzip \
    x11-utils \
    xsltproc \
    xz-utils \
    zip \
    zlib1g-dev \
    zstd \
 && rm -rf /var/lib/apt/lists/*

RUN git lfs install --system

RUN curl -fsSL https://storage.googleapis.com/git-repo-downloads/repo \
    -o /usr/local/bin/repo \
 && chmod +x /usr/local/bin/repo

RUN mkdir -p "${ANDROID_SDK_ROOT}/cmdline-tools" \
 && curl -fsSL "https://dl.google.com/android/repository/commandlinetools-linux-${CMDLINE_TOOLS_VERSION}_latest.zip" \
    -o /tmp/cmdline-tools.zip \
 && unzip -q /tmp/cmdline-tools.zip -d /tmp/android-cmdline \
 && if [ -d /tmp/android-cmdline/cmdline-tools ]; then \
      mv /tmp/android-cmdline/cmdline-tools "${ANDROID_SDK_ROOT}/cmdline-tools/latest"; \
    else \
      mkdir -p "${ANDROID_SDK_ROOT}/cmdline-tools/latest" \
      && cp -a /tmp/android-cmdline/tools/. "${ANDROID_SDK_ROOT}/cmdline-tools/latest/"; \
    fi \
 && rm -rf /tmp/cmdline-tools.zip /tmp/android-cmdline

ENV ANDROID_SDK_ROOT=${ANDROID_SDK_ROOT}
ENV ANDROID_HOME=${ANDROID_SDK_ROOT}
ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
ENV PATH=${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools:${ANDROID_SDK_ROOT}/emulator:${PATH}
ENV USE_CCACHE=1
ENV CCACHE_DIR=/ccache

RUN sed -i 's/TLSv1, TLSv1.1, //g' "${JAVA_HOME}/jre/lib/security/java.security"

RUN yes | sdkmanager --licenses >/dev/null \
 && sdkmanager "platform-tools" >/dev/null

RUN rm -rf "${ANDROID_SDK_ROOT}/emulator" \
 && curl -fsSL "https://dl.google.com/android/repository/${ANDROID_EMULATOR_ZIP}" \
    -o /tmp/android-emulator.zip \
 && unzip -q /tmp/android-emulator.zip -d "${ANDROID_SDK_ROOT}" \
 && rm -f /tmp/android-emulator.zip

WORKDIR /work
