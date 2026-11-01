import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StatusBadge } from './StatusBadge';

describe('StatusBadge', () => {
  it('renders the human-readable analysis status', () => {
    render(<StatusBadge status="PARTIAL_SUCCESS" />);
    expect(screen.getByText('Partial')).toBeInTheDocument();
  });
});
