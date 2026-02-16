/**
 * E2E: データ取込ページ
 *
 * ファイルアップロードUI、バリデーション、マスタデータカードを検証する。
 */

import { test, expect } from './fixtures';

test.describe('Import Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/import');
  });

  test('should display import page title', async ({ page }) => {
    await expect(page.getByText('データ取込')).toBeVisible();
  });

  test('should display file upload area', async ({ page }) => {
    // CSV/Excel関連のアップロード説明が表示される
    await expect(page.getByText(/CSV|アップロード|ファイル/i).first()).toBeVisible();
  });

  test('should show supported file format info', async ({ page }) => {
    // CSVフォーマット情報が表示される
    await expect(page.getByText(/CSV/i).first()).toBeVisible();
  });

  test('should have drag-and-drop zone', async ({ page }) => {
    // ドロップゾーンまたはファイル入力が存在する
    const dropZone = page.locator('[type="file"], [data-testid="drop-zone"], .border-dashed');
    await expect(dropZone.first()).toBeAttached();
  });
});
