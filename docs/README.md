[日本語](README.ja.md)

# Claude Code Skills

Custom skills for Claude Code to automate news aggregation and reporting.

## Skills

| Command               | Description                                                          |
| --------------------- | -------------------------------------------------------------------- |
| `/ai-news-summary`    | Collect and summarize AI news, generate PDF, post to Slack           |
| `/aws-blog-summary`   | Collect and summarize AWS blog articles, generate PDF, post to Slack |
| `/jp-it-news-summary` | Collect and summarize Japanese IT news, generate PDF, post to Slack  |
| `/report-email`       | Send email with PDF attachment                                       |

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

Configure `config/secrets.json` in each skill directory (refer to `secrets.example.json`).

## License

Private
