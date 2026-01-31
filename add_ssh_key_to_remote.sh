#!/bin/bash
# Script to add SSH public key to remote server
# Usage: ./add_ssh_key_to_remote.sh

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load config
if [ -f .migration_config ]; then
    source .migration_config
fi

REMOTE_HOST="${REMOTE_HOST:-103.101.59.102}"
REMOTE_USER="${REMOTE_SSH_USER:-as}"
SSH_KEY="${REMOTE_SSH_KEY:-$HOME/.ssh/id_ed25519_odoo}"

if [ ! -f "${SSH_KEY}.pub" ]; then
    echo -e "${RED}✗ Public key not found: ${SSH_KEY}.pub${NC}"
    exit 1
fi

PUBLIC_KEY=$(cat "${SSH_KEY}.pub")

echo "=========================================="
echo "Add SSH Public Key to Remote Server"
echo "=========================================="
echo ""
echo "Remote: ${REMOTE_USER}@${REMOTE_HOST}"
echo "Key: ${SSH_KEY}.pub"
echo ""
echo -e "${YELLOW}You will be prompted for SSH password to add the key${NC}"
echo ""

# Add public key to remote server
ssh -o StrictHostKeyChecking=no "${REMOTE_USER}@${REMOTE_HOST}" "
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    if ! grep -q '${PUBLIC_KEY}' ~/.ssh/authorized_keys 2>/dev/null; then
        echo '${PUBLIC_KEY}' >> ~/.ssh/authorized_keys
        chmod 600 ~/.ssh/authorized_keys
        echo 'SSH key added successfully!'
    else
        echo 'SSH key already exists in authorized_keys'
    fi
"

echo ""
echo -e "${GREEN}✓ SSH public key added to remote server${NC}"
echo ""
echo "Testing connection with SSH key..."
if ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${REMOTE_USER}@${REMOTE_HOST}" "echo 'Connection successful!'" 2>/dev/null; then
    echo -e "${GREEN}✓ SSH key authentication working!${NC}"
    echo ""
    echo "You can now use passwordless SSH authentication."
else
    echo -e "${YELLOW}⚠ Connection test failed. Please verify manually.${NC}"
fi

