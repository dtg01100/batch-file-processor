#! /usr/bin/env bash

podman run --rm --volume "$(pwd):/src/":z docker.io/batonogov/pyinstaller-windows:v4.0.1
