# Google Secret Manager Integration

This project now retrieves credentials via Google Secret Manager (GSM) using the helper in `gcp_secrets.py`. Secrets are cached in-process and still honor local environment variables for overrides. Follow the steps below to provision, grant access, and consume secrets across environments.

## 1. Create Secrets
- Enable the **Secret Manager API** in the target Google Cloud project.
- Create each secret (e.g. `OPENAI_API_KEY`, `SERPAPI_KEY`, `SENDGRID_API_KEY`, `ADMIN_EMAIL`) and add the credential value as **version 1**. You can use the Cloud Console or:
  ```bash
  gcloud secrets create OPENAI_API_KEY --replication-policy="automatic"
  printf "sk-..." | gcloud secrets versions add OPENAI_API_KEY --data-file=-
  ```
- Repeat for every credential. Use the same secret IDs referenced in code; otherwise pass `project_id` explicitly when calling `get_secret`.

## 2. Grant Access
Grant the runtime service account the `roles/secretmanager.secretAccessor` role:
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```
Replace `SERVICE_ACCOUNT` and `PROJECT_ID` with your values. For local development, the account associated with your Application Default Credentials (ADC) must have the same role.

## 3. Local Development
1. Ensure the virtualenv dependency is installed: `pip install -r requirements.txt`.
2. Authenticate with ADC so the Secret Manager client can impersonate your user:
   ```bash
   gcloud auth application-default login
   ```
   OR point `GOOGLE_APPLICATION_CREDENTIALS` to a service-account JSON file that has `secretAccessor`.
3. Optionally keep a `.env` file for overrides; environment variables take precedence over Secret Manager (handy for offline work or testing).

## 4. Cloud Run
1. Deploy with a service account that has `secretAccessor`.
2. Reference secrets at deploy time; the helper will read them using ADC so an explicit `--set-env-vars` is unnecessary, but Cloud Run supports binding secrets to env vars if you want fast startup:
   ```bash
   gcloud run deploy jobsearch-api \
     --image gcr.io/PROJECT_ID/jobsearch-api:latest \
     --service-account SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com \
     --set-secrets OPENAI_API_KEY=OPENAI_API_KEY:latest,SERPAPI_KEY=SERPAPI_KEY:latest \
     --region REGION \
     --allow-unauthenticated
   ```
3. Any secret bound via `--set-secrets` lands in the container as an environment variable, which the helper will use without hitting the Secret Manager API.

## 5. Google Kubernetes Engine (GKE)
Choose one of two patterns:

- **Workload Identity + Secret Manager API (recommended)**  
  1. Enable Workload Identity on your cluster.  
  2. Bind your GSA with `roles/secretmanager.secretAccessor`.  
  3. Annotate the Kubernetes service account (`ksa`) to impersonate the GSA.  
  4. Pods access secrets directly via the helper; no extra volumes are needed.

- **Secret Manager CSI Driver**  
  1. Install the CSI driver: `gcloud container clusters update CLUSTER --update-addons=GcpFilestoreCsiDriver`.  
  2. Create `SecretProviderClass` objects that reference GSM secrets.  
  3. Mount them into pods; secrets materialize as files, then set env vars or read files during startup.

## 6. Troubleshooting
- `google.api_core.exceptions.PermissionDenied`: verify the active service account has `secretAccessor`.
- `RuntimeError: Cannot resolve project`: set `GCP_PROJECT`/`GOOGLE_CLOUD_PROJECT` or pass `project_id` to `get_secret`.
- Secrets are cached per process. If you rotate a secret, restart the service or call `gcp_secrets.get_secret.cache_clear()` to force a refresh.

For detailed usage, see `gcp_secrets.py`. Update existing deployment scripts to ensure the required IAM bindings and ADC configuration are in place before switching environments.

