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

var availableForks = []string{"phase0", "altair", "bellatrix", "capella", "deneb", "electra", "fulu"}

type SpecsManager struct {
	log         logrus.FieldLogger
	branch      string
	repoPath    string
	cache       map[string]string
	cacheMutex  sync.RWMutex
	initialized bool
}

func NewSpecsManager(log logrus.FieldLogger, branch string) *SpecsManager {
	homeDir, _ := os.UserHomeDir()
	return &SpecsManager{
		log:      log.WithField("component", "specs_manager"),
		branch:   branch,
		repoPath: filepath.Join(homeDir, ".ethereum-specs"),
		cache:    make(map[string]string, 100),
	}
}

func (sm *SpecsManager) Initialize(ctx context.Context) error {
	return sm.InitializeWithAutoUpdate(ctx, true)
}

func (sm *SpecsManager) InitializeWithAutoUpdate(ctx context.Context, autoUpdate bool) error {
	sm.log.Info("Initializing specs repository")

	if _, err := os.Stat(sm.repoPath); os.IsNotExist(err) {
		// Repository doesn't exist - must clone synchronously
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
		// Repository exists and auto-update is enabled - update in background
		sm.log.Info("Repository exists, starting background update")

		// Start update in a goroutine so we don't block initialization
		go func() {
			sm.log.Info("Starting background repository update")

			// Use a new context that won't be cancelled when the request completes
			updateCtx := context.Background()

			cmd := exec.CommandContext(updateCtx, "git", "fetch", "origin")
			cmd.Dir = sm.repoPath
			if output, err := cmd.CombinedOutput(); err != nil {
				sm.log.WithError(err).WithField("output", string(output)).Warn("Failed to fetch updates")
				return
			}

			cmd = exec.CommandContext(updateCtx, "git", "checkout", sm.branch)
			cmd.Dir = sm.repoPath
			if output, err := cmd.CombinedOutput(); err != nil {
				sm.log.WithError(err).WithField("output", string(output)).Warn("Failed to checkout branch")
				return
			}

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

func (sm *SpecsManager) GetSpec(ctx context.Context, params json.RawMessage) (interface{}, error) {
	var args struct {
		Fork  string `json:"fork"`
		Topic string `json:"topic"`
	}

	if err := json.Unmarshal(params, &args); err != nil {
		return nil, fmt.Errorf("invalid parameters: %w", err)
	}

	if !sm.isValidFork(args.Fork) {
		return nil, fmt.Errorf("invalid fork: %s", args.Fork)
	}

	specPath := filepath.Join(sm.repoPath, "specs", args.Fork, args.Topic+".md")

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

	content, err := os.ReadFile(specPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("spec not found: %s/%s", args.Fork, args.Topic)
		}
		return nil, fmt.Errorf("failed to read spec: %w", err)
	}

	contentStr := string(content)

	sm.cacheMutex.Lock()
	sm.cache[specPath] = contentStr
	sm.cacheMutex.Unlock()

	return map[string]interface{}{
		"content": contentStr,
		"fork":    args.Fork,
		"topic":   args.Topic,
	}, nil
}

func (sm *SpecsManager) SearchSpecs(ctx context.Context, params json.RawMessage) (interface{}, error) {
	var args struct {
		Query string `json:"query"`
		Fork  string `json:"fork,omitempty"`
	}

	if err := json.Unmarshal(params, &args); err != nil {
		return nil, fmt.Errorf("invalid parameters: %w", err)
	}

	if args.Fork != "" && !sm.isValidFork(args.Fork) {
		return nil, fmt.Errorf("invalid fork: %s", args.Fork)
	}

	results := []map[string]interface{}{}
	searchForks := availableForks
	if args.Fork != "" {
		searchForks = []string{args.Fork}
	}

	queryLower := strings.ToLower(args.Query)
	re, reErr := regexp.Compile("(?i)" + regexp.QuoteMeta(args.Query))

	for _, fork := range searchForks {
		forkPath := filepath.Join(sm.repoPath, "specs", fork)

		entries, err := os.ReadDir(forkPath)
		if err != nil {
			continue
		}

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
			if !strings.Contains(strings.ToLower(contentStr), queryLower) {
				continue
			}

			matches := []string{}
			if reErr == nil {
				scanner := bufio.NewScanner(bytes.NewReader(content))
				lineNum := 0
				for scanner.Scan() {
					lineNum++
					line := scanner.Text()
					if re.MatchString(line) {
						contextStart := maxInt(0, lineNum-2)
						contextEnd := minInt(lineNum+2, len(strings.Split(contentStr, "\n")))

						lines := strings.Split(contentStr, "\n")
						context := strings.Join(lines[contextStart:contextEnd], "\n")
						matches = append(matches, fmt.Sprintf("Line %d:\n%s", lineNum, context))

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

func (sm *SpecsManager) ListForks(ctx context.Context) (interface{}, error) {
	actualForks := []string{}

	specsPath := filepath.Join(sm.repoPath, "specs")
	entries, err := os.ReadDir(specsPath)
	if err != nil {
		return map[string]interface{}{
			"forks": availableForks,
		}, nil
	}

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

	if len(actualForks) == 0 {
		actualForks = availableForks
	}

	return map[string]interface{}{
		"forks": actualForks,
	}, nil
}

func (sm *SpecsManager) CompareForks(ctx context.Context, params json.RawMessage) (interface{}, error) {
	var args struct {
		Fork1 string `json:"fork1"`
		Fork2 string `json:"fork2"`
		Topic string `json:"topic"`
	}

	if err := json.Unmarshal(params, &args); err != nil {
		return nil, fmt.Errorf("invalid parameters: %w", err)
	}

	if !sm.isValidFork(args.Fork1) || !sm.isValidFork(args.Fork2) {
		return nil, fmt.Errorf("invalid fork specified")
	}

	spec1Path := filepath.Join(sm.repoPath, "specs", args.Fork1, args.Topic+".md")
	spec2Path := filepath.Join(sm.repoPath, "specs", args.Fork2, args.Topic+".md")

	content1, err1 := os.ReadFile(spec1Path)
	content2, err2 := os.ReadFile(spec2Path)

	result := map[string]interface{}{
		"fork1": args.Fork1,
		"fork2": args.Fork2,
		"topic": args.Topic,
	}

	if err1 != nil && err2 != nil {
		return nil, fmt.Errorf("topic not found in either fork")
	}

	if err1 != nil {
		result["status"] = fmt.Sprintf("Topic only exists in %s", args.Fork2)
		result["content_fork2"] = string(content2)
	} else if err2 != nil {
		result["status"] = fmt.Sprintf("Topic only exists in %s", args.Fork1)
		result["content_fork1"] = string(content1)
	} else {
		lines1 := strings.Split(string(content1), "\n")
		lines2 := strings.Split(string(content2), "\n")

		diff := sm.computeSimpleDiff(lines1, lines2)
		result["status"] = "Both forks have this topic"
		result["differences"] = diff
	}

	return result, nil
}

func (sm *SpecsManager) GetConstant(ctx context.Context, params json.RawMessage) (interface{}, error) {
	var args struct {
		Name string `json:"name"`
		Fork string `json:"fork,omitempty"`
	}

	if err := json.Unmarshal(params, &args); err != nil {
		return nil, fmt.Errorf("invalid parameters: %w", err)
	}

	searchForks := []string{}
	if args.Fork != "" {
		if !sm.isValidFork(args.Fork) {
			return nil, fmt.Errorf("invalid fork: %s", args.Fork)
		}
		searchForks = []string{args.Fork}
	} else {
		for i := len(availableForks) - 1; i >= 0; i-- {
			searchForks = append(searchForks, availableForks[i])
		}
	}

	results := map[string]interface{}{}
	constantPattern := regexp.MustCompile(fmt.Sprintf(`(?m)^\|\s*%s\s*\|\s*([^|]+)\s*\|`, regexp.QuoteMeta(args.Name)))

	for _, fork := range searchForks {
		forkPath := filepath.Join(sm.repoPath, "specs", fork)
		entries, err := os.ReadDir(forkPath)
		if err != nil {
			continue
		}

		for _, entry := range entries {
			if !strings.HasSuffix(entry.Name(), ".md") {
				continue
			}

			filePath := filepath.Join(forkPath, entry.Name())
			content, err := os.ReadFile(filePath)
			if err != nil {
				continue
			}

			matches := constantPattern.FindAllStringSubmatch(string(content), -1)
			if len(matches) > 0 {
				value := strings.TrimSpace(matches[0][1])

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

func (sm *SpecsManager) isValidFork(fork string) bool {
	for _, f := range availableForks {
		if f == fork {
			return true
		}
	}
	return false
}

func (sm *SpecsManager) computeSimpleDiff(lines1, lines2 []string) []map[string]interface{} {
	diff := []map[string]interface{}{}

	i, j := 0, 0
	for i < len(lines1) || j < len(lines2) {
		if i >= len(lines1) {
			diff = append(diff, map[string]interface{}{
				"type":     "added",
				"line":     lines2[j],
				"position": j + 1,
			})
			j++
		} else if j >= len(lines2) {
			diff = append(diff, map[string]interface{}{
				"type":     "removed",
				"line":     lines1[i],
				"position": i + 1,
			})
			i++
		} else if lines1[i] == lines2[j] {
			i++
			j++
		} else {
			lookahead := 5
			found := false

			for k := 1; k <= lookahead && i+k < len(lines1); k++ {
				for l := 0; l <= lookahead && j+l < len(lines2); l++ {
					if lines1[i+k] == lines2[j+l] {
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

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}
