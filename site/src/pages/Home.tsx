import { Hero } from "../components/Hero";
import { VoiceExploded } from "../components/VoiceExploded";
import { ToneGallery } from "../components/ToneGallery";
import { HelixPipeline } from "../components/HelixPipeline";
import { Evidence } from "../components/Evidence";
import { CodeFlythrough } from "../components/CodeFlythrough";
import { Demo } from "../sections/Demo";
import {
  Problem,
  Science,
  Confidentiality,
  Limitations,
  Team,
} from "../sections/Sections";

// The main scroll experience. Deeper detail lives on the dedicated pages
// (/how, /method, /code) linked from the nav.
export function Home() {
  return (
    <>
      <Hero />
      <VoiceExploded />
      <Problem />
      <ToneGallery />
      <Science />
      <HelixPipeline />
      <Evidence />
      <CodeFlythrough />
      <Demo />
      <Confidentiality />
      <Limitations />
      <Team />
    </>
  );
}
