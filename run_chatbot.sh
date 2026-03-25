#!/bin/bash
# Quick start script for the parking chatbot

echo "🚗 Starting SmartPark Chatbot..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating from template..."
    cp .env.example .env
    echo ""
    echo "Please edit .env and add your keys"
    echo "Then run this script again."
    exit 1
fi

# Activate virtual environment if it exists
if [ -d .venv ]; then
    source .venv/bin/activate
fi

# Run the chatbot
python -m rag_and_chatbot.src.chatbot.main
