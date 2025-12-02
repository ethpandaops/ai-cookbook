// Package main contains the execution specs repository management and tool implementations
// for the Ethereum Specs MCP server. This file handles execution layer specifications
// from the ethereum/execution-apis repository.
package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"sync"

	"github.com/sirupsen/logrus"
)

// availableUpgrades defines execution layer upgrade names in chronological order.
// These correspond to markdown files in the ethereum/execution-apis repository.
var availableUpgrades = []string{"paris", "shanghai", "cancun", "prague", "osaka", "amsterdam"}

// ExecutionSpecsManager handles all interactions with the Ethereum execution APIs
// repository. It manages git operations, caching, and provides methods to query
// Engine API specs and JSON-RPC method definitions.
type ExecutionSpecsManager struct {
	log          logrus.FieldLogger
	branch       string
	repoPath     string
	methodCache  map[string]OpenRPCMethod
	engineCache  map[string]string
	cacheMutex   sync.RWMutex
	initialized  bool
	methodsReady bool
}

// NewExecutionSpecsManager creates a new instance of the execution specs manager.
func NewExecutionSpecsManager(log logrus.FieldLogger, branch string) *ExecutionSpecsManager {
	execPath, err := os.Executable()
	if err != nil {
		log.WithError(err).Fatal("Failed to get executable path")
	}

	realPath, err := filepath.EvalSymlinks(execPath)
	if err != nil {
		realPath = execPath
	}

	baseDir := filepath.Dir(filepath.Dir(realPath))
	repoPath := filepath.Join(baseDir, ".execution-apis")

	log.WithField("repo_path", repoPath).Info("Using execution-apis repository path")

	return &ExecutionSpecsManager{
		log:         log.WithField("component", "execution_specs_manager"),
		branch:      branch,
		repoPath:    repoPath,
		methodCache: make(map[string]OpenRPCMethod, 50),
		engineCache: make(map[string]string, 20),
	}
}

// InitializeWithAutoUpdate prepares the execution-apis repository for use.
//
//nolint:gosec // G204: branch is from trusted config, not user input
func (em *ExecutionSpecsManager) InitializeWithAutoUpdate(ctx context.Context, autoUpdate bool) error {
	em.log.Info("Initializing execution-apis repository")

	if _, err := os.Stat(em.repoPath); os.IsNotExist(err) {
		em.log.Info("Cloning ethereum/execution-apis repository")

		cmd := exec.CommandContext(ctx, "git", "clone",
			"--branch", em.branch,
			"https://github.com/ethereum/execution-apis.git",
			em.repoPath)

		if output, err := cmd.CombinedOutput(); err != nil {
			return fmt.Errorf("failed to clone repository: %w\nOutput: %s", err, output)
		}

		em.log.Info("Repository cloned successfully")
	} else if autoUpdate {
		em.log.Info("Repository exists, starting background update")

		go em.runBackgroundUpdate()
	} else {
		em.log.Info("Repository exists, skipping update (auto-update disabled)")
	}

	em.initialized = true
	em.log.Info("Execution-apis repository initialized successfully")

	return nil
}

// runBackgroundUpdate performs a git fetch/checkout/pull in the background.
//
//nolint:gosec // G204: branch is from trusted config, not user input
func (em *ExecutionSpecsManager) runBackgroundUpdate() {
	em.log.Info("Starting background repository update")

	updateCtx := context.Background()

	cmd := exec.CommandContext(updateCtx, "git", "fetch", "origin")
	cmd.Dir = em.repoPath

	if output, err := cmd.CombinedOutput(); err != nil {
		em.log.WithError(err).WithField("output", string(output)).Warn("Failed to fetch updates")

		return
	}

	cmd = exec.CommandContext(updateCtx, "git", "checkout", em.branch)
	cmd.Dir = em.repoPath

	if output, err := cmd.CombinedOutput(); err != nil {
		em.log.WithError(err).WithField("output", string(output)).Warn("Failed to checkout branch")

		return
	}

	cmd = exec.CommandContext(updateCtx, "git", "pull", "origin", em.branch)
	cmd.Dir = em.repoPath

	if output, err := cmd.CombinedOutput(); err != nil {
		em.log.WithError(err).WithField("output", string(output)).Warn("Failed to pull updates")

		return
	}

	em.log.Info("Background repository update completed successfully")
}

