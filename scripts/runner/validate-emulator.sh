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
BROWSER_VALIDATION_PACKAGE="${EMULATOR_BROWSER_PACKAGE:-${BROWSER_PACKAGE}}"

mkdir -p "${ARTIFACT_DIR}/logs" "${ARTIFACT_DIR}/screenshots"
RESULT="${ARTIFACT_DIR}/EMULATOR-VALIDATION.json"
STATUS="fail"
FAILURE=""
EMULATOR_PID=""
ADB_BIN="adb"

adb_capture() {
  local output="$1"
  shift

  timeout 30s "${ADB_BIN}" -s emulator-5554 "$@" > "${output}" 2>&1 || true
}

collect_runtime_artifacts() {
  local device_state

  if [[ -z "${EMULATOR_PID}" ]] || ! kill -0 "${EMULATOR_PID}" 2>/dev/null; then
    return 0
  fi

  device_state="$("${ADB_BIN}" -s emulator-5554 get-state 2>/dev/null | tr -d '\r' || true)"
  if [[ "${device_state}" != "device" ]]; then
    return 0
  fi

  adb_capture "${ARTIFACT_DIR}/logs/getprop.txt" shell getprop
  adb_capture "${ARTIFACT_DIR}/logs/ps.txt" shell ps -A
  adb_capture "${ARTIFACT_DIR}/logs/activity-processes.txt" shell dumpsys activity processes
  adb_capture "${ARTIFACT_DIR}/logs/package-kiosk.txt" shell dumpsys package "${KIOSK_LAUNCHER_PACKAGE}"
  adb_capture "${ARTIFACT_DIR}/logs/package-ha.txt" shell dumpsys package "${HA_PACKAGE}"
  adb_capture "${ARTIFACT_DIR}/logs/package-browser.txt" shell dumpsys package "${BROWSER_VALIDATION_PACKAGE}"
  for package in ${KIOSK_EXTRA_APP_PACKAGES:-}; do
    safe_name="${package//[^A-Za-z0-9_.-]/_}"
    adb_capture "${ARTIFACT_DIR}/logs/package-${safe_name}.txt" shell dumpsys package "${package}"
  done
  adb_capture "${ARTIFACT_DIR}/logs/logcat.txt" logcat -d
}

