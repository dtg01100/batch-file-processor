#!/usr/bin/env bash
# Build Windows executable using PyInstaller in Docker container
# NOTE: When Docker uses the host socket (devcontainer scenario), paths must be 
# relative to the host filesystem, not the container's /workspaces path

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect if we're in a devcontainer with host Docker socket
is_devcontainer() {
	[[ -n "$DEVCONTAINER" ]] || ([[ -f /.dockerenv ]] && [[ -S /var/run/docker.sock ]])
}

# Get host path for Docker volume mount
get_host_path() {
	local container_path="$1"
    
	# First check if HOST_PATH is explicitly provided
	if [[ -n "$HOST_PATH" ]]; then
		echo "$HOST_PATH"
		return
	fi
    
	if is_devcontainer; then
		if [[ -n "$DEVCONTAINER_WORKDIR" ]]; then
			echo "$DEVCONTAINER_WORKDIR"
		elif [[ -n "$WORKSPACE_FOLDER" ]]; then
			echo "$WORKSPACE_FOLDER"
		else
			echo "$container_path"
		fi
	else
		echo "$container_path"
	fi
}

host_path=$(get_host_path "$PROJECT_ROOT")

if [[ "$host_path" == "/workspaces/batch-file-processor" ]] && is_devcontainer; then
	echo "WARNING: Running inside a devcontainer; mounting /workspaces may be required for docker-in-docker."
	echo "Proceeding to run Docker with the workspace mounted. If the build fails, rerun with HOST_PATH set to your host path:"
	echo "  HOST_PATH=/home/user/projects/batch-file-processor ./buildwin.sh"
	# continue despite devcontainer environment to support docker-in-docker setups
fi

sudo docker run --rm --volume "$host_path:/src/" --env SPECFILE=./main_interface.spec docker.io/batonogov/pyinstaller-windows:v4.0.1
