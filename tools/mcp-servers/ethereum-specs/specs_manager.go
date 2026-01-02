// Package main contains the specs repository management and tool implementations
// for the Ethereum Specs MCP server. This file handles consensus layer specifications
// from the ethereum/consensus-specs repository.
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

// availableForks defines all Ethereum consensus fork names in chronological order.
// These correspond to directories in the ethereum/consensus-specs repository.
var availableForks = []string{"phase0", "altair", "bellatrix", "capella", "deneb", "electra", "fulu"}

// SpecsManager is an alias for ConsensusSpecsManager for backwards compatibility.
type SpecsManager = ConsensusSpecsManager

// NewSpecsManager is an alias for NewConsensusSpecsManager for backwards compatibility.
func NewSpecsManager(log logrus.FieldLogger, branch string) *ConsensusSpecsManager {
	return NewConsensusSpecsManager(log, branch)
}

// ConsensusSpecsManager handles all interactions with the Ethereum consensus specifications
// repository. It manages git operations, caching, and provides methods to query specification
// content from ethereum/consensus-specs.
type ConsensusSpecsManager struct {
	log         logrus.FieldLogger
	branch      string            // Git branch to track (e.g., "master", "dev")
	repoPath    string            // Local path to the cloned repository
	cache       map[string]string // In-memory cache of spec content to reduce disk I/O
	cacheMutex  sync.RWMutex      // Protects concurrent access to the cache
	initialized bool              // Tracks whether initialization has completed
}

// NewConsensusSpecsManager creates a new instance of the consensus specs manager.
// The repository will be cloned locally to keep everything self-contained.
func NewConsensusSpecsManager(log logrus.FieldLogger, branch string) *ConsensusSpecsManager {
	// Get the actual binary path (resolving any symlinks)
	execPath, err := os.Executable()
	if err != nil {
		log.WithError(err).Fatal("Failed to get executable path")
	}

	// Resolve symlinks to get the real path
	realPath, err := filepath.EvalSymlinks(execPath)
	if err != nil {
		realPath = execPath
	}

	// The binary is at: .../ethereum-specs/bin/ethereum-specs-mcp
	// We want the repo at: .../ethereum-specs/.consensus-specs
	// So go up two levels from the binary and then into ethereum-specs
	baseDir := filepath.Dir(filepath.Dir(realPath))

	repoPath := filepath.Join(baseDir, ".consensus-specs")
	log.WithField("repo_path", repoPath).Info("Using repository path")

	return &ConsensusSpecsManager{
		log:      log.WithField("component", "consensus_specs_manager"),
		branch:   branch,
		repoPath: repoPath,
		cache:    make(map[string]string, 100), // Pre-allocate for ~100 cached specs
	}
}

// Initialize is a convenience wrapper that always enables auto-update.
// Deprecated: Use InitializeWithAutoUpdate directly for better control.
func (sm *ConsensusSpecsManager) Initialize(ctx context.Context) error {
	return sm.InitializeWithAutoUpdate(ctx, true)
}

// InitializeWithAutoUpdate prepares the specs repository for use.
// If the repository doesn't exist, it will be cloned synchronously.
// If it exists and autoUpdate is true, updates will run in the background.
func (sm *ConsensusSpecsManager) InitializeWithAutoUpdate(ctx context.Context, autoUpdate bool) error {
	sm.log.Info("Initializing specs repository")

	if _, err := os.Stat(sm.repoPath); os.IsNotExist(err) {
		// First-time setup: must complete clone before server can start
		sm.log.Info("Cloning ethereum/consensus-specs repository")
		cmd := exec.CommandContext(ctx, "git", "clone",
			"--branch", sm.branch,
			"https://github.com/ethereum/consensus-specs.git",
			sm.repoPath)

		if output, err := cmd.CombinedOutput(); err != nil {
			return fmt.Errorf("failed to clone repository: %w\nOutput: %s", err, output)
		}
		sm.log.Info("Repository cloned successfully")
	} else if autoUpdate {
		// Repository exists: update in background to avoid blocking server startup
		sm.log.Info("Repository exists, starting background update")

		// Launch update in goroutine for non-blocking operation
		go func() {
			sm.log.Info("Starting background repository update")

			// Create independent context to survive parent cancellation
			updateCtx := context.Background()

			// Fetch latest changes from remote
			cmd := exec.CommandContext(updateCtx, "git", "fetch", "origin")
			cmd.Dir = sm.repoPath
			if output, err := cmd.CombinedOutput(); err != nil {
				sm.log.WithError(err).WithField("output", string(output)).Warn("Failed to fetch updates")
				return
			}

			// Ensure we're on the correct branch
			cmd = exec.CommandContext(updateCtx, "git", "checkout", sm.branch)
			cmd.Dir = sm.repoPath
			if output, err := cmd.CombinedOutput(); err != nil {
				sm.log.WithError(err).WithField("output", string(output)).Warn("Failed to checkout branch")
				return
			}

			// Pull latest changes
			cmd = exec.CommandContext(updateCtx, "git", "pull", "origin", sm.branch)
			cmd.Dir = sm.repoPath
			if output, err := cmd.CombinedOutput(); err != nil {
				sm.log.WithError(err).WithField("output", string(output)).Warn("Failed to pull updates")
				return
			}

			sm.log.Info("Background repository update completed successfully")
		}()
	} else {
		sm.log.Info("Repository exists, skipping update (auto-update disabled)")
	}

	sm.initialized = true
	sm.log.Info("Specs repository initialized successfully")
	return nil
}

