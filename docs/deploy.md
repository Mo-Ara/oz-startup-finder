# Deploy Notes

## HuggingFace Spaces

1. Create a new Space using the "Docker" template.
2. Push this repo to the Space or connect a GitHub repository.
3. Set `OPENROUTER_API_KEY` in the Space secrets.
4. Place `data/startups.db` in the Space root or mount it as a volume.
5. The app starts on port 7860 via `python ui/app.py`.

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
