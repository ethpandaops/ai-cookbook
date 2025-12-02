// Package main implements an MCP (Model Context Protocol) server that provides
// access to Ethereum specifications. The server enables AI tools like Claude to
// query, search, and compare Ethereum protocol specifications across different
// forks for both consensus layer (phase0 through fulu) and execution layer
// (paris through osaka) specifications.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	"github.com/modelcontextprotocol/go-sdk/mcp"
	"github.com/sirupsen/logrus"
)

// Layer constants for spec queries.
const (
	layerConsensus = "consensus"
	layerEngine    = "engine"
	layerEth       = "eth"
	layerAll       = "all"
)

// EthereumSpecsServer implements the MCP server for Ethereum specifications.
// It manages the lifecycle of spec repository access and provides handlers
// for MCP tool calls for both consensus and execution layer specs.
type EthereumSpecsServer struct {
	log              logrus.FieldLogger
	specsManager     *SpecsManager
	executionManager *ExecutionSpecsManager
	config           Config
}

// Config holds the runtime configuration for the MCP server.
// These values are typically provided via environment variables.
type Config struct {
	// AutoUpdate controls whether the specs repositories are updated on startup.
	AutoUpdate bool `json:"autoUpdate"`

	// SpecsBranch specifies which branch of ethereum/consensus-specs to track.
	SpecsBranch string `json:"specsBranch"`

	// ExecutionAPIsBranch specifies which branch of ethereum/execution-apis to track.
	ExecutionAPIsBranch string `json:"executionApisBranch"`
}

// GetSpecParams defines the parameters for retrieving a specific specification document.
type GetSpecParams struct {
	Fork  string `json:"fork" jsonschema:"Fork name for consensus (phase0-fulu) or upgrade name for engine (paris-osaka)"`
	Topic string `json:"topic" jsonschema:"Topic name (beacon-chain, fork-choice, p2p-interface, validator, etc)"`
	Layer string `json:"layer,omitempty" jsonschema:"Optional: consensus (default), engine, or eth"`
}

// SearchSpecsParams defines the parameters for searching across specifications.
type SearchSpecsParams struct {
	Query string `json:"query" jsonschema:"Search query"`
	Fork  string `json:"fork,omitempty" jsonschema:"Optional: limit search to specific fork/upgrade"`
	Layer string `json:"layer,omitempty" jsonschema:"Optional: consensus, engine, eth, or all (default: all)"`
}

// ListForksParams defines parameters for listing available forks/upgrades.
type ListForksParams struct {
	Layer string `json:"layer,omitempty" jsonschema:"Optional: consensus (default), engine, or all"`
}

// CompareForksParams defines the parameters for comparing specs between forks.
type CompareForksParams struct {
	Fork1 string `json:"fork1" jsonschema:"First fork to compare"`
	Fork2 string `json:"fork2" jsonschema:"Second fork to compare"`
	Topic string `json:"topic" jsonschema:"Topic to compare"`
}

// GetConstantParams defines the parameters for retrieving protocol constants.
type GetConstantParams struct {
	Name string `json:"name" jsonschema:"Constant name (e.g., MAX_EFFECTIVE_BALANCE)"`
	Fork string `json:"fork,omitempty" jsonschema:"Optional: specific fork (defaults to latest)"`
}

// GetRPCMethodParams defines the parameters for retrieving JSON-RPC method info.
type GetRPCMethodParams struct {
	Method string `json:"method" jsonschema:"JSON-RPC method name (e.g., eth_call, engine_newPayloadV4)"`
}

// ListRPCMethodsParams defines the parameters for listing JSON-RPC methods.
type ListRPCMethodsParams struct {
	Namespace string `json:"namespace,omitempty" jsonschema:"Optional: filter by namespace (eth, engine, debug)"`
}

// GetForkMappingParams is empty as get_fork_mapping requires no parameters.
type GetForkMappingParams struct{}

// NewEthereumSpecsServer creates a new server instance with the provided configuration.
func NewEthereumSpecsServer(log logrus.FieldLogger, config Config) *EthereumSpecsServer {
	return &EthereumSpecsServer{
		log:    log.WithField("component", "server"),
		config: config,
	}
}

