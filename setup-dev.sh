#!/bin/bash

# setup-dev.sh - Links the repository source files to the Pi agent execution folders

echo "🔗 Setting up Symlink Driven Development for Pi Swarm Extension..."

REPO_DIR="$HOME/repos/personal/pi/pi-swarm-extension/src"
PI_EXT_DIR="$HOME/.pi/agent/extensions"
PI_SWARM_DIR="$HOME/.pi/agent/swarms"

# Ensure target directories exist
mkdir -p "$PI_EXT_DIR"
mkdir -p "$PI_SWARM_DIR"

# 1. Link the orchestrator extension
rm -f "$PI_EXT_DIR/swarm-orchestrator.ts"
ln -s "$REPO_DIR/swarm-orchestrator.ts" "$PI_EXT_DIR/swarm-orchestrator.ts"
echo "✅ Linked swarm-orchestrator.ts"

# 2. Link the brave search extension
rm -f "$PI_EXT_DIR/brave-search.ts"
ln -s "$REPO_DIR/brave-search.ts" "$PI_EXT_DIR/brave-search.ts"
echo "✅ Linked brave-search.ts"

# 3. Link the python crew runner
rm -f "$PI_SWARM_DIR/crew_runner.py"
ln -s "$REPO_DIR/crew_runner.py" "$PI_SWARM_DIR/crew_runner.py"
echo "✅ Linked crew_runner.py"

echo "🚀 Setup complete! Any changes made in the repository will instantly reflect in Pi."
