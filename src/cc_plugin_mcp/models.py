"""Pydantic models for plugin data."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PluginInfo(BaseModel):
    """Basic plugin information."""

    name: str = Field(..., description="プラグイン名")
    description: str = Field(..., description="プラグイン説明")
    agents: list[str] = Field(default_factory=list, description="エージェントのリスト")
    commands: list[str] = Field(default_factory=list, description="コマンドのリスト")
    skills: list[str] = Field(default_factory=list, description="スキルのリスト")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate plugin name format."""
        if not v:
            raise ValueError("Plugin name cannot be empty")
        if len(v) > 256:
            raise ValueError("Plugin name cannot exceed 256 characters")
        # Allow alphanumeric, hyphens, underscores
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError(
                "Plugin name can only contain alphanumeric characters, "
                "hyphens, and underscores",
            )
        return v


class PluginElement(BaseModel):
    """Element of a plugin to load (e.g., skill, command, agent)."""

    element_type: str = Field(..., description="要素のタイプ: skills, agents, commands")
    name: str = Field(..., description="要素の名前")

    @field_validator("element_type")
    @classmethod
    def validate_element_type(cls, v: str) -> str:
        """Validate element type."""
        valid_types = {"skills", "agents", "commands"}
        if v not in valid_types:
            raise ValueError(
                f"Invalid element type '{v}'. Must be one of {valid_types}",
            )
        return v

    @field_validator("name")
    @classmethod
    def validate_element_name(cls, v: str) -> str:
        """Validate element name format."""
        if not v:
            raise ValueError("Element name cannot be empty")
        if len(v) > 256:
            raise ValueError("Element name cannot exceed 256 characters")
        return v


class PluginElementRequest(BaseModel):
    """Request to load plugin elements."""

    elements: list[PluginElement] = Field(..., description="読み込む要素のリスト")


class LoadedElement(BaseModel):
    """Loaded plugin element with content."""

    element_type: str = Field(..., description="要素のタイプ")
    name: str = Field(..., description="要素の名前")
    path: str = Field(..., description="ファイルパス")
    content: str = Field(..., description="ファイルの内容")


class LoadedElementsResponse(BaseModel):
    """Response containing loaded plugin elements."""

    plugin_name: str = Field(..., description="プラグイン名")
    elements: list[LoadedElement] = Field(..., description="読み込まれた要素のリスト")


class PluginDetail(BaseModel):
    """Detailed plugin information from marketplace.json."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., description="プラグイン名")
    owner: dict[str, Any] | None = Field(None, description="オーナー情報")
    metadata: dict[str, Any] | None = Field(None, description="メタデータ")
    plugins: list[dict[str, Any]] = Field(
        default_factory=list,
        description="プラグイン定義リスト",
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="エラーメッセージ")
    detail: str | None = Field(None, description="詳細情報")
