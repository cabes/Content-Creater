#!/bin/bash
# Initial setup script for Content Creater
set -e

echo "=== Content Creater Setup ==="

# Create necessary directories
echo "Creating directories..."
mkdir -p config/{prompts,compliance,accounts,workflows,templates,knowledge,pronunciation,audio/{bgm,sfx},stories}
mkdir -p media/{images,audio,video,cache}
mkdir -p logs

# Check Python version
echo "Checking Python version..."
python3 --version

# Install dependencies
if command -v poetry &> /dev/null; then
    echo "Installing dependencies with Poetry..."
    poetry install
else
    echo "Poetry not found. Install with: pip install poetry"
    echo "Then run: poetry install"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Set your API key: export LLM_API_KEY='your-key'"
echo "  2. Run a test pipeline: python scripts/run_pipeline.py --workflow hook --domain finance"
echo "  3. Start with Docker: docker compose up"
echo ""
