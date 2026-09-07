# ContextHub OpenTofu

This directory is the source of truth for the production Cloud Run service.
OpenTofu stores shared state in the private, versioned GCS bucket
`contexthub-rag-app-tofu-state` under the `contexthub/production` prefix.

The existing Cloud Run service is adopted through the `import` block in
`main.tf`. The import is idempotent after the resource is recorded in state.

## Inspect a deployment locally

Authenticate with Google Cloud Application Default Credentials, then provide an
existing immutable image URL:

```bash
gcloud auth application-default login
tofu -chdir=terraform init
tofu -chdir=terraform plan \
  -var='image_url=us-central1-docker.pkg.dev/contexthub-rag-app/contexthub/contexthub:COMMIT_SHA'
```

Apply only after reviewing the plan:

```bash
tofu -chdir=terraform apply \
  -var='image_url=us-central1-docker.pkg.dev/contexthub-rag-app/contexthub/contexthub:COMMIT_SHA'
```

Normal production deployments are started manually through the GitHub `Deploy`
workflow. It builds and pushes the image, previews the OpenTofu plan, and then
applies it.
