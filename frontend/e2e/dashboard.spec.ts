/**
 * E2E: ダッシュボードページ
 *
 * KPIカード、チャート、リスク分布の表示を検証する。
 */

import { test, expect, MOCK_SUMMARY } from './fixtures';

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display page title', async ({ page }) => {
    await expect(page.getByText('ダッシュボード')).toBeVisible();
  });

  test('should display KPI stat cards', async ({ page }) => {
    // 仕訳データ件数が表示される
    await expect(
      page.getByText(MOCK_SUMMARY.total_entries.toLocaleString(), { exact: false })
    ).toBeVisible({ timeout: 5000 });
  });

  test('should display risk distribution section', async ({ page }) => {
    // リスク関連のテキストが表示される
    await expect(page.getByText(/リスク/i).first()).toBeVisible({ timeout: 5000 });
  });

  test('should have working refresh button', async ({ page }) => {
    const refreshBtn = page
      .locator('button')
      .filter({ has: page.locator('[data-lucide="refresh-cw"], svg') })
      .first();
    if (await refreshBtn.isVisible()) {
      await refreshBtn.click();
      // リフレッシュ後もデータが表示される
      await expect(
        page.getByText(MOCK_SUMMARY.total_entries.toLocaleString(), { exact: false })
      ).toBeVisible({ timeout: 5000 });
    }
  });

  test('should render charts without errors', async ({ page }) => {
    // Rechartsコンテナが存在する
    const chartContainers = page.locator('.recharts-responsive-container');
    // 少なくとも1つのチャートが存在
    await expect(chartContainers.first()).toBeVisible({ timeout: 5000 });
  });
});
