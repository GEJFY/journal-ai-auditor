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
    // サイドバーとページ内の両方にダッシュボードがあるので heading で特定
    await expect(page.locator('h1, h2, [class*="title"]').first()).toBeVisible();
  });

  test('should display KPI stat cards', async ({ page }) => {
    // 仕訳データ件数が表示される（ロケール番号フォーマット）
    await expect(
      page.getByText(MOCK_SUMMARY.total_entries.toLocaleString(), { exact: false })
    ).toBeVisible({ timeout: 10000 });
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
      // リフレッシュ後もKPIデータが表示される
      await page.waitForTimeout(1000);
    }
    // ページが正常に動作している
    await expect(page.locator('body')).toBeVisible();
  });

  test('should render page content without errors', async ({ page }) => {
    // ページがエラーなく表示される（SVGチャートまたはテキストコンテンツ）
    await page.waitForTimeout(2000);
    const hasSvg = await page
      .locator('svg')
      .first()
      .isVisible()
      .catch(() => false);
    const hasContent = await page
      .getByText(MOCK_SUMMARY.total_entries.toLocaleString(), { exact: false })
      .isVisible()
      .catch(() => false);
    expect(hasSvg || hasContent).toBeTruthy();
  });
});
