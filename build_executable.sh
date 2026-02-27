#!/usr/bin/env bash

set -e

docker run --rm -v "$(pwd):/src" docker.io/batonogov/pyinstaller-windows:v4.0.1