// GetSpec retrieves the content of a specific specification document.
// The content is cached after first access to improve performance.
func (sm *ConsensusSpecsManager) GetSpec(ctx context.Context, params json.RawMessage) (interface{}, error) {
	var args struct {
		Fork  string `json:"fork"`
		Topic string `json:"topic"`
	}

	if err := json.Unmarshal(params, &args); err != nil {
		return nil, fmt.Errorf("invalid parameters: %w", err)
	}

	// Validate fork name against known forks
	if !sm.isValidFork(args.Fork) {
		return nil, fmt.Errorf("invalid fork: %s", args.Fork)
	}

	// Build path to the specification file
	specPath := filepath.Join(sm.repoPath, "specs", args.Fork, args.Topic+".md")

	// Check cache first to avoid repeated disk reads
	sm.cacheMutex.RLock()
	if content, ok := sm.cache[specPath]; ok {
		sm.cacheMutex.RUnlock()
		return map[string]interface{}{
			"content": content,
			"fork":    args.Fork,
			"topic":   args.Topic,
		}, nil
	}
	sm.cacheMutex.RUnlock()

	// Read from disk if not cached
	content, err := os.ReadFile(specPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("spec not found: %s/%s", args.Fork, args.Topic)
		}
		return nil, fmt.Errorf("failed to read spec: %w", err)
	}

	contentStr := string(content)

	// Update cache with new content
	sm.cacheMutex.Lock()
	sm.cache[specPath] = contentStr
	sm.cacheMutex.Unlock()

	return map[string]interface{}{
		"content": contentStr,
		"fork":    args.Fork,
		"topic":   args.Topic,
	}, nil
}

// SearchSpecs searches for a query string across specification files.
// It returns matching files with context around the matched lines.
func (sm *ConsensusSpecsManager) SearchSpecs(ctx context.Context, params json.RawMessage) (interface{}, error) {
	var args struct {
		Query string `json:"query"`
		Fork  string `json:"fork,omitempty"` // Optional: limit to specific fork
	}

	if err := json.Unmarshal(params, &args); err != nil {
		return nil, fmt.Errorf("invalid parameters: %w", err)
	}

	// Validate fork if specified
	if args.Fork != "" && !sm.isValidFork(args.Fork) {
		return nil, fmt.Errorf("invalid fork: %s", args.Fork)
	}

	results := []map[string]interface{}{}

	// Determine which forks to search
	searchForks := availableForks
	if args.Fork != "" {
		searchForks = []string{args.Fork}
	}

	// Prepare search patterns for case-insensitive matching
	queryLower := strings.ToLower(args.Query)
	re, reErr := regexp.Compile("(?i)" + regexp.QuoteMeta(args.Query))

	// Search through each fork's specifications
	for _, fork := range searchForks {
		forkPath := filepath.Join(sm.repoPath, "specs", fork)

		entries, err := os.ReadDir(forkPath)
		if err != nil {
			continue // Skip if fork directory doesn't exist
		}

		// Check each markdown file in the fork
		for _, entry := range entries {
			if !strings.HasSuffix(entry.Name(), ".md") {
				continue
			}

			filePath := filepath.Join(forkPath, entry.Name())
			content, err := os.ReadFile(filePath)
			if err != nil {
				continue
			}

			contentStr := string(content)

			// Quick check if file contains the query
			if !strings.Contains(strings.ToLower(contentStr), queryLower) {
				continue
			}

			// Extract matching lines with context
			matches := []string{}
			if reErr == nil {
				scanner := bufio.NewScanner(bytes.NewReader(content))
				lineNum := 0
				for scanner.Scan() {
					lineNum++
					line := scanner.Text()
					if re.MatchString(line) {
						// Include 2 lines before and after for context
						contextStart := maxInt(0, lineNum-2)
						contextEnd := minInt(lineNum+2, len(strings.Split(contentStr, "\n")))

						lines := strings.Split(contentStr, "\n")
						context := strings.Join(lines[contextStart:contextEnd], "\n")
						matches = append(matches, fmt.Sprintf("Line %d:\n%s", lineNum, context))

						// Limit matches per file to prevent overwhelming output
						if len(matches) >= 5 {
							break
						}
					}
				}
			}

			topic := strings.TrimSuffix(entry.Name(), ".md")
			results = append(results, map[string]interface{}{
				"fork":    fork,
				"topic":   topic,
				"matches": matches,
			})
		}
	}

	return map[string]interface{}{
		"query":   args.Query,
		"results": results,
		"count":   len(results),
	}, nil
}

