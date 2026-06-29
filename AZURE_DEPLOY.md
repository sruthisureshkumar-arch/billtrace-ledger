# Deploying BillTrace Ledger to Azure App Service

This guide walks through everything from creating an Azure account to a live URL — from scratch.

---

## 0. Create Azure Computer Vision Resource (for real OCR)

1. In the Azure Portal, search **"Computer Vision"** → **Create**
2. Fill in:
   - Resource group: `billtrace-rg`
   - Region: `Central India`
   - Name: `billtrace-vision`
   - Pricing tier: **Free F0** (5,000 calls/month free)
3. Click **Review + Create** → **Create**
4. Once created, go to the resource → **Keys and Endpoint**
5. Copy **Key 1** and the **Endpoint URL**
6. In your Azure App Service → **Configuration → Application settings**, add:
   - `AZURE_VISION_KEY` = your Key 1
   - `AZURE_VISION_ENDPOINT` = your Endpoint URL

> Without these set, the app still works — it falls back to a demo serial number when an image is uploaded.

---

## 1. Create a Free Azure Account

1. Go to https://azure.microsoft.com/free and click **Start free**
2. Sign in with a Microsoft account (or create one)
3. Complete identity verification — you get $200 credit + 12 months of free services

---

## 2. Install the Azure CLI

**macOS (Homebrew):**
```bash
brew update && brew install azure-cli
```

Verify it worked:
```bash
az --version
```

Log in:
```bash
az login
```
A browser window will open — sign in with your Azure account.

---

## 3. Create Azure Resources (one-time setup)

Run these commands in your terminal. Replace `<your-name>` with something unique (e.g. your GitHub username).

```bash
# Variables — edit these
RESOURCE_GROUP="billtrace-rg"
LOCATION="eastus"
ACR_NAME="billtraceregistry"        # must be globally unique, letters/numbers only
APP_NAME="billtrace-ledger"         # must be globally unique

# Create a resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create an Azure Container Registry (ACR) to store your Docker image
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

# Create an App Service Plan (B1 = cheapest paid tier, ~$13/mo; F1 = free but no Docker)
az appservice plan create \
  --name billtrace-plan \
  --resource-group $RESOURCE_GROUP \
  --is-linux \
  --sku B1

# Create the Web App pointing at ACR
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan billtrace-plan \
  --name $APP_NAME \
  --deployment-container-image-name $ACR_NAME.azurecr.io/billtrace-ledger:latest
```

---

## 4. Get Your Secrets for GitHub Actions

```bash
# Get ACR credentials
az acr credential show --name $ACR_NAME

# Get the publish profile (download as XML, paste into GitHub secret)
az webapp deployment list-publishing-profiles \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --xml
```

---

## 5. Add Secrets to GitHub

In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**

Add these four secrets:

| Secret Name | Value |
|---|---|
| `ACR_LOGIN_SERVER` | `<acr-name>.azurecr.io` |
| `ACR_USERNAME` | Username from step 4 |
| `ACR_PASSWORD` | Password from step 4 |
| `AZURE_APP_NAME` | `billtrace-ledger` (your app name) |
| `AZURE_PUBLISH_PROFILE` | Full XML output from step 4 |

---

## 6. Push to Deploy

Every push to `main` now triggers the GitHub Actions workflow (`.github/workflows/azure-deploy.yml`), which:
1. Builds the Docker image
2. Pushes it to your Azure Container Registry
3. Deploys it to Azure App Service automatically

```bash
git add .
git commit -m "feat: add azure deployment + Emil Kowalski design update"
git push origin main
```

Your app will be live at: `https://<APP_NAME>.azurewebsites.net`

---

## 7. Verify It's Running

```bash
az webapp browse --name $APP_NAME --resource-group $RESOURCE_GROUP
```

---

## Tips for the Microsoft Application

- Azure App Service with CI/CD via GitHub Actions demonstrates a real production deployment workflow
- The Dockerfile shows containerization skills
- Mention the Azure Container Registry + App Service architecture in your application writeup
- You can show the live `azurewebsites.net` URL as a deployed project link
