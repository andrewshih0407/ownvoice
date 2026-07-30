import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useSmoothScroll } from "../lib/useSmoothScroll";
import { CustomCursor } from "./CustomCursor";
import { ToneMascot } from "./ToneMascot";
import { SoundToggle } from "./SoundToggle";
import { FloatingNav } from "./FloatingNav";
import { Footer } from "../sections/Sections";

// Shared chrome for every route: cursor, mascot, sound, nav, footer, plus the
// Lenis smooth-scroll instance. Resets scroll to top and refreshes ScrollTrigger
// on each navigation so pinned sections measure the new page correctly.
export function Layout() {
  useSmoothScroll();
  const { pathname } = useLocation();

  useEffect(() => {
    const L = (window as any).__lenis;
    if (L && L.scrollTo) L.scrollTo(0, { immediate: true });
    else window.scrollTo(0, 0);
    const t = window.setTimeout(() => ScrollTrigger.refresh(), 200);
    return () => window.clearTimeout(t);
  }, [pathname]);

  return (
    <>
      <CustomCursor />
      <ToneMascot />
      <SoundToggle />
      <FloatingNav />
      <main key={pathname}>
        <Outlet />
      </main>
      <Footer />
    </>
  );
}
