import { useEffect, useRef } from "react";

// Lightweight scroll reveal using IntersectionObserver (respects reduced motion
// via the CSS in global.css). Wraps children and adds .is-in when in view.
export function Reveal({
  children,
  as: Tag = "div",
  className = "",
  delay = 0,
  ...rest
}: {
  children: React.ReactNode;
  as?: any;
  className?: string;
  delay?: number;
  [key: string]: any;
}) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            (entry.target as HTMLElement).style.transitionDelay = `${delay}ms`;
            entry.target.classList.add("is-in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -8% 0px" }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [delay]);

  return (
    <Tag ref={ref} className={`reveal ${className}`} {...rest}>
      {children}
    </Tag>
  );
}
