.PHONY: build clean test deps run help

# Build variables
BINARY_NAME=ethereum-specs-mcp
BUILD_DIR=bin
VERSION=$(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
BUILD_TIME=$(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
LDFLAGS=-ldflags "-X main.Version=$(VERSION) -X main.BuildTime=$(BUILD_TIME) -w -s"

# Default target
default: build

help:
	@echo "Available targets:"
	@echo "  build    - Build the MCP server binary"
	@echo "  clean    - Remove build artifacts"
	@echo "  test     - Run tests"
	@echo "  deps     - Download and tidy dependencies"
	@echo "  run      - Build and run the server interactively"
	@echo "  help     - Show this help message"

build: deps
	@echo "Building ethereum-specs MCP server..."
	@go build $(LDFLAGS) -o $(BUILD_DIR)/$(BINARY_NAME) .
	@chmod +x $(BUILD_DIR)/$(BINARY_NAME)
	@echo "✅ Built $(BUILD_DIR)/$(BINARY_NAME)"

deps:
	@go mod download
	@go mod tidy

clean:
	@rm -f $(BUILD_DIR)/$(BINARY_NAME)
	@rm -f /tmp/ethereum-specs-mcp.log
	@rm -rf .consensus-specs/
	@echo "🧹 Cleaned build artifacts and local repository"

test:
	@go test -v -race -coverprofile=coverage.out ./...

run: build
	@echo "Starting ethereum-specs MCP server..."
	@$(BUILD_DIR)/$(BINARY_NAME)