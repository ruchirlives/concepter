# Concepter Web - Docker Deployment Guide

This guide provides setup instructions to deploy the Concepter Web application via Docker.
* Copyright (c) 2025 Ruchir Shah
* Licensed under the GNU GPLv3. See [LICENSE](./LICENSE) file for details.

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
HOME = 
OPENAI_API_KEY = 
RUNTIME_ENV=local
API_PASSCODE = your-secure-passcode-here

# MONGODB
MONGO_URL = 
MONGO_CERT_NAME =  # ending .pem
MONGO_CLOUD_PATH =  # Cloud runtime location of .pem file
```

### 🔐 API Authentication

The application includes passcode-based authentication for all API endpoints. See [AUTHENTICATION.md](./AUTHENTICATION.md) for detailed setup and usage instructions.

* Set `API_PASSCODE` environment variable to enable authentication
* All API requests must include `X-Passcode` header
* Static files and documentation routes are excluded from authentication

### 🔑 Required Files

* If using local runtime, you need to place your Mongo .pem credential file into your HOME folder, the HOME specified in .env
* Ensure the Dockerfile or your Docker run command mounts this folder correctly.

---

## 📁 File Structure Overview

```
ConcepterWeb/
├── app.py
├── requirements.txt
├── containers/          # Real folders, previously junctions
├── handlers/
├── helpers/
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

Ensure `.env`, `.pem` are listed in `.gitignore` so they aren't tracked by Git.
---

## 🚀 Local Docker Run (Optional)

If testing locally:

```powershell
docker build -t concepter-web .
docker run -p 8080:8080 --env-file .env concepter-web
```

---

## 🔎 Verifying Deployment

If deployed to Google Cloud Run:

* Visit the service URL from `gcloud run deploy` output
* Make sure to add your secrets and cloud environment variables 
* Check logs via:

```bash
gcloud logs read --project=YOUR_PROJECT_ID
```

---

Need help? Contact @ruchirlives or refer to your deployment script for more detail.
