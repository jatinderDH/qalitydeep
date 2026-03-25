# QAlityDeep Docs UI

Developer documentation dashboard UI (Next.js, Tailwind, shadcn-style).

## Run

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Stack

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- shadcn-style components (Button, Input, Card, Badge, Tabs)
- lucide-react icons
- react-resizable-panels

## Structure

- `app/page.tsx` – main layout and state
- `components/navbar.tsx` – top nav
- `components/sidebar.tsx` – left endpoint list
- `components/endpoint-bar.tsx` – POST + URL + Send request
- `components/api-editor.tsx` – Headers & body form
- `components/code-block-panel.tsx` – REQUEST (cURL/TS/Python) + RESPONSE
- `components/ui/*` – shared UI primitives