// GetEngineSpec retrieves the content of an Engine API specification document.
func (em *ExecutionSpecsManager) GetEngineSpec(ctx context.Context, params json.RawMessage) (any, error) {
	var args struct {
		Upgrade string `json:"upgrade"`
		Topic   string `json:"topic,omitempty"`
	}

	if err := json.Unmarshal(params, &args); err != nil {
		return nil, fmt.Errorf("invalid parameters: %w", err)
	}

	// Determine file to read
	var filename string

	if args.Topic != "" {
		filename = args.Topic + ".md"
	} else if args.Upgrade != "" {
		if !em.isValidUpgrade(args.Upgrade) {
			return nil, fmt.Errorf("invalid upgrade: %s", args.Upgrade)
		}

		filename = args.Upgrade + ".md"
	} else {
		return nil, fmt.Errorf("either upgrade or topic must be specified")
	}

	specPath := filepath.Join(em.repoPath, "src", "engine", filename)

	// Check cache
	em.cacheMutex.RLock()

	if content, ok := em.engineCache[specPath]; ok {
		em.cacheMutex.RUnlock()

		return map[string]any{
			"content": content,
			"upgrade": args.Upgrade,
			"topic":   args.Topic,
			"layer":   "engine",
		}, nil
	}

	em.cacheMutex.RUnlock()

	content, err := os.ReadFile(specPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("engine spec not found: %s", filename)
		}

		return nil, fmt.Errorf("failed to read spec: %w", err)
	}

	contentStr := string(content)

	em.cacheMutex.Lock()
	em.engineCache[specPath] = contentStr
	em.cacheMutex.Unlock()

	return map[string]any{
		"content": contentStr,
		"upgrade": args.Upgrade,
		"topic":   args.Topic,
		"layer":   "engine",
	}, nil
}

// GetRPCMethod retrieves detailed information about a JSON-RPC method.
func (em *ExecutionSpecsManager) GetRPCMethod(ctx context.Context, params json.RawMessage) (any, error) {
	var args struct {
		Method string `json:"method"`
	}

	if err := json.Unmarshal(params, &args); err != nil {
		return nil, fmt.Errorf("invalid parameters: %w", err)
	}

	if args.Method == "" {
		return nil, fmt.Errorf("method name is required")
	}

	// Ensure methods are loaded
	if err := em.loadAllMethods(); err != nil {
		return nil, fmt.Errorf("failed to load methods: %w", err)
	}

	em.cacheMutex.RLock()
	method, found := em.methodCache[args.Method]
	em.cacheMutex.RUnlock()

	if !found {
		return nil, fmt.Errorf("method not found: %s", args.Method)
	}

	return map[string]any{
		"method": method,
	}, nil
}

// ListRPCMethods returns a list of available JSON-RPC methods.
func (em *ExecutionSpecsManager) ListRPCMethods(ctx context.Context, params json.RawMessage) (any, error) {
	var args struct {
		Namespace string `json:"namespace,omitempty"`
	}

	if err := json.Unmarshal(params, &args); err != nil {
		return nil, fmt.Errorf("invalid parameters: %w", err)
	}

	if err := em.loadAllMethods(); err != nil {
		return nil, fmt.Errorf("failed to load methods: %w", err)
	}

	em.cacheMutex.RLock()
	defer em.cacheMutex.RUnlock()

	methods := make([]map[string]string, 0, len(em.methodCache))

	for name, method := range em.methodCache {
		// Filter by namespace if specified
		if args.Namespace != "" && !strings.HasPrefix(name, args.Namespace+"_") {
			continue
		}

		methods = append(methods, map[string]string{
			"name":    name,
			"summary": method.Summary,
		})
	}

	return map[string]any{
		"methods":   methods,
		"count":     len(methods),
		"namespace": args.Namespace,
	}, nil
}

// ListUpgrades returns all available Engine API upgrade names.
func (em *ExecutionSpecsManager) ListUpgrades(ctx context.Context) (any, error) {
	actualUpgrades := make([]string, 0, len(availableUpgrades))
	enginePath := filepath.Join(em.repoPath, "src", "engine")

	entries, readErr := os.ReadDir(enginePath)
	if readErr == nil {
		for _, entry := range entries {
			if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".md") {
				continue
			}

			name := strings.TrimSuffix(entry.Name(), ".md")

			for _, upgrade := range availableUpgrades {
				if name == upgrade {
					actualUpgrades = append(actualUpgrades, upgrade)

					break
				}
			}
		}
	}

	if len(actualUpgrades) == 0 {
		actualUpgrades = availableUpgrades
	}

	return map[string]any{
		"upgrades": actualUpgrades,
	}, nil
}

// SearchSpecs searches for a query string across execution API specifications.
func (em *ExecutionSpecsManager) SearchSpecs(ctx context.Context, params json.RawMessage) (any, error) {
	var args struct {
		Query   string `json:"query"`
		Upgrade string `json:"upgrade,omitempty"`
	}

	if err := json.Unmarshal(params, &args); err != nil {
		return nil, fmt.Errorf("invalid parameters: %w", err)
	}

	results := make([]map[string]any, 0, 10)
	queryLower := strings.ToLower(args.Query)
	re, reErr := regexp.Compile("(?i)" + regexp.QuoteMeta(args.Query))
	enginePath := filepath.Join(em.repoPath, "src", "engine")

	// Search Engine API markdown files
	entries, err := os.ReadDir(enginePath)
	if err == nil {
		for _, entry := range entries {
			if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".md") {
				continue
			}

			upgrade := strings.TrimSuffix(entry.Name(), ".md")
			if args.Upgrade != "" && upgrade != args.Upgrade {
				continue
			}

			filePath := filepath.Join(enginePath, entry.Name())

			content, readErr := os.ReadFile(filePath)
			if readErr != nil {
				continue
			}

			contentStr := string(content)
			if !strings.Contains(strings.ToLower(contentStr), queryLower) {
				continue
			}

			matches := em.extractMatches(content, contentStr, re, reErr)
			results = append(results, map[string]any{
				"layer":   "engine",
				"upgrade": upgrade,
				"matches": matches,
			})
		}
	}

	// Search eth YAML files for method names and summaries
	if loadErr := em.loadAllMethods(); loadErr == nil {
		em.cacheMutex.RLock()

		for name, method := range em.methodCache {
			if strings.Contains(strings.ToLower(name), queryLower) ||
				strings.Contains(strings.ToLower(method.Summary), queryLower) {
				results = append(results, map[string]any{
					"layer":   "eth",
					"method":  name,
					"summary": method.Summary,
				})
			}
		}

		em.cacheMutex.RUnlock()
	}

	return map[string]any{
		"query":   args.Query,
		"results": results,
		"count":   len(results),
	}, nil
}

