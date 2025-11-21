# RailFair Frontend (Netlify Ready)

This directory contains the static landing/search experience for RailFair. It is ready to be deployed to Netlify (or any static host) with minimal setup.

## Files of interest

- `index.html`, `style.css`, `script.js`, `stations.json`: core UI assets.
- `config.js`: runtime hook for specifying the backend origin (see below).
- `netlify.toml`: default Netlify configuration (publish dir + `/api/*` proxy template).

## Configure the backend endpoint

1. Decide how the frontend reaches your backend:
   - **Same origin proxy**: edit `netlify.toml` and set the redirect target to your backend domain. Netlify will forward any `/api/*` call to that URL, so the browser still thinks it is calling the same origin.
   - **Direct cross-origin calls**: edit `config.js` and set `configuredBase` to your backend origin (e.g. `https://api.your-domain.com`). The script already falls back to `window.location.origin` when left blank.
2. If you go cross-origin, make sure the backend sends proper CORS headers.

## Deploying to Netlify

1. In the Netlify dashboard, create a new site from Git and set **Base directory** to `frontend/railfair`.
2. Leave the **Build command** empty (the site is pure static). The `netlify.toml` already specifies the publish directory as `.`.
3. Set up any required environment variables (if your backend needs them).
4. Trigger a deploy. Netlify will upload all files as-is.

## Local preview

Because there is no build step, you can simply open `index.html` in a browser. For local API testing, run the backend on `http://localhost:8000`, then either:

- update `config.js` to `const configuredBase = 'http://localhost:8000';`, or
- start a lightweight proxy (e.g. `npx serve` plus `local-ssl-proxy`) that mirrors the `/api` path.

## Keeping stations data fresh

`stations.json` ships with the 2024-04-29 timetable snapshot. When you obtain newer data, replace the file with the latest export; the frontend will pick it up automatically.

Happy shipping!

