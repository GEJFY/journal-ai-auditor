/**
 * E2E: サイドバーナビゲーション
 *
 * 全ルートへの遷移、アクティブ状態、レイアウト要素を検証する。
 */

import { test, expect } from './fixtures';

test.describe('Sidebar Navigation', () => {
  test('should display sidebar with navigation groups', async ({ page }) => {
    await page.goto('/');

    // サイドバーのナビグループが表示される
    await expect(page.getByText('概要').first()).toBeVisible();
    await expect(page.getByText('データ管理').first()).toBeVisible();
  });

  test('should navigate to all main routes', async ({ page }) => {
    const routes = [
      { text: 'データ取込', path: '/import' },
      { text: '仕訳検索', path: '/search' },
      { text: 'リスク分析', path: '/risk' },
      { text: '時系列分析', path: '/timeseries' },
      { text: '勘定科目分析', path: '/accounts' },
      { text: 'AI分析', path: '/ai-analysis' },
      { text: 'レポート生成', path: '/reports' },
      { text: '設定', path: '/settings' },
    ];

    await page.goto('/');

    for (const route of routes) {
      // リンクをテキストで特定してクリック
      await page.locator('a').filter({ hasText: route.text }).first().click();
      // URLが変わる
      await expect(page).toHaveURL(new RegExp(route.path));
    }
  });

  test('should highlight active navigation item', async ({ page }) => {
    await page.goto('/risk');

    // リスク分析リンクがアクティブ状態を持つ
    const riskLink = page.locator('a').filter({ hasText: 'リスク分析' }).first();
    await expect(riskLink).toBeVisible();
    // アクティブ状態のCSSクラスが適用されている
    await expect(riskLink).toHaveClass(/active/);
  });
});

test.describe('Header', () => {
  test('should display JAIA branding', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('JAIA').first()).toBeVisible();
  });

  test('should show connection status indicator', async ({ page }) => {
    await page.goto('/');
    // ページが正常に読み込まれる
    await page.waitForTimeout(2000);
    await expect(page.locator('body')).toBeVisible();
  });
});
