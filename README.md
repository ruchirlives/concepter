# Concepter Web - Docker Deployment Guide

This guide provides setup instructions to deploy the Concepter Web application via Docker.

---

## ✨ Overview

Concepter Web is a Python-based backend that optionally integrates with a React frontend build via a junction (`react-build`). This guide assumes you're running on Windows and using PowerShell.

---

## 🚀 Docker Prerequisites

* **Docker Desktop** installed and running
* **Git** installed
* **PowerShell** as terminal

---

## ⚙️ Environment Setup

Before building or running the app, create a `.env` file in the project root with the following variables:

```env
NEO4J_URL=
NEO4J_USER=
NEO4J_PASSWORD=

# Local Documents
HOME = 

# ASTRA DB
OPENAI_API_KEY = 
ASTRADB_TOKEN = 
ASTRADB_ENDPOINT = 
ASTRADB_KEYSPACE = e.g. default_keyspace

RUNTIME_ENV=local

# MONGODB
MONGO_URL = 
MONGO_CERT_NAME = 
MONGO_CLOUD_PATH = 
```

### 🔑 Required Files

* Place your `your-service-account.json` and any `.pem` or cert files inside a local folder called `credentials/`.

Ensure the Dockerfile or your Docker run command mounts this folder correctly.

---

## 📁 File Structure Overview

```
ConcepterWeb/
├── app.py
├── requirements.txt
├── containers/          # Real folders, previously junctions
├── handlers/
├── helpers/
├── react-build/         # Built React frontend (optional)
└── .env
```

---

## 🌐 Docker Commands

### ✅ Build the image

```powershell
.\deployment-script.ps1
```

This script:

* Calculates if requirements need reinstalling
* Copies junction contents into a staging folder
* Builds the Docker image
* Pushes to Google Container Registry
* Deploys to Cloud Run

---

## 🚫 .gitignore Reminder

Ensure `.env`, `.pem`, and `credentials/` are listed in `.gitignore` so they aren't tracked by Git.
Put your .pem into your HOME folder, the HOME specified in .env
---

## 🚀 Local Docker Run (Optional)

If testing locally:

```powershell
docker build -t concepter-web .
docker run -p 8080:8080 \
  --env-file .env \
  -v "$PWD/credentials:/app/credentials" \
  concepter-web
```

---

## 🔎 Verifying Deployment

If deployed to Google Cloud Run:

* Visit the service URL from `gcloud run deploy` output
* Check logs via:

```bash
gcloud logs read --project=YOUR_PROJECT_ID
```

---

## ✨ Tips

* Keep `react-build` up to date by running `yarn build` or `npm run build` from your React project
* Recreate junctions with `mklink /J` if needed after cloning

---

Need help? Contact @ruchirlives or refer to your deployment script for more detail.
