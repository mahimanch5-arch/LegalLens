import { describe, expect, it } from 'vitest';
import { parseSseChunk } from './sse';

describe('parseSseChunk', () => {
  it('parses complete frames and keeps the partial remainder', () => {
    const buf = 'event: token\ndata: {"text":"Hel"}\n\nevent: token\ndata: {"text":"lo"}\n\nevent: tok';
    const { events, rest } = parseSseChunk(buf);
    expect(events).toEqual([
      { event: 'token', data: { text: 'Hel' } },
      { event: 'token', data: { text: 'lo' } },
    ]);
    expect(rest).toBe('event: tok');
  });

  it('ignores comments and malformed frames', () => {
    const { events } = parseSseChunk(': keep-alive\n\nevent: token\ndata: {bad json\n\nevent: done\ndata: {}\n\n');
    expect(events).toEqual([{ event: 'done', data: {} }]);
  });

  it('handles CRLF line endings', () => {
    const { events } = parseSseChunk('event: stage\r\ndata: {"label":"x"}\r\n\r\n');
    expect(events).toEqual([{ event: 'stage', data: { label: 'x' } }]);
  });
});
