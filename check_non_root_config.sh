#!/bin/bash

# This script checks if all services in docker-compose.yml have USER_ID and GROUP_ID args

echo "Checking services in docker-compose.yml for non-root user configuration..."

# Define third-party services that don't need non-root config
THIRD_PARTY_SERVICES="redis postgres traefik"
VOLUME_SERVICES="pg_data redis_data"

# Get list of all service names
SERVICE_NAMES=$(grep -E "^  [a-zA-Z0-9_-]+:" docker-compose.yml | sed 's/^  \([a-zA-Z0-9_-]*\):.*/\1/')

# Count total services
TOTAL_SERVICES=$(echo "$SERVICE_NAMES" | wc -l)
echo "Total services found: $TOTAL_SERVICES"

# Counters
CONFIGURED_SERVICES=0
THIRD_PARTY_COUNT=0
VOLUME_COUNT=0
UNCONFIGURED_SERVICES=0

# Check each service
while read -r SERVICE; do
    echo -n "Checking $SERVICE: "
    
    # Check if it's a third-party service or volume
    if echo "$THIRD_PARTY_SERVICES" | grep -q -w "$SERVICE"; then
        echo "- Third-party service (skip)"
        THIRD_PARTY_COUNT=$((THIRD_PARTY_COUNT + 1))
        continue
    fi
    
    if echo "$VOLUME_SERVICES" | grep -q -w "$SERVICE"; then
        echo "- Volume service (skip)"
        VOLUME_COUNT=$((VOLUME_COUNT + 1))
        continue
    fi
    
    # Extract the service section (from service name to next service or EOF)
    SERVICE_START=$(grep -n "^  $SERVICE:" docker-compose.yml | cut -d: -f1)
    NEXT_SERVICE=$(tail -n +$((SERVICE_START+1)) docker-compose.yml | grep -n "^  [a-zA-Z0-9_-]\+:" | head -1 | cut -d: -f1)
    
    if [ -z "$NEXT_SERVICE" ]; then
        # If no next service, read until end of file
        SERVICE_DEF=$(tail -n +$SERVICE_START docker-compose.yml)
    else
        # If there's a next service, read until that line
        SERVICE_DEF=$(tail -n +$SERVICE_START docker-compose.yml | head -n $NEXT_SERVICE)
    fi
    
    if echo "$SERVICE_DEF" | grep -q "USER_ID=\${APP_USER_ID:-1000}" && echo "$SERVICE_DEF" | grep -q "GROUP_ID=\${APP_GROUP_ID:-1000}"; then
        echo "✓ Correctly configured"
        CONFIGURED_SERVICES=$((CONFIGURED_SERVICES + 1))
    else
        echo "✗ Missing USER_ID or GROUP_ID args"
        UNCONFIGURED_SERVICES=$((UNCONFIGURED_SERVICES + 1))
    fi
done <<< "$SERVICE_NAMES"

echo "-----------------------------------"
echo "Summary:"
echo "- Custom services configured correctly: $CONFIGURED_SERVICES"
echo "- Third-party services (no config needed): $THIRD_PARTY_COUNT"
echo "- Volume services (no config needed): $VOLUME_COUNT"
echo "- Custom services needing configuration: $UNCONFIGURED_SERVICES"

if [ $UNCONFIGURED_SERVICES -eq 0 ]; then
    echo "All custom services are properly configured for non-root users!"
else
    echo "Some custom services need to be updated. Please check the docker-compose.yml file."
fi
