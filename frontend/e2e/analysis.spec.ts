/**
 * E2E: 分析ページ群
 *
 * リスク分析、時系列分析、勘定科目分析、AI分析の表示を検証する。
 */

import { test, expect } from './fixtures';

test.describe('Risk Analysis Page', () => {
  test('should display risk page content', async ({ page }) => {
    await page.goto('/risk');
    await expect(page.getByText(/リスク/)).toBeVisible();
  });

  test('should show risk distribution data', async ({ page }) => {
    await page.goto('/risk');
    // High / Medium / Low のいずれかが表示される
    await expect(page.getByText(/high|medium|low|高|中|低/i).first()).toBeVisible({
      timeout: 5000,
    });
  });
});

test.describe('Time Series Page', () => {
  test('should display time series page', async ({ page }) => {
    await page.goto('/timeseries');
    await expect(page.getByText(/時系列|トレンド|月次/i).first()).toBeVisible();
  });

  test('should render trend charts', async ({ page }) => {
    await page.goto('/timeseries');
    // チャートコンテナが表示される
    const charts = page.locator('.recharts-responsive-container');
    await expect(charts.first()).toBeVisible({ timeout: 5000 });
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
    // テキスト入力またはチャットインターフェースが存在
    const inputArea = page.locator(
      'textarea, input[type="text"], [contenteditable="true"], [data-testid="chat-input"]'
    );
    // AI分析ページにはチャットUIまたは分析開始ボタンがある
    const startBtn = page.getByRole('button', { name: /分析|開始|送信/i });
    const hasInput = await inputArea
      .first()
      .isVisible()
      .catch(() => false);
    const hasButton = await startBtn.isVisible().catch(() => false);
    expect(hasInput || hasButton).toBeTruthy();
  });
});
