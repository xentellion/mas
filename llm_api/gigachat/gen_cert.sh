#!/bin/sh
DATA=$(echo "Q" | openssl s_client -connect ngw.devices.sberbank.ru:9443 -showcerts | sed -n '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/p')
echo "$DATA" > data/gigachat/ca-gigachat.pem