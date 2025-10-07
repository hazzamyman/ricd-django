const { test, expect } = require('@playwright/test');

test('Harry navbar - check for duplicates', async ({ page }) => {
  await page.goto('http://192.168.5.64:8000/');
  await page.fill('input[name="username"]', 'harry');
  await page.fill('input[name="password"]', 'chair7car');
  await page.click('button[type="submit"]');
  await page.waitForLoadState('networkidle');
  await page.goto('http://192.168.5.64:8000/portal/ricd/');
  await page.waitForLoadState('networkidle');
  
  // Screenshot navbar area
  await page.screenshot({ path: 'ricd/testproj/screenshots/harry_navbar.png', clip: { x: 0, y: 0, width: 1200, height: 300 } });
  
  // Count main nav items
  const mainNavItems = await page.locator('.navbar-nav.me-auto li.nav-item').count();
  console.log('Harry - Number of main nav items:', mainNavItems);
  
  // Check for duplicate dashboard links
  const ricdDashboardLinks = await page.locator('a[href="/portal/ricd/"]').count();
  console.log('Harry - RICD Dashboard links:', ricdDashboardLinks);
  
  const councilDashboardLinks = await page.locator('a[href="/portal/council/"]').count();
  console.log('Harry - Council Dashboard links:', councilDashboardLinks);
  
  // Check for duplicate Reports dropdowns
  const reportsDropdowns = await page.locator('#reportsDropdown').count();
  console.log('Harry - Reports dropdowns:', reportsDropdowns);
  
  // Check for Management dropdown (should be 1 if RICD)
  const managementDropdowns = await page.locator('#managementDropdown').count();
  console.log('Harry - Management dropdowns:', managementDropdowns);
  
  // Check for Analytics
  const analyticsLinks = await page.locator('a[href="/portal/analytics/"]').count();
  console.log('Harry - Analytics links:', analyticsLinks);
  
  // Check for Council Details
  const councilDetailsLinks = await page.locator('a[href*="/portal/council_detail/"]').count();
  console.log('Harry - Council Details links:', councilDetailsLinks);
  
  expect(ricdDashboardLinks).toBe(1);
  expect(councilDashboardLinks).toBe(0); // Should not see Council Dashboard if prioritized RICD
  expect(reportsDropdowns).toBe(1);
  expect(managementDropdowns).toBe(1);
  expect(analyticsLinks).toBe(1);
  expect(councilDetailsLinks).toBe(0); // Should not see if prioritized RICD
});