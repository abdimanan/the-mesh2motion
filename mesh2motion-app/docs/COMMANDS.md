# Mesh2Motion App – Command Reference

All commands are run from the root of the `mesh2motion-app` folder (where `package.json` and `Dockerfile` live) unless noted otherwise.

```bash
cd "/Users/astaandrama2/abdimanan/blender/the mesh2motion/mesh2motion-app"
```
cd mesh2motion-app


You can run the app in one of two ways:

- **Option A – Locally with Node.js** (best for development, faster reloads)
- **Option B – With Docker** (nothing installed on your machine except Docker)

---

## Option A – Run locally with Node.js

### 1. Prerequisites

The project uses Node.js **24.11.0** (pinned in `.nvmrc`).

```bash
# Check what you have installed
node -v
npm -v
```

If you use [nvm](https://github.com/nvm-sh/nvm) to manage Node versions:

```bash
nvm install      # installs the version from .nvmrc (24.11.0)
nvm use          # switches to it
```

Or install Node 24 with Homebrew (macOS):

```bash
brew install node@24
```

### 2. Install dependencies

```bash
npm install
```

For a clean, exact install from `package-lock.json` (e.g. CI or after problems):

```bash
npm ci
```

### 3. Start the development server

```bash
npm run dev
```

- Vite starts a dev server and opens the browser automatically.
- URL: **http://localhost:5173**
- Stop it with `Ctrl + C`.

Pages served by the app:

| Page | URL |
|---|---|
| Main app | http://localhost:5173/ |
| Create | http://localhost:5173/create.html |
| Retarget | http://localhost:5173/retarget/index.html |
| Preview generator (internal tool) | http://localhost:5173/preview-generator/index.html |

### 4. Production build

```bash
npm run build
```

Creates a `dist/` folder with the static files ready to deploy.

To preview the production build locally:

```bash
npx vite preview
```

- URL: **http://localhost:4173**

### 5. Tests

```bash
npm test               # run Vitest (watch mode)
npx vitest run         # run tests once and exit
npm run test:ui        # Vitest browser UI
npm run test:coverage  # coverage report (output in coverage/)
```

### 6. Linting

```bash
npm run lint           # check code with ESLint
npm run lint:fix       # auto-fix lint problems
```

### 7. Type checking (optional)

```bash
npx tsc --noEmit
```

---

## Option B – Run with Docker

The repo includes a `Dockerfile` (Node 24 Alpine, runs `npm run dev`) and a `docker-compose.yaml` that maps **host port 3000 → container port 5173**.

### 1. Prerequisites

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and make sure it is **running** before you use any of the commands below.

```bash
docker --version
docker compose version
```

> Newer Docker uses `docker compose` (with a space). The older standalone
> `docker-compose` (with a hyphen) works the same way if that is what you have.

### 2. Build and start with Docker Compose (recommended)

```bash
docker compose up -d --build
```

- `-d` runs it in the background.
- `--build` builds or rebuilds the image first.
- URL: **http://localhost:3000**

### 3. Everyday Docker Compose commands

```bash
docker compose ps                 # is the container running?
docker compose logs -f            # follow the logs (Ctrl + C to stop following)
docker compose stop               # stop the container (keeps it)
docker compose start              # start it again
docker compose restart            # restart it
docker compose down               # stop and remove the container
docker compose down --rmi local   # also remove the built image
docker compose up -d --build      # rebuild after changing code, then start
```

> The Dockerfile **copies** the source into the image (`COPY . /app`), so code
> changes on your machine are **not** picked up automatically. Re-run
> `docker compose up -d --build` after editing files.

Open a shell inside the running container:

```bash
docker compose exec mesh2motion-app sh
```

### 4. Plain Docker (without Compose)

```bash
# Build the image
docker build -t mesh2motion-app .

# Run it (host port 3000 -> container port 5173)
docker run -d --name mesh2motion-app -p 3000:5173 mesh2motion-app

# Logs / stop / start / remove
docker logs -f mesh2motion-app
docker stop mesh2motion-app
docker start mesh2motion-app
docker rm -f mesh2motion-app

# Remove the image
docker rmi mesh2motion-app
```

- URL: **http://localhost:3000**

---

## Deployment (Cloudflare – maintainers only)

The project ships a `wrangler.jsonc` for Cloudflare Workers that serves the `dist/` folder and a survey worker backed by a D1 database. This needs access to the project's Cloudflare account, so you do **not** need it to run the app locally.

```bash
npm run build          # build dist/ first
npx wrangler dev       # run the worker locally
npx wrangler deploy    # deploy (requires Cloudflare login + permissions)
```

---

## The `mesh2motion-assets` repo

`../mesh2motion-assets` holds the original Blender source files (models, rigs, animations). The app **does not need it to run**: the final compressed GLB files are already in this repo under `static/`. Use the assets repo only if you want to edit or create new animations in Blender.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Port 5173 / 3000 already in use | Stop the other process, or run `npm run dev -- --port 5174`. For Docker, change `"3000:5173"` in `docker-compose.yaml` to e.g. `"3001:5173"`. |
| Weird install errors | `rm -rf node_modules && npm ci` |
| `Cannot connect to the Docker daemon` | Start Docker Desktop and wait until it says it is running. |
| Docker shows old code | `docker compose up -d --build` |
| Wrong Node version | `nvm use` (reads `.nvmrc`) |

---

## Quick start (TL;DR)

```bash
# Local
npm install
npm run dev            # http://localhost:5173

# Docker
docker compose up -d --build   # http://localhost:3000
docker compose down            # stop
```
