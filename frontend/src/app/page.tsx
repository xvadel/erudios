import type { Metadata } from "next";
import { HeroSection } from "@/components/home/HeroSection";
import { TopicGrid } from "@/components/home/TopicGrid";
import { FeatureSection } from "@/components/home/FeatureSection";

export const metadata: Metadata = {
  title: "Erudios — Your AI Learning Architect for ML & AI",
  description:
    "Stop searching, start learning. Erudios builds personalized curricula for any AI/ML topic — curated resources, clear learning paths, and always knows what to teach you next.",
};

export default function HomePage() {
  return (
    <div className="flex flex-col">
      <HeroSection />
      <FeatureSection />
      <TopicGrid />
    </div>
  );
}
