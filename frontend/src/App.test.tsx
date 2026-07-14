import { render, screen } from '@testing-library/react';
import App from './App';
import { describe, it, expect } from 'vitest';

describe('Executive Briefing Console', () => {
  it('renders the main application header', () => {
    render(<App />);
    const headerElement = screen.getByText(/Executive Briefing Console/i);
    expect(headerElement).toBeInTheDocument();
  });

  it('renders the initial empty state', () => {
    render(<App />);
    const emptyStateText = screen.getByText(/Workspace is Idle/i);
    expect(emptyStateText).toBeInTheDocument();
  });
});