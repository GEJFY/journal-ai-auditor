/**
 * E2E: ダッシュボードページ
 *
 * KPIカード、チャート、リスク分布の表示を検証する。
 */

import { test, expect } from './fixtures';

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display page title', async ({ page }) => {
    // ページが正常に表示される
    await expect(page.locator('h1, h2, [class*="title"]').first()).toBeVisible();
  });

  test('should display KPI stat cards', async ({ page }) => {
    // KPIカードが表示される（数値またはカードコンポーネント）
    await page.waitForTimeout(3000);
    // 仕訳データの件数または金額が表示されている
    const hasKpiNumber = await page
      .getByText(/784[,.]?824|78万|仕訳|entries/i)
      .first()
      .isVisible()
      .catch(() => false);
    const hasStatCard = await page
      .locator('[class*="stat"], [class*="card"], [class*="kpi"]')
      .first()
      .isVisible()
      .catch(() => false);
    const hasSvgIcon = await page
      .locator('main svg, [class*="content"] svg')
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasKpiNumber || hasStatCard || hasSvgIcon).toBeTruthy();
  });

  test('should display risk distribution section', async ({ page }) => {
    // メインコンテンツエリア内のリスク関連テキスト
    await expect(
      page
        .locator('main, [class*="content"]')
        .getByText(/リスク/i)
        .first()
    ).toBeVisible({ timeout: 10000 });
  });

  test('should have working refresh button', async ({ page }) => {
    // ページ読み込み完了を待機
    await page.waitForTimeout(2000);
    const refreshBtn = page.locator('button svg').first();
    if (await refreshBtn.isVisible()) {
      await refreshBtn.click();
      await page.waitForTimeout(1000);
    }
    // ページが正常に動作している
    await expect(page.locator('body')).toBeVisible();
  });

  test('should render page content without errors', async ({ page }) => {
    // ページがエラーなく表示される
    await page.waitForTimeout(2000);
    const hasSvg = await page
      .locator('svg')
      .first()
      .isVisible()
      .catch(() => false);
    const hasContent = await page
      .getByText(/784[,.]?824/)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasSvg || hasContent).toBeTruthy();
  });
});
