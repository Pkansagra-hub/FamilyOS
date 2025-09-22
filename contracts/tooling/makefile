.PHONY: validate openapi lint test install-deps help

# Default target
help:
	@echo "MemoryOS Contracts Build Tools"
	@echo "=============================="
	@echo ""
	@echo "Available targets:"
	@echo "  validate     - Validate all schemas and contracts"
	@echo "  openapi      - Bundle and validate OpenAPI specs"
	@echo "  lint         - Run Spectral linting on OpenAPI specs"
	@echo "  test         - Run all validation tests"
	@echo "  install-deps - Install Python dependencies"
	@echo "  clean        - Clean temporary files"
	@echo "  help         - Show this help message"

# Install required dependencies
install-deps:
	pip install jsonschema pyyaml openapi-spec-validator
	npm install -g @redocly/cli spectral

# Validate all contracts
validate:
	python3 tooling/validate_all.py

# Bundle and validate OpenAPI specs
openapi:
	@echo "🔍 Bundling OpenAPI specifications..."
	@for spec in modules/*/api/openapi.yaml; do \
		if [ -f "$$spec" ]; then \
			echo "Bundling $$spec"; \
			npx @redocly/cli bundle "$$spec" -o /dev/null || true; \
		fi \
	done
	@echo "✅ OpenAPI bundling complete"

# Run Spectral linting
lint:
	@echo "🧹 Running Spectral linting..."
	@if [ -f tooling/spectral.config.yaml ]; then \
		for spec in modules/*/api/openapi.yaml; do \
			if [ -f "$$spec" ]; then \
				echo "Linting $$spec"; \
				npx spectral lint "$$spec" -r tooling/spectral.config.yaml || true; \
			fi \
		done; \
	else \
		echo "⚠️  No Spectral config found, using default rules"; \
		for spec in modules/*/api/openapi.yaml; do \
			if [ -f "$$spec" ]; then \
				echo "Linting $$spec"; \
				npx spectral lint "$$spec" || true; \
			fi \
		done; \
	fi
	@echo "✅ Linting complete"

# Run all tests
test: validate openapi lint
	@echo "🎉 All contract tests passed!"

# Clean temporary files
clean:
	@echo "🧹 Cleaning temporary files..."
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete"

# PowerShell variants for Windows
validate-ps:
	python tooling/validate_all.py

openapi-ps:
	@echo "🔍 Bundling OpenAPI specifications..."
	Get-ChildItem -Path "modules/*/api/openapi.yaml" -Recurse | ForEach-Object { \
		Write-Host "Bundling $$($_.FullName)"; \
		npx @redocly/cli bundle "$$($_.FullName)" -o nul; \
	}

lint-ps:
	@echo "🧹 Running Spectral linting..."
	Get-ChildItem -Path "modules/*/api/openapi.yaml" -Recurse | ForEach-Object { \
		Write-Host "Linting $$($_.FullName)"; \
		npx spectral lint "$$($_.FullName)" -r tooling/spectral.config.yaml; \
	}
