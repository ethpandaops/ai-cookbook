// Package main contains fork mapping utilities that define the correspondence
// between consensus layer fork names and execution layer upgrade names.
package main

// ForkMapping represents the correspondence between CL and EL naming conventions.
type ForkMapping struct {
	ConsensusFork    string `json:"consensusFork"`
	ExecutionUpgrade string `json:"executionUpgrade"`
	Description      string `json:"description"`
	Activated        string `json:"activated,omitempty"`
}

// forkMappings defines the canonical mapping between CL forks and EL upgrades.
// This list is ordered chronologically.
var forkMappings = []ForkMapping{
	{
		ConsensusFork:    "phase0",
		ExecutionUpgrade: "",
		Description:      "Beacon Chain launch, no EL changes",
		Activated:        "2020-12-01",
	},
	{
		ConsensusFork:    "altair",
		ExecutionUpgrade: "",
		Description:      "Beacon Chain upgrade, no EL changes",
		Activated:        "2021-10-27",
	},
	{
		ConsensusFork:    "bellatrix",
		ExecutionUpgrade: "paris",
		Description:      "The Merge",
		Activated:        "2022-09-15",
	},
	{
		ConsensusFork:    "capella",
		ExecutionUpgrade: "shanghai",
		Description:      "Withdrawals",
		Activated:        "2023-04-12",
	},
	{
		ConsensusFork:    "deneb",
		ExecutionUpgrade: "cancun",
		Description:      "EIP-4844 Blobs",
		Activated:        "2024-03-13",
	},
	{
		ConsensusFork:    "electra",
		ExecutionUpgrade: "prague",
		Description:      "Pectra upgrade",
	},
	{
		ConsensusFork:    "fulu",
		ExecutionUpgrade: "osaka",
		Description:      "Future upgrade",
	},
}

// GetForkMapping returns the full mapping table between CL forks and EL upgrades.
func GetForkMapping() []ForkMapping {
	return forkMappings
}

// GetExecutionUpgrade returns the EL upgrade name for a given CL fork.
// Returns empty string and false if the fork has no corresponding EL upgrade.
func GetExecutionUpgrade(consensusFork string) (string, bool) {
	for _, m := range forkMappings {
		if m.ConsensusFork == consensusFork {
			if m.ExecutionUpgrade == "" {
				return "", false
			}

			return m.ExecutionUpgrade, true
		}
	}

	return "", false
}

// GetConsensusFork returns the CL fork name for a given EL upgrade.
// Returns empty string and false if the upgrade is not found.
func GetConsensusFork(executionUpgrade string) (string, bool) {
	for _, m := range forkMappings {
		if m.ExecutionUpgrade == executionUpgrade {
			return m.ConsensusFork, true
		}
	}

	return "", false
}
