import os
import pytest

os.environ["METALS_DEV_API_KEY"] = "test-api-key"
os.environ["METALS_DEV_BASE_URL"] = "https://api.metals.dev/v1"
os.environ["METAL_RATE_CACHE_TTL"] = "30"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"
