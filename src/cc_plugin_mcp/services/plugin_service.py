"""Plugin service for reading and processing plugin data."""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from cc_plugin_mcp.models import LoadedElement, PluginDetail, PluginInfo

logger = logging.getLogger(__name__)


class PluginService:
    """Service for managing plugin data."""

    def __init__(self, plugins_dir: Path | None = None) -> None:
        """Initialize the plugin service.

        Args:
            plugins_dir: Path to ~/.claude/plugins directory. If None, uses default.

        """
        if plugins_dir is None:
            plugins_dir = Path.home() / ".claude" / "plugins"
        self.plugins_dir = plugins_dir
        self.marketplaces_dir = self.plugins_dir / "marketplaces"
        # Initialize cache
        self._marketplace_cache = {}

    def _validate_safe_path(self, base_dir: Path, relative_path: str) -> Path:
        """Validate that a path is safe and within the base directory.

        Args:
            base_dir: The base directory to validate against.
            relative_path: The relative path to validate.

        Returns:
            The resolved path if valid.

        Raises:
            ValueError: If path is outside the base directory (path traversal attempt).

        """
        base_dir_resolved = base_dir.resolve()
        full_path = (base_dir / relative_path).resolve()

        # Check that the resolved path is within the base directory
        try:
            full_path.relative_to(base_dir_resolved)
        except ValueError as e:
            msg = f"Invalid path: {relative_path} attempts to access outside {base_dir}"
            raise ValueError(msg) from e

        return full_path

    def get_plugin_list(self) -> list[PluginInfo]:
        """Get list of all available plugins from all marketplaces.

        Returns:
            List of PluginInfo objects with categorized elements.

        Raises:
            FileNotFoundError: If required plugin files are not found.
            json.JSONDecodeError: If plugin files have invalid JSON.

        """
        return self._get_all_marketplace_plugins()

    def _get_all_marketplace_plugins(self) -> list[PluginInfo]:
        """Get all plugins from all marketplaces with categorized elements.

        Returns:
            List of PluginInfo objects from all marketplaces.

        """
        if not self.marketplaces_dir.exists():
            logger.debug(f"Marketplaces directory not found: {self.marketplaces_dir}")
            return []

        plugins: list[PluginInfo] = []

        # Iterate through all marketplace directories
        for marketplace_dir in self.marketplaces_dir.iterdir():
            if not marketplace_dir.is_dir():
                continue

            marketplace_path = marketplace_dir / ".claude-plugin" / "marketplace.json"
            if not marketplace_path.exists():
                continue

            try:
                with marketplace_path.open() as f:
                    marketplace_data = json.load(f)

                # Extract plugins from marketplace.json
                marketplace_plugins = marketplace_data.get("plugins", [])
                for plugin in marketplace_plugins:
                    # Extract elements from plugin definition
                    agents = self._extract_element_names(plugin.get("agents", []))
                    commands = self._extract_element_names(
                        plugin.get("commands", []),
                    )
                    skills = self._extract_element_names(plugin.get("skills", []))

                    plugin_info_obj = PluginInfo(
                        name=plugin.get("name", ""),
                        description=plugin.get("description", ""),
                        agents=agents,
                        commands=commands,
                        skills=skills,
                    )
                    plugins.append(plugin_info_obj)
            except (OSError, json.JSONDecodeError) as e:
                # Skip invalid marketplace files
                logger.warning(
                    f"Skipping invalid marketplace file {marketplace_path}: {e!s}",
                )
                continue

        return plugins

    def _extract_element_names(self, elements: list[Any]) -> list[str]:
        """Extract element names from plugin definition.

        Args:
            elements: List of element paths or definitions.

        Returns:
            List of extracted element names.

        """
        names = []
        for element in elements:
            if isinstance(element, str):
                # Extract filename without extension from path
                path = Path(element)
                name = path.stem
                names.append(name)
            elif isinstance(element, dict):
                # If it's a dict, try to get name field
                if "name" in element:
                    names.append(element["name"])
        return names

    def describe_plugin(self, plugin_name: str) -> PluginDetail:
        """Get detailed information about a specific plugin.

        Args:
            plugin_name: Name of the plugin to describe.

        Returns:
            PluginDetail object with full plugin information.

        Raises:
            FileNotFoundError: If plugin is not found in any marketplace.
            json.JSONDecodeError: If plugin JSON is invalid.

        """
        if not self.marketplaces_dir.exists():
            msg = f"Marketplaces directory not found: {self.marketplaces_dir}"
            raise FileNotFoundError(msg)

        # Search through all marketplace directories
        for marketplace_dir in self.marketplaces_dir.iterdir():
            if not marketplace_dir.is_dir():
                continue

            marketplace_path = marketplace_dir / ".claude-plugin" / "marketplace.json"
            if not marketplace_path.exists():
                continue

            try:
                with marketplace_path.open() as f:
                    marketplace_data = json.load(f)

                # Check if this plugin exists in this marketplace
                marketplace_plugins = marketplace_data.get("plugins", [])
                for plugin in marketplace_plugins:
                    if plugin.get("name") == plugin_name:
                        # Found the plugin, return only this plugin's data
                        return PluginDetail(
                            name=plugin.get("name", ""),
                            owner=marketplace_data.get("owner"),
                            metadata=plugin.get("metadata")
                            or marketplace_data.get("metadata"),
                            plugins=[plugin],
                        )
            except (OSError, json.JSONDecodeError):
                # Skip invalid marketplace files
                continue

        # Plugin not found in any marketplace
        msg = f"Plugin '{plugin_name}' not found in any marketplace"
        raise FileNotFoundError(msg)

    def find_plugin_in_marketplace(
        self,
        plugin_name: str,
    ) -> dict[str, Any] | None:
        """Find plugin definition within a marketplace's plugins list.

        Args:
            plugin_name: Name of the plugin to find.

        Returns:
            Plugin definition dict or None if not found.

        """
        try:
            plugin_detail = self.describe_plugin(plugin_name)
            plugins = plugin_detail.plugins

            for plugin in plugins:
                if plugin.get("name") == plugin_name:
                    return plugin

            return None
        except FileNotFoundError:
            return None

    @staticmethod
    @lru_cache(maxsize=128)
    def _find_plugin_marketplace_dir_cached(
        marketplaces_dir: str,
        plugin_name: str,
    ) -> str | None:
        """Cached version of find_plugin_marketplace_dir.

        Args:
            marketplaces_dir: String representation of marketplaces directory.
            plugin_name: Name of the plugin to find.

        Returns:
            String path to the plugin's marketplace directory, or None if not found.

        """
        marketplaces_path = Path(marketplaces_dir)
        if not marketplaces_path.exists():
            return None

        for marketplace_dir in marketplaces_path.iterdir():
            if not marketplace_dir.is_dir():
                continue

            marketplace_path = marketplace_dir / ".claude-plugin" / "marketplace.json"
            if not marketplace_path.exists():
                continue

            try:
                with marketplace_path.open() as f:
                    marketplace_data = json.load(f)

                marketplace_plugins = marketplace_data.get("plugins", [])
                for plugin in marketplace_plugins:
                    if plugin.get("name") == plugin_name:
                        return str(marketplace_dir)
            except (OSError, json.JSONDecodeError):
                continue

        return None

    def find_plugin_marketplace_dir(self, plugin_name: str) -> Path | None:
        """Find the marketplace directory for a specific plugin.

        Args:
            plugin_name: Name of the plugin to find.

        Returns:
            Path to the plugin's marketplace directory, or None if not found.

        """
        # Use cached method for lookups
        result_str = self._find_plugin_marketplace_dir_cached(
            str(self.marketplaces_dir),
            plugin_name,
        )

        if result_str is None:
            logger.debug(f"Plugin '{plugin_name}' marketplace directory not found")
            return None

        logger.debug(
            f"Found plugin '{plugin_name}' marketplace directory (cached)",
        )
        return Path(result_str)

    def _resolve_element_path(
        self,
        marketplace_dir: Path,
        plugin_source: str,
        element_type: str,
        element_path: str,
        element_name: str,
    ) -> Path | None:
        """Resolve the full path to an element file.

        Args:
            marketplace_dir: The marketplace directory.
            plugin_source: The source directory of the plugin (relative path).
            element_type: Type of element ('skills', 'agents', 'commands').
            element_path: The path from plugin definition.
            element_name: The name of the element.

        Returns:
            Full path to the element file, or None if not found.

        """
        path_obj = Path(element_path)
        name = path_obj.stem

        if element_name not in (name, element_path):
            return None

        # Resolve path relative to plugin source directory with security validation
        try:
            plugin_base_dir = marketplace_dir / plugin_source
            full_path = self._validate_safe_path(plugin_base_dir, element_path)
        except ValueError:
            # Path is outside the plugin directory
            return None

        if element_type == "skills":
            # For skills, the path might be a directory containing SKILL.md
            if full_path.is_dir():
                skill_file = full_path / "SKILL.md"
                if skill_file.exists() and skill_file.is_file():
                    return skill_file
            elif full_path.exists() and full_path.is_file():
                # If it's already a file, use it
                return full_path

        # For agents and commands, use the provided path directly
        elif full_path.exists() and full_path.is_file():
            return full_path

        return None

    def load_plugin_element(
        self,
        plugin_name: str,
        element_type: str,
        element_name: str,
    ) -> LoadedElement | None:
        """Load content of a plugin element (skill, command, or agent).

        Args:
            plugin_name: Name of the plugin.
            element_type: Type of element ('skills', 'agents', 'commands').
            element_name: Name of the element to load.

        Returns:
            LoadedElement object with content, or None if not found.

        Raises:
            ValueError: If element_type is invalid.

        """
        valid_types = {"skills", "agents", "commands"}
        if element_type not in valid_types:
            msg = f"Invalid element_type '{element_type}'. Must be one of {valid_types}"
            logger.error(msg)
            raise ValueError(msg)

        # Find the plugin's marketplace directory
        marketplace_dir = self.find_plugin_marketplace_dir(plugin_name)
        if not marketplace_dir:
            return None

        # Get plugin definition
        plugin_def = self.find_plugin_in_marketplace(plugin_name)
        if not plugin_def:
            return None

        # Get the plugin source directory
        plugin_source = plugin_def.get("source", "")
        if not plugin_source:
            return None

        # Get the element paths from the plugin definition
        element_paths = plugin_def.get(element_type, [])
        if not element_paths:
            return None

        # Find the specific element
        for element_path in element_paths:
            if not isinstance(element_path, str):
                continue

            full_path = self._resolve_element_path(
                marketplace_dir,
                plugin_source,
                element_type,
                element_path,
                element_name,
            )

            if full_path:
                try:
                    with full_path.open() as f:
                        content = f.read()
                    logger.info(
                        f"Loaded {element_type} element '{element_name}' "
                        f"from plugin '{plugin_name}'",
                    )
                    return LoadedElement(
                        element_type=element_type,
                        name=element_name,
                        path=str(full_path),
                        content=content,
                    )
                except OSError as e:
                    logger.warning(
                        f"Failed to read element file {full_path}: {e!s}",
                    )
                    return None

        logger.debug(
            f"Element '{element_name}' of type '{element_type}' "
            f"not found in plugin '{plugin_name}'",
        )
        return None

    def load_plugin_elements(
        self,
        plugin_name: str,
        elements: list[dict[str, Any]],
    ) -> list[LoadedElement]:
        """Load multiple plugin elements.

        Args:
            plugin_name: Name of the plugin.
            elements: List of dicts with 'type' and 'name' keys.
                     Example: [{"type": "skills", "name": "skill1"}, ...]

        Returns:
            List of loaded elements.

        """
        loaded = []
        for element in elements:
            element_type = element.get("type") or element.get("element_type")
            element_name = element.get("name")

            if not element_type or not element_name:
                continue

            loaded_element = self.load_plugin_element(
                plugin_name,
                element_type,
                element_name,
            )
            if loaded_element:
                loaded.append(loaded_element)

        return loaded
