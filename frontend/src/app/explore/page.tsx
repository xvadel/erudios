import { Suspense } from "react";
import ExplorePage from "./ExplorePage";

export default function ExplorePageWrapper() {
  return (
    <Suspense
      fallback={
        <div className="max-w-7xl mx-auto px-4 pt-24 pb-20">
          <div className="space-y-4">
            <div className="shimmer h-10 w-64 rounded" />
            <div className="shimmer h-4 w-32 rounded" />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-8">
              {Array.from({ length: 9 }).map((_, i) => (
                <div key={i} className="shimmer h-32 rounded-2xl" />
              ))}
            </div>
          </div>
        </div>
      }
    >
      <ExplorePage />
    </Suspense>
  );
}
