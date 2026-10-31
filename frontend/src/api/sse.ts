import { apiUrl, ApiError } from './client';
import type { StreamEvent } from './types';

/**
 * Parses a text/event-stream body into events. EventSource only supports GET,
 * and the chat turn is a POST, so we read the fetch body stream ourselves.
 */
export function parseSseChunk(buffer: string): { events: StreamEvent[]; rest: string } {
  const events: StreamEvent[] = [];
  const blocks = buffer.split(/\r?\n\r?\n/);
  const rest = blocks.pop() ?? '';
  for (const block of blocks) {
    let name = 'message';
    const dataLines: string[] = [];
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith(':')) continue; // comment / keep-alive
      if (line.startsWith('event:')) name = line.slice(6).trim();
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''));
    }
    if (dataLines.length === 0) continue;
    try {
      events.push({ event: name, data: JSON.parse(dataLines.join('\n')) } as StreamEvent);
    } catch {
      // Malformed frame: skip rather than abort the whole answer.
    }
  }
  return { events, rest };
}

export interface StreamResult {
  /** True when the server sent `done` or `error`; false means the stream was cut off. */
  terminated: boolean;
}

export async function streamPost(
  path: string,
  body: unknown,
  onEvent: (e: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<StreamResult> {
  const res = await fetch(apiUrl(path), {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    let errBody = {};
    try {
      errBody = await res.json();
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, errBody);
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  let terminated = false;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    const parsed = parseSseChunk(buffer);
    buffer = parsed.rest;
    for (const e of parsed.events) {
      if (e.event === 'done' || e.event === 'error') terminated = true;
      onEvent(e);
    }
  }
  if (buffer.trim()) {
    for (const e of parseSseChunk(buffer + '\n\n').events) {
      if (e.event === 'done' || e.event === 'error') terminated = true;
      onEvent(e);
    }
  }
  return { terminated };
}
