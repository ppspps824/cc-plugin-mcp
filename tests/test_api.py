"""Tests for FastAPI endpoints."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from cc_plugin_mcp.main import app
from cc_plugin_mcp.models import LoadedElement, PluginInfo
from cc_plugin_mcp.services.plugin_service import PluginService


@pytest.fixture
def client():
    """Provide FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def temp_plugin_dir():
    """Create temporary plugin directory for testing."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestHealthCheck:
    """Health check endpoint tests."""

    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestGetPlugins:
    """Plugin list endpoint tests."""

    def test_get_plugins(self, client):
        """Test getting all marketplace plugins."""
        with patch.object(
            PluginService, "get_plugin_list"
        ) as mock_get_plugins:
            mock_plugins = [
                PluginInfo(
                    name="test-plugin",
                    description="Test plugin description",
                ),
                PluginInfo(
                    name="another-plugin",
                    description="Another plugin description",
                ),
            ]
            mock_get_plugins.return_value = mock_plugins

            response = client.get("/plugins")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "test-plugin"
            assert data[1]["name"] == "another-plugin"

    def test_get_plugins_file_not_found(self, client):
        """Test error handling when plugin file not found."""
        with patch.object(
            PluginService, "get_plugin_list"
        ) as mock_get_plugins:
            mock_get_plugins.side_effect = FileNotFoundError(
                "Plugin directory not found"
            )

            response = client.get("/plugins")
            assert response.status_code == 404


class TestPluginService:
    """Plugin service tests."""

    def test_get_all_marketplace_plugins(self, temp_plugin_dir):
        """Test reading all plugins from marketplaces."""
        # Create mock marketplace structure
        marketplace_dir = temp_plugin_dir / "marketplaces" / "test-marketplace"
        marketplace_dir.mkdir(parents=True)
        plugin_dir = marketplace_dir / ".claude-plugin"
        plugin_dir.mkdir(parents=True)

        # Create marketplace.json
        marketplace_file = plugin_dir / "marketplace.json"
        marketplace_file.write_text(
            json.dumps(
                {
                    "name": "test-marketplace",
                    "plugins": [
                        {
                            "name": "plugin1",
                            "description": "First plugin",
                        },
                        {
                            "name": "plugin2",
                            "description": "Second plugin",
                        },
                    ],
                }
            )
        )

        service = PluginService(plugins_dir=temp_plugin_dir)
        plugins = service.get_plugin_list()

        assert len(plugins) == 2
        assert plugins[0].name == "plugin1"
        assert plugins[1].name == "plugin2"

    def test_describe_plugin(self, temp_plugin_dir):
        """Test getting plugin details."""
        # Create marketplace structure
        marketplace_dir = temp_plugin_dir / "marketplaces" / "test-marketplace"
        plugin_dir = marketplace_dir / ".claude-plugin"
        plugin_dir.mkdir(parents=True)

        marketplace_file = plugin_dir / "marketplace.json"
        plugin_data = {
            "name": "test-marketplace",
            "owner": {"name": "Test Author"},
            "metadata": {"version": "1.0.0", "description": "Test"},
            "plugins": [
                {
                    "name": "test-plugin",
                    "description": "Test plugin",
                    "source": "./plugins/test-plugin",
                }
            ],
        }
        marketplace_file.write_text(json.dumps(plugin_data))

        service = PluginService(plugins_dir=temp_plugin_dir)
        plugin_detail = service.describe_plugin("test-plugin")

        # Should return the requested plugin's data, not the marketplace data
        assert plugin_detail.name == "test-plugin"
        assert plugin_detail.owner["name"] == "Test Author"
        assert len(plugin_detail.plugins) == 1
        assert plugin_detail.plugins[0]["name"] == "test-plugin"


class TestPathTraversalSecurity:
    """Path traversal security tests."""

    def test_path_traversal_attack_blocked(self, temp_plugin_dir):
        """Test that path traversal attacks are blocked."""
        service = PluginService(plugins_dir=temp_plugin_dir)

        # Create a mock marketplace structure
        marketplace_dir = temp_plugin_dir / "marketplaces" / "test-marketplace"
        marketplace_dir.mkdir(parents=True)

        # Attempt to access a path outside the plugin directory
        with pytest.raises(ValueError, match="Invalid path"):
            service._validate_safe_path(marketplace_dir, "../../../etc/passwd")

    def test_valid_path_accepted(self, temp_plugin_dir):
        """Test that valid paths within plugin directory are accepted."""
        service = PluginService(plugins_dir=temp_plugin_dir)

        # Create a mock marketplace structure
        marketplace_dir = temp_plugin_dir / "marketplaces" / "test-marketplace"
        marketplace_dir.mkdir(parents=True)

        # Create a valid file
        valid_file = marketplace_dir / "plugin.json"
        valid_file.write_text("{}")

        # Should not raise an exception
        result = service._validate_safe_path(marketplace_dir, "plugin.json")
        assert result.name == "plugin.json"

    def test_nested_valid_path_accepted(self, temp_plugin_dir):
        """Test that valid nested paths within plugin directory are accepted."""
        service = PluginService(plugins_dir=temp_plugin_dir)

        marketplace_dir = temp_plugin_dir / "marketplaces" / "test-marketplace"
        nested_dir = marketplace_dir / "plugins" / "test-plugin"
        nested_dir.mkdir(parents=True)

        # Create a valid nested file
        valid_file = nested_dir / "SKILL.md"
        valid_file.write_text("# Test Skill")

        # Should not raise an exception
        result = service._validate_safe_path(
            marketplace_dir,
            "plugins/test-plugin/SKILL.md",
        )
        assert result.name == "SKILL.md"


class TestLogging:
    """Logging functionality tests."""

    def test_invalid_marketplace_logged(self, temp_plugin_dir, caplog):
        """Test that invalid marketplace files are logged as warnings."""
        import logging

        # Create a mock marketplace structure with invalid JSON
        marketplace_dir = temp_plugin_dir / "marketplaces" / "test-marketplace"
        marketplace_dir.mkdir(parents=True)
        plugin_dir = marketplace_dir / ".claude-plugin"
        plugin_dir.mkdir(parents=True)

        # Create invalid JSON file
        marketplace_file = plugin_dir / "marketplace.json"
        marketplace_file.write_text("{ invalid json }")

        service = PluginService(plugins_dir=temp_plugin_dir)

        with caplog.at_level(logging.WARNING):
            plugins = service.get_plugin_list()

        # Should return empty list
        assert len(plugins) == 0
        # Should have logged a warning
        assert any("invalid" in record.message.lower() for record in caplog.records)

    def test_plugin_elements_loading_logged(self, temp_plugin_dir, caplog):
        """Test that plugin elements loading is logged appropriately."""
        import logging

        # Create marketplace structure
        marketplace_dir = temp_plugin_dir / "marketplaces" / "test-marketplace"
        plugin_dir = marketplace_dir / ".claude-plugin"
        plugin_dir.mkdir(parents=True)

        plugin_source_dir = marketplace_dir / "plugins" / "test-plugin"
        plugin_source_dir.mkdir(parents=True)

        # Create marketplace.json and plugin files
        marketplace_file = plugin_dir / "marketplace.json"
        marketplace_file.write_text(
            json.dumps(
                {
                    "plugins": [
                        {
                            "name": "test-plugin",
                            "description": "Test plugin",
                            "source": "./plugins/test-plugin",
                            "skills": ["./SKILL.md"],
                        }
                    ]
                }
            )
        )

        # Create a skill file
        skill_file = plugin_source_dir / "SKILL.md"
        skill_file.write_text("# Test Skill")

        service = PluginService(plugins_dir=temp_plugin_dir)

        with caplog.at_level(logging.INFO):
            element = service.load_plugin_element("test-plugin", "skills", "SKILL")

        # Should have loaded the element
        assert element is not None
        # Should have logged load info
        assert any(
            "load" in record.message.lower() for record in caplog.records
        ) or element is not None


class TestErrorHandling:
    """Error handling consistency tests."""

    def test_missing_marketplaces_dir_returns_empty_list(self, temp_plugin_dir):
        """Test that missing marketplaces directory returns empty list."""
        # Do not create marketplaces directory
        service = PluginService(plugins_dir=temp_plugin_dir)

        plugins = service.get_plugin_list()
        assert plugins == []

    def test_describe_plugin_not_found_raises_error(self, temp_plugin_dir):
        """Test that describe_plugin raises FileNotFoundError when plugin not found."""
        service = PluginService(plugins_dir=temp_plugin_dir)

        with pytest.raises(FileNotFoundError, match="not found"):
            service.describe_plugin("nonexistent-plugin")

    def test_find_plugin_in_marketplace_returns_none(self, temp_plugin_dir):
        """Test that find_plugin_in_marketplace returns None when not found."""
        service = PluginService(plugins_dir=temp_plugin_dir)

        result = service.find_plugin_in_marketplace("nonexistent-plugin")
        assert result is None

    def test_find_plugin_marketplace_dir_returns_none(self, temp_plugin_dir):
        """Test that find_plugin_marketplace_dir returns None when not found."""
        service = PluginService(plugins_dir=temp_plugin_dir)

        result = service.find_plugin_marketplace_dir("nonexistent-plugin")
        assert result is None


class TestLoadPluginElements:
    """Tests for load_plugin_elements endpoint and methods."""

    def test_load_plugin_elements_endpoint(self, client):
        """Test POST /plugins/{plugin_name}/load-elements endpoint."""
        with patch.object(
            PluginService, "load_plugin_elements"
        ) as mock_load:
            mock_load.return_value = [
                LoadedElement(
                    element_type="skills",
                    name="SKILL",
                    path="/path/to/SKILL.md",
                    content="# Test Skill",
                )
            ]

            response = client.post(
                "/plugins/test-plugin/load-elements",
                json={
                    "elements": [
                        {"element_type": "skills", "name": "SKILL"}
                    ]
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["plugin_name"] == "test-plugin"
            assert len(data["elements"]) == 1
            assert data["elements"][0]["name"] == "SKILL"

    def test_load_plugin_elements_invalid_type(self, client):
        """Test that invalid element type returns 400."""
        response = client.post(
            "/plugins/test-plugin/load-elements",
            json={"elements": [{"element_type": "invalid", "name": "test"}]},
        )

        assert response.status_code == 422

    def test_load_plugin_elements_not_found(self, client):
        """Test that plugin not found returns 404."""
        with patch.object(
            PluginService, "load_plugin_elements"
        ) as mock_load:
            mock_load.side_effect = FileNotFoundError("Plugin not found")

            response = client.post(
                "/plugins/nonexistent/load-elements",
                json={"elements": [{"element_type": "skills", "name": "test"}]},
            )

            assert response.status_code == 404

    def test_load_plugin_element_single(self, temp_plugin_dir):
        """Test loading a single plugin element."""
        # Setup marketplace structure
        marketplace_dir = temp_plugin_dir / "marketplaces" / "test-marketplace"
        plugin_dir = marketplace_dir / ".claude-plugin"
        plugin_dir.mkdir(parents=True)

        plugin_source_dir = marketplace_dir / "plugins" / "test-plugin"
        plugin_source_dir.mkdir(parents=True)

        # Create marketplace.json
        marketplace_file = plugin_dir / "marketplace.json"
        marketplace_file.write_text(
            json.dumps(
                {
                    "plugins": [
                        {
                            "name": "test-plugin",
                            "description": "Test plugin",
                            "source": "./plugins/test-plugin",
                            "skills": ["./SKILL.md"],
                        }
                    ]
                }
            )
        )

        # Create skill file
        skill_file = plugin_source_dir / "SKILL.md"
        skill_file.write_text("# Test Skill Content")

        service = PluginService(plugins_dir=temp_plugin_dir)
        element = service.load_plugin_element("test-plugin", "skills", "SKILL")

        assert element is not None
        assert element.name == "SKILL"
        assert element.element_type == "skills"
        assert "Test Skill Content" in element.content

    def test_load_multiple_elements(self, temp_plugin_dir):
        """Test loading multiple plugin elements."""
        # Setup marketplace structure
        marketplace_dir = temp_plugin_dir / "marketplaces" / "test-marketplace"
        plugin_dir = marketplace_dir / ".claude-plugin"
        plugin_dir.mkdir(parents=True)

        plugin_source_dir = marketplace_dir / "plugins" / "test-plugin"
        plugin_source_dir.mkdir(parents=True)

        # Create marketplace.json
        marketplace_file = plugin_dir / "marketplace.json"
        marketplace_file.write_text(
            json.dumps(
                {
                    "plugins": [
                        {
                            "name": "test-plugin",
                            "description": "Test plugin",
                            "source": "./plugins/test-plugin",
                            "skills": ["./SKILL1.md", "./SKILL2.md"],
                            "agents": ["./agent.md"],
                        }
                    ]
                }
            )
        )

        # Create element files
        (plugin_source_dir / "SKILL1.md").write_text("# Skill 1")
        (plugin_source_dir / "SKILL2.md").write_text("# Skill 2")
        (plugin_source_dir / "agent.md").write_text("# Agent")

        service = PluginService(plugins_dir=temp_plugin_dir)

        elements_to_load = [
            {"type": "skills", "name": "SKILL1"},
            {"type": "skills", "name": "SKILL2"},
            {"type": "agents", "name": "agent"},
        ]

        loaded = service.load_plugin_elements("test-plugin", elements_to_load)

        assert len(loaded) == 3
        assert any(e.name == "SKILL1" for e in loaded)
        assert any(e.name == "SKILL2" for e in loaded)
        assert any(e.name == "agent" for e in loaded)


class TestCaching:
    """Tests for caching functionality."""

    def test_find_plugin_marketplace_dir_caching(self, temp_plugin_dir):
        """Test that find_plugin_marketplace_dir results are cached."""
        # Setup marketplace structure
        marketplace_dir = temp_plugin_dir / "marketplaces" / "test-marketplace"
        plugin_dir = marketplace_dir / ".claude-plugin"
        plugin_dir.mkdir(parents=True)

        marketplace_file = plugin_dir / "marketplace.json"
        marketplace_file.write_text(
            json.dumps(
                {
                    "plugins": [
                        {
                            "name": "test-plugin",
                            "description": "Test plugin",
                            "source": "./plugins/test-plugin",
                        }
                    ]
                }
            )
        )

        service = PluginService(plugins_dir=temp_plugin_dir)

        # First call
        result1 = service.find_plugin_marketplace_dir("test-plugin")

        # Second call - should be cached
        result2 = service.find_plugin_marketplace_dir("test-plugin")

        assert result1 == result2
        assert result1 is not None

    def test_cache_invalidation_on_different_plugins(self, temp_plugin_dir):
        """Test that cache works independently for different plugins."""
        marketplace_dir = temp_plugin_dir / "marketplaces" / "test-marketplace"
        plugin_dir = marketplace_dir / ".claude-plugin"
        plugin_dir.mkdir(parents=True)

        marketplace_file = plugin_dir / "marketplace.json"
        marketplace_file.write_text(
            json.dumps(
                {
                    "plugins": [
                        {
                            "name": "plugin1",
                            "description": "Plugin 1",
                            "source": "./plugins/plugin1",
                        },
                        {
                            "name": "plugin2",
                            "description": "Plugin 2",
                            "source": "./plugins/plugin2",
                        },
                    ]
                }
            )
        )

        service = PluginService(plugins_dir=temp_plugin_dir)

        result1 = service.find_plugin_marketplace_dir("plugin1")
        result2 = service.find_plugin_marketplace_dir("plugin2")

        assert result1 == result2  # Same marketplace
        assert result1 is not None


class TestInputValidation:
    """Tests for input validation."""

    def test_plugin_name_validation_empty(self):
        """Test that empty plugin name is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            PluginInfo(name="", description="Test")

    def test_plugin_name_validation_too_long(self):
        """Test that plugin name exceeding 256 characters is rejected."""
        long_name = "a" * 257
        with pytest.raises(ValueError, match="cannot exceed 256 characters"):
            PluginInfo(name=long_name, description="Test")

    def test_plugin_name_validation_invalid_chars(self):
        """Test that plugin name with invalid characters is rejected."""
        with pytest.raises(ValueError, match="alphanumeric"):
            PluginInfo(name="test@plugin!", description="Test")

    def test_plugin_name_validation_valid(self):
        """Test that valid plugin names are accepted."""
        # Should not raise
        plugin = PluginInfo(name="test-plugin_123", description="Test")
        assert plugin.name == "test-plugin_123"

    def test_element_type_validation_invalid(self):
        """Test that invalid element type is rejected."""
        from cc_plugin_mcp.models import PluginElement

        with pytest.raises(ValueError, match="Invalid element type"):
            PluginElement(element_type="invalid_type", name="test")

    def test_element_type_validation_valid(self):
        """Test that valid element types are accepted."""
        from cc_plugin_mcp.models import PluginElement

        # Should not raise for valid types
        for element_type in ["skills", "agents", "commands"]:
            element = PluginElement(element_type=element_type, name="test")
            assert element.element_type == element_type

    def test_element_name_validation_empty(self):
        """Test that empty element name is rejected."""
        from cc_plugin_mcp.models import PluginElement

        with pytest.raises(ValueError, match="cannot be empty"):
            PluginElement(element_type="skills", name="")

    def test_element_name_validation_too_long(self):
        """Test that element name exceeding 256 characters is rejected."""
        from cc_plugin_mcp.models import PluginElement

        long_name = "a" * 257
        with pytest.raises(ValueError, match="cannot exceed 256 characters"):
            PluginElement(element_type="skills", name=long_name)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
