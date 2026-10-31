import { useCallback, useEffect, useRef, useState, type RefObject } from 'react';

/**
 * Keeps a scroll container pinned to the bottom while content streams in — but only while
 * the user is already near the bottom. Scrolling up to read releases the pin.
 */
export function useAutoScroll(ref: RefObject<HTMLElement>, contentKey: unknown) {
  const pinned = useRef(true);
  const [atBottom, setAtBottom] = useState(true);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const onScroll = () => {
      const near = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
      pinned.current = near;
      setAtBottom(near);
    };
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, [ref]);

  useEffect(() => {
    const el = ref.current;
    if (el && pinned.current) el.scrollTop = el.scrollHeight;
  }, [ref, contentKey]);

  const scrollToBottom = useCallback(
    (smooth = true) => {
      const el = ref.current;
      if (!el) return;
      pinned.current = true;
      el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
    },
    [ref],
  );

  return { atBottom, scrollToBottom };
}
