# cuda-sample-quality-analyzer — Web App

Full-stack web application for analyzing CUDA sample repository quality.

Paste any public GitHub repo URL → get a scored quality dashboard instantly.

---

## Project Structure

```
cuda-analyzer-web/
├── backend/          ← FastAPI (deploy to Render)
│   ├── main.py
│   ├── analyzer/     ← core analysis engine
│   ├── requirements.txt
│   └── render.yaml
└── frontend/         ← React (deploy to Vercel)
    ├── src/
    │   ├── App.js
    │   └── App.css
    └── package.json
```

---

## Deploy Backend (Render) — do this first

1. Push the `backend/` folder to a GitHub repo (or the whole project)
2. Go to [render.com](https://render.com) → **New** → **Web Service**
3. Connect your GitHub repo
4. Set:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Click **Deploy**
6. Copy your Render URL — looks like `https://cuda-analyzer-api.onrender.com`

---

## Deploy Frontend (Vercel) — do this second

1. Go to [vercel.com](https://vercel.com) → **New Project**
2. Import the same GitHub repo
3. Set:
   - **Root Directory:** `frontend`
   - **Framework:** Create React App
   - **Environment Variable:**
     - Key: `REACT_APP_API_URL`
     - Value: your Render URL from above (e.g. `https://cuda-analyzer-api.onrender.com`)
4. Click **Deploy**

Done. Your site is live.

---

## Run Locally

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
REACT_APP_API_URL=http://localhost:8000 npm start
```

---

## Usage

Paste any public GitHub repo with `.cu` or `.cuh` files:

```
https://github.com/NVIDIA/cuda-samples
https://github.com/NVIDIA/cuda-by-example
```

The analyzer scores each sample directory across:
- **Documentation** (25pts) — README, build/run instructions, expected output
- **Clarity** (25pts) — comment density, kernel naming, file length
- **Best Practices** (30pts) — error checks, memory cleanup, sync after launch
- **Modernity** (20pts) — no outdated APIs or legacy terminology
