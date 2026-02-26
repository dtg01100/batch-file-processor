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
		# Attempt to use tar-stream mode: stream the workspace to the Docker daemon over stdin
		echo "Host path parent ($parent_dir) is read-only; using tar-stream mode to send workspace to Docker daemon."
		# Ensure dist destination exists
		mkdir -p "$PROJECT_ROOT/dist"
		# Stream workspace into the container, run pyinstaller using the in-container spec, then stream back the resulting dist/ directory
		tar -C "$PROJECT_ROOT" -c . |
		sudo docker run -i --workdir /src --env SPECFILE=/src/main_interface.spec docker.io/batonogov/pyinstaller-windows:v4.0.1 \
		sh -c $'python - <<\'PY\'\nimport sys,tarfile,os\nos.makedirs("/src", exist_ok=True)\nwith tarfile.open(fileobj=sys.stdin.buffer, mode="r|*") as tf:\n    tf.extractall("/src")\nPY\n\npyinstaller /src/main_interface.spec\n\npython - <<\'PY\'\nimport sys,tarfile,os\nwith tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as tf:\n    if os.path.exists("/src/dist"):\n        tf.add('/src/dist', arcname='dist')\nPY\n' \
		| tar -C "$PROJECT_ROOT" -x -
		exit $?
	fi
fi

sudo docker run --rm --workdir /src --volume "$host_path:/src/" --env SPECFILE=/src/main_interface.spec docker.io/batonogov/pyinstaller-windows:v4.0.1
