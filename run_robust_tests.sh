#!/bin/bash
# Robust Testing System Runner
# Combines pre-deployment setup and comprehensive testing

echo "🧪 ROBUST DJANGO TESTING SYSTEM"
echo "================================"
echo ""

# Check if we're in the right directory
if [ ! -f "robust_system_test.py" ]; then
    echo "❌ Error: robust_system_test.py not found in current directory"
    echo "Please run this script from the project root directory (/home/harry/projects/ricd)"
    exit 1
fi

# Check if pre-deployment script exists and is executable
if [ ! -x "pre_deployment_setup.sh" ]; then
    echo "❌ Error: pre_deployment_setup.sh not found or not executable"
    echo "Please ensure both scripts are in the current directory"
    exit 1
fi

echo "📋 Step 1: Running Pre-deployment Setup..."
echo "------------------------------------------"
./pre_deployment_setup.sh

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Pre-deployment setup failed!"
    echo "Please check the errors above and fix them before proceeding."
    exit 1
fi

echo ""
echo "📋 Step 2: Running Comprehensive Test Suite..."
echo "-----------------------------------------------"
python robust_system_test.py

TEST_RESULT=$?

echo ""
echo "📋 Test Results Summary:"
echo "========================="

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ ALL TESTS PASSED!"
    echo "🎉 Your Django application is ready for deployment!"
    echo ""
    echo "Next steps:"
    echo "1. Review any warnings in the output above"
    echo "2. Fix any issues found during testing"
    echo "3. Run migrations if needed: cd testproj && python manage.py migrate"
    echo "4. Deploy your application"
else
    echo "❌ SOME TESTS FAILED!"
    echo "🔧 Please review the errors above and fix them before deploying."
    echo ""
    echo "Common issues to check:"
    echo "1. NameErrors in views (check imports)"
    echo "2. Missing database tables (run migrations)"
    echo "3. Template rendering errors (check context variables)"
    echo "4. URL configuration issues (check urls.py)"
    echo ""
    echo "After fixing issues, re-run this script."
fi

exit $TEST_RESULT