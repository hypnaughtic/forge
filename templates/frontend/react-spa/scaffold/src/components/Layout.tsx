import React from "react";

interface LayoutProps {
  children: React.ReactNode;
}

/**
 * Root layout component providing consistent page structure.
 *
 * Wraps all pages with a header, main content area, and footer.
 * Extend this component to add navigation, sidebars, or global UI.
 */
export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50 text-gray-900">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <h1 className="text-xl font-semibold">
            <a href="/" className="hover:text-blue-600 transition-colors">
              App
            </a>
          </h1>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 text-center text-sm text-gray-500">
          Built with React + Vite + Tailwind
        </div>
      </footer>
    </div>
  );
}
