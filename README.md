# Market-Intel

Autonomous marketing intelligence engine. Collects data from multiple sources, processes it, stores it, and generates daily intelligence reports.

## Architecture

```
market-intel/
├── collectors/          # Data sources (Reddit, RSS, Google News)
│   ├── base.py          # BaseCollector ABC — all collectors inherit this
│   ├── reddit_collector.py
│   ├── rss_collector.py
│   └── google_news_collector.py
├── processors/          # Transform collected data
│   ├── base.py          # BaseProcessor ABC
│   ├── dedup.py          # Remove duplicates
│   └── enrich.py         # Add sentiment, keywords, read time
├── storage/             # Persist data
│   ├── base.py          # BaseStorage ABC
│   └── json_store.py     # Versioned JSON file storage
├── reports/             # Generate output
│   ├── base.py          # BaseReportGenerator ABC
│   └── markdown_report.py  # Daily Markdown intelligence report
├── workflows/           # Orchestration
│   └── daily_run.py     # Ties everything together
├── core/                # Shared infrastructure
│   ├── models.py         # RawItem + ProcessedItem data models
│   ├── container.py      # Dependency injection container
│   ├── logger.py         # Structured JSON logging
│   ├── retry.py          # Exponential backoff retry decorator
│   └── config_loader.py  # YAML config loader
├── config/
│   └── loader.py
├── tests/               # Unit tests
├── data/                # Collected data (auto-generated)
├── reports/             # Generated reports (auto-generated)
└── config.yaml          # Main configuration
```

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run
python main.py

# Test
pytest tests/ -v
```

## Configuration

Edit `config.yaml` to control:
- Which collectors are enabled
- Which subreddits / RSS feeds / Google News queries to track
- Processor settings (dedup keys, enrichment options)
- Storage path and retention
- Report format and sections

## Adding a New Collector

1. Create `collectors/my_collector.py`
2. Inherit from `BaseCollector`
3. Implement `_fetch()` → return `list[RawItem]`
4. Register in `workflows/daily_run.py`

```python
from collectors.base import BaseCollector
from core.models import RawItem

class MyCollector(BaseCollector):
    name = "my_source"

    def _fetch(self) -> list[RawItem]:
        # Your logic here
        return [RawItem.create(
            source="my_source",
            source_name="My Source",
            title="...",
            url="...",
        )]
```

## Automation

GitHub Actions runs the pipeline every 6 hours. Data and reports are committed back to the repo automatically.

## Design Principles

- **Modular**: Every collector, processor, storage, and report is replaceable.
- **DI**: Components receive dependencies via constructor, never import each other directly.
- **Config-driven**: Everything controlled via `config.yaml`.
- **Stdlib-first**: Only dependency is `pyyaml`. HTTP, XML parsing, JSON storage all use stdlib.
- **Observable**: Structured JSON logging to stdout.
- **Resilient**: Retry with exponential backoff on all network calls.

## License

MIT
