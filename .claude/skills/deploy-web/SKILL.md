---
name: deploy-web
description: Build dsa-web and restart server on port 8000 for testing
---

# Deploy Web Skill

After code changes to `apps/dsa-web/`, build and deploy for testing.

## Steps

1. **Build the web app**:
   ```bash
   cd apps/dsa-web && npm ci && npm run build
   ```

2. **Restart the server on port 8000**:
   ```bash
   fuser -k 8000/tcp 2>/dev/null; sleep 1
   cd /home/muzig/.openclaw/workspace/daily_stock_analysis
   nohup uvicorn server:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &
   ```

3. **Verify**:
   ```bash
   curl -s http://localhost:8000/docs -o /dev/null -w "%{http_code}"
   ```
   Expected: `200`

## When to Run

- After modifying any file in `apps/dsa-web/src/`
- After modifying API routes in `api/`
- After modifying backend files that affect API responses
- When user wants to test changes at http://localhost:8000

## Verification

Report the build status and server status to the user.