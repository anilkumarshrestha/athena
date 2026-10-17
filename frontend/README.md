# Athena frontend

Vite + React + TypeScript + Tailwind v4. Visual rules live in [../DESIGN.md](../DESIGN.md).
Setup, configuration and run instructions are in the [main README](../README.md).

```bash
npm install
npm run dev     # http://localhost:3000, proxies /api to :8077
npm run build   # type-check + production build to dist/ (served by FastAPI)
npm run lint
```
