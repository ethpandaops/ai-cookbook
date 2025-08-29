package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	"github.com/modelcontextprotocol/go-sdk/mcp"
	"github.com/sirupsen/logrus"
)

type EthereumSpecsServer struct {
	log          logrus.FieldLogger
	specsManager *SpecsManager
	config       Config
}

type Config struct {
	AutoUpdate  bool   `json:"auto_update"`
	SpecsBranch string `json:"specs_branch"`
}

// Tool parameter structs
type GetSpecParams struct {
	Fork  string `json:"fork" jsonschema:"Fork name (phase0, altair, bellatrix, capella, deneb, electra, fulu)"`
	Topic string `json:"topic" jsonschema:"Topic name (beacon-chain, fork-choice, p2p-interface, validator, etc)"`
}

type SearchSpecsParams struct {
	Query string `json:"query" jsonschema:"Search query"`
	Fork  string `json:"fork,omitempty" jsonschema:"Optional: limit search to specific fork"`
}

type ListForksParams struct{}

type CompareForksParams struct {
	Fork1 string `json:"fork1" jsonschema:"First fork to compare"`
	Fork2 string `json:"fork2" jsonschema:"Second fork to compare"`
	Topic string `json:"topic" jsonschema:"Topic to compare"`
}

type GetConstantParams struct {
	Name string `json:"name" jsonschema:"Constant name (e.g., MAX_EFFECTIVE_BALANCE)"`
	Fork string `json:"fork,omitempty" jsonschema:"Optional: specific fork (defaults to latest)"`
}

func NewEthereumSpecsServer(log logrus.FieldLogger, config Config) *EthereumSpecsServer {
	return &EthereumSpecsServer{
		log:    log.WithField("component", "server"),
		config: config,
	}
}

func (s *EthereumSpecsServer) Initialize(ctx context.Context) error {
	s.log.Info("Initializing ethereum-specs MCP server")

	specsManager := NewSpecsManager(s.log, s.config.SpecsBranch)
	s.specsManager = specsManager

	// Always initialize the specs manager to ensure the repository is available
	if err := s.specsManager.InitializeWithAutoUpdate(ctx, s.config.AutoUpdate); err != nil {
		s.log.WithError(err).Error("Failed to initialize specs manager")
		return fmt.Errorf("failed to initialize specs manager: %w", err)
	}

	return nil
}

// GetSpec handles the get_spec tool call
func (s *EthereumSpecsServer) GetSpec(ctx context.Context, req *mcp.CallToolRequest, args GetSpecParams) (*mcp.CallToolResult, any, error) {
	// Convert params to JSON for the specs manager
	paramsJSON, err := json.Marshal(args)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal params: %w", err)
	}

	result, err := s.specsManager.GetSpec(ctx, paramsJSON)
	if err != nil {
		return nil, nil, err
	}

	// Convert result to JSON string for text content
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

// SearchSpecs handles the search_specs tool call
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

// ListForks handles the list_forks tool call
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

// CompareForks handles the compare_forks tool call
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

// GetConstant handles the get_constant tool call
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
	log := logrus.New()
	log.SetFormatter(&logrus.TextFormatter{
		FullTimestamp: true,
		ForceColors:   false,
	})

	// CRITICAL: Log to stderr or file, never to stdout (stdout is for MCP protocol)
	log.SetOutput(os.Stderr)

	config := Config{
		AutoUpdate:  os.Getenv("AUTO_UPDATE") != "false",
		SpecsBranch: os.Getenv("SPECS_BRANCH"),
	}

	if config.SpecsBranch == "" {
		config.SpecsBranch = "dev"
	}

	// Create our server instance
	ethServer := NewEthereumSpecsServer(log, config)

	// Initialize the server (loads specs)
	ctx := context.Background()
	if err := ethServer.Initialize(ctx); err != nil {
		log.WithError(err).Fatal("Failed to initialize server")
	}

	// Create MCP server
	server := mcp.NewServer(
		&mcp.Implementation{
			Name:    "ethereum-specs",
			Version: "1.0.0",
		},
		nil, // No custom options
	)

	// Register our tools
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

	// Run the server over stdin/stdout
	log.Info("Starting ethereum-specs MCP server on stdio")
	if err := server.Run(ctx, &mcp.StdioTransport{}); err != nil {
		log.WithError(err).Fatal("Server failed")
	}
}
