#!/usr/bin/env bash
set -euo pipefail

name=${1:-smoke}
printf 'hello, %s\n' "$name"
