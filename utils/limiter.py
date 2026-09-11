from flask_limiter.util import get_remote_address
from flask_limiter import Limiter

limiter = Limiter(
    key_func=get_remote_address,
    # storage_uri="redis://localhost:6379/0",
    storage_uri="memory://",
    default_limits=[],
)