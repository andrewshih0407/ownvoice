// Smooth-scroll to a section by id, using the shared Lenis instance when
// available (falls back to native smooth scroll under reduced motion).
export function scrollToId(id: string) {
  const lenis = (window as any).__lenis;
  const target = document.getElementById(id);
  if (!target) return;
  if (lenis && typeof lenis.scrollTo === "function") {
    lenis.scrollTo(target, { offset: -10 });
  } else {
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}
