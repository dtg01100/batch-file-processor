#! /usr/bin/env bash

podman run --rm --volume "$(pwd):/src/":Z docker.io/batonogov/pyinstaller-windows:v4.0.1
