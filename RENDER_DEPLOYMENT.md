# Deploying Multi-Core CPU Scheduling Simulator (Phase 1) on Render

This guide walks you through deploying the project as a **Free Web Service** on [Render.com](https://render.com/).

---

## 1. Prerequisites
- A free [Render.com](https://render.com/) account.
- Your project pushed to a GitHub or GitLab repository.

---

## 2. Included Deployment Files
The following files are configured and ready in the repository:
- `requirements.txt`: Python packages (`Flask`, `flask-cors`, `gunicorn`, `rich`, `pytest`).
- `Procfile`: Specifies the web process command (`web: gunicorn app:app`).
- `app.py`: Top-level WSGI entrypoint exposing the Flask application.
- `render.yaml`: Blueprint definition for Render.
- `runtime.txt`: Pins Python version (`python-3.11.9`).
- Health Check Endpoints: `/healthz` and `/api/health`.

---

## 3. Step-by-Step Deployment Steps

### Option A: Standard Web Service (Quickest)
1. Go to your [Render Dashboard](https://dashboard.render.com/) and click **New +** -> **Web Service**.
2. Connect your GitHub / GitLab repository (`Multi-Core-CPU-Scheduling-Simulator` or your fork).
3. Choose the branch you want to deploy (`phase-1` or `main`).
4. Fill in the service details:
   - **Name**: `multicore-cpu-scheduler` (or any name you choose)
   - **Region**: Closest to you (e.g. Frankfurt, Oregon, Singapore)
   - **Language**: `Python 3`
   - **Branch**: `phase-1` (or whichever branch holds this commit)
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     gunicorn app:app
     ```
   - **Instance Type**: `Free`
5. *(Optional but recommended)* Click **Advanced**:
   - **Health Check Path**: `/api/health`
   - **Environment Variables**:
     - `PYTHON_VERSION` = `3.11.9`
6. Click **Create Web Service**.

---

### Option B: Deploy via Blueprint (`render.yaml`)
1. In the Render Dashboard, click **New +** -> **Blueprint**.
2. Select your repository and branch (`phase-1`).
3. Render will detect `render.yaml` and configure the service automatically.
4. Click **Apply**.

---

## 4. Verification
Once the deploy finishes (usually 1-2 minutes):
1. Render gives you an HTTPS URL: `https://<your-service-name>.onrender.com`.
2. Open the URL in your browser to verify the interactive dashboard.
3. Test the health check endpoint: `https://<your-service-name>.onrender.com/api/health`.
