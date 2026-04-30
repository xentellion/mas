#!/bin/bash

export LLM=http://localhost:8002
export LLM_SELECTED=deepseek-r1
export LOG_PROMPTS=1
export TPS=15
export RMQ=http://localhost:5672
export ACTIVE_LLMS=1

docker compose up -d

cd agent_app
exec ./venv-agent/bin/python main.py "$@"