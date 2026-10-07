"""`CRAWLERS` mapeia o campo `crawler` de `ingest/sources.yaml` para a implementação.

Fica num módulo próprio (e não em `ingest/crawlers/__init__.py`) para que `ingest.crawl` possa
importar o cliente HTTP sem importar os crawlers, que por sua vez importam `ingest.crawl`.
"""

from ingest.crawl import Crawler
from ingest.crawlers import cebraspe

CRAWLERS: dict[str, Crawler] = {"cebraspe": cebraspe.crawler}
