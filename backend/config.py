"""
Configuration module for the RAG Validation Pipeline.
Loads environment variables and provides typed access to all settings.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    agent1_model: str = ""
    agent2_model: str = ""

    @property
    def active_api_key(self) -> str:
        if self.provider == "gemini":
            return self.gemini_api_key
        return self.groq_api_key


@dataclass
class SearchConfig:
    """Search provider configuration."""
    provider: str = ""
    tavily_api_key: str = ""
    serpapi_key: str = ""

    @property
    def active_api_key(self) -> str:
        if self.provider == "serpapi":
            return self.serpapi_key
        return self.tavily_api_key


@dataclass
class PipelineSettings:
    """Pipeline behavior configuration."""
    strict_rag_mode: bool = True
    temporal_cutoff_year: int = 2021
    output_format: str = "PDF"


@dataclass
class UITheme:
    """Frontend theme configuration."""
    theme_name: str = "Neo-Brutalism"
    color_base: str = "#FFFFFF"
    color_borders: str = "#000000"
    color_agent1: str = "#00FF00"
    color_agent2: str = "#0000FF"


@dataclass
class AppConfig:
    """Root application configuration."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    pipeline: PipelineSettings = field(default_factory=PipelineSettings)
    ui: UITheme = field(default_factory=UITheme)
    upload_dir: str = ""
    reports_dir: str = ""

    def validate(self) -> list[str]:
        """Validate configuration. Returns list of error messages."""
        errors = []
        if self.llm.provider == "groq" and not self.llm.groq_api_key:
            errors.append("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        if self.llm.provider == "gemini" and not self.llm.gemini_api_key:
            errors.append("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        if self.search.provider == "tavily" and not self.search.tavily_api_key:
            errors.append("TAVILY_API_KEY is required when SEARCH_PROVIDER=tavily")
        if self.search.provider == "serpapi" and not self.search.serpapi_key:
            errors.append("SERPAPI_KEY is required when SEARCH_PROVIDER=serpapi")
        return errors


def _clean_str(val: str) -> str:
    """Clean surrounding quotes and whitespace from environment strings."""
    if not val:
        return ""
    return val.strip().strip('"').strip("'")


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    project_root = os.path.dirname(os.path.dirname(__file__))
    env_path = os.path.join(project_root, ".env")
    load_dotenv(env_path, override=True)

    upload_dir = os.path.join(project_root, "uploads")
    reports_dir = os.path.join(project_root, "reports")
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    return AppConfig(
        llm=LLMConfig(
            provider=_clean_str(os.getenv("LLM_PROVIDER", "groq")),
            groq_api_key=_clean_str(os.getenv("GROQ_API_KEY", "")),
            gemini_api_key=_clean_str(os.getenv("GEMINI_API_KEY", "")),
            agent1_model=_clean_str(os.getenv("AGENT1_MODEL", "llama-3.1-8b-instant")),
            agent2_model=_clean_str(os.getenv("AGENT2_MODEL", "llama-3.1-8b-instant")),
        ),
        search=SearchConfig(
            provider=_clean_str(os.getenv("SEARCH_PROVIDER", "tavily")),
            tavily_api_key=_clean_str(os.getenv("TAVILY_API_KEY", "")),
            serpapi_key=_clean_str(os.getenv("SERPAPI_KEY", "")),
        ),
        pipeline=PipelineSettings(
            strict_rag_mode=_clean_str(os.getenv("STRICT_RAG_MODE", "true")).lower() == "true",
            temporal_cutoff_year=int(_clean_str(os.getenv("TEMPORAL_CUTOFF_YEAR", "2021"))),
            output_format=_clean_str(os.getenv("OUTPUT_FORMAT", "PDF")),
        ),
        ui=UITheme(),
        upload_dir=upload_dir,
        reports_dir=reports_dir,
    )

