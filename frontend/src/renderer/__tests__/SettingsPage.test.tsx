/**
 * SettingsPage Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SettingsPage from '../pages/SettingsPage';

beforeEach(() => {
  localStorage.clear();
});

describe('SettingsPage', () => {
  it('renders all setting sections', () => {
    render(<SettingsPage />);
    expect(screen.getByText('データ設定')).toBeTruthy();
    expect(screen.getByText('AI設定')).toBeTruthy();
    expect(screen.getByText('外観設定')).toBeTruthy();
  });

  it('renders fiscal year select with default April', () => {
    render(<SettingsPage />);
    const fiscalSelect = screen.getByDisplayValue('4月');
    expect(fiscalSelect).toBeTruthy();
  });

  it('renders LLM provider options', () => {
    render(<SettingsPage />);
    expect(screen.getByText('Anthropic (Claude)')).toBeTruthy();
    expect(screen.getByText('AWS Bedrock')).toBeTruthy();
    expect(screen.getByText('Google Vertex AI')).toBeTruthy();
    expect(screen.getByText('Azure OpenAI')).toBeTruthy();
  });

  it('renders theme options', () => {
    render(<SettingsPage />);
    expect(screen.getByText('システム設定に従う')).toBeTruthy();
    expect(screen.getByText('ライト')).toBeTruthy();
    expect(screen.getByText('ダーク')).toBeTruthy();
  });

  it('saves settings to localStorage on save button click', async () => {
    render(<SettingsPage />);
    const saveButton = screen.getByText('設定を保存');
    fireEvent.click(saveButton);

    expect(await screen.findByText('保存しました')).toBeTruthy();

    const stored = localStorage.getItem('jaia-settings');
    expect(stored).toBeTruthy();
  });

  it('loads saved settings from localStorage', () => {
    localStorage.setItem(
      'jaia-settings',
      JSON.stringify({
        fiscalYearStart: '01',
        llmProvider: 'bedrock',
        llmModel: '',
        apiKey: '',
        theme: 'dark',
      })
    );

    render(<SettingsPage />);
    expect(screen.getByDisplayValue('1月')).toBeTruthy();
    expect(screen.getByDisplayValue('AWS Bedrock')).toBeTruthy();
    expect(screen.getByDisplayValue('ダーク')).toBeTruthy();
  });
});
