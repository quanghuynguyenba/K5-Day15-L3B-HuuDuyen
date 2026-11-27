import { useCallback, useEffect, useRef, useState } from "react";

const BOTTOM_THRESHOLD = 90;

export default function useChatScroll({
  messages,
  loading,
  plan,
  error,
  preview,
  selection,
}) {
  const listRef = useRef(null);
  const contentRef = useRef(null);
  const follow = useRef(!preview);
  const previousCount = useRef(messages.length);
  const [awayFromBottom, setAwayFromBottom] = useState(false);
  const [hasNewReply, setHasNewReply] = useState(false);
  useEffect(() => {
    if (selection?.source === "map") follow.current = false;
  }, [selection]);

  const scrollToLatest = useCallback(() => {
    const el = listRef.current;
    if (!el) return;
    // Instant scrolling avoids intermediate smooth-scroll events disabling follow.
    el.scrollTo({ top: el.scrollHeight, behavior: "instant" });
    follow.current = true;
    setAwayFromBottom(false);
    setHasNewReply(false);
  }, []);

  const trackScroll = useCallback(() => {
    const el = listRef.current;
    if (!el) return;
    const nearBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight < BOTTOM_THRESHOLD;
    follow.current = nearBottom;
    setAwayFromBottom(!nearBottom);
    if (nearBottom) setHasNewReply(false);
  }, []);

  useEffect(() => {
    const added = messages.length > previousCount.current;
    previousCount.current = messages.length;
    if (follow.current && !preview) scrollToLatest();
    else if (added) setHasNewReply(true);
  }, [messages, loading, plan, error, preview, scrollToLatest]);

  useEffect(() => {
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => {
      if (follow.current && !preview) scrollToLatest();
    });
    if (listRef.current) observer.observe(listRef.current);
    if (contentRef.current) observer.observe(contentRef.current);
    return () => observer.disconnect();
  }, [preview, scrollToLatest]);

  return {
    listRef,
    contentRef,
    trackScroll,
    scrollToLatest,
    awayFromBottom,
    hasNewReply,
  };
}
