// Package main contains YAML parsing utilities for OpenRPC specification files
// from the ethereum/execution-apis repository.
package main

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

// OpenRPCMethod represents a parsed JSON-RPC method definition from an OpenRPC spec.
type OpenRPCMethod struct {
	Name         string              `yaml:"name" json:"name"`
	Summary      string              `yaml:"summary" json:"summary"`
	Params       []OpenRPCParam      `yaml:"params" json:"params"`
	Result       OpenRPCResult       `yaml:"result" json:"result"`
	Errors       []OpenRPCError      `yaml:"errors,omitempty" json:"errors,omitempty"`
	Examples     []OpenRPCExample    `yaml:"examples,omitempty" json:"examples,omitempty"`
	ExternalDocs *OpenRPCExternalDoc `yaml:"externalDocs,omitempty" json:"externalDocs,omitempty"`
}

// OpenRPCParam represents a parameter in a JSON-RPC method.
type OpenRPCParam struct {
	Name     string         `yaml:"name" json:"name"`
	Required bool           `yaml:"required,omitempty" json:"required,omitempty"`
	Schema   map[string]any `yaml:"schema" json:"schema"`
}

// OpenRPCResult represents the result of a JSON-RPC method.
type OpenRPCResult struct {
	Name   string         `yaml:"name" json:"name"`
	Schema map[string]any `yaml:"schema" json:"schema"`
}

// OpenRPCError represents an error that can be returned by a JSON-RPC method.
type OpenRPCError struct {
	Code    int    `yaml:"code" json:"code"`
	Message string `yaml:"message" json:"message"`
}

// OpenRPCExample represents an example request/response for a JSON-RPC method.
type OpenRPCExample struct {
	Name   string `yaml:"name" json:"name"`
	Params []any  `yaml:"params" json:"params"`
	Result any    `yaml:"result" json:"result"`
}

// OpenRPCExternalDoc represents a link to external documentation.
type OpenRPCExternalDoc struct {
	Description string `yaml:"description" json:"description"`
	URL         string `yaml:"url" json:"url"`
}

// ParseOpenRPCFile parses a YAML file containing OpenRPC method definitions.
// Returns a slice of methods found in the file.
func ParseOpenRPCFile(filePath string) ([]OpenRPCMethod, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read file: %w", err)
	}

	// The file may contain a single method or an array of methods
	var methods []OpenRPCMethod

	// First try to parse as array
	if unmarshalErr := yaml.Unmarshal(data, &methods); unmarshalErr == nil && len(methods) > 0 {
		return methods, nil
	}

	// Try to parse as a single method
	var method OpenRPCMethod
	if unmarshalErr := yaml.Unmarshal(data, &method); unmarshalErr == nil && method.Name != "" {
		return []OpenRPCMethod{method}, nil
	}

	// Try to parse as an object with a "methods" key
	var wrapper struct {
		Methods []OpenRPCMethod `yaml:"methods"`
	}

	if unmarshalErr := yaml.Unmarshal(data, &wrapper); unmarshalErr == nil && len(wrapper.Methods) > 0 {
		return wrapper.Methods, nil
	}

	// Try parsing as YAML documents separated by ---
	file, openErr := os.Open(filePath)
	if openErr != nil {
		return nil, fmt.Errorf("failed to open file: %w", openErr)
	}
	defer file.Close()

	decoder := yaml.NewDecoder(file)
	methods = make([]OpenRPCMethod, 0, 10)

	for {
		var m OpenRPCMethod
		if decodeErr := decoder.Decode(&m); decodeErr != nil {
			break
		}

		if m.Name != "" {
			methods = append(methods, m)
		}
	}

	if len(methods) > 0 {
		return methods, nil
	}

	return nil, fmt.Errorf("no valid OpenRPC methods found in file")
}

// ParseOpenRPCSchema parses a YAML schema definition file.
// Returns a map of schema definitions found in the file.
func ParseOpenRPCSchema(filePath string) (map[string]any, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read file: %w", err)
	}

	var schemas map[string]any
	if err := yaml.Unmarshal(data, &schemas); err != nil {
		return nil, fmt.Errorf("failed to parse YAML: %w", err)
	}

	return schemas, nil
}
