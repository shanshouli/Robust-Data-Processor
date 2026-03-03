# Tenant Log Management Dashboard (Frontend)

This Angular workspace provides the Tenant Log Management Dashboard for the multi-tenant log ingestion system.

## Prerequisites

- Node.js 20+ (or newer)
- npm 10+

## Install Dependencies

```bash
npm install
```

## Run the Dev Server

```bash
npm run start
```

The application will be available at `http://localhost:4200/`.

## Build for Production

```bash
npm run build
```

The production build output will be generated in `frontend/dist/frontend/`.

## Notes

- Tailwind CSS is enabled for utility-first layout and styling.
- Angular Material is used for accessible, enterprise-grade UI components.
- The current data stream and metrics are simulated and can be wired to real APIs by updating the services under `src/app/core/services/`.
