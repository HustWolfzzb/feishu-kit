# Contributing to feishu-kit

Thank you for your interest in contributing to feishu-kit! This guide covers everything you need to get started.

## Development Setup

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:

   ```bash
   git clone https://github.com/YOUR_USERNAME/feishu-kit.git
   cd feishu-kit
   ```

3. **Create a virtual environment** and install the package with all development dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   # .venv\Scripts\activate    # Windows
   pip install -e ".[dev,server]"
   ```

4. **Install pre-commit hooks**:

   ```bash
   pre-commit install
   ```

   This automatically runs linting and formatting checks on every commit.

## Code Style

feishu-kit uses **ruff** for both linting and formatting.

- **Line length**: 100 characters
- **Target Python version**: 3.11+
- **Rule set**: `E`, `F`, `W`, `I`, `UP`, `B`, `SIM`, `RUF` (see `pyproject.toml` for details)

Run checks manually:

```bash
ruff check .          # lint
ruff format --check . # format check
ruff format .         # auto-format
```

## Commit Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/). Each commit message should be structured as:

```
<type>: <description>
```

Common types:

| Type       | Use for                                         |
|------------|-------------------------------------------------|
| `feat:`    | A new feature                                   |
| `fix:`     | A bug fix                                       |
| `docs:`    | Documentation-only changes                      |
| `style:`   | Formatting, whitespace (no code change)         |
| `refactor:`| Code restructuring without behavior change      |
| `perf:`    | Performance improvements                        |
| `test:`    | Adding or updating tests                        |
| `chore:`   | Build, CI, tooling, or auxiliary changes        |
| `ci:`      | CI/CD configuration changes                     |

Examples:

```
feat(wiki): add support for listing wiki spaces by permission
fix(client): retry on 429 rate-limit responses
docs: update CONTRIBUTING.md with module guide
```

## PR Process

1. **Create a branch** from `main`:

   ```bash
   git checkout -b feat/my-new-feature
   ```

2. **Make your changes**, ensuring tests pass locally:

   ```bash
   pytest tests/ -v
   ```

3. **Commit** using Conventional Commits format.

4. **Push** to your fork and **open a Pull Request** against the `main` branch of the upstream repository.

5. **CI must pass.** All checks (linting, formatting, tests) must succeed before merge.

6. **Address review feedback** by pushing additional commits to the same branch.

## Adding a New Module

feishu-kit modules live in `feishu_kit/modules/`. Follow these steps to add a new one (using `approval` as an example):

### 1. Create the module directory

```bash
mkdir feishu_kit/modules/approval
```

### 2. Create the service class

Create `feishu_kit/modules/approval/service.py`:

```python
from __future__ import annotations

from feishu_kit.core.client import FeishuClient


class ApprovalService:
    """Wrapper around Feishu Approval API."""

    def __init__(self, client: FeishuClient) -> None:
        self._client = client

    async def list_instances(self, approval_code: str) -> list[dict]:
        path = "/open-apis/approval/v4/instance"
        resp = await self._client.get(path, params={"approval_code": approval_code})
        return resp.get("data", {}).get("instance_list", [])
```

### 3. Export from `__init__.py`

Create `feishu_kit/modules/approval/__init__.py`:

```python
from feishu_kit.modules.approval.service import ApprovalService

__all__ = ["ApprovalService"]
```

### 4. (Optional) Add a FastAPI router

Create `feishu_kit/modules/approval/router.py` if the module should expose HTTP endpoints via the built-in server:

```python
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/approval", tags=["approval"])


@router.get("/instances")
async def list_instances(approval_code: str):
    # delegate to ApprovalService
    ...
```

Register the router in `server/__init__.py` (or the relevant app factory).

### 5. Add tests

Create `tests/test_approval.py`:

```python
import pytest

from feishu_kit.modules.approval import ApprovalService


@pytest.fixture
def approval_service(client):
    return ApprovalService(client)


async def test_list_instances(approval_service):
    ...
```

### 6. Update `CHANGELOG.md`

Add an entry under the appropriate version heading.

## Running Tests

Run the full test suite:

```bash
pytest tests/ -v
```

Run a single test file:

```bash
pytest tests/test_wiki.py -v
```

Run with coverage (if `pytest-cov` is installed):

```bash
pytest tests/ -v --cov=feishu_kit --cov-report=term-missing
```

> **Note:** Tests require Python 3.11+ and the `[dev]` optional dependencies installed.

---

Thank you for contributing to feishu-kit!
