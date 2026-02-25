# ---------------------------------------------------------------------------
# Research Environment API – developer task Makefile runner
#
# pytest.ini owns base pytest config (tb style, markers, etc.).
# This Makefile provides convenient shortcuts.
#
#   make help                  show this message
#
#   ── all tests ───────────────────────────────────────────────────────────
#   make test                  unit + integration tests
#   make test-verbose          unit + integration, verbose output
#
#   ── unit tests ──────────────────────────────────────────────────────────
#   make test-unit             all unit tests
#   make test-unit-services    unit/services only
#   make test-unit-background  unit/background only
#
#   ── integration tests ───────────────────────────────────────────────────
#   make test-integration             all integration tests
#   make test-integration-sharing     sharing suite only
#   make test-integration-workbench   workbench suite only
#   make test-integration-workspace   workspace suite only
#   make test-integration-monitoring  monitoring suite only
#   make test-integration-workflow    workflow suite only
#
#   ── coverage ────────────────────────────────────────────────────────────
#   make coverage              run all tests + print coverage report
#   make coverage-html         run all tests + open HTML report in browser
# ---------------------------------------------------------------------------

PYTHON   := venv/python/bin/python
PYTEST   := $(PYTHON) -m pytest

UNIT_PATH        := research_environment_api/tests/unit
INTEGRATION_PATH := research_environment_api/tests/integration

COV_FLAGS := \
    --cov=research_environment_api \
    --cov-report=term-missing

.PHONY: help \
        test test-verbose \
        test-unit test-unit-services test-unit-background \
        test-integration \
        test-integration-sharing test-integration-workbench \
        test-integration-workspace test-integration-monitoring \
        test-integration-workflow \
        coverage coverage-html

# ---------------------------------------------------------------------------

help:
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "  ── all tests ──────────────────────────────────────────────────"
	@echo "  test                        unit + integration tests"
	@echo "  test-verbose                unit + integration, verbose output"
	@echo ""
	@echo "  ── unit tests ─────────────────────────────────────────────────"
	@echo "  test-unit                   all unit tests"
	@echo "  test-unit-services          unit/services only"
	@echo "  test-unit-background        unit/background only"
	@echo ""
	@echo "  ── integration tests ──────────────────────────────────────────"
	@echo "  test-integration            all integration tests"
	@echo "  test-integration-sharing    sharing suite only"
	@echo "  test-integration-workbench  workbench suite only"
	@echo "  test-integration-workspace  workspace suite only"
	@echo "  test-integration-monitoring monitoring suite only"
	@echo "  test-integration-workflow   workflow suite only"
	@echo ""
	@echo "  ── coverage ───────────────────────────────────────────────────"
	@echo "  coverage                    all tests + print coverage report"
	@echo "  coverage-html               all tests + open HTML report"
	@echo ""

# -- all tests ---------------------------------------------------------------

test:
	$(PYTEST) $(UNIT_PATH) $(INTEGRATION_PATH)

test-verbose:
	$(PYTEST) $(UNIT_PATH) $(INTEGRATION_PATH) -v

# -- unit tests --------------------------------------------------------------

test-unit:
	$(PYTEST) $(UNIT_PATH)

test-unit-services:
	$(PYTEST) $(UNIT_PATH)/services

test-unit-background:
	$(PYTEST) $(UNIT_PATH)/background

# -- integration tests -------------------------------------------------------

test-integration:
	$(PYTEST) $(INTEGRATION_PATH)

test-integration-sharing:
	$(PYTEST) $(INTEGRATION_PATH)/sharing

test-integration-workbench:
	$(PYTEST) $(INTEGRATION_PATH)/workbench

test-integration-workspace:
	$(PYTEST) $(INTEGRATION_PATH)/workspace

test-integration-monitoring:
	$(PYTEST) $(INTEGRATION_PATH)/monitoring

test-integration-workflow:
	$(PYTEST) $(INTEGRATION_PATH)/workflow

# -- coverage ----------------------------------------------------------------

coverage:
	$(PYTEST) $(UNIT_PATH) $(INTEGRATION_PATH) $(COV_FLAGS)

coverage-html:
	$(PYTEST) $(UNIT_PATH) $(INTEGRATION_PATH) $(COV_FLAGS) --cov-report=html:htmlcov
	open htmlcov/index.html

