import { describe, expect, it } from 'vitest';
import { linkCitations } from './citations';

describe('linkCitations', () => {
  it('links bare markers, including adjacent ones', () => {
    expect(linkCitations('Notice is 120 days [1][2].')).toBe('Notice is 120 days [1](#cite-1)[2](#cite-2).');
  });
  it('leaves real Markdown links alone', () => {
    expect(linkCitations('See [3](https://example.com)')).toBe('See [3](https://example.com)');
  });
  it('hides a half-streamed marker at the end', () => {
    expect(linkCitations('within 30 days [1', true)).toBe('within 30 days ');
    expect(linkCitations('within 30 days [', true)).toBe('within 30 days ');
  });
});
