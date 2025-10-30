"""FastAPI application for Claude Code Plugin MCP."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from fastmcp.server.openapi import MCPType, RouteMap

from cc_plugin_mcp.models import (
    LoadedElementsResponse,
    PluginElementRequest,
    PluginInfo,
)
from cc_plugin_mcp.services.plugin_service import PluginService

# Initialize FastAPI app
app = FastAPI(
    title="Claude Code Plugin MCP",
    description="Access Claude Code plugins via REST API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Initialize plugin service
plugin_service = PluginService()


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/plugins", operation_id="list_plugins")
async def get_plugins() -> list[PluginInfo]:
    """Get list of all available plugins from marketplaces.

    Returns:
        List of plugins with name, description, and categorized elements
        (agents, commands, skills).

    Raises:
        HTTPException: If plugins cannot be read.

    """
    try:
        plugins = plugin_service.get_plugin_list()
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin directory not found: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading plugins: {e!s}",
        ) from e
    else:
        return plugins


@app.post("/plugins/{plugin_name}/load-elements", operation_id="load_elements")
async def load_plugin_elements_endpoint(
    plugin_name: str,
    request: PluginElementRequest,
) -> LoadedElementsResponse:
    """Load plugin elements (skills, agents, commands) with their content.

    Args:
        plugin_name: Name of the plugin.
        request: Request body with elements to load.

    Returns:
        Response with loaded element contents.

    Raises:
        HTTPException: If plugin is not found or elements cannot be read.

    """
    try:
        # Convert PluginElement objects to dicts
        elements_data = [
            {
                "type": element.element_type,
                "name": element.name,
            }
            for element in request.elements
        ]

        loaded_elements = plugin_service.load_plugin_elements(
            plugin_name,
            elements_data,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid element type: {e!s}",
        ) from e
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin not found: {plugin_name}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading plugin elements: {e!s}",
        ) from e
    else:
        return LoadedElementsResponse(
            plugin_name=plugin_name,
            elements=loaded_elements,
        )


@app.exception_handler(ValueError)
async def value_error_handler(
    _request: Request,
    exc: ValueError,
) -> JSONResponse:
    """Handle ValueError exceptions."""
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid request", "detail": str(exc)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# Configure route maps to exclude health check endpoint
route_maps = [
    # Exclude health check endpoint - it's not an MCP tool
    RouteMap(pattern=r"^/health$", mcp_type=MCPType.EXCLUDE),
]

# Initialize FastMCP with custom route mappings
# Server name is shortened to "cc-plugin-mcp"
# Tools are named via operation_id: "list" and "load"
mcp = FastMCP.from_fastapi(
    app=app,
    name="cc-plugin-mcp",
    route_maps=route_maps,
)


def main() -> None:
    """Entry point for MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
