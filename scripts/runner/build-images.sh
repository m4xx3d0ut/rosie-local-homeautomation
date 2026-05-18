#!/usr/bin/env bash
set -euo pipefail

PROFILE_PATH="${PROFILE_PATH:-/work/repo/profiles/shield-k1-lineage15-dev.yaml}"
ENV_FILE="/tmp/rosie-profile.env"

python3 /work/repo/scripts/runner/render-env.py \
  --profile "${PROFILE_PATH}" \
  --container \
  --output "${ENV_FILE}"
# shellcheck disable=SC1090
source "${ENV_FILE}"
# shellcheck disable=SC1091
source /work/repo/scripts/runner/ensure-container-user.sh

mkdir -p "${ANDROID_ROOT}" "${CCACHE_DIR}" "${ARTIFACT_DIR}/logs"

if [[ ! -d "${ANDROID_ROOT}/.repo" ]]; then
  echo "missing Android source checkout: ${ANDROID_ROOT}; run make sync-sources first" >&2
  exit 1
fi

if [[ "${SYNC_SOURCES_ON_BUILD:-0}" == "1" ]]; then
  /work/repo/scripts/runner/sync-sources.sh
else
  echo "Using existing Android source checkout: ${ANDROID_ROOT}"
fi

if [[ -f "${REPO_ROOT}/${BLOB_ARCHIVE}" ]]; then
  tar -I zstd -xf "${REPO_ROOT}/${BLOB_ARCHIVE}" -C "${ANDROID_ROOT}"
else
  echo "missing vendor blob archive: ${REPO_ROOT}/${BLOB_ARCHIVE}" >&2
  exit 1
fi

python3 /work/repo/scripts/runner/prune-missing-optional-vendor-apps.py \
  --android-root "${ANDROID_ROOT}" \
  2>&1 | tee "${ARTIFACT_DIR}/logs/prune-missing-optional-vendor-apps.log"

/work/repo/scripts/runner/inject-prebuilts.sh 2>&1 | tee "${ARTIFACT_DIR}/logs/inject-prebuilts.log"

if [[ -n "${EMULATOR_SYSTEM_IMAGE_SIZE:-}" ]]; then
  emulator_board_config="${ANDROID_ROOT}/$(dirname "${EMULATOR_PRODUCT_MK}")/BoardConfig.mk"
  if [[ ! -f "${emulator_board_config}" ]]; then
    echo "missing emulator BoardConfig: ${emulator_board_config}" >&2
    exit 1
  fi
  sed -i '/^# Rosie emulator sizing begin$/,/^# Rosie emulator sizing end$/d' "${emulator_board_config}"
  {
    printf '\n# Rosie emulator sizing begin\n'
    printf 'BOARD_SYSTEMIMAGE_PARTITION_SIZE := %s\n' "${EMULATOR_SYSTEM_IMAGE_SIZE}"
    printf '# Rosie emulator sizing end\n'
  } >> "${emulator_board_config}"
fi

cd "${ANDROID_ROOT}"
# shellcheck disable=SC1091
set +u
source build/envsetup.sh

clean_shared_framework_resources() {
  # framework-res uses product overlays but writes some generated outputs under
  # out/target/common. Clear them when switching products so framework-res.apk
  # and the generated android/com.android.internal R classes agree.
  rm -rf \
    "${ANDROID_ROOT}/out/target/common/R/android" \
    "${ANDROID_ROOT}/out/target/common/R/com/android/internal" \
    "${ANDROID_ROOT}/out/target/common/obj/APPS/framework-res_intermediates"
}

echo "Building Shield K1 target: ${TABLET_LUNCH}"
clean_shared_framework_resources
lunch "${TABLET_LUNCH}"
eval "${TABLET_BUILD_COMMAND}" 2>&1 | tee "${ARTIFACT_DIR}/logs/build-tablet.log"

# AOSP/Lineage common intermediates are shared across products in this checkout.
# Build the emulator target last so validation sees an emulator framework and
# emulator apps compiled against the same resource table.
echo "Building emulator companion target: ${EMULATOR_LUNCH}"
clean_shared_framework_resources
lunch "${EMULATOR_LUNCH}"
eval "${EMULATOR_BUILD_COMMAND}" 2>&1 | tee "${ARTIFACT_DIR}/logs/build-emulator.log"

{
  find "${ANDROID_ROOT}/out/target/product/${EMULATOR_OUTPUT_PRODUCT}" -maxdepth 3 \
    \( -name 'lineage-*.zip' -o -name '*.img' -o -name 'sdk-repo-linux-system-images.zip' \) \
    -print
  find "${ANDROID_ROOT}/out/target/product/${TABLET_OUTPUT_PRODUCT}" -maxdepth 3 \
    \( -name 'lineage-*.zip' -o -name '*.img' -o -name 'sdk-repo-linux-system-images.zip' \) \
    -print
} | sort > "${ARTIFACT_DIR}/ANDROID-OUTPUTS.txt"
