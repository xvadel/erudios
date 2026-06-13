import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/layout/Header";

export const metadata: Metadata = {
  title: "Erudios — AI Curriculum Builder",
  description:
    "Your personal AI learning architect for Machine Learning, Deep Learning, NLP, RAG, and Agentic AI. Discover curated resources, build personalized learning paths, and never wonder what to learn next.",
  keywords: ["machine learning", "deep learning", "RAG", "AI", "curriculum", "learning path"],
  openGraph: {
    title: "Erudios — AI Curriculum Builder",
    description: "Personalized AI/ML learning paths. Built around you.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>
        <Header />
        <main className="min-h-[calc(100dvh-4rem)]">{children}</main>
      </body>
    </html>
  );
}
