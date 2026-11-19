"""Reuse the production D2.5 loaders and cache the one full-field Minkowski cover."""
from functools import lru_cache
from engineering import *

field_guard=lru_cache(maxsize=2)(field_guard)
