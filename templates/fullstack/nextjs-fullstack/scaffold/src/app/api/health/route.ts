import { NextResponse } from "next/server";
import { db } from "@/lib/db";

/**
 * Health check API route.
 *
 * Verifies application and database connectivity.
 * Used by container orchestrators and monitoring tools.
 */
export async function GET() {
  const checks: Record<string, string> = { app: "ok" };

  try {
    await db.$queryRaw`SELECT 1`;
    checks.database = "ok";
  } catch {
    checks.database = "error";
    return NextResponse.json(
      { status: "unhealthy", checks },
      { status: 503 }
    );
  }

  return NextResponse.json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    checks,
  });
}
