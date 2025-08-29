// Package main implements an MCP (Model Context Protocol) server that provides
// access to Ethereum consensus specifications. The server enables AI tools like
// Claude to query, search, and compare Ethereum protocol specifications across
// different forks (phase0 through fulu).
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	"github.com/modelcontextprotocol/go-sdk/mcp"
	"github.com/sirupsen/logrus"
)

// EthereumSpecsServer implements the MCP server for Ethereum specifications.
// It manages the lifecycle of spec repository access and provides handlers
// for MCP tool calls.
type EthereumSpecsServer struct {
	log          logrus.FieldLogger
	specsManager *SpecsManager
	config       Config
}

// Config holds the runtime configuration for the MCP server.
// These values are typically provided via environment variables.
type Config struct {
	// AutoUpdate controls whether the specs repository is updated on startup.
	// This ensures the server has the latest protocol specifications.
	AutoUpdate bool `json:"auto_update"`

	// SpecsBranch specifies which branch of ethereum/consensus-specs to track.
	// Common values are "dev" for cutting-edge specs or "master" for stable.
	SpecsBranch string `json:"specs_branch"`
}

// GetSpecParams defines the parameters for retrieving a specific specification document.
// The jsonschema tags are used by the MCP SDK to generate tool schemas for AI models.
type GetSpecParams struct {
	Fork  string `json:"fork" jsonschema:"Fork name (phase0, altair, bellatrix, capella, deneb, electra, fulu)"`
	Topic string `json:"topic" jsonschema:"Topic name (beacon-chain, fork-choice, p2p-interface, validator, etc)"`
}

// SearchSpecsParams defines the parameters for searching across specifications.
// Fork is optional to allow searching across all forks when omitted.
type SearchSpecsParams struct {
	Query string `json:"query" jsonschema:"Search query"`
	Fork  string `json:"fork,omitempty" jsonschema:"Optional: limit search to specific fork"`
}

// ListForksParams is an empty struct as list_forks requires no parameters.
type ListForksParams struct{}

// CompareForksParams defines the parameters for comparing specs between forks.
// This is useful for understanding protocol changes between upgrades.
type CompareForksParams struct {
	Fork1 string `json:"fork1" jsonschema:"First fork to compare"`
	Fork2 string `json:"fork2" jsonschema:"Second fork to compare"`
	Topic string `json:"topic" jsonschema:"Topic to compare"`
}

// GetConstantParams defines the parameters for retrieving protocol constants.
// Fork is optional; when omitted, the constant is searched across all forks.
type GetConstantParams struct {
	Name string `json:"name" jsonschema:"Constant name (e.g., MAX_EFFECTIVE_BALANCE)"`
	Fork string `json:"fork,omitempty" jsonschema:"Optional: specific fork (defaults to latest)"`
}

// NewEthereumSpecsServer creates a new server instance with the provided configuration.
func NewEthereumSpecsServer(log logrus.FieldLogger, config Config) *EthereumSpecsServer {
	return &EthereumSpecsServer{
		log:    log.WithField("component", "server"),
		config: config,
	}
}

// Initialize prepares the server by setting up the specs repository.
// This may trigger a git clone or pull depending on the auto-update setting.
func (s *EthereumSpecsServer) Initialize(ctx context.Context) error {
	s.log.Info("Initializing ethereum-specs MCP server")

	specsManager := NewSpecsManager(s.log, s.config.SpecsBranch)
	s.specsManager = specsManager

	// Initialize the repository, potentially triggering an update.
	// This ensures specs are available before the server starts accepting requests.
	if err := s.specsManager.InitializeWithAutoUpdate(ctx, s.config.AutoUpdate); err != nil {
		s.log.WithError(err).Error("Failed to initialize specs manager")
		return fmt.Errorf("failed to initialize specs manager: %w", err)
	}

	return nil
}

// GetSpec retrieves a specific specification document for a given fork and topic.
// It returns the full markdown content of the requested specification.
func (s *EthereumSpecsServer) GetSpec(ctx context.Context, req *mcp.CallToolRequest, args GetSpecParams) (*mcp.CallToolResult, any, error) {
	// The specs manager expects JSON input to maintain compatibility
	// with potential future transport mechanisms beyond MCP.
	paramsJSON, err := json.Marshal(args)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal params: %w", err)
	}

	result, err := s.specsManager.GetSpec(ctx, paramsJSON)
	if err != nil {
		return nil, nil, err
	}

	// MCP expects text content, so we serialize the result to JSON
	resultJSON, err := json.Marshal(result)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal result: %w", err)
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: string(resultJSON)},
		},
	}, nil, nil
}

