/**
 * Home page — a React Server Component by default.
 *
 * This component renders entirely on the server. It can fetch data
 * directly (no API route needed) and its JavaScript is never sent
 * to the client.
 */
export default function Home() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Welcome</h2>
      <p className="text-gray-600 mb-4">
        Your Next.js application is running. This is a Server Component —
        it renders on the server and sends only HTML to the browser.
      </p>
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-2">Getting Started</h3>
        <ul className="list-disc list-inside text-gray-600 space-y-1">
          <li>Edit <code className="bg-gray-100 px-1 rounded">src/app/page.tsx</code> to modify this page</li>
          <li>Add new routes by creating directories in <code className="bg-gray-100 px-1 rounded">src/app/</code></li>
          <li>Define your database schema in <code className="bg-gray-100 px-1 rounded">prisma/schema.prisma</code></li>
        </ul>
      </div>
    </div>
  );
}
