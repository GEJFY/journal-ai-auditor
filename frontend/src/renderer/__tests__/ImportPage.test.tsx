/**
 * ImportPage Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ImportPage from '../pages/ImportPage';

describe('ImportPage', () => {
  it('renders step indicator', () => {
    render(<ImportPage />);
    expect(screen.getByText('マスタデータ')).toBeTruthy();
    expect(screen.getByText('仕訳データ')).toBeTruthy();
  });

  it('renders master data section with 4 data types', () => {
    render(<ImportPage />);
    expect(screen.getByText('Step 1: マスタデータの取込')).toBeTruthy();
    expect(screen.getByText('勘定科目表')).toBeTruthy();
    expect(screen.getByText('部門マスタ')).toBeTruthy();
    expect(screen.getByText('取引先マスタ')).toBeTruthy();
    expect(screen.getByText('ユーザーマスタ')).toBeTruthy();
  });

  it('renders sample file references', () => {
    render(<ImportPage />);
    expect(screen.getByText(/01_chart_of_accounts\.csv/)).toBeTruthy();
    expect(screen.getByText(/02_department_master\.csv/)).toBeTruthy();
    expect(screen.getByText(/03_vendor_master\.csv/)).toBeTruthy();
    expect(screen.getByText(/04_user_master\.csv/)).toBeTruthy();
  });

  it('renders journal entry section', () => {
    render(<ImportPage />);
    expect(screen.getByText('Step 2: 仕訳データ (Journal Entries) の取込')).toBeTruthy();
    expect(screen.getByText('仕訳データファイルをドラッグ＆ドロップ')).toBeTruthy();
  });

  it('has file input for journal entries', () => {
    render(<ImportPage />);
    const input = document.getElementById('je-file-input') as HTMLInputElement;
    expect(input).toBeTruthy();
    expect(input.accept).toBe('.csv,.xlsx,.xls');
  });

  it('shows error for unsupported file type on journal entry upload', async () => {
    render(<ImportPage />);
    const input = document.getElementById('je-file-input') as HTMLInputElement;

    const file = new File(['data'], 'test.txt', { type: 'text/plain' });
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByText(/対応していないファイル形式/)).toBeTruthy();
  });

  it('renders 4 master upload buttons', () => {
    render(<ImportPage />);
    const buttons = screen.getAllByText('ファイルを選択');
    expect(buttons.length).toBe(4);
  });
});
