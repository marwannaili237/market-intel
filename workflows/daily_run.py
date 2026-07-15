"""
Main workflow orchestrator — ties collectors, processors, storage, and reports together.

This is the entry point called by main.py and GitHub Actions.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from core.config_loader import Config
from core.container import Container
from core.logger import get_logger, setup_logging
from core.models import RawItem, ProcessedItem


class DailyRun:
    """Orchestrates a single collection + processing + storage + report run."""

    def __init__(self, config: Config):
        self._config = config
        self._logger = get_logger("workflow")
        self._container = Container(config.to_dict())
        self._run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self._setup_components()

    def _setup_components(self) -> None:
        """Register all enabled components in the container."""
        collectors_config = self._config.collectors
        retry_config = self._config.retry

        # Collectors
        from collectors.reddit_collector import RedditCollector
        from collectors.rss_collector import RSSCollector
        from collectors.google_news_collector import GoogleNewsCollector

        reddit_cfg = collectors_config.get("reddit", {})
        if reddit_cfg.get("enabled", False):
            self._container.register_collector("reddit", RedditCollector(reddit_cfg, retry_config))

        rss_cfg = collectors_config.get("rss", {})
        if rss_cfg.get("enabled", False):
            self._container.register_collector("rss", RSSCollector(rss_cfg, retry_config))

        gn_cfg = collectors_config.get("google_news", {})
        if gn_cfg.get("enabled", False):
            self._container.register_collector("google_news", GoogleNewsCollector(gn_cfg, retry_config))

        # Processors
        processors_config = self._config.processors
        from processors.dedup import DedupProcessor
        from processors.enrich import EnrichProcessor

        dedup_cfg = processors_config.get("dedup", {})
        if dedup_cfg.get("enabled", True):
            self._container.register_processor("dedup", DedupProcessor(dedup_cfg))

        enrich_cfg = processors_config.get("enrich", {})
        if enrich_cfg.get("enabled", True):
            self._container.register_processor("enrich", EnrichProcessor(enrich_cfg))

        # Storage
        storage_config = self._config.storage
        from storage.json_store import JSONStorage
        self._container.set_storage(JSONStorage(storage_config))

        # Reports
        reports_config = self._config.reports
        md_cfg = reports_config.get("markdown", {})
        if md_cfg.get("enabled", True):
            from reports.markdown_report import MarkdownReportGenerator
            self._container.set_report_generator(MarkdownReportGenerator(md_cfg))

    def run(self) -> dict:
        """Execute the full pipeline. Returns a summary dict."""
        self._logger.info(f"Starting run {self._run_id}")
        start_time = datetime.now(timezone.utc)

        # Phase 1: Collect
        self._logger.info("Phase 1: Collection")
        raw_items: list[RawItem] = []
        for name, collector in self._container.get_collectors().items():
            items = collector.collect()
            raw_items.extend(items)

        self._logger.info(f"Collection complete: {len(raw_items)} total raw items", extra={"total_raw": len(raw_items)})

        # Phase 2: Process
        self._logger.info("Phase 2: Processing")
        processed_items = [ProcessedItem.from_raw(raw) for raw in raw_items]

        for name, processor in self._container.get_processors().items():
            processed_items = processor.process(processed_items)

        self._logger.info(f"Processing complete: {len(processed_items)} processed items", extra={"total_processed": len(processed_items)})

        # Phase 3: Store
        self._logger.info("Phase 3: Storage")
        item_dicts = [item.to_dict() for item in processed_items]
        storage_path = self._container.get_storage().save(item_dicts, self._run_id)

        # Phase 4: Report
        self._logger.info("Phase 4: Report generation")
        report_path = ""
        report_gen = self._container.get_report_generator()
        if report_gen:
            report_path = report_gen.generate(processed_items, self._run_id)

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        summary = {
            "run_id": self._run_id,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": round(duration, 2),
            "raw_items_collected": len(raw_items),
            "processed_items": len(processed_items),
            "collectors_used": list(self._container.get_collectors().keys()),
            "processors_used": list(self._container.get_processors().keys()),
            "storage_path": storage_path,
            "report_path": report_path,
            "status": "success" if processed_items else "no_data",
        }

        self._logger.info(f"Run complete in {duration:.1f}s", extra=summary)
        return summary
