#!/bin/sh
KEYWORD='/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/p'
DATA=$(echo "Q" | openssl s_client -connect ngw.devices.sberbank.ru:9443 -showcerts | sed -n "$KEYWORD")
echo "$DATA" > ca-gigachat.pem