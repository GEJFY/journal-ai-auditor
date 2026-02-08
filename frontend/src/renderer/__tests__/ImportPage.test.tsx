/**
 * ImportPage Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ImportPage from '../pages/ImportPage';

describe('ImportPage', () => {
  it('renders upload area', () => {
    render(<ImportPage />);
    expect(screen.getByText('データ取込')).toBeTruthy();
    expect(screen.getByText('ファイルをドラッグ＆ドロップ')).toBeTruthy();
  });

  it('renders supported formats section', () => {
    render(<ImportPage />);
    expect(screen.getByText('対応フォーマット')).toBeTruthy();
    expect(screen.getByText('AICPA GL_Detail')).toBeTruthy();
    expect(screen.getByText('汎用CSV/Excel')).toBeTruthy();
  });

  it('renders import history section', () => {
    render(<ImportPage />);
    expect(screen.getByText('取込履歴')).toBeTruthy();
    expect(screen.getByText('まだ取込履歴がありません')).toBeTruthy();
  });

  it('accepts CSV file input', () => {
    render(<ImportPage />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toBeTruthy();
    expect(input.accept).toBe('.csv,.xlsx,.xls');
  });

  it('shows validation status on file drop', async () => {
    render(<ImportPage />);
    const dropZone = screen.getByText('ファイルをドラッグ＆ドロップ').closest('div');
    expect(dropZone).toBeTruthy();

    const file = new File(['col1,col2\nval1,val2'], 'test.csv', { type: 'text/csv' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByText(/検証中/)).toBeTruthy();
  });

  it('rejects non-supported file types', async () => {
    render(<ImportPage />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    const file = new File(['data'], 'test.txt', { type: 'text/plain' });
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByText(/対応していないファイル形式/)).toBeTruthy();
  });
});
