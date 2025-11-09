#!/bin/bash
# Quick script to verify Vertex AI API is enabled

PROJECT_ID="titanium-portal-476620"

echo "Checking if Vertex AI API is enabled for project: $PROJECT_ID"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "gcloud CLI not found. Install it from: https://cloud.google.com/sdk/docs/install"
    echo ""
    echo "Or manually enable the API at:"
    echo "https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=$PROJECT_ID"
    exit 1
fi

# Check API status
echo "Checking Vertex AI API status..."
gcloud services list --project=$PROJECT_ID --filter="name:aiplatform.googleapis.com" --format="table(name,state)"

echo ""
echo "To enable Vertex AI API, run:"
echo "gcloud services enable aiplatform.googleapis.com --project=$PROJECT_ID"
echo ""
echo "To check service account permissions, run:"
echo "gcloud projects get-iam-policy $PROJECT_ID"

