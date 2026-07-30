# Deploying OwnVoice publicly

One container serves the site **and** the API from a single origin, so there is
one public URL and no CORS to configure. Verified locally in exactly this
configuration before writing this.

```
GET  /                 the React site
GET  /how /method /code  SPA deep links -> index.html, router takes over
GET  /assets/*         hashed JS/CSS
GET  /samples/*        the CC0 demo clip
GET  /health           status
POST /simulate         clean audio -> dysarthric audio
POST /transcribe       audio -> text, fine-tuned vs stock
```

---

## ⚠ Read this before you deploy

**Set `OWNVOICE_MODEL`.** The Dockerfile defaults it to `openai/whisper-small`
— the same as the baseline. Deploy without changing it and the demo compares
the model against itself: two identical transcripts, identical CERs, no error
anywhere. It looks like it works. `/health` reports
`"tuned_is_distinct_from_base": false` and the container shouts at boot, but
nothing stops you.

**The free tier has no GPU.** Everything measured on this machine ran on an
RTX 5060. On CPU, whisper-small twice over takes tens of seconds per clip, and
the first request also downloads and loads both models. `OWNVOICE_MAX_SECONDS`
is set to 15 in the Dockerfile for that reason. The site already handles the
cold-start case — it tells visitors the server may be waking up.

**Everything served is still simulated dysarthria.** Publishing does not change
what the numbers mean. The limitations section on the site says so; leave it in.

---

## Getting the model there

The checkpoint is 922 MB and is gitignored. Two options.

### Option A — push it to the Hub as a model repo (recommended)

Cleaner: the Space stays small, builds stay fast, and the model is versioned
separately.

```bash
pip install huggingface_hub
huggingface-cli login
huggingface-cli upload <your-username>/ownvoice-asr runs/asr_v1 . --repo-type model
```

Then set in the Space: `OWNVOICE_MODEL=<your-username>/ownvoice-asr`

### Option B — bake it into the image

Copy `runs/asr_v1` into the build context, add a `COPY` line to the Dockerfile,
and track it with git-LFS. Slower pushes, larger image, and HF Spaces have a
size ceiling — only worth it if you want one self-contained artifact.

---

## Hugging Face Space

The same pattern NeuroTrace already uses.

1. Create a Space: SDK **Docker**, hardware **CPU basic** (free) or better.
2. Push this repo to it. The Dockerfile is at the root and needs no changes.
   ```bash
   git remote add space https://huggingface.co/spaces/<user>/<space-name>
   git push space main
   ```
   HF auto-creates an initial commit, so the first push usually needs
   `--force`.
3. In the Space's **Settings → Variables**, set:
   ```
   OWNVOICE_MODEL        <your-username>/ownvoice-asr
   OWNVOICE_MAX_SECONDS  15
   ```
4. Wait for the build, then check `/health` and confirm
   `"tuned_is_distinct_from_base": true` before sharing the link.

Spaces sleep after inactivity. The first visitor after a sleep waits for a cold
start plus model load — worth knowing before you send the URL to a judge.

---

## Any other container host

```bash
docker build -t ownvoice .
docker run -p 7860:7860 \
  -e OWNVOICE_MODEL=<your-username>/ownvoice-asr \
  ownvoice
```

Render's free tier will not work — 512 MB cannot hold two Whisper models. Fly.io
or a small VPS both can.

---

## Site only, no model

If you want the site public before the model is hosted anywhere, the build in
`site/dist/` is a static bundle and deploys to Netlify, Vercel or GitHub Pages
as-is. Point `VITE_API_BASE` at the API's origin, or leave it empty and accept
that the demo shows "Model server not reachable".

Everything except the Demo section works standalone: the exploded view, the
tone-flattening interaction, the evidence panels and all three sub-pages are
client-side.

---

## Rebuilding after a change

```bash
cd site && npm run build && cd ..
rm -rf backend/web && cp -r site/dist backend/web    # local prod test only
python backend/app.py
```

In the container this is automatic — stage 1 builds the site and copies
`dist/` into `backend/web/`.

## Local development

Leave `backend/web/` absent. The API runs on :7860 and Vite serves the site on
:5173 with CORS already allowing that origin.

```bash
python backend/app.py          # terminal 1
cd site && npm run dev         # terminal 2
```
