#!/usr/bin/env python3
"""
Comprehensive Django Application Page Tester
Tests all URLs from portal/urls.py and documents failures
"""

import requests
import re
from urllib.parse import urljoin
import json
from datetime import datetime

BASE_URL = "http://192.168.5.64:8000"
LOGIN_URL = f"{BASE_URL}/accounts/login/"

# Test user configurations
TEST_USERS = [
    {
        'username': 'harry',
        'password': 'chair7car',
        'description': 'RICD User (harry)',
        'user_type': 'RICD'
    },
    {
        'username': 'mark',
        'password': 'mark',
        'description': 'Council User (mark)',
        'user_type': 'Council'
    }
]

# URLs that require authentication - expanded comprehensive list
PROTECTED_URLS = [
    "/portal/ricd/",
    "/portal/council/",
    "/portal/projects/",
    "/portal/councils/",
    "/portal/works/",
    "/portal/analytics/",
    "/portal/help/ricd/",
    "/portal/help/council/",
    "/portal/maintenance/construction-methods/",
    "/portal/maintenance/site-configuration/",
    "/portal/defects/",
    "/portal/defects/create/",
    "/portal/users/",
    "/portal/officers/",
    "/portal/work-types/",
    "/portal/output-types/",
    "/portal/maintenance/monthly-tracker-items/",
    "/portal/maintenance/monthly-tracker-item-groups/",
    "/portal/maintenance/quarterly-report-items/",
    "/portal/maintenance/stage1-steps/",
    "/portal/maintenance/stage2-steps/",
    "/portal/funding-approvals/",
    "/portal/agreements/remote-capital/",
    "/portal/agreements/forward-rpf/",
    "/portal/agreements/interim-frp/",
    "/portal/reports/enhanced-monthly/",
    "/portal/reports/enhanced-quarterly/",
    "/portal/reports/enhanced-stage1/",
    "/portal/reports/enhanced-stage2/",
    "/portal/reports/monthly/",
    "/portal/reports/quarterly/",
]

# URLs that might work without auth
PUBLIC_URLS = [
    "/",
    "/accounts/login/",
]

