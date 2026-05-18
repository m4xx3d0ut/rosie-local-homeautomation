FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG ANDROID_SDK_ROOT=/opt/android-sdk

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
    fontconfig \
    git-core \
    gnupg \
    imagemagick \
    libc6-dev-i386 \
    libgl1 \
    libncurses5 \
    lib32ncurses-dev \
    lib32z1-dev \
    libxml2-utils \
    lzop \
    openjdk-11-jdk \
    python3 \
    python3-yaml \
    python-is-python3 \
    rsync \
    unzip \
    xz-utils \
    zip \
    zlib1g-dev \
    zstd \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://storage.googleapis.com/git-repo-downloads/repo \
    -o /usr/local/bin/repo \
 && chmod +x /usr/local/bin/repo

RUN mkdir -p "${ANDROID_SDK_ROOT}/cmdline-tools" \
 && curl -fsSL https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip \
    -o /tmp/cmdline-tools.zip \
 && unzip -q /tmp/cmdline-tools.zip -d /tmp/android-cmdline \
 && mv /tmp/android-cmdline/cmdline-tools "${ANDROID_SDK_ROOT}/cmdline-tools/latest" \
 && rm -rf /tmp/cmdline-tools.zip /tmp/android-cmdline

ENV ANDROID_SDK_ROOT=${ANDROID_SDK_ROOT}
ENV ANDROID_HOME=${ANDROID_SDK_ROOT}
ENV PATH=${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools:${ANDROID_SDK_ROOT}/emulator:${PATH}
ENV USE_CCACHE=1
ENV CCACHE_DIR=/ccache

RUN yes | sdkmanager --licenses >/dev/null \
 && sdkmanager "platform-tools" "emulator" >/dev/null

WORKDIR /work
