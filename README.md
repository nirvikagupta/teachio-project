# Teachio

An adaptive, student-centered learning app built with [Streamlit](https://streamlit.io/).
Students onboard with a learning profile, upload study material, get AI-generated study
aids, quizzes, podcasts, and practice active recall via a "TeachBack" feature.

## Tech stack

- **Streamlit** — UI and app server
- **Groq** — LLM calls for the teaching agents
- **gTTS** — text-to-speech for podcasts
- **pypdf** — parsing uploaded study material

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Configuration

The app reads a Groq API key from the environment or Streamlit secrets — nothing is
hardcoded. Provide it one of these ways:

- Environment variable: `export GROQ_API_KEY=your_key`
- Local file `.streamlit/secrets.toml` (git-ignored):

  ```toml
  GROQ_API_KEY = "your_key"
  ```

## Deploying on Streamlit Community Cloud

1. Point a new app at this repo with `app.py` as the entry file.
2. Add `GROQ_API_KEY` under the app's **Settings → Secrets**.

## Data

User profiles (`data/users.json`) and uploaded files (`data/uploads/`) are git-ignored —
they are created at runtime and are not committed to the repository.
