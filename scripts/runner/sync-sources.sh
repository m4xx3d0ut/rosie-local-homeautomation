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

mkdir -p "${ANDROID_ROOT}" "${ARTIFACT_DIR}/logs" "${HOME:-/tmp}"
git config --global user.name "${GIT_USER_NAME:-Rosie Build}"
git config --global user.email "${GIT_USER_EMAIL:-rosie-build@example.invalid}"

cd "${ANDROID_ROOT}"
if [[ ! -d .repo ]]; then
  repo init \
    -u "${LINEAGE_REPO_URL}" \
    -b "${LINEAGE_BRANCH}" \
    --no-clone-bundle
fi

python3 /work/repo/scripts/runner/write-local-manifest.py \
  --profile "${PROFILE_PATH}" \
  --android-root "${ANDROID_ROOT}"

repo sync \
  -c \
  --force-sync \
  --no-clone-bundle \
  --no-tags \
  -j"${LINEAGE_SYNC_JOBS}" \
  2>&1 | tee "${ARTIFACT_DIR}/logs/repo-sync.log"

repo forall -c '
  if git lfs ls-files | grep -q .; then
    echo "git lfs pull: ${REPO_PROJECT}"
    git lfs pull
  fi
' 2>&1 | tee "${ARTIFACT_DIR}/logs/git-lfs-pull.log"
