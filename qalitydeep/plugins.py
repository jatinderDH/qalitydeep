"""Plugin system for QAlityDeep — discover and load custom metrics, storage backends, etc."""
from __future__ import annotations

from typing import Any, Dict, List, Type

from rich.console import Console
from rich.table import Table

console = Console()

# Plugin group names for entry points
PLUGIN_GROUPS = {
    "qalitydeep.metrics": "Custom evaluation metrics",
    "qalitydeep.storage": "Storage backends",
    "qalitydeep.providers": "LLM providers",
    "qalitydeep.reports": "Report formats",
    "qalitydeep.notifications": "Notification channels",
}


def discover_plugins(group: str) -> Dict[str, Any]:
    """Discover plugins registered under *group* via Python entry points.

    Returns a dict of {name: loaded_class_or_object}.
    """
    try:
        from importlib.metadata import entry_points
    except ImportError:
        from importlib_metadata import entry_points  # Python < 3.9 fallback

    eps = entry_points()
    # Handle both Python 3.9+ (SelectableGroups) and 3.12+ (direct dict)
    if hasattr(eps, "select"):
        group_eps = eps.select(group=group)
    elif isinstance(eps, dict):
        group_eps = eps.get(group, [])
    else:
        group_eps = [ep for ep in eps if ep.group == group]

    plugins: Dict[str, Any] = {}
    for ep in group_eps:
        try:
            plugins[ep.name] = ep.load()
        except Exception as exc:
            console.print(f"[yellow]Warning:[/yellow] Failed to load plugin '{ep.name}': {exc}")

    return plugins


def discover_metric_plugins() -> Dict[str, Type]:
    """Discover and return custom metrics from installed packages."""
    return discover_plugins("qalitydeep.metrics")


def register_discovered_metrics() -> int:
    """Auto-register all discovered metric plugins into the METRIC_REGISTRY.

    Returns the count of newly registered metrics.
    """
    from .metrics import METRIC_REGISTRY, register_metric

    plugins = discover_metric_plugins()
    count = 0
    for name, cls in plugins.items():
        if name not in METRIC_REGISTRY:
            register_metric(name, cls)
            count += 1
    return count


def load_custom_metric(spec: str) -> Type:
    """Load a custom metric from a dotted module path.

    Supports the "custom:module.path.ClassName" syntax used in YAML configs.

    Examples:
        "custom:my_package.metrics.BrandSafetyMetric"
        "custom:validators.JsonSchemaMetric"
    """
    # Strip "custom:" prefix if present
    if spec.startswith("custom:"):
        spec = spec[7:]

    parts = spec.rsplit(".", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid custom metric spec '{spec}'. "
            f"Expected format: 'module.path.ClassName' or 'custom:module.path.ClassName'."
        )

    module_path, class_name = parts

    import importlib
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ImportError(
            f"Cannot import module '{module_path}' for custom metric. "
            f"Make sure the package is installed."
        ) from exc

    cls = getattr(module, class_name, None)
    if cls is None:
        raise AttributeError(
            f"Module '{module_path}' has no class '{class_name}'."
        )

    return cls


def list_plugins_table() -> None:
    """Print a Rich table of all discovered plugins."""
    table = Table(
        title="Installed Plugins",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Group", style="bold")
    table.add_column("Name")
    table.add_column("Source")

    total = 0
    for group, description in PLUGIN_GROUPS.items():
        plugins = discover_plugins(group)
        if plugins:
            for name, cls in plugins.items():
                module = getattr(cls, "__module__", "unknown")
                table.add_row(description, name, module)
                total += 1

    if total == 0:
        console.print("[dim]No plugins installed.[/dim]")
        console.print(
            "\nTo create a plugin, add an entry point to your package's pyproject.toml:\n"
            '  [project.entry-points."qalitydeep.metrics"]\n'
            '  my_metric = "my_package:MyMetricClass"\n'
        )
    else:
        console.print(table)