// ListForks returns all available fork names from the repository.
// It checks the actual directories present rather than just returning the hardcoded list.
func (sm *ConsensusSpecsManager) ListForks(ctx context.Context) (interface{}, error) {
	actualForks := []string{}

	// Check which forks actually exist in the repository
	specsPath := filepath.Join(sm.repoPath, "specs")
	entries, err := os.ReadDir(specsPath)
	if err != nil {
		// If we can't read the directory, return the known fork list
		return map[string]interface{}{
			"forks": availableForks,
		}, nil
	}

	// Match directory names against known forks
	for _, entry := range entries {
		if entry.IsDir() {
			for _, fork := range availableForks {
				if entry.Name() == fork {
					actualForks = append(actualForks, fork)
					break
				}
			}
		}
	}

	// Fallback to known forks if none found (shouldn't happen)
	if len(actualForks) == 0 {
		actualForks = availableForks
	}

	return map[string]interface{}{
		"forks": actualForks,
	}, nil
}

// CompareForks generates a diff between the same topic across two different forks.
// This helps understand how specifications evolved between protocol upgrades.
func (sm *ConsensusSpecsManager) CompareForks(ctx context.Context, params json.RawMessage) (interface{}, error) {
	var args struct {
		Fork1 string `json:"fork1"`
		Fork2 string `json:"fork2"`
		Topic string `json:"topic"`
	}

	if err := json.Unmarshal(params, &args); err != nil {
		return nil, fmt.Errorf("invalid parameters: %w", err)
	}

	// Validate both forks
	if !sm.isValidFork(args.Fork1) || !sm.isValidFork(args.Fork2) {
		return nil, fmt.Errorf("invalid fork specified")
	}

	// Build paths to both specification files
	spec1Path := filepath.Join(sm.repoPath, "specs", args.Fork1, args.Topic+".md")
	spec2Path := filepath.Join(sm.repoPath, "specs", args.Fork2, args.Topic+".md")

	// Read both files (errors handled below)
	content1, err1 := os.ReadFile(spec1Path)
	content2, err2 := os.ReadFile(spec2Path)

	result := map[string]interface{}{
		"fork1": args.Fork1,
		"fork2": args.Fork2,
		"topic": args.Topic,
	}

	// Handle cases where topic doesn't exist in one or both forks
	if err1 != nil && err2 != nil {
		return nil, fmt.Errorf("topic not found in either fork")
	}

	if err1 != nil {
		// Topic only exists in fork2 (new in this fork)
		result["status"] = fmt.Sprintf("Topic only exists in %s", args.Fork2)
		result["content_fork2"] = string(content2)
	} else if err2 != nil {
		// Topic only exists in fork1 (removed in fork2)
		result["status"] = fmt.Sprintf("Topic only exists in %s", args.Fork1)
		result["content_fork1"] = string(content1)
	} else {
		// Topic exists in both: compute diff
		lines1 := strings.Split(string(content1), "\n")
		lines2 := strings.Split(string(content2), "\n")

		diff := sm.computeSimpleDiff(lines1, lines2)
		result["status"] = "Both forks have this topic"
		result["differences"] = diff
	}

	return result, nil
}

