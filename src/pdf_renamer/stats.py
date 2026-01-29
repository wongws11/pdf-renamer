"""
Statistics tracking for PDF processing
"""


class ProcessingStats:
    """Track processing statistics"""

    def __init__(self):
        self.processed = 0
        self.failed = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.skipped = 0

    def __str__(self) -> str:
        total = self.processed + self.failed + self.skipped
        hit_rate = (
            (self.cache_hits / (self.cache_hits + self.cache_misses) * 100)
            if (self.cache_hits + self.cache_misses) > 0
            else 0
        )

        return f"""
SUMMARY
{'='*70}
Total processed: {self.processed}/{total}
Failed: {self.failed}/{total}
Skipped: {self.skipped}/{total}

Cache Statistics:
  Cache hits: {self.cache_hits} (reused previous analysis)
  Cache misses: {self.cache_misses} (new LLM analysis)
  Hit rate: {hit_rate:.1f}%
"""
