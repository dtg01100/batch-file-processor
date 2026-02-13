#!/usr/bin/env bash
docker run --rm --volume "$(pwd):/src/" --env SPECFILE=./main_interface.spec docker.io/batonogov/pyinstaller-windows:v4.0.1
