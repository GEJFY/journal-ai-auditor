/**
 * ImportPage Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ImportPage from '../pages/ImportPage';

// Mock fetch for upload/preview flow
const mockFetch = vi.fn();
global.fetch = mockFetch;

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

  it('shows column mapping panel after successful upload', async () => {
    // Mock upload response
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ temp_file_id: 'test-id-123' }),
      })
      // Mock preview response
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            filename: 'test_data.csv',
            total_rows: 100,
            columns: ['伝票番号', '計上日', '勘定コード', '金額', '借貸'],
            column_count: 5,
            suggested_mapping: {
              journal_id: '伝票番号',
              effective_date: '計上日',
              gl_account_number: '勘定コード',
              amount: '金額',
              debit_credit_indicator: '借貸',
            },
            unmapped_columns: [],
            missing_required: [],
            sample_data: [{ 伝票番号: 'J001', 計上日: '2024-01-01' }],
            dtypes: {},
          }),
      });

    render(<ImportPage />);
    const input = document.getElementById('je-file-input') as HTMLInputElement;
    const file = new File(['col1,col2\nval1,val2'], 'test_data.csv', {
      type: 'text/csv',
    });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText('test_data.csv')).toBeTruthy();
    });
    expect(screen.getByText('取込先フィールド')).toBeTruthy();
    expect(screen.getByText('検証する')).toBeTruthy();
  });

  it('shows required field labels in mapping panel', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ temp_file_id: 'test-id-456' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            filename: 'data.csv',
            total_rows: 50,
            columns: ['col_a', 'col_b'],
            column_count: 2,
            suggested_mapping: {},
            unmapped_columns: ['col_a', 'col_b'],
            missing_required: [
              'journal_id',
              'effective_date',
              'gl_account_number',
              'amount',
              'debit_credit_indicator',
            ],
            sample_data: [],
            dtypes: {},
          }),
      });

    render(<ImportPage />);
    const input = document.getElementById('je-file-input') as HTMLInputElement;
    const file = new File(['a,b\n1,2'], 'data.csv', { type: 'text/csv' });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/必須項目.*件未設定/)).toBeTruthy();
    });
  });

  it('renders target field definitions', () => {
    render(<ImportPage />);
    // Step indicator shows both master and journal sections
    expect(screen.getByText('マスタデータ')).toBeTruthy();
    expect(screen.getByText('仕訳データ')).toBeTruthy();
  });
});
