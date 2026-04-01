# Playwright Video + Postman Step-by-Step

## 1) Create a slower Playwright demo video

1. Open terminal at `repo/frontend`.
2. Install dependencies (first time only):
   - `npm install`
3. Install Playwright browser (first time only):
   - `npx playwright install`
4. Run the video-focused suite:
   - `npm run test:e2e:video`
5. After the run, open video outputs in:
   - `repo/frontend/test-results/`

Notes:
- This suite runs only `e2e/video-demo.spec.js`.
- It is configured with `slowMo: 450`, `headless: false`, and `video: on`.

## 2) Import Postman collection and environment

1. Open Postman.
2. Click **Import**.
3. Import collection file:
   - `repo/postman/HarborSuite.postman_collection.json`
4. Import environment file:
   - `repo/postman/HarborSuite.local.postman_environment.json`
5. Select environment **HarborSuite Local** in Postman.

## 3) Run API flow in Postman

Run requests in this order:

1. `0) Health`
2. `1) Login (bearer)`
3. `2) Current user (/auth/me)`
4. `3) List folios`
5. `4) Confirm quote`
6. `5) Create order`
7. `6) Queue folio print`
8. `7) Post reversal`
9. `8) Logout`

The collection auto-saves variables (token, folio_id, reconfirm_token, order_id) from responses.