// SearchSpecs searches for a query string across all specifications.
// It can be limited to a specific fork or search across all forks.
func (s *EthereumSpecsServer) SearchSpecs(ctx context.Context, req *mcp.CallToolRequest, args SearchSpecsParams) (*mcp.CallToolResult, any, error) {
	paramsJSON, err := json.Marshal(args)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal params: %w", err)
	}

	result, err := s.specsManager.SearchSpecs(ctx, paramsJSON)
	if err != nil {
		return nil, nil, err
	}

	resultJSON, err := json.Marshal(result)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal result: %w", err)
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: string(resultJSON)},
		},
	}, nil, nil
}

// ListForks returns all available consensus fork names in the repository.
// This helps users discover which protocol versions are available.
func (s *EthereumSpecsServer) ListForks(ctx context.Context, req *mcp.CallToolRequest, args ListForksParams) (*mcp.CallToolResult, any, error) {
	result, err := s.specsManager.ListForks(ctx)
	if err != nil {
		return nil, nil, err
	}

	resultJSON, err := json.Marshal(result)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal result: %w", err)
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: string(resultJSON)},
		},
	}, nil, nil
}

// CompareForks generates a diff between the same topic across two different forks.
// This is essential for understanding protocol changes between upgrades.
func (s *EthereumSpecsServer) CompareForks(ctx context.Context, req *mcp.CallToolRequest, args CompareForksParams) (*mcp.CallToolResult, any, error) {
	paramsJSON, err := json.Marshal(args)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal params: %w", err)
	}

	result, err := s.specsManager.CompareForks(ctx, paramsJSON)
	if err != nil {
		return nil, nil, err
	}

	resultJSON, err := json.Marshal(result)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal result: %w", err)
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: string(resultJSON)},
		},
	}, nil, nil
}

// GetConstant retrieves the value of a protocol constant from the specifications.
// Constants define important protocol parameters like validator limits and timing.
func (s *EthereumSpecsServer) GetConstant(ctx context.Context, req *mcp.CallToolRequest, args GetConstantParams) (*mcp.CallToolResult, any, error) {
	paramsJSON, err := json.Marshal(args)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal params: %w", err)
	}

	result, err := s.specsManager.GetConstant(ctx, paramsJSON)
	if err != nil {
		return nil, nil, err
	}

	resultJSON, err := json.Marshal(result)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal result: %w", err)
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: string(resultJSON)},
		},
	}, nil, nil
}

func main() {
	// Configure structured logging for debugging and monitoring
	log := logrus.New()
	log.SetFormatter(&logrus.TextFormatter{
		FullTimestamp: true,
		ForceColors:   false, // Disable colors as output goes to files/stderr
	})

	// CRITICAL: MCP protocol requires stdout for communication.
	// All logging must go to stderr to avoid corrupting the protocol stream.
	log.SetOutput(os.Stderr)

	// Load configuration from environment variables.
	// This allows flexible deployment without recompilation.
	config := Config{
		AutoUpdate:  os.Getenv("AUTO_UPDATE") != "false", // Default to true for latest specs
		SpecsBranch: os.Getenv("SPECS_BRANCH"),
	}

	// Default to master branch for stable specifications
	if config.SpecsBranch == "" {
		config.SpecsBranch = "master"
	}

	// Create and initialize the server
	ethServer := NewEthereumSpecsServer(log, config)

	// Initialize repository and cache before starting MCP server.
	// This ensures specs are available for immediate querying.
	ctx := context.Background()
	if err := ethServer.Initialize(ctx); err != nil {
		log.WithError(err).Fatal("Failed to initialize server")
	}

	// Create MCP server instance with metadata for client discovery
	server := mcp.NewServer(
		&mcp.Implementation{
			Name:    "ethereum-specs",
			Version: "1.0.0",
		},
		nil, // No custom options needed for basic stdio transport
	)

	// Register all available tools with their handlers.
	// Each tool corresponds to a specific query capability.
	mcp.AddTool(server, &mcp.Tool{
		Name:        "get_spec",
		Description: "Get specific spec content for a fork and topic",
	}, ethServer.GetSpec)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "search_specs",
		Description: "Search across specifications",
	}, ethServer.SearchSpecs)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "list_forks",
		Description: "List all available forks",
	}, ethServer.ListForks)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "compare_forks",
		Description: "Show differences between fork versions for a specific topic",
	}, ethServer.CompareForks)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "get_constant",
		Description: "Get configuration constants",
	}, ethServer.GetConstant)

	// Start the MCP server using stdio transport.
	// The server will run until the client disconnects or an error occurs.
	log.Info("Starting ethereum-specs MCP server on stdio")
	if err := server.Run(ctx, &mcp.StdioTransport{}); err != nil {
		log.WithError(err).Fatal("Server failed")
	}
}
