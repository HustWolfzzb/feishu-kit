# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-05-13

### Added

#### Core
- **FeishuClient** — async HTTP client with automatic tenant access token management, retry logic, and typed error handling (`feishu_kit.core.client`).
- **ClientPool** — manage multiple Feishu bots/tenants simultaneously with per-client configuration (`feishu_kit.core.pool`).
- **Settings** — Pydantic Settings integration for loading `APP_ID`, `APP_SECRET`, and other config from environment variables or `.env` files (`feishu_kit.core.settings`).
- **Exceptions** — structured exception hierarchy for Feishu API errors (`feishu_kit.core.exceptions`).

#### Modules (7 modules)
- **Wiki** — create, read, update, and list Feishu Wiki documents and spaces (`feishu_kit.modules.wiki`).
- **Drive** — upload, download, and manage files and folders in Feishu Drive (`feishu_kit.modules.drive`).
- **Messaging** — send and receive messages, manage chats and message resources (`feishu_kit.modules.messaging`).
- **Contacts** — query users, departments, and contact groups (`feishu_kit.modules.contacts`).
- **Calendar** — create and manage calendar events and calendars (`feishu_kit.modules.calendar`).
- **Task** — create, update, and query tasks and task lists (`feishu_kit.modules.task`).
- **Markdown-to-Feishu** — convert standard Markdown to Feishu document blocks via `mistune` (`feishu_kit.modules.md2feishu`).

#### CLI
- **feishu-kit CLI** — Typer-based command-line interface with Rich output for common operations (`feishu_kit.cli`).

#### FastAPI Server
- **Built-in server** — optional FastAPI application with modular router system, service registry, and webhook support (`server/`).

#### Examples & Tutorials
- **7 example scripts** covering hello-world, wiki basics, document writing, file upload, Markdown conversion, multi-bot usage, and a full course-builder tutorial (`examples/`).

#### Tests
- **Initial test suite** covering client initialization, connection pool behavior, Markdown parsing, and wiki module operations (`tests/`).

#### Infrastructure
- MIT License.
- `pyproject.toml` with setuptools build backend, optional dependency groups (`dev`, `server`, `docs`).
- Ruff configuration for linting and formatting.
- Pytest configuration with async support.
