#!/bin/bash
# Pre-deployment setup script for Django application testing
# This script clears caches and restarts services before running tests

echo "🚀 Starting Pre-deployment Setup..."
echo "=================================="

# Change to test project directory
echo "📁 Changing to test project directory..."
cd testproj

# Activate virtual environment using dot notation (works in sh and bash)
echo "🐍 Activating virtual environment..."
. ../venv/bin/activate

if [ $? -eq 0 ]; then
    echo "✅ Virtual environment activated successfully"
else
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

# Clear Django URL caches
echo "🧹 Clearing Django URL caches..."
python manage.py shell -c "from django.urls import clear_url_caches; clear_url_caches()"

if [ $? -eq 0 ]; then
    echo "✅ Django URL caches cleared"
else
    echo "⚠️ Failed to clear Django URL caches (continuing...)"
fi

# Restart ricd service
echo "🔄 Restarting ricd service..."
sudo systemctl restart ricd

if [ $? -eq 0 ]; then
    echo "✅ ricd service restarted"
else
    echo "❌ Failed to restart ricd service"
    exit 1
fi

# Check ricd service status
echo "📊 Checking ricd service status..."
sudo systemctl status ricd --no-pager -l

# Restart nginx service
echo "🌐 Restarting nginx service..."
sudo systemctl restart nginx

if [ $? -eq 0 ]; then
    echo "✅ nginx service restarted"
else
    echo "⚠️ Failed to restart nginx service (continuing...)"
fi

# Check nginx service status
echo "📊 Checking nginx service status..."
sudo systemctl status nginx --no-pager -l

echo ""
echo "🎯 Pre-deployment setup complete!"
echo "=================================="
echo "✅ Environment is ready for testing"
echo "🔍 You can now run your test suite"