finish() {
  local exit_code=$?
  if [[ "${exit_code}" -ne 0 && -z "${FAILURE}" ]]; then
    FAILURE="validator exited before completing all checks"
  fi
  collect_runtime_artifacts
  if [[ -n "${EMULATOR_PID}" ]] && kill -0 "${EMULATOR_PID}" 2>/dev/null; then
    "${ADB_BIN}" -s emulator-5554 emu kill >/dev/null 2>&1 || kill "${EMULATOR_PID}" >/dev/null 2>&1 || true
  fi
  python3 - "${RESULT}" "${STATUS}" "${FAILURE}" <<'PY'
import json
import sys
from datetime import datetime, timezone

path, status, failure = sys.argv[1:4]
payload = {
    "schema": "rosie-local-ha.emulator-validation/v1",
    "status": status,
    "failure": failure or None,
    "finished_at": datetime.now(timezone.utc).isoformat(),
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
  exit "${exit_code}"
}
trap finish EXIT

fail() {
  FAILURE="$1"
  echo "validation failed: ${FAILURE}" >&2
  exit 1
}

assert_window_focuses_package() {
  local dump_file="$1"
  local package="$2"
  local message="$3"

  if ! awk -v package="${package}" '
    /mCurrentFocus=/ || /mFocusedApp=/ || /mFocusedWindow=/ {
      if (index($0, package) > 0) {
        found = 1
      }
    }
    END { exit found ? 0 : 1 }
  ' "${dump_file}"; then
    fail "${message}"
  fi
}

cd "${ANDROID_ROOT}"
# shellcheck disable=SC1091
set +u
source build/envsetup.sh
lunch "${EMULATOR_LUNCH}"
EMULATOR_BIN="$(command -v emulator)"
ADB_BIN="$(command -v adb)"
if [[ "${USE_SDK_EMULATOR:-0}" == "1" && -x "${ANDROID_SDK_ROOT:-}/platform-tools/adb" ]]; then
  ADB_BIN="${ANDROID_SDK_ROOT}/platform-tools/adb"
fi
if [[ "${USE_SDK_EMULATOR:-0}" == "1" && -x "${ANDROID_SDK_ROOT:-}/emulator/emulator" ]]; then
  EMULATOR_BIN="${ANDROID_SDK_ROOT}/emulator/emulator"
fi
export PATH="$(dirname "${ADB_BIN}"):$(dirname "${EMULATOR_BIN}"):${PATH}"

EMULATOR_OUT="${ANDROID_ROOT}/out/target/product/${EMULATOR_OUTPUT_PRODUCT}"
for pstore_dir in \
  "${EMULATOR_OUT}/data/misc/pstore" \
  "${EMULATOR_OUT}/build.avd/data/misc/pstore"; do
  mkdir -p "${pstore_dir}"
  truncate -s 65536 "${pstore_dir}/pstore.bin"
done
rm -f \
  "${EMULATOR_OUT}"/*.qcow2 \
  "${EMULATOR_OUT}"/*.lock \
  "${EMULATOR_OUT}/build.avd/"*.qcow2 \
  "${EMULATOR_OUT}/build.avd/"*.lock

"${ADB_BIN}" kill-server >/dev/null 2>&1 || true
"${ADB_BIN}" start-server

emulator_kernel_args=()
if [[ "${USE_SDK_EMULATOR:-0}" != "1" && -f "${EMULATOR_OUT}/kernel" ]]; then
  emulator_kernel_args=(-engine classic -kernel "${EMULATOR_OUT}/kernel")
fi
"${EMULATOR_BIN}" \
  "${emulator_kernel_args[@]}" \
  -verbose \
  -no-window \
  -no-audio \
  -no-boot-anim \
  -no-snapshot \
  -wipe-data \
  -selinux permissive \
  -show-kernel \
  -accel on \
  -gpu swiftshader_indirect \
  -port 5554 \
  >"${ARTIFACT_DIR}/logs/emulator.log" 2>&1 &
EMULATOR_PID=$!

deadline=$((SECONDS + BOOT_TIMEOUT_SECONDS))
device_state=""
while [[ "${SECONDS}" -lt "${deadline}" ]]; do
  if ! kill -0 "${EMULATOR_PID}" 2>/dev/null; then
    fail "emulator exited before adb became available"
  fi
  device_state="$("${ADB_BIN}" -s emulator-5554 get-state 2>/dev/null | tr -d '\r' || true)"
  if [[ "${device_state}" == "device" ]]; then
    break
  fi
  sleep 5
done

[[ "${device_state}" == "device" ]] \
  || fail "emulator did not become available through adb within ${BOOT_TIMEOUT_SECONDS}s"

while [[ "${SECONDS}" -lt "${deadline}" ]]; do
  boot_completed="$("${ADB_BIN}" -s emulator-5554 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
  if [[ "${boot_completed}" == "1" ]]; then
    break
  fi
  sleep 5
done

[[ "$("${ADB_BIN}" -s emulator-5554 shell getprop sys.boot_completed | tr -d '\r')" == "1" ]] \
  || fail "emulator did not finish booting within ${BOOT_TIMEOUT_SECONDS}s"

"${ADB_BIN}" -s emulator-5554 shell pm list packages | tr -d '\r' | sort \
  > "${ARTIFACT_DIR}/logs/packages.txt"

grep -Fx "package:${HA_PACKAGE}" "${ARTIFACT_DIR}/logs/packages.txt" \
  || fail "Home Assistant package is not installed: ${HA_PACKAGE}"
grep -Fx "package:${BROWSER_VALIDATION_PACKAGE}" "${ARTIFACT_DIR}/logs/packages.txt" \
  || fail "browser package is not installed: ${BROWSER_VALIDATION_PACKAGE}"
grep -Fx "package:${KIOSK_LAUNCHER_PACKAGE}" "${ARTIFACT_DIR}/logs/packages.txt" \
  || fail "kiosk launcher package is not installed: ${KIOSK_LAUNCHER_PACKAGE}"
for package in ${KIOSK_EXTRA_APP_PACKAGES:-}; do
  grep -Fx "package:${package}" "${ARTIFACT_DIR}/logs/packages.txt" \
    || fail "pinned app package is not installed: ${package}"
done

for package in ${NO_GMS_PACKAGES}; do
  if grep -Fx "package:${package}" "${ARTIFACT_DIR}/logs/packages.txt"; then
    fail "forbidden Google package is installed: ${package}"
  fi
done

for package in ${KIOSK_REMOVE_PACKAGES}; do
  if grep -Fx "package:${package}" "${ARTIFACT_DIR}/logs/packages.txt"; then
    fail "removed package is still installed: ${package}"
  fi
done

device_provisioned="$("${ADB_BIN}" -s emulator-5554 shell settings get global device_provisioned | tr -d '\r')"
user_setup_complete="$("${ADB_BIN}" -s emulator-5554 shell settings get secure user_setup_complete | tr -d '\r')"
lockscreen_disabled="$("${ADB_BIN}" -s emulator-5554 shell settings get secure lockscreen.disabled | tr -d '\r')"
immersive_confirmations="$("${ADB_BIN}" -s emulator-5554 shell settings get secure immersive_mode_confirmations | tr -d '\r')"
uimode_night="$("${ADB_BIN}" -s emulator-5554 shell cmd uimode night | tr -d '\r')"
auto_time="$("${ADB_BIN}" -s emulator-5554 shell settings get global auto_time | tr -d '\r')"
auto_time_zone="$("${ADB_BIN}" -s emulator-5554 shell settings get global auto_time_zone | tr -d '\r')"
ntp_server="$("${ADB_BIN}" -s emulator-5554 shell settings get global ntp_server | tr -d '\r')"
timezone_name="$("${ADB_BIN}" -s emulator-5554 shell getprop persist.sys.timezone | tr -d '\r')"
location_providers="$("${ADB_BIN}" -s emulator-5554 shell settings get secure location_providers_allowed | tr -d '\r')"
[[ "${device_provisioned}" == "1" ]] || fail "device_provisioned is ${device_provisioned}, expected 1"
[[ "${user_setup_complete}" == "1" ]] || fail "user_setup_complete is ${user_setup_complete}, expected 1"
[[ "${lockscreen_disabled}" == "1" ]] || fail "lockscreen.disabled is ${lockscreen_disabled}, expected 1"
[[ "${immersive_confirmations}" == "confirmed" ]] \
  || fail "immersive_mode_confirmations is ${immersive_confirmations}, expected confirmed"
[[ "${uimode_night}" == "Night mode: ${SYSTEM_UI_NIGHT_MODE}" ]] \
  || fail "uimode night is ${uimode_night}, expected Night mode: ${SYSTEM_UI_NIGHT_MODE}"
[[ "${auto_time}" == "${SYSTEM_AUTO_TIME_VALUE}" ]] \
  || fail "auto_time is ${auto_time}, expected ${SYSTEM_AUTO_TIME_VALUE}"
[[ "${auto_time_zone}" == "${SYSTEM_AUTO_TIME_ZONE_VALUE}" ]] \
  || fail "auto_time_zone is ${auto_time_zone}, expected ${SYSTEM_AUTO_TIME_ZONE_VALUE}"
[[ "${ntp_server}" == "${SYSTEM_NTP_SERVER}" || "${ntp_server}" == "null" ]] \
  || fail "ntp_server is ${ntp_server}, expected ${SYSTEM_NTP_SERVER}"
if [[ -n "${SYSTEM_TIMEZONE:-}" ]]; then
  [[ "${timezone_name}" == "${SYSTEM_TIMEZONE}" ]] \
    || fail "timezone is ${timezone_name}, expected ${SYSTEM_TIMEZONE}"
fi
IFS=',' read -r -a expected_location_providers <<< "${SYSTEM_LOCATION_PROVIDERS_ALLOWED}"
for provider in "${expected_location_providers[@]}"; do
  [[ ",${location_providers}," == *",${provider},"* ]] \
    || fail "location provider ${provider} missing from ${location_providers}"
done

python3 - "${APP_RUNTIME_PERMISSION_GRANTS_JSON}" <<'PY' > "${ARTIFACT_DIR}/logs/runtime-permission-grants.txt"
import json
import sys

for grant in json.loads(sys.argv[1]):
    for permission in grant.get("permissions", []):
        print(f"{grant['package']} {permission}")
PY
while read -r package permission; do
  [[ -n "${package}" ]] || continue
  "${ADB_BIN}" -s emulator-5554 shell dumpsys package "${package}" \
    | tr -d '\r' \
    | grep -F "${permission}: granted=true" \
    || fail "${permission} is not granted for ${package}"
done < "${ARTIFACT_DIR}/logs/runtime-permission-grants.txt"

"${ADB_BIN}" -s emulator-5554 shell \
  cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME \
  > "${ARTIFACT_DIR}/logs/home-resolve.txt" 2>&1 \
  || fail "failed to resolve HOME intent"
grep -F "${KIOSK_LAUNCHER_PACKAGE}" "${ARTIFACT_DIR}/logs/home-resolve.txt" \
  || fail "HOME intent does not resolve to kiosk launcher"

"${ADB_BIN}" -s emulator-5554 shell input keyevent KEYCODE_WAKEUP || true
"${ADB_BIN}" -s emulator-5554 shell input keyevent KEYCODE_HOME || true
sleep 6
"${ADB_BIN}" -s emulator-5554 shell cmd statusbar collapse >/dev/null 2>&1 || true
sleep 1
"${ADB_BIN}" -s emulator-5554 shell dumpsys window windows \
  > "${ARTIFACT_DIR}/logs/home-focus.txt" 2>&1 || true
assert_window_focuses_package \
  "${ARTIFACT_DIR}/logs/home-focus.txt" \
  "${KIOSK_LAUNCHER_PACKAGE}" \
  "HOME key did not focus kiosk launcher"
"${ADB_BIN}" -s emulator-5554 exec-out screencap -p > "${ARTIFACT_DIR}/screenshots/kiosk-home.png" || true

"${ADB_BIN}" -s emulator-5554 shell monkey -p "${HA_PACKAGE}" -c android.intent.category.LAUNCHER 1 \
  > "${ARTIFACT_DIR}/logs/launch-ha.log" 2>&1 \
  || fail "failed to launch Home Assistant"
sleep 8
"${ADB_BIN}" -s emulator-5554 shell pidof "${HA_PACKAGE}" >/dev/null 2>&1 \
  || fail "Home Assistant process did not stay alive after launch"

"${ADB_BIN}" -s emulator-5554 shell monkey -p "${BROWSER_VALIDATION_PACKAGE}" -c android.intent.category.LAUNCHER 1 \
  > "${ARTIFACT_DIR}/logs/launch-browser.log" 2>&1 \
  || fail "failed to launch browser"
sleep 5
"${ADB_BIN}" -s emulator-5554 shell input keyevent KEYCODE_WAKEUP || true
"${ADB_BIN}" -s emulator-5554 shell input keyevent KEYCODE_HOME || true
sleep 2
"${ADB_BIN}" -s emulator-5554 shell dumpsys window windows \
  > "${ARTIFACT_DIR}/logs/final-home-focus.txt" 2>&1 || true
assert_window_focuses_package \
  "${ARTIFACT_DIR}/logs/final-home-focus.txt" \
  "${KIOSK_LAUNCHER_PACKAGE}" \
  "final HOME key did not return to kiosk launcher"

"${ADB_BIN}" -s emulator-5554 exec-out screencap -p > "${ARTIFACT_DIR}/screenshots/final.png" || true
"${ADB_BIN}" -s emulator-5554 logcat -d > "${ARTIFACT_DIR}/logs/logcat.txt" || true

STATUS="pass"
