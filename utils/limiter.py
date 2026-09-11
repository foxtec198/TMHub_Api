from os import getenv
from flask_limiter.util import get_remote_address
from flask_limiter import Limiter

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=getenv("RATELIMIT_STORAGE_URI", "memory://"),
    default_limits=[],
)
