import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import MessageBubble from '../MessageBubble';

describe('MessageBubble', () => {
  const baseTimestamp = new Date('2024-01-01T12:00:00Z');

  it('renders user message with justify-end (right alignment)', () => {
    const { container } = render(
      <MessageBubble role="user" content="Hello" timestamp={baseTimestamp} />
    );
    const outerDiv = container.firstChild as HTMLElement;
    expect(outerDiv.className).toContain('justify-end');
  });

  it('renders assistant message with justify-start (left alignment)', () => {
    const { container } = render(
      <MessageBubble role="assistant" content="Hi there" timestamp={baseTimestamp} />
    );
    const outerDiv = container.firstChild as HTMLElement;
    expect(outerDiv.className).toContain('justify-start');
  });

  it('renders system message with justify-center', () => {
    const { container } = render(
      <MessageBubble role="system" content="System message" timestamp={baseTimestamp} />
    );
    const outerDiv = container.firstChild as HTMLElement;
    expect(outerDiv.className).toContain('justify-center');
  });

  it('displays message content text', () => {
    render(
      <MessageBubble role="user" content="Test message content" timestamp={baseTimestamp} />
    );
    expect(screen.getByText('Test message content')).toBeInTheDocument();
  });

  it('shows timestamp relative time', () => {
    const recentTimestamp = new Date(Date.now() - 30 * 1000); // 30s ago
    render(
      <MessageBubble role="assistant" content="Hi" timestamp={recentTimestamp} />
    );
    expect(screen.getByText('Just now')).toBeInTheDocument();
  });

  it('applies correct styling for user role (primary background)', () => {
    const { container } = render(
      <MessageBubble role="user" content="User msg" timestamp={baseTimestamp} />
    );
    const bubbleDiv = container.querySelector('.bg-primary-600');
    expect(bubbleDiv).toBeInTheDocument();
  });
});
