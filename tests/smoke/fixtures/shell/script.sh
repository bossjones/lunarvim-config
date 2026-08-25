#!/usr/bin/env bash
set -euo pipefail

name=${1:-smoke}
if [[ "$name" == "smoke" ]];then
printf 'hello, %s\n' "$name"
fi
