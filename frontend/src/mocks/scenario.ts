/**
 * Dev-only switches that force the mock API into states that are hard to reach naturally
 * (refusals, provider outages, interrupted streams). Read by the handlers, set by the
 * ScenarioSwitcher panel.
 */
export type NextReply = 'normal' | 'refusal' | 'llm_unavailable' | 'rate_limited' | 'timeout' | 'interrupted';
export type StreamSpeed = 'fast' | 'normal' | 'slow';

export interface Scenario {
  nextReply: NextReply;
  /** Keep `nextReply` after it fires instead of resetting to normal. */
  sticky: boolean;
  speed: StreamSpeed;
  nextUploadFails: boolean;
}

const KEY = 'legallens.mockscenario.v1';
const DEFAULT: Scenario = { nextReply: 'normal', sticky: false, speed: 'normal', nextUploadFails: false };

function load(): Scenario {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return { ...DEFAULT, ...(JSON.parse(raw) as Partial<Scenario>) };
  } catch {
    /* ignore */
  }
  return { ...DEFAULT };
}

let current = load();
const listeners = new Set<() => void>();

export const scenario = {
  get: () => current,
  set(patch: Partial<Scenario>) {
    current = { ...current, ...patch };
    try {
      localStorage.setItem(KEY, JSON.stringify(current));
    } catch {
      /* ignore */
    }
    listeners.forEach((l) => l());
  },
  subscribe(l: () => void) {
    listeners.add(l);
    return () => {
      listeners.delete(l);
    };
  },
  /** Returns the forced reply for this turn and clears it unless sticky. */
  consumeReply(): NextReply {
    const r = current.nextReply;
    if (r !== 'normal' && !current.sticky) scenario.set({ nextReply: 'normal' });
    return r;
  },
  consumeUploadFailure(): boolean {
    const f = current.nextUploadFails;
    if (f) scenario.set({ nextUploadFails: false });
    return f;
  },
  tokenDelayMs: () => ({ fast: 6, normal: 22, slow: 70 })[current.speed],
};