class PageTester:
    def __init__(self, user_config):
        self.user_config = user_config
        self.session = requests.Session()
        self.results = []
        self.report_file = f"diagnostics/comprehensive_page_test_report_{user_config['user_type'].lower()}_{user_config['username']}.md"

    def login(self):
        """Login to get authenticated session"""
        try:
            # Get login page first to get CSRF token
            response = self.session.get(LOGIN_URL)
            if response.status_code != 200:
                return False, f"Login page returned {response.status_code}"

            # Extract CSRF token
            csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
            if not csrf_match:
                return False, "Could not find CSRF token"

            csrf_token = csrf_match.group(1)

            # Login
            login_data = {
                'username': self.user_config['username'],
                'password': self.user_config['password'],
                'csrfmiddlewaretoken': csrf_token,
            }

            response = self.session.post(LOGIN_URL, data=login_data,
                                        headers={'Referer': LOGIN_URL}, allow_redirects=True)

            # Check if login was successful by looking for dashboard content or redirect to portal
            if "/portal/" in response.url or "RICD Dashboard" in response.text or "Council Dashboard" in response.text:
                return True, f"Login successful - redirected to {response.url}"
            elif "Please login" in response.text or "/accounts/login/" in response.url:
                # Save error response for debugging
                with open("diagnostics/login_error_response.html", 'w') as f:
                    f.write(response.text)
                return False, f"Login failed - still on login page. Response saved to diagnostics/login_error_response.html"
            else:
                # Save error response for debugging
                with open("diagnostics/login_error_response.html", 'w') as f:
                    f.write(response.text)
                return False, f"Login failed with status {response.status_code}. Response saved to diagnostics/login_error_response.html"

        except Exception as e:
            return False, f"Login error: {str(e)}"

    def test_url(self, url_path, description=""):
        """Test a single URL"""
        full_url = urljoin(BASE_URL, url_path)

        try:
            response = self.session.get(full_url, timeout=30)

            result = {
                'url': url_path,
                'full_url': full_url,
                'status_code': response.status_code,
                'description': description,
                'timestamp': datetime.now().isoformat(),
                'success': response.status_code == 200,
                'error_details': None,
                'response_size': len(response.text)
            }

            if response.status_code != 200:
                result['error_details'] = f"HTTP {response.status_code}"
                if response.status_code == 404:
                    result['error_details'] += " - Page not found"
                elif response.status_code == 403:
                    result['error_details'] += " - Forbidden (authentication required)"
                elif response.status_code == 500:
                    result['error_details'] += " - Internal server error"

                    # Try to extract error details from response
                    if "Traceback" in response.text:
                        # Extract first few lines of traceback
                        lines = response.text.split('\n')
                        traceback_start = None
                        for i, line in enumerate(lines):
                            if "Traceback" in line:
                                traceback_start = i
                                break

                        if traceback_start is not None:
                            traceback_lines = lines[traceback_start:traceback_start+10]
                            result['error_details'] += f"\nTraceback: {' '.join(traceback_lines)}"

            self.results.append(result)
            return result

        except requests.exceptions.Timeout:
            result = {
                'url': url_path,
                'full_url': full_url,
                'status_code': None,
                'description': description,
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'error_details': "Request timeout",
                'response_size': 0
            }
            self.results.append(result)
            return result

        except Exception as e:
            result = {
                'url': url_path,
                'full_url': full_url,
                'status_code': None,
                'description': description,
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'error_details': f"Error: {str(e)}",
                'response_size': 0
            }
            self.results.append(result)
            return result

    def test_all_urls(self):
        """Test all URLs from portal/urls.py"""
        print(f"Starting comprehensive page testing at {datetime.now()}")

        # Test public URLs first
        print("Testing public URLs...")
        for url in PUBLIC_URLS:
            result = self.test_url(url, "Public page")
            print(f"  {url}: {result['status_code']} - {'✓' if result['success'] else '✗'}")

        # Try login
        print("Attempting login...")
        login_success, login_message = self.login()
        print(f"  Login: {'✓' if login_success else '✗'} - {login_message}")

        if login_success:
            # Test protected URLs
            print("Testing protected URLs...")
            for url in PROTECTED_URLS:
                result = self.test_url(url, "Protected page")
                print(f"  {url}: {result['status_code']} - {'✓' if result['success'] else '✗'}")

                if not result['success'] and result['error_details']:
                    print(f"    Error: {result['error_details'][:100]}...")

        # Generate report
        self.generate_report()

    def generate_report(self):
        """Generate comprehensive test report"""

        # Count results
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if r['success']])
        failed_tests = total_tests - successful_tests

        report = f"""# Comprehensive Django Application Testing Report

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Test Environment:** Django Development Server on {BASE_URL}
**Test Credentials:** {self.user_config['description']} ({self.user_config['username']})
**User Type:** {self.user_config['user_type']}

## Test Summary
- **Total Tests:** {total_tests}
- **Successful:** {successful_tests}
- **Failed:** {failed_tests}
- **Success Rate:** {successful_tests/total_tests*100:.1f}%

## Test Results

| URL | Status | Error Details |
|-----|--------|---------------|
"""

        for result in self.results:
            status = "✓" if result['success'] else "✗"
            error = result['error_details'] or ""
            report += f"| `{result['url']}` | {status} ({result['status_code'] or 'ERR'}) | {error} |\n"

        report += "\n## Detailed Results\n\n"

        for result in self.results:
            report += f"### {result['url']}\n"
            report += f"- **Full URL:** {result['full_url']}\n"
            report += f"- **Status:** {'SUCCESS' if result['success'] else 'FAILED'}\n"
            report += f"- **HTTP Code:** {result['status_code']}\n"
            report += f"- **Response Size:** {result['response_size']} bytes\n"
            report += f"- **Timestamp:** {result['timestamp']}\n"

            if result['error_details']:
                report += f"- **Error Details:** {result['error_details']}\n"

            report += "\n"

        # Write report
        with open(self.report_file, 'w') as f:
            f.write(report)

        print(f"\nReport generated: {self.report_file}")
        print(f"Summary: {successful_tests}/{total_tests} tests passed ({successful_tests/total_tests*100:.1f}%)")

if __name__ == "__main__":
    print(f"Starting comprehensive page testing for all users at {datetime.now()}")

    all_results = []

    for user_config in TEST_USERS:
        print(f"\n{'='*60}")
        print(f"Testing user: {user_config['description']}")
        print(f"{'='*60}")

        tester = PageTester(user_config)
        tester.test_all_urls()

        # Collect results for summary
        all_results.append({
            'user': user_config,
            'results': tester.results,
            'success_count': len([r for r in tester.results if r['success']]),
            'total_count': len(tester.results)
        })

    # Generate overall summary
    print(f"\n{'='*80}")
    print("OVERALL TESTING SUMMARY")
    print(f"{'='*80}")

    for result in all_results:
        user = result['user']
        success_count = result['success_count']
        total_count = result['total_count']
        success_rate = success_count / total_count * 100 if total_count > 0 else 0

        print(f"{user['description']}: {success_count}/{total_count} tests passed ({success_rate:.1f}%)")
        report_filename = f"diagnostics/comprehensive_page_test_report_{user['user_type'].lower()}_{user['username']}.md"
        print(f"  Report: {report_filename}")

    print(f"\nDetailed reports generated in diagnostics/ directory")
    print(f"All testing completed at {datetime.now()}")