#!/bin/bash

VERSION="3.14"
VERSION_SHORT=$(echo $VERSION | tr -d '.')

VENV_DIR="venv-agent"
VENV_PIP="$VENV_DIR/bin/pip"
REMOTE=0

ENTRY_PORT=8002
RMQ_PORT=5672

usage() {
    echo "Usage: $0 [-r remote]"
    echo "  --r <url:port> Entrypoint for remote backend"
    exit 1
}

while getopts "r:" opt; do
    case "$opt" in
        r) REMOTE=$OPTARG ;;
        h) usage ;;
    esac
done

echo ======================Initializing======================

# If no url passed run in docker
if [ $REMOTE == 0 ]; then
    REMOTE=127.0.0.1
    echo "Starting up docker locally"
    docker compose up -d
else
    echo "Connecting to remote server $REMOTE"
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$REMOTE:$ENTRY_PORT")
    
    if [ "$STATUS" -eq 200 ]; then
        echo "Connection Successful"
    else
        echo "Connection error: $STATUS"
        exit 1
    fi
fi

export LLM="http://$REMOTE:$ENTRY_PORT"
export RMQ="http://$REMOTE:$RMQ_PORT"
export LLM_SELECTED=deepseek-r1
export LOG_PROMPTS=1
export TPS=15
export ACTIVE_LLMS=1

# Check python version
echo "Checking python version"
if ! command -v "python$VERSION" &> /dev/null ; then
    echo "Required python version not found. Installing"
    if command -v apt &> /dev/null; then
        sudo apt update
        sudo apt install -y software-properties-common
        sudo add-apt-repository -y ppa:deadsnakes/ppa
        sudo apt update
        sudo apt install -y "python$VERSION" "python$VERSION-venv"
    elif command -v pacman &> /dev/null; then
        sudo pacman -Syu --noconfirm
        sudo pacman -S --noconfirm "python$VERSION_SHORT" || {
            echo "Python$VERSION_SHORT npt found in official repo."
            yay -S "python$VERSION_SHORT"
        }
    else
        echo "Unknown package manager. Aborting."
        exit 1
    fi
else
    echo "Python found"
fi

# Check venv
cd agent_app
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment"
    "python$PYTHON_VER" -m venv "$VENV_DIR"
    if [ $? -eq 0 ]; then
        echo "$VENV_DIR. was successfully created"
    else
        echo "Error while creating venv"
        exit 1
    fi
else
    echo "Venv folder found. Using it"
fi

# Dependencies
echo "Installing dependencies"
$VENV_PIP install --upgrade pip
$VENV_PIP install -r "requirements.txt" -q
echo "Installed."

# Launch
exec ./venv-agent/bin/python main.py "$@"
