# YatraSathi Web

React 19 + TypeScript + Vite + Tailwind + Leaflet client for the YatraSathi API.

```bash
npm install
npm run dev      # http://localhost:5173, proxies API calls to http://localhost:8000
npm run build    # type-check + production build into dist/
npm run lint
```

## Configuration

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | API origin, e.g. `https://api.yatrasathi.com`. Leave empty when the API is served from the same origin (the Docker image uses `/api` via nginx). |

Production builds are deployed to Cloudflare Pages (`public/_redirects` provides
the SPA fallback, `public/_headers` the security headers).
