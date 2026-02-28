import express from "express";
import cors from "cors";
import helmet from "helmet";
import { config } from "./config";
import { errorHandler } from "./middleware/error-handler";
import { healthRouter } from "./routes/health";

const app = express();

// Security middleware
app.use(helmet());
app.use(cors({ origin: config.corsOrigins }));

// Body parsing
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Routes
app.use("/health", healthRouter);

app.get("/", (_req, res) => {
  res.json({
    app: config.appName,
    version: config.appVersion,
    docs: "/health",
  });
});

// Error handling (must be registered last)
app.use(errorHandler);

// Start server
app.listen(config.port, config.host, () => {
  console.log(`${config.appName} listening on ${config.host}:${config.port}`);
});

export default app;
