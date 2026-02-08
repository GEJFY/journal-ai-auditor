/**
 * App Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';

// Mock fetch for health check
beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'healthy', app: 'JAIA', version: '0.2.0' }),
    })
  );
});

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />);
    expect(document.querySelector('#root') || document.body).toBeTruthy();
  });

  it('renders navigation sidebar', () => {
    render(<App />);
    expect(screen.getByText('JAIA')).toBeTruthy();
  });

  it('renders dashboard by default', () => {
    render(<App />);
    expect(screen.getByText(/ダッシュボード/)).toBeTruthy();
  });
});
