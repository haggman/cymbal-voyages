#!/bin/sh
# Writes the served agent card with this service's public URL, then starts the A2A server.
# AGENT_URL is the Cloud Run service URL, e.g. https://orchestrator-123456789012.us-central1.run.app
set -e
if [ -n "$AGENT_URL" ]; then
  sed "s#__AGENT_URL__#${AGENT_URL%/}#g" /app/agents/orchestrator/agent.card.template.json \
    > /app/agents/orchestrator/agent.json
fi
exec adk api_server --a2a --host 0.0.0.0 --port "${PORT:-8080}" /app/agents
