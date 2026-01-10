#!/bin/bash/
konsole --noclose --new-tab -e docker compose up chromadb &
konsole --noclose --new-tab -e docker compose up ollama &
konsole --noclose --new-tab -e docker compose up deepseek &
konsole --noclose --new-tab -e docker compose up gigachat &
