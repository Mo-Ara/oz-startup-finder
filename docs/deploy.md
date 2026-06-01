# Deploy Notes

## HuggingFace Spaces (Gradio)

1. Open the existing Space: `https://huggingface.co/spaces/Mo-Ara/oz-startup-finder`
2. In the Space **Settings**:
   - Add a secret named `OPENROUTER_API_KEY`.
3. In the Space **Files** tab:
   - Upload `data/startups.db`.
4. In the GitHub repo **Settings → Secrets and variables → Actions**, add:
   - `HF_TOKEN`
   - `HF_SPACE_REPO_ID` (`Mo-Ara/oz-startup-finder`)
5. Push to `master` or trigger the `deploy-hf.yml` workflow.
6. Verify the Space reloads with `app.py` and the Gradio UI appears.

## Cloud Run

```bash
gcloud run deploy oz-startup-finder \
  --image=gcr.io/PROJECT_ID/oz-startup-finder \
  --port=7860 \
  --allow-unauthenticated \
  --memory=1Gi
```

## Local

```bash
python -m scripts.seed_demo
python ui/app.py
```
