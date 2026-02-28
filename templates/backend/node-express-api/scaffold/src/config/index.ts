import dotenv from "dotenv";

dotenv.config();

function requireEnv(key: string, fallback?: string): string {
  const value = process.env[key] ?? fallback;
  if (value === undefined) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

export const config = {
  // Application
  appName: requireEnv("APP_NAME", "Express API"),
  appVersion: requireEnv("APP_VERSION", "0.1.0"),
  nodeEnv: requireEnv("NODE_ENV", "development"),

  // Server
  host: requireEnv("HOST", "0.0.0.0"),
  port: parseInt(requireEnv("PORT", "3000"), 10),

  // Database
  databaseUrl: requireEnv("DATABASE_URL"),

  // CORS
  corsOrigins: requireEnv("CORS_ORIGINS", "http://localhost:5173").split(","),

  // JWT
  jwtSecret: requireEnv("JWT_SECRET", "change-me-in-production"),
  jwtExpiresIn: requireEnv("JWT_EXPIRES_IN", "24h"),
} as const;
