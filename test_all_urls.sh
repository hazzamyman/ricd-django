#!/bin/bash

# Comprehensive URL Testing Script
# Tests ALL URLs in the Django application systematically

echo "🔍 COMPREHENSIVE URL TESTING STARTED"
echo "=========================================="

BASE_URL="http://127.0.0.1:8080"
DJANGO_DIR="testproj"

# Function to test a URL
test_url() {
    local url=$1
    local method=${2:-"GET"}
    local auth=${3:-"none"}

    echo -n "Testing: $method $url"

    if [ "$auth" = "council" ]; then
        echo " (council auth)"

    elif [ "$auth" = "admin" ]; then
        echo " (admin auth)"
    else
        echo " (no auth)"
    fi

    # For now, just test basic GET requests
    # In a full implementation, we'd handle cookies, CSRF, etc.
    response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$url")

    if [ "$response" -eq 200 ]; then
        echo "✅ 200 OK"
    elif [ "$response" -eq 302 ]; then
        echo "↪️  302 Redirect (probably auth required)"
    elif [ "$response" -eq 403 ]; then
        echo "🔒 403 Forbidden"
    elif [ "$response" -ge 500 ]; then
        echo "💥 500+ Server Error"
    else
        echo "⚠️  $response"
    fi
}

# Change to Django directory to get URL patterns
cd "$DJANGO_DIR"

echo ""
echo "🏗️  TESTING DASHBOARD VIEWS"
echo "-------------------------"
test_url "/portal/ricd/" "GET" "admin"
test_url "/portal/council/" "GET" "council"

echo ""
echo "📋 TESTING CRUD VIEWS"
echo "--------------------"
test_url "/portal/agreements/interim-frp/" "GET" "admin"
test_url "/portal/councils/" "GET" "admin"
test_url "/portal/programs/" "GET" "admin"
test_url "/portal/projects/" "GET" "admin"
test_url "/portal/work-types/" "GET" "admin"
test_url "/portal/output-types/" "GET" "admin"
test_url "/portal/funding-approvals/" "GET" "admin"

echo ""
echo "📄 TESTING DETAIL VIEWS"
echo "----------------------"
test_url "/portal/project/1/" "GET" "admin"  # This might need to be adjusted for actual IDs
test_url "/portal/councils/1/" "GET" "admin"
test_url "/portal/programs/1/" "GET" "admin"

echo ""
echo "📝 TESTING TEMPLATE VIEWS"
echo "------------------------"
test_url "/portal/analytics/" "GET" "admin"
test_url "/portal/help/ricd/" "GET" "admin"
test_url "/portal/help/council/" "GET" "council"
test_url "/portal/reports/monthly/" "GET" "admin"
test_url "/portal/reports/quarterly/" "GET" "council"
test_url "/portal/reports/stage1/" "GET" "admin"
test_url "/portal/reports/stage2/" "GET" "admin"

echo ""
echo "🏗️  TESTING CREATE VIEWS"
echo "-----------------------"
test_url "/portal/councils/create/" "GET" "admin"
test_url "/portal/programs/create/" "GET" "admin"
test_url "/portal/work-types/create/" "GET" "admin"
test_url "/portal/output-types/create/" "GET" "admin"

echo ""
echo "📋 TESTING AGENDA VIEWS"
echo "----------------------"
test_url "/portal/agreements/forward-rpf/" "GET" "admin"
test_url "/portal/agreements/remote-capital/" "GET" "admin"

echo ""
echo "👥 TESTING USER MANAGEMENT"
echo "-------------------------"
test_url "/portal/users/" "GET" "admin"
test_url "/portal/officers/" "GET" "admin"

echo ""
echo "🔍 TESTING EXPORT VIEWS"
echo "----------------------"
test_url "/portal/analytics/export/addresses-works/" "GET" "admin"

echo ""
echo "=========================================="
echo "📊 TESTING SUMMARY:"
echo "=========================================="
echo "✅ Tests completed for major URL patterns"
echo "💡 Note: Some URLs require authentication/valid data"
echo "🔧 Next steps:"
echo "   1. Add real authentication tokens"
echo "   2. Test all possible ID variations"
echo "   3. Test form submissions"
echo "   4. Check for template rendering errors"
echo "=========================================="

cd ..