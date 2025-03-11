#!/bin/bash

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p uploads
mkdir -p backend/models
mkdir -p backend/routes
mkdir -p backend/services
mkdir -p frontend/pages
mkdir -p liteLLM
mkdir -p docs

# Copy environment file template
cp .env.example .env

echo "Setup complete! Please update the .env file with your API keys and configuration."
echo "To start the application:"
echo "1. Update .env with your API keys"
echo "2. Run 'docker-compose -f docker/docker-compose.yml up --build'" 