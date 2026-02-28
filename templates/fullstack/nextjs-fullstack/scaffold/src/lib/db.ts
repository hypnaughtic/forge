import { PrismaClient } from "@prisma/client";

/**
 * Prisma client singleton.
 *
 * In development, Next.js hot-reloads modules frequently. Without this
 * pattern, each reload creates a new PrismaClient and a new connection
 * pool, eventually exhausting database connections.
 *
 * Storing the client on globalThis survives hot reloads. In production,
 * modules are loaded once, so the globalThis check is a no-op.
 */

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

export const db =
  globalForPrisma.prisma ??
  new PrismaClient({
    log:
      process.env.NODE_ENV === "development"
        ? ["query", "error", "warn"]
        : ["error"],
  });

if (process.env.NODE_ENV !== "production") {
  globalForPrisma.prisma = db;
}
