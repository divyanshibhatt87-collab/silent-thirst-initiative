# The Silent Thirst Initiative

This project is a multi-page awareness website about AI, data centers, and water use. It now includes a lightweight Python backend that:

- serves the public website
- accepts real contact form submissions
- stores submissions in `data/submissions.jsonl`
- optionally forwards those submissions to a real inbox over SMTP

## Run locally

```powershell
py app.py
```

Then open `http://127.0.0.1:4173`.

## Configure inbox forwarding

Copy `.env.example` into `.env` in your host or hosting dashboard and provide real SMTP values:

- `INBOX_EMAIL`: the destination mailbox
- `FROM_EMAIL`: sender address used by the site
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`

If these are not set, the site still stores submissions locally but does not send email.

## Public deployment

This repo is prepared for deployment on a generic Python host. The important pieces are:

- entrypoint: `app.py`
- start command: `python app.py`
- dynamic port support via the `PORT` environment variable
- deployment-friendly `Procfile`
- optional Render blueprint file: `render.yaml`

Any host that can run a Python web process and set environment variables can make this publicly accessible.

## Important note for Render free deployments

Render free web services are great for first public launches, but they have two important limitations:

- the local filesystem is ephemeral, so `data/submissions.jsonl` should not be treated as permanent storage
- outbound SMTP ports are restricted on free web services, so direct SMTP inbox forwarding is not a reliable fit there

For a beginner-friendly first launch on Render Free:

- publish the website first
- test the public URL
- then move form delivery to an HTTPS-based email/form service or a hosted database