// Initialize prepares the server by setting up both specs repositories.
func (s *EthereumSpecsServer) Initialize(ctx context.Context) error {
	s.log.Info("Initializing ethereum-specs MCP server")

	// Initialize consensus specs manager
	specsManager := NewSpecsManager(s.log, s.config.SpecsBranch)
	s.specsManager = specsManager

	if err := s.specsManager.InitializeWithAutoUpdate(ctx, s.config.AutoUpdate); err != nil {
		s.log.WithError(err).Error("Failed to initialize consensus specs manager")

		return fmt.Errorf("failed to initialize consensus specs manager: %w", err)
	}

	// Initialize execution specs manager
	executionManager := NewExecutionSpecsManager(s.log, s.config.ExecutionAPIsBranch)
	s.executionManager = executionManager

	if err := s.executionManager.InitializeWithAutoUpdate(ctx, s.config.AutoUpdate); err != nil {
		s.log.WithError(err).Error("Failed to initialize execution specs manager")

		return fmt.Errorf("failed to initialize execution specs manager: %w", err)
	}

	return nil
}

// GetSpec retrieves a specific specification document for a given fork and topic.
// The layer parameter determines which repository to query (consensus, engine, or eth).
func (s *EthereumSpecsServer) GetSpec(
	ctx context.Context,
	req *mcp.CallToolRequest,
	args GetSpecParams,
) (*mcp.CallToolResult, any, error) {
	layer := args.Layer
	if layer == "" {
		layer = layerConsensus // backwards compatible default
	}

	var (
		result any
		err    error
	)

	switch layer {
	case layerConsensus:
		paramsJSON, marshalErr := json.Marshal(args)
		if marshalErr != nil {
			return nil, nil, fmt.Errorf("failed to marshal params: %w", marshalErr)
		}

		result, err = s.specsManager.GetSpec(ctx, paramsJSON)

	case layerEngine:
		paramsJSON, marshalErr := json.Marshal(map[string]string{
			"upgrade": args.Fork,
			"topic":   args.Topic,
		})
		if marshalErr != nil {
			return nil, nil, fmt.Errorf("failed to marshal params: %w", marshalErr)
		}

		result, err = s.executionManager.GetEngineSpec(ctx, paramsJSON)

	case layerEth:
		paramsJSON, marshalErr := json.Marshal(map[string]string{
			"category": args.Topic,
		})
		if marshalErr != nil {
			return nil, nil, fmt.Errorf("failed to marshal params: %w", marshalErr)
		}

		result, err = s.executionManager.GetEthCategory(ctx, paramsJSON)

	default:
		return nil, nil, fmt.Errorf("invalid layer: %s (must be consensus, engine, or eth)", layer)
	}

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

// SearchSpecs searches for a query string across specifications.
// By default, searches all layers (consensus, engine, eth).
func (s *EthereumSpecsServer) SearchSpecs(
	ctx context.Context,
	req *mcp.CallToolRequest,
	args SearchSpecsParams,
) (*mcp.CallToolResult, any, error) {
	layer := args.Layer
	if layer == "" {
		layer = layerAll
	}

	results := make(map[string]any)

	// Search consensus specs
	if layer == layerAll || layer == layerConsensus {
		paramsJSON, _ := json.Marshal(args)

		consensusResults, err := s.specsManager.SearchSpecs(ctx, paramsJSON)
		if err == nil {
			results[layerConsensus] = consensusResults
		}
	}

	// Search execution specs
	if layer == layerAll || layer == layerEngine || layer == layerEth {
		paramsJSON, _ := json.Marshal(map[string]string{
			"query":   args.Query,
			"upgrade": args.Fork,
		})

		execResults, err := s.executionManager.SearchSpecs(ctx, paramsJSON)
		if err == nil {
			results["execution"] = execResults
		}
	}

	resultJSON, err := json.Marshal(results)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal result: %w", err)
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: string(resultJSON)},
		},
	}, nil, nil
}

