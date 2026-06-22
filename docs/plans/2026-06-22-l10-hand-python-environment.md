# L10 Hand Python Environment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a small, offline-testable Python control environment for a Linker Hand L10 left hand, ready to run when the hardware is connected.

**Architecture:** Provide a local package with a common controller interface and two backends: `dashboard` calls the official Windows dashboard HTTP API, and `sdk` loads the official LinkerHand Python SDK from a user-provided path. The CLI defaults to dry-run-safe discovery and explicit commands for gestures, speed, pose, and state reads.

**Tech Stack:** Python 3.12, pytest, requests, PyYAML, official LinkerHand Python SDK checked out separately when hardware testing is needed.

---

### Task 1: Project Skeleton And Failing Tests

**Files:**
- Create: `pyproject.toml`
- Create: `l10_hand_control/__init__.py`
- Create: `l10_hand_control/config.py`
- Create: `l10_hand_control/dashboard.py`
- Create: `l10_hand_control/sdk_backend.py`
- Create: `l10_hand_control/cli.py`
- Create: `tests/test_config.py`
- Create: `tests/test_dashboard.py`
- Create: `tests/test_sdk_backend.py`
- Create: `tests/test_cli.py`

**Steps:**
1. Write tests first for config defaults, dashboard request bodies, SDK constructor/method calls, and CLI argument dispatch.
2. Run `python -m pytest -q` and confirm tests fail because package files do not exist or functions are missing.
3. Implement the minimal package and CLI to satisfy tests.
4. Re-run `python -m pytest -q` and confirm all tests pass.

### Task 2: Config Templates And Setup Script

**Files:**
- Create: `config/l10_left.example.yaml`
- Create: `scripts/setup_env.ps1`
- Create: `scripts/install_official_sdk.ps1`
- Create: `README.md`

**Steps:**
1. Add tests or CLI checks for config loading from YAML.
2. Add templates with `hand_type: left`, `hand_joint: L10`, `can: PCAN_USBBUS1`, `dashboard_url: http://127.0.0.1:7080`.
3. Add PowerShell setup scripts using `python -m venv` and `python -m pip`, avoiding the mismatched global `pip`.
4. Document offline commands and hardware test commands.

### Task 3: Verification

**Files:**
- No production changes expected.

**Steps:**
1. Run `python -m venv .venv` if missing.
2. Install editable project and test dependencies with `.\.venv\Scripts\python.exe -m pip install -e .[test]`.
3. Run `.\.venv\Scripts\python.exe -m pytest -q`.
4. Run CLI help with `.\.venv\Scripts\python.exe -m l10_hand_control --help`.
5. Do not run hardware commands unless the user confirms the hand is connected and secured.
