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
	# If /workspaces is read-only (common in some devcontainers), copy workspace to /tmp so Docker can mount it.
	parent_dir="$(dirname "$host_path")"
	if [[ ! -w "$parent_dir" ]]; then
		TMP_SRC="/tmp/src/batch-file-processor-$$"
		echo "Host path parent ($parent_dir) is read-only; copying workspace to $TMP_SRC to allow Docker mount."
		rm -rf "$TMP_SRC"
		mkdir -p "$TMP_SRC"
		if command -v rsync >/dev/null 2>&1; then
			rsync -a --exclude='.git' "$PROJECT_ROOT"/ "$TMP_SRC"/
		else
			cp -a "$PROJECT_ROOT"/. "$TMP_SRC"/
		fi
		host_path="$TMP_SRC"
		echo "Using $host_path as docker mount source."
		# cleanup when the script exits
		trap 'rm -rf "$TMP_SRC"' EXIT
	fi
fi

sudo docker run --rm --workdir /src --volume "$host_path:/src/" --env SPECFILE=./main_interface.spec docker.io/batonogov/pyinstaller-windows:v4.0.1
