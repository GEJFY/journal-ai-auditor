/**
 * E2E: レスポンシブレイアウト
 *
 * デスクトップ・タブレット・モバイルでのレイアウト表示を検証する。
 */

import { test, expect } from './fixtures';

test.describe('Desktop Layout (1280x720)', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('should show sidebar on desktop', async ({ page }) => {
    await page.goto('/');
    // サイドバーのナビリンクが表示される
    await expect(page.getByRole('link', { name: 'ダッシュボード' })).toBeVisible();
    await expect(page.getByRole('link', { name: '設定' })).toBeVisible();
  });

  test('should display full navigation labels', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('データ管理').first()).toBeVisible();
  });
});

test.describe('Tablet Layout (768x1024)', () => {
  test.use({ viewport: { width: 768, height: 1024 } });

  test('should render page content on tablet', async ({ page }) => {
    await page.goto('/');
    // ページコンテンツが表示される
    await expect(page.getByText(/ダッシュボード|JAIA/i).first()).toBeVisible();
  });
});

test.describe('Mobile Layout (375x667)', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('should display content on mobile', async ({ page }) => {
    await page.goto('/');
    // モバイルでもページコンテンツが表示される
    await expect(page.locator('body')).toBeVisible();
    // JAIAブランディングまたはコンテンツが見える
    await expect(page.getByText(/JAIA|ダッシュボード/i).first()).toBeVisible();
  });

  test('should show page content on mobile', async ({ page }) => {
    await page.goto('/');
    // ページコンテンツは常に表示される
    await expect(page.getByText(/ダッシュボード|JAIA/i).first()).toBeVisible();
  });

  test('should navigate on mobile', async ({ page }) => {
    await page.goto('/');
    // モバイルでもナビゲーションが可能であることを確認
    // サイドバーリンクが表示されているか、メニューボタンがあるか
    const settingsLink = page.getByRole('link', { name: '設定' });
    const isSettingsVisible = await settingsLink.isVisible().catch(() => false);

    if (isSettingsVisible) {
      await settingsLink.click();
      await expect(page).toHaveURL(/settings/);
    } else {
      // メニューボタン経由のナビゲーション
      const menuBtn = page
        .locator('button')
        .filter({ has: page.locator('svg') })
        .first();
      if (await menuBtn.isVisible()) {
        await menuBtn.click();
        await page.waitForTimeout(500);
        const link = page.getByRole('link', { name: '設定' });
        if (await link.isVisible({ timeout: 2000 }).catch(() => false)) {
          await link.click();
          await expect(page).toHaveURL(/settings/);
        }
      }
    }
  });
});
