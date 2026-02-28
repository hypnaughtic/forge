/**
 * Home page component.
 * Loaded lazily via React.lazy() in App.tsx.
 */
export default function Home() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Welcome</h2>
      <p className="text-gray-600">
        Your React application is running. Edit this page to get started.
      </p>
    </div>
  );
}
