#!/bin/bash
# install.sh - IM2 PipelineCtl installation script

set -e

echo "IM2 PipelineCtl Installation Script"
echo "==================================="
echo

# Determine script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLI_PATH="$SCRIPT_DIR/pipelinectl.py"
COMPLETION_PATH="$SCRIPT_DIR/pipelinectl_completion.sh"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is required but not installed."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install -r "$SCRIPT_DIR/requirements.txt"

# Make script executable
chmod +x "$CLI_PATH"

# Create .im2 directory if it doesn't exist
mkdir -p ~/.im2

# Ask for installation options
echo
echo "Where would you like to install pipelinectl?"
echo "1. Local bin directory (~/.local/bin)"
echo "2. System bin directory (/usr/local/bin) [requires sudo]"
echo "3. Skip installation (just install dependencies)"
read -p "Enter option (1-3): " OPTION

case $OPTION in
    1)
        mkdir -p ~/.local/bin
        INSTALL_PATH=~/.local/bin/pipelinectl
        echo "Installing to $INSTALL_PATH..."
        ln -sf "$CLI_PATH" "$INSTALL_PATH"
        
        # Add to PATH if not already there
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            echo "Adding ~/.local/bin to PATH in your .bashrc"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
            echo "Please restart your shell or run 'source ~/.bashrc' to update your PATH."
        fi
        ;;
    2)
        INSTALL_PATH=/usr/local/bin/pipelinectl
        echo "Installing to $INSTALL_PATH (requires sudo)..."
        sudo ln -sf "$CLI_PATH" "$INSTALL_PATH"
        ;;
    3)
        echo "Skipping installation."
        ;;
    *)
        echo "Invalid option. Skipping installation."
        ;;
esac

# Ask for shell completion installation
echo
echo "Would you like to set up shell completion?"
echo "1. Yes, add to ~/.bashrc"
echo "2. No"
read -p "Enter option (1-2): " COMPLETION_OPTION

if [ "$COMPLETION_OPTION" -eq 1 ]; then
    echo "Setting up shell completion..."
    echo "source $COMPLETION_PATH" >> ~/.bashrc
    echo "Shell completion added to ~/.bashrc."
    echo "Please restart your shell or run 'source ~/.bashrc' to enable completion."
fi

# Create configuration
echo
echo "Creating default configuration..."
mkdir -p ~/.im2

if [ ! -f ~/.im2/config.yaml ]; then
    cat > ~/.im2/config.yaml << EOF
# IM2 PipelineCtl Configuration

# API settings
api:
  url: http://localhost:8000
  # token: your_token_here  # Uncomment and set your API token if needed

# Default settings
defaults:
  output_format: table  # Options: table, json
EOF
    echo "Default configuration created at ~/.im2/config.yaml."
else
    echo "Configuration file already exists at ~/.im2/config.yaml."
fi

echo
echo "Installation completed successfully!"
if [ "$OPTION" -ne 3 ]; then
    echo "You can now run 'pipelinectl --help' to get started."
fi
