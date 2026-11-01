/**
 * Runs recorded backend SSE bodies through the frontend's own parser (frontend/src/api/sse.ts),
 * exactly as streamPost does: chunked reads, then a final flush of the remaining buffer.
 * Usage: vite-node parse_sse.ts <input.json> <output.json>
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { parseSseChunk } from '../../../frontend/src/api/sse';

const [input, output] = process.argv.slice(2);
const bodies = JSON.parse(readFileSync(input, 'utf8')) as Record<string, string>;
const result: Record<string, { events: unknown[]; terminated: boolean }> = {};

for (const [name, body] of Object.entries(bodies)) {
  const events: { event: string; data: unknown }[] = [];
  let buffer = '';
  // Feed in awkward 7-byte chunks to exercise frame reassembly.
  for (let i = 0; i < body.length; i += 7) {
    buffer += body.slice(i, i + 7);
    const parsed = parseSseChunk(buffer);
    buffer = parsed.rest;
    events.push(...parsed.events);
  }
  if (buffer.trim()) events.push(...parseSseChunk(buffer + '\n\n').events);
  result[name] = { events, terminated: events.some((e) => e.event === 'done' || e.event === 'error') };
}
writeFileSync(output, JSON.stringify(result));
