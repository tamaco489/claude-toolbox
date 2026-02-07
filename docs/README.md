[日本語](README.ja.md)

# Claude Code Skills

Custom skills for Claude Code to automate news aggregation and reporting.

## Skills

| Skill                | Description                                                          |
| -------------------- | -------------------------------------------------------------------- |
| `ai-news-summary`    | Collect and summarize AI news, generate PDF, post to Slack           |
| `aws-blog-summary`   | Collect and summarize AWS blog articles, generate PDF, post to Slack |
| `jp-it-news-summary` | Collect and summarize Japanese IT news, generate PDF, post to Slack  |
| `report-email`       | Send email with PDF attachment                                       |

## Setup

```bash
# Create virtual environment
python3 -m venv .venv

# Install dependencies
source .venv/bin/activate
pip install requests beautifulsoup4 feedparser reportlab fake-useragent
```

## Configuration

Create `config/secrets.json` in each skill directory:

```json
{
  "slack_token": "xoxb-...",
  "slack_channel": "#channel-name"
}
```

## Usage

Invoke skills via Claude Code:

```
/ai-news-summary
/aws-blog-summary
/jp-it-news-summary
```

## License

Private
