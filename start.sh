#!/bin/bash
CHROMA=$(docker ps -q -f name="chromadb")
if [[ ! $CHROMA ]]; then
    kitty -e docker compose up chromadb &
fi

GIGACHAT=$(docker ps -q -f name="gigachat")
if [[ ! $GIGACHAT ]]; then
    kitty -e docker compose up gigachat &
fi
