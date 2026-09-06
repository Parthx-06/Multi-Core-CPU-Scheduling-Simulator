# Deploying Multi-Core CPU Scheduling Simulator on Render

This guide provides step-by-step instructions for deploying the project to **[Render.com](https://render.com)** as a production Python Web Service.

---

## 🚀 Option 1: 1-Click Blueprint Deployment (Recommended)

Because this repository includes a [`render.yaml`](render.yaml) Blueprint, Render can configure everything automatically.

1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Configure project for Render deployment"
   git push origin main
   ```
2. Log in to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** at the top right and select **Blueprint**.
4. Connect your GitHub repository (`Parthx-06/Multi-Core-CPU-Scheduling-Simulator`).
5. Render will detect the `render.yaml` specification automatically.
6. Click **Apply**. Render will automatically:
   - Install dependencies via `pip install -r requirements.txt`
   - Start the service with `gunicorn app:app`
   - Monitor health at `/api/health`
7. Once deployed, open your live Render URL (e.g. `https://multicore-scheduler-simulator.onrender.com`).

---

## 🛠️ Option 2: Manual Web Service Setup on Render

If you prefer to configure the Web Service manually via Render's web UI:

1. In the [Render Dashboard](https://dashboard.render.com), click **New +** > **Web Service**.
2. Connect your GitHub repository.
3. Configure the following settings:
   - **Name**: `multicore-scheduler-simulator` (or your choice)
   - **Language / Runtime**: `Python 3`
   - **Branch**: `main`
   - **Region**: Choose the closest region (e.g., Singapore, Frankfurt, Ohio, Oregon)
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     gunicorn app:app
     ```
   - **Instance Type**: `Free`
4. Expand **Advanced Settings**:
   - **Health Check Path**: `/api/health`
   - **Environment Variables**:
     - `PYTHON_VERSION`: `3.11.9`
     - `PORT`: `10000` (Render sets this dynamically, but setting default is good practice)
5. Click **Create Web Service**.

---

## 🔍 Verification & Health Check

Once your deployment completes:
- **Web UI**: Visit `https://<your-app-name>.onrender.com`
- **Health Check**: `https://<your-app-name>.onrender.com/api/health` should return:
  ```json
  {
    "status": "healthy",
    "service": "multi-core-cpu-scheduling-simulator",
    "version": "2.0.0"
  }
  ```
- **Simulate Endpoint**: `POST https://<your-app-name>.onrender.com/api/simulate`
- **Benchmark Presets**: `GET https://<your-app-name>.onrender.com/api/phase2_comparison`

---

## 💡 Notes on Render Free Tier

- **Spin-Down on Inactivity**: On the Render Free Tier, services spin down after 15 minutes of inactivity. When a new request arrives, Render spins up the instance in ~30–50 seconds (cold start).
- **Fast Startup**: Because static benchmark results (`phase1_benchmark_results.json` and `phase2_comparison_results.json`) are pre-generated and bundled, your app starts up in less than 2 seconds without requiring re-computation on boot.
