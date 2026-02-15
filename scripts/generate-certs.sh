#!/usr/bin/env bash
set -euo pipefail

# Atlas Research Infrastructure - PKI Automation Script
# Generates CA, Broker, and Client certificates for mTLS.

OUT_DIR=${1:-"./certs_out"}
DAYS=365
CA_SUBJECT="/CN=Atlas Lab CA"
BROKER_CN="atlas-core"
# Devices to generate certs for
DEVICES=("atlas-core" "atlas-lab" "atlas-field" "atlas-mobile")

mkdir -p "$OUT_DIR"
cd "$OUT_DIR"

echo "===> Generating CA"
if [[ ! -f ca.key ]]; then
    openssl genrsa -out ca.key 4096
    openssl req -x509 -new -nodes -key ca.key -sha256 -days 825 
        -subj "$CA_SUBJECT" -out ca.crt
else
    echo "CA already exists, skipping."
fi

echo "===> Generating Broker Certificate ($BROKER_CN)"
if [[ ! -f broker.key ]]; then
    openssl genrsa -out broker.key 2048
    openssl req -new -key broker.key -subj "/CN=$BROKER_CN" -out broker.csr
    
    # In a real scenario, you'd want to pass the IP via env or argument
    BROKER_IP=${ATLAS_BROKER_IP:-"127.0.0.1"}
    
    cat > broker.ext <<EOF
subjectAltName=IP:$BROKER_IP,DNS:$BROKER_CN,DNS:localhost
EOF
    openssl x509 -req -in broker.csr -CA ca.crt -CAkey ca.key -CAcreateserial 
        -out broker.crt -days "$DAYS" -sha256 -extfile broker.ext
    rm broker.csr broker.ext
else
    echo "Broker cert already exists, skipping."
fi

for name in "${DEVICES[@]}"; do
    echo "===> Generating Client Certificate: $name"
    if [[ ! -f "${name}.key" ]]; then
        openssl genrsa -out "${name}.key" 2048
        openssl req -new -key "${name}.key" -subj "/CN=${name}" -out "${name}.csr"
        openssl x509 -req -in "${name}.csr" -CA ca.crt -CAkey ca.key -CAcreateserial 
            -out "${name}.crt" -days "$DAYS" -sha256
        rm "${name}.csr"
    else
        echo "Client cert ${name} already exists, skipping."
    fi
done

echo "===> DONE! Certificates are in $OUT_DIR"
echo "Remember to distribute them to the respective devices/folders."
