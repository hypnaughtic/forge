import { Router } from "express";

export const healthRouter = Router();

/**
 * Health check endpoint for container orchestration.
 * Returns application status and basic diagnostics.
 */
healthRouter.get("/", async (_req, res) => {
  res.json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    checks: {
      app: "ok",
    },
  });
});