// GetEthCategory retrieves the content of an eth namespace category YAML file.
func (em *ExecutionSpecsManager) GetEthCategory(ctx context.Context, params json.RawMessage) (any, error) {
	var args struct {
		Category string `json:"category"`
	}

	if err := json.Unmarshal(params, &args); err != nil {
		return nil, fmt.Errorf("invalid parameters: %w", err)
	}

	if args.Category == "" {
		return nil, fmt.Errorf("category is required")
	}

	filePath := filepath.Join(em.repoPath, "src", "eth", args.Category+".yaml")

	content, err := os.ReadFile(filePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("category not found: %s", args.Category)
		}

		return nil, fmt.Errorf("failed to read category: %w", err)
	}

	methods, parseErr := ParseOpenRPCFile(filePath)
	if parseErr != nil {
		// Return raw content if parsing fails
		return map[string]any{
			"category":   args.Category,
			"rawContent": string(content),
			"layer":      "eth",
			"parseError": parseErr.Error(),
		}, parseErr
	}

	return map[string]any{
		"category": args.Category,
		"methods":  methods,
		"layer":    "eth",
	}, nil
}

// isValidUpgrade checks if an upgrade name is in the list of known upgrades.
func (em *ExecutionSpecsManager) isValidUpgrade(upgrade string) bool {
	for _, u := range availableUpgrades {
		if u == upgrade {
			return true
		}
	}

	return false
}

// loadAllMethods parses all YAML files and populates the method cache.
func (em *ExecutionSpecsManager) loadAllMethods() error {
	em.cacheMutex.RLock()

	if em.methodsReady {
		em.cacheMutex.RUnlock()

		return nil
	}

	em.cacheMutex.RUnlock()

	em.cacheMutex.Lock()
	defer em.cacheMutex.Unlock()

	// Double-check after acquiring write lock
	if em.methodsReady {
		return nil
	}

	// Load from eth namespace
	ethPath := filepath.Join(em.repoPath, "src", "eth")

	entries, err := os.ReadDir(ethPath)
	if err != nil {
		return fmt.Errorf("failed to read eth directory: %w", err)
	}

	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".yaml") {
			continue
		}

		filePath := filepath.Join(ethPath, entry.Name())

		methods, parseErr := ParseOpenRPCFile(filePath)
		if parseErr != nil {
			em.log.WithError(parseErr).WithField("file", entry.Name()).Debug("Failed to parse YAML file")

			continue
		}

		for _, method := range methods {
			if method.Name != "" {
				em.methodCache[method.Name] = method
			}
		}
	}

	// Load from engine/openrpc/methods if it exists
	engineMethodsPath := filepath.Join(em.repoPath, "src", "engine", "openrpc", "methods")

	if engineEntries, readErr := os.ReadDir(engineMethodsPath); readErr == nil {
		for _, entry := range engineEntries {
			if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".yaml") {
				continue
			}

			filePath := filepath.Join(engineMethodsPath, entry.Name())

			methods, parseErr := ParseOpenRPCFile(filePath)
			if parseErr != nil {
				continue
			}

			for _, method := range methods {
				if method.Name != "" {
					em.methodCache[method.Name] = method
				}
			}
		}
	}

	em.methodsReady = true
	em.log.WithField("count", len(em.methodCache)).Info("Loaded RPC methods")

	return nil
}

// extractMatches extracts matching lines with context from content.
func (em *ExecutionSpecsManager) extractMatches(
	content []byte,
	contentStr string,
	re *regexp.Regexp,
	reErr error,
) []string {
	matches := make([]string, 0, 5)

	if reErr != nil {
		return matches
	}

	scanner := bufio.NewScanner(bytes.NewReader(content))
	lineNum := 0
	lines := strings.Split(contentStr, "\n")

	for scanner.Scan() {
		lineNum++
		line := scanner.Text()

		if re.MatchString(line) {
			contextStart := max(0, lineNum-3)
			contextEnd := min(lineNum+2, len(lines))
			contextLines := strings.Join(lines[contextStart:contextEnd], "\n")
			matches = append(matches, fmt.Sprintf("Line %d:\n%s", lineNum, contextLines))

			if len(matches) >= 5 {
				break
			}
		}
	}

	return matches
}
