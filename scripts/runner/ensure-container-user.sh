#!/usr/bin/env bash
set -euo pipefail

finish() {
  return "$1" 2>/dev/null || exit "$1"
}

if id -un >/dev/null 2>&1; then
  finish 0
fi

nss_wrapper="$(ldconfig -p 2>/dev/null | awk '/libnss_wrapper\.so/{print $NF; exit}')"
if [[ -z "${nss_wrapper}" || ! -f "${nss_wrapper}" ]]; then
  echo "unable to resolve current uid and libnss-wrapper is unavailable" >&2
  finish 1
fi

uid="$(id -u)"
gid="$(id -g)"
home="${HOME:-/tmp/rosie-home}"
mkdir -p "${home}"

passwd_file="${home}/passwd"
group_file="${home}/group"
printf 'rosiebuilder:x:%s:%s:Rosie Build:%s:/bin/bash\n' "${uid}" "${gid}" "${home}" > "${passwd_file}"
printf 'rosiebuilder:x:%s:\n' "${gid}" > "${group_file}"

export NSS_WRAPPER_PASSWD="${passwd_file}"
export NSS_WRAPPER_GROUP="${group_file}"
export LD_PRELOAD="${nss_wrapper}${LD_PRELOAD:+:${LD_PRELOAD}}"
export USER=rosiebuilder
export LOGNAME=rosiebuilder

if ! id -un >/dev/null 2>&1; then
  echo "failed to configure passwd entry for uid ${uid}" >&2
  finish 1
fi

finish 0
