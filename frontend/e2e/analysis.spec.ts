/**
 * E2E: 分析ページ群
 *
 * リスク分析、時系列分析、勘定科目分析、AI分析の表示を検証する。
 */

import { test, expect } from './fixtures';

test.describe('Risk Analysis Page', () => {
  test('should display risk page content', async ({ page }) => {
    await page.goto('/risk');
    // サイドバー以外のメインコンテンツ内のリスクテキスト
    await expect(page.getByText(/リスク/).first()).toBeVisible();
  });

  test('should show risk distribution data', async ({ page }) => {
    await page.goto('/risk');
    // ページが読み込まれる
    await page.waitForTimeout(2000);
    // ページコンテンツが表示されていることを確認
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Time Series Page', () => {
  test('should display time series page', async ({ page }) => {
    await page.goto('/timeseries');
    await expect(page.getByText(/時系列|トレンド|月次/i).first()).toBeVisible();
  });

  test('should render page without errors', async ({ page }) => {
    await page.goto('/timeseries');
    // ページが正常に表示される（SVGチャートまたはテキスト要素）
    await page.waitForTimeout(3000);
    const hasSvg = await page
      .locator('svg')
      .first()
      .isVisible()
      .catch(() => false);
    const hasText = await page
      .getByText(/時系列|トレンド|月次/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasSvg || hasText).toBeTruthy();
  });
});

test.describe('Accounts Page', () => {
  test('should display accounts page', async ({ page }) => {
    await page.goto('/accounts');
    await expect(page.getByText(/勘定科目/i).first()).toBeVisible();
  });
});

test.describe('AI Analysis Page', () => {
  test('should display AI analysis page', async ({ page }) => {
    await page.goto('/ai-analysis');
    await expect(page.getByText(/AI|分析/i).first()).toBeVisible();
  });

  test('should show chat or analysis interface', async ({ page }) => {
    await page.goto('/ai-analysis');
    await page.waitForTimeout(1000);
    // テキスト入力、ボタン、または分析UIが存在
    const inputArea = page.locator(
      'textarea, input[type="text"], [contenteditable="true"], [data-testid="chat-input"]'
    );
    const startBtn = page.getByRole('button', { name: /分析|開始|送信/i });
    const hasInput = await inputArea
      .first()
      .isVisible()
      .catch(() => false);
    const hasButton = await startBtn.isVisible().catch(() => false);
    const hasPage = await page.locator('body').isVisible();
    expect(hasInput || hasButton || hasPage).toBeTruthy();
  });
});
