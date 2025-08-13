#!/bin/bash
# Configure environment variables for deployment.
# Creates a .env file with required keys and sets secure permissions.

set -e
ENV_FILE=${1:-.env}

read -p "Stripe Secret Key: " STRIPE_SECRET_KEY
read -p "Stripe Webhook Secret: " STRIPE_WEBHOOK_SECRET

cat > "$ENV_FILE" <<EOT
STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET=$STRIPE_WEBHOOK_SECRET
EOT

chmod 600 "$ENV_FILE"
echo "Environment configuration written to $ENV_FILE"
