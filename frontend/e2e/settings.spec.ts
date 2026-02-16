/**
 * E2E: 設定ページ
 *
 * 設定フォーム、テーマ切替、ルール管理UIを検証する。
 */

import { test, expect } from './fixtures';

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
  });

  test('should display settings page title', async ({ page }) => {
    await expect(page.getByText('設定')).toBeVisible();
  });

  test('should show LLM provider settings', async ({ page }) => {
    // LLMプロバイダー設定セクションが表示
    await expect(page.getByText(/LLM|プロバイダ|AI設定/i).first()).toBeVisible();
  });

  test('should show theme selector', async ({ page }) => {
    // テーマ選択が存在する
    await expect(page.getByText(/テーマ|ダーク|ライト|システム/i).first()).toBeVisible();
  });

  test('should have save button', async ({ page }) => {
    const saveBtn = page.getByRole('button', { name: /保存|Save/i });
    await expect(saveBtn).toBeVisible();
  });

  test('should show rules section', async ({ page }) => {
    // ルール管理セクションが表示される
    await expect(page.getByText(/ルール|監査ルール|Rules/i).first()).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Theme Toggle', () => {
  test('should toggle dark mode', async ({ page }) => {
    await page.goto('/settings');

    // ダークモードボタンをクリック
    const darkBtn = page.getByText(/ダーク/i).first();
    if (await darkBtn.isVisible()) {
      await darkBtn.click();
      // html要素にdarkクラスが追加される（1秒のポーリングで反映）
      await page.waitForTimeout(1500);
      const htmlClass = await page.locator('html').getAttribute('class');
      expect(htmlClass).toContain('dark');
    }
  });
});
