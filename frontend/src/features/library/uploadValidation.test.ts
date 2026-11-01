import { describe, expect, it } from 'vitest';
import { validateFiles } from './uploadValidation';

const file = (name: string, size: number) => {
  const f = new File(['x'], name);
  Object.defineProperty(f, 'size', { value: size });
  return f;
};

describe('validateFiles', () => {
  it('accepts supported files under the limit', () => {
    const { accepted, rejected } = validateFiles([file('a.pdf', 1000), file('b.DOCX', 2000), file('c.txt', 10)]);
    expect(accepted).toHaveLength(3);
    expect(rejected).toHaveLength(0);
  });

  it('names the limit and the actual size for oversized files (FR-2)', () => {
    const { rejected } = validateFiles([file('big.pdf', 73 * 1024 * 1024)]);
    expect(rejected[0].reason).toBe('This file is 73.0 MB; the limit is 50 MB.');
  });

  it('rejects unsupported types without blocking the rest of the batch (FR-3)', () => {
    const { accepted, rejected } = validateFiles([file('scan.png', 100), file('ok.pdf', 100)]);
    expect(accepted.map((f) => f.name)).toEqual(['ok.pdf']);
    expect(rejected[0].reason).toMatch(/PNG files are not supported/);
  });
});
