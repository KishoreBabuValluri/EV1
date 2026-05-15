"""
Gunicorn production config.
Run with: gunicorn -c gunicorn.conf.py "app:create_app('production')"

gthread worker class is required for SSE (long-lived streaming connections).
Each worker handles up to `threads` concurrent SSE clients.
"""
import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"        # Required for SSE — sync would block
threads = 4                     # Concurrent SSE streams per worker
bind = "0.0.0.0:5000"
timeout = 120
keepalive = 65                  # Must be > Razorpay/SSE keepalive interval (25s)
accesslog = "-"
errorlog = "-"
loglevel = "warning"
preload_app = True
