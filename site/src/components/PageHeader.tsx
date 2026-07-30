import { Reveal } from "./Reveal";

// Consistent page header that clears the fixed nav. Light or dark tone.
export function PageHeader({
  eyebrow,
  title,
  intro,
  tone = "light",
}: {
  eyebrow: string;
  title: string;
  intro?: string;
  tone?: "light" | "dark";
}) {
  return (
    <header className={`pagehead pagehead--${tone}`}>
      <div className="container">
        <Reveal as="p" className="eyebrow pagehead__eyebrow">{eyebrow}</Reveal>
        <Reveal as="h1" className="display-lg pagehead__title" delay={60}>{title}</Reveal>
        {intro && (
          <Reveal as="p" className="lead pagehead__intro" delay={120}>{intro}</Reveal>
        )}
      </div>
      <style>{`
        .pagehead { padding:clamp(120px,18vh,200px) clamp(20px,5vw,72px) clamp(40px,6vh,72px); }
        .pagehead--light { background:var(--cream); color:var(--ink); }
        .pagehead--dark { background:#0b0a10; color:var(--cream); }
        .pagehead--dark .pagehead__eyebrow { color:var(--sky); }
        .pagehead__title { max-width:18ch; margin:0.2em 0 0.4em; }
        .pagehead__intro { max-width:60ch; }
        .pagehead--dark .pagehead__intro { color:rgba(244,239,230,0.82); }
      `}</style>
    </header>
  );
}