// ListForks returns available fork/upgrade names.
// Can be filtered by layer (consensus, engine, or all).
func (s *EthereumSpecsServer) ListForks(
	ctx context.Context,
	req *mcp.CallToolRequest,
	args ListForksParams,
) (*mcp.CallToolResult, any, error) {
	layer := args.Layer
	if layer == "" {
		layer = layerConsensus
	}

	results := make(map[string]any)

	if layer == layerAll || layer == layerConsensus {
		consensusForks, err := s.specsManager.ListForks(ctx)
		if err == nil {
			results[layerConsensus] = consensusForks
		}
	}

	if layer == layerAll || layer == layerEngine {
		engineUpgrades, err := s.executionManager.ListUpgrades(ctx)
		if err == nil {
			results[layerEngine] = engineUpgrades
		}
	}

	resultJSON, err := json.Marshal(results)
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
func (s *EthereumSpecsServer) CompareForks(
	ctx context.Context,
	req *mcp.CallToolRequest,
	args CompareForksParams,
) (*mcp.CallToolResult, any, error) {
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
func (s *EthereumSpecsServer) GetConstant(
	ctx context.Context,
	req *mcp.CallToolRequest,
	args GetConstantParams,
) (*mcp.CallToolResult, any, error) {
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

// GetRPCMethod retrieves detailed information about a JSON-RPC method.
func (s *EthereumSpecsServer) GetRPCMethod(
	ctx context.Context,
	req *mcp.CallToolRequest,
	args GetRPCMethodParams,
) (*mcp.CallToolResult, any, error) {
	paramsJSON, err := json.Marshal(args)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal params: %w", err)
	}

	result, err := s.executionManager.GetRPCMethod(ctx, paramsJSON)
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

// ListRPCMethods returns a list of available JSON-RPC methods.
func (s *EthereumSpecsServer) ListRPCMethods(
	ctx context.Context,
	req *mcp.CallToolRequest,
	args ListRPCMethodsParams,
) (*mcp.CallToolResult, any, error) {
	paramsJSON, err := json.Marshal(args)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal params: %w", err)
	}

	result, err := s.executionManager.ListRPCMethods(ctx, paramsJSON)
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

// GetForkMapping returns the mapping between consensus and execution layer naming.
func (s *EthereumSpecsServer) GetForkMapping(
	ctx context.Context,
	req *mcp.CallToolRequest,
	args GetForkMappingParams,
) (*mcp.CallToolResult, any, error) {
	mapping := GetForkMapping()

	resultJSON, err := json.Marshal(map[string]any{
		"mappings": mapping,
	})
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
	log.SetOutput(os.Stderr)

	config := Config{
		AutoUpdate:          os.Getenv("AUTO_UPDATE") != "false",
		SpecsBranch:         os.Getenv("SPECS_BRANCH"),
		ExecutionAPIsBranch: os.Getenv("EXECUTION_APIS_BRANCH"),
	}

	if config.SpecsBranch == "" {
		config.SpecsBranch = "master"
	}

	if config.ExecutionAPIsBranch == "" {
		config.ExecutionAPIsBranch = "main"
	}

	ethServer := NewEthereumSpecsServer(log, config)

	ctx := context.Background()
	if err := ethServer.Initialize(ctx); err != nil {
		log.WithError(err).Fatal("Failed to initialize server")
	}

	server := mcp.NewServer(
		&mcp.Implementation{
			Name:    "ethereum-specs",
			Version: "2.0.0",
		},
		nil,
	)

	// Register consensus layer tools
	mcp.AddTool(server, &mcp.Tool{
		Name:        "get_spec",
		Description: "Get specific spec content for a fork and topic. Use layer parameter: consensus (default), engine, or eth",
	}, ethServer.GetSpec)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "search_specs",
		Description: "Search across specifications. Searches all layers by default (consensus, engine, eth)",
	}, ethServer.SearchSpecs)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "list_forks",
		Description: "List all available forks/upgrades. Use layer parameter: consensus (default), engine, or all",
	}, ethServer.ListForks)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "compare_forks",
		Description: "Show differences between fork versions for a specific topic",
	}, ethServer.CompareForks)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "get_constant",
		Description: "Get configuration constants",
	}, ethServer.GetConstant)

	// Register execution layer tools
	mcp.AddTool(server, &mcp.Tool{
		Name:        "get_rpc_method",
		Description: "Get detailed information about a JSON-RPC method including parameters, return type, and examples",
	}, ethServer.GetRPCMethod)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "list_rpc_methods",
		Description: "List available JSON-RPC methods with optional namespace filter (eth, engine, debug)",
	}, ethServer.ListRPCMethods)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "get_fork_mapping",
		Description: "Get mapping between consensus layer fork names and execution layer upgrade names",
	}, ethServer.GetForkMapping)

	log.Info("Starting ethereum-specs MCP server on stdio")

	if err := server.Run(ctx, &mcp.StdioTransport{}); err != nil {
		log.WithError(err).Fatal("Server failed")
	}
}
