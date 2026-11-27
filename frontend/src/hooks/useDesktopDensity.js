import { useLayoutEffect, useState } from "react";

// Keep the supplied 1900px design's proportions on narrower desktop viewports.
// Mobile/tablet retain their own responsive layout and accessible text sizing.
export function desktopDensity(width) {
  return width > 1100 ? Math.min(1, Math.max(0.8, width / 1900)) : 1;
}

export default function useDesktopDensity() {
  const [density, setDensity] = useState(() =>
    desktopDensity(window.innerWidth),
  );
  useLayoutEffect(() => {
    const resize = () => setDensity(desktopDensity(window.innerWidth));
    window.addEventListener("resize", resize);
    resize();
    return () => window.removeEventListener("resize", resize);
  }, []);
  return density;
}
