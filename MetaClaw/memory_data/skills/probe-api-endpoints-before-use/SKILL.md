---
name: probe-api-endpoints-before-use
description: Use when making HTTP requests to an API or service. Always verify the endpoint exists by checking documentation or probing the base URL first.
category: automation
---

## Probe API Endpoints Before Calling

1. Before making API calls, check if documentation exists in the project (README.md, API docs)
2. Probe the base URL first with `curl <base-url>` to see available routes
3. If getting "Not Found", stop and investigate:
   - Check if the server is actually running
   - List available routes/endpoints
   - Verify the correct URL path and HTTP method
4. Common endpoints to probe: `/`, `/docs`, `/api`, `/health`

**Anti-pattern:** Making POST requests to `/api/temi/move` without verifying the endpoint exists results in 404 Not Found errors.
