import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-dvh flex items-center justify-center px-4">
      <div className="text-center">
        <p className="text-8xl font-bold gradient-text mb-4">404</p>
        <h1 className="text-2xl font-semibold mb-2">Page not found</h1>
        <p className="text-muted-foreground mb-8">
          The page you're looking for doesn't exist.
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
        >
          Back to home
        </Link>
      </div>
    </div>
  );
}
