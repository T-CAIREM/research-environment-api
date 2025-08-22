#!/bin/bash
set -e

CERT=$(kubectl get secret "research-environment-api-rstudio-certificate" -o jsonpath='{.data.tls\.crt}')
KEY=$(kubectl get secret "research-environment-api-rstudio-certificate" -o jsonpath='{.data.tls\.key}')
EXPIRATION_DATE=$(kubectl get certificate "research-environment-api-rstudio-certificate" -o jsonpath='{.status.notAfter}')

COMBINED="CERT:$CERT\nKEY:$KEY"
CHECKSUM=$(echo -n "$COMBINED" | sha256sum | awk '{print $1}')

STORED_CHECKSUM=""
if kubectl get secret "research-environment-api-cert-checksum" 2>/dev/null; then
  STORED_CHECKSUM=$(kubectl get secret "research-environment-api-cert-checksum" -o jsonpath='{.data.checksum}' | base64 --decode)
fi

if [ "$CHECKSUM" != "$STORED_CHECKSUM" ]; then

  CERT_DECODED=$(echo "$CERT" | base64 -d)
  KEY_DECODED=$(echo "$KEY" | base64 -d)

  JSON_PAYLOAD=$(jq -n \
    --arg crt "$CERT_DECODED" \
    --arg key "$KEY_DECODED" \
    --arg expiration "$EXPIRATION_DATE" \
    '{tls_crt: $crt, tls_key: $key, expiration_date: $expiration}')

  echo "$JSON_PAYLOAD" | gcloud secrets versions add "research-environment-api-rstudio-certificate" --data-file=-

  if [ -n "$STORED_CHECKSUM" ]; then
    kubectl patch secret "research-environment-api-cert-checksum" -p="{\"data\":{\"checksum\":\"$(echo -n "$CHECKSUM" | base64 -w0)\"}}"
  else
    kubectl create secret generic "research-environment-api-cert-checksum" --from-literal=checksum="$CHECKSUM"
  fi
fi