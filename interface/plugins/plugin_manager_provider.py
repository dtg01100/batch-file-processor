"""Shared plugin manager provider.

Provides a single lazily initialized plugin manager instance for callers that
do not receive one through dependency injection.
"""

from functools import lru_cache

from interface.plugins.plugin_manager import PluginManager


@lru_cache(maxsize=1)
def get_shared_plugin_manager() -> PluginManager:
    """Return a shared, initialized plugin manager instance."""
    manager = PluginManager()
    manager.discover_plugins()
    manager.initialize_plugins()
    return manager
