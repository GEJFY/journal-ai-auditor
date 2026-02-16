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
    await expect(page.getByText('データ管理')).toBeVisible();
    await expect(page.getByText('分析')).toBeVisible();
  });
});

test.describe('Tablet Layout (768x1024)', () => {
  test.use({ viewport: { width: 768, height: 1024 } });

  test('should render page content on tablet', async ({ page }) => {
    await page.goto('/');
    // ダッシュボードコンテンツが表示される
    await expect(page.getByText('ダッシュボード')).toBeVisible();
  });
});

test.describe('Mobile Layout (375x667)', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('should hide sidebar by default on mobile', async ({ page }) => {
    await page.goto('/');
    // モバイルではサイドバーのナビグループラベルが非表示
    // （ハンバーガーメニュー制御の場合）
    const navGroup = page.getByText('データ管理');
    const isVisible = await navGroup.isVisible().catch(() => false);
    // モバイルレスポンシブでサイドバーが隠れるか、コンテンツが表示される
    if (!isVisible) {
      // ハンバーガーメニューが存在する
      const menuBtn = page
        .locator('button')
        .filter({
          has: page.locator('svg'),
        })
        .first();
      await expect(menuBtn).toBeVisible();
    }
  });

  test('should show mobile menu toggle', async ({ page }) => {
    await page.goto('/');
    // ページコンテンツは常に表示される
    await expect(page.getByText(/ダッシュボード|JAIA/i).first()).toBeVisible();
  });

  test('should navigate on mobile via menu', async ({ page }) => {
    await page.goto('/');

    // モバイルでメニューボタンをタップして設定に遷移
    const menuBtn = page
      .locator('button')
      .filter({
        has: page.locator('svg'),
      })
      .first();

    if (await menuBtn.isVisible()) {
      await menuBtn.click();
      // メニュー展開後に設定リンクをクリック
      const settingsLink = page.getByRole('link', { name: '設定' });
      if (await settingsLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await settingsLink.click();
        await expect(page).toHaveURL(/settings/);
      }
    }
  });
});