// GetConstant searches for and retrieves the value of a protocol constant.
// Constants are typically defined in markdown tables within the specifications.
func (sm *ConsensusSpecsManager) GetConstant(ctx context.Context, params json.RawMessage) (interface{}, error) {
	var args struct {
		Name string `json:"name"`
		Fork string `json:"fork,omitempty"` // Optional: specific fork
	}

	if err := json.Unmarshal(params, &args); err != nil {
		return nil, fmt.Errorf("invalid parameters: %w", err)
	}

	// Determine which forks to search
	searchForks := []string{}
	if args.Fork != "" {
		if !sm.isValidFork(args.Fork) {
			return nil, fmt.Errorf("invalid fork: %s", args.Fork)
		}
		searchForks = []string{args.Fork}
	} else {
		// Search newest forks first when no fork specified
		for i := len(availableForks) - 1; i >= 0; i-- {
			searchForks = append(searchForks, availableForks[i])
		}
	}

	results := map[string]interface{}{}

	// Pattern to match constants in markdown tables
	// Format: | CONSTANT_NAME | value | description |
	constantPattern := regexp.MustCompile(fmt.Sprintf(`(?m)^\|\s*%s\s*\|\s*([^|]+)\s*\|`, regexp.QuoteMeta(args.Name)))

	// Search through each fork's specifications
	for _, fork := range searchForks {
		forkPath := filepath.Join(sm.repoPath, "specs", fork)
		entries, err := os.ReadDir(forkPath)
		if err != nil {
			continue
		}

		// Check each specification file
		for _, entry := range entries {
			if !strings.HasSuffix(entry.Name(), ".md") {
				continue
			}

			filePath := filepath.Join(forkPath, entry.Name())
			content, err := os.ReadFile(filePath)
			if err != nil {
				continue
			}

			// Look for the constant in the file
			matches := constantPattern.FindAllStringSubmatch(string(content), -1)
			if len(matches) > 0 {
				value := strings.TrimSpace(matches[0][1])

				// Organize results by fork and topic
				if _, exists := results[fork]; !exists {
					results[fork] = map[string]interface{}{}
				}

				forkResults := results[fork].(map[string]interface{})
				topic := strings.TrimSuffix(entry.Name(), ".md")
				forkResults[topic] = value
			}
		}
	}

	if len(results) == 0 {
		return nil, fmt.Errorf("constant %s not found", args.Name)
	}

	return map[string]interface{}{
		"constant": args.Name,
		"values":   results,
	}, nil
}

// isValidFork checks if a fork name is in the list of known forks.
func (sm *ConsensusSpecsManager) isValidFork(fork string) bool {
	for _, f := range availableForks {
		if f == fork {
			return true
		}
	}
	return false
}

// computeSimpleDiff generates a line-by-line diff between two text files.
// It uses a simple algorithm with lookahead to detect insertions, deletions, and changes.
// The diff is limited to 100 changes to prevent overwhelming output.
func (sm *ConsensusSpecsManager) computeSimpleDiff(lines1, lines2 []string) []map[string]interface{} {
	diff := []map[string]interface{}{}

	i, j := 0, 0
	for i < len(lines1) || j < len(lines2) {
		// Handle end of file cases
		if i >= len(lines1) {
			// Remaining lines in file2 are additions
			diff = append(diff, map[string]interface{}{
				"type":     "added",
				"line":     lines2[j],
				"position": j + 1,
			})
			j++
		} else if j >= len(lines2) {
			// Remaining lines in file1 are deletions
			diff = append(diff, map[string]interface{}{
				"type":     "removed",
				"line":     lines1[i],
				"position": i + 1,
			})
			i++
		} else if lines1[i] == lines2[j] {
			// Lines match, advance both pointers
			i++
			j++
		} else {
			// Lines differ: use lookahead to find next matching lines
			lookahead := 5
			found := false

			// Try to find matching lines within lookahead window
			for k := 1; k <= lookahead && i+k < len(lines1); k++ {
				for l := 0; l <= lookahead && j+l < len(lines2); l++ {
					if lines1[i+k] == lines2[j+l] {
						// Found match: mark intervening lines as removed/added
						for m := 0; m < k; m++ {
							diff = append(diff, map[string]interface{}{
								"type":     "removed",
								"line":     lines1[i+m],
								"position": i + m + 1,
							})
						}
						for m := 0; m < l; m++ {
							diff = append(diff, map[string]interface{}{
								"type":     "added",
								"line":     lines2[j+m],
								"position": j + m + 1,
							})
						}
						i += k
						j += l
						found = true
						break
					}
				}
				if found {
					break
				}
			}

			// No match found within lookahead: treat as changed line
			if !found {
				diff = append(diff, map[string]interface{}{
					"type":     "changed",
					"from":     lines1[i],
					"to":       lines2[j],
					"position": i + 1,
				})
				i++
				j++
			}
		}

		// Limit diff size to prevent excessive output
		if len(diff) > 100 {
			diff = append(diff, map[string]interface{}{
				"type":    "truncated",
				"message": "Diff truncated after 100 changes",
			})
			break
		}
	}

	return diff
}

// minInt returns the smaller of two integers.
func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// maxInt returns the larger of two integers.
func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}
