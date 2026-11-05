"""One process keeps the public geocoder throttle and cache shared across threads."""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
workers = 1
threads = 8
timeout = 120
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
