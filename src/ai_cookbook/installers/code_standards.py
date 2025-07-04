"""Code standards installer for PandaOps Cookbook."""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import shutil

from ..installers.base import BaseInstaller, InstallationResult
from ..utils.file_operations import (
    ensure_directory, copy_files, directory_exists,
    list_files, remove_directory, read_json_file,
    file_exists, read_text_file, write_text_file
)
from ..config.settings import CLAUDE_DIR, CLAUDE_STANDARDS_DIR

# Get the project root directory (ai-cookbook)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Markers for the ethPandaOps section in CLAUDE.md
SECTION_START_MARKER = "<!-- ETHPANDAOPS_STANDARDS_START -->"
SECTION_END_MARKER = "<!-- ETHPANDAOPS_STANDARDS_END -->"


class CodeStandardsInstaller(BaseInstaller):
    """Installer for Claude code standards integration."""
    
    def __init__(self):
        """Initialize code standards installer."""
        super().__init__(
            name="Code Standards",
            description="Install ethPandaOps code standards for Claude"
        )
        self.standards_source = PROJECT_ROOT / "claude-code" / "code-standards"
        self.claude_md_path = CLAUDE_DIR / "CLAUDE.md"
        
    def check_status(self) -> Dict[str, Any]:
        """Check installation status of code standards.
        
        Returns:
            Dictionary with status information:
            - installed: Whether standards are fully installed
            - standards_installed: Whether standard files are in place
            - claude_md_modified: Whether CLAUDE.md contains ethPandaOps section
            - installed_languages: List of installed language standards
            - config_version: Version from config.json if available
        """
        standards_installed = directory_exists(CLAUDE_STANDARDS_DIR) and \
                            len(list_files(CLAUDE_STANDARDS_DIR)) > 0
        claude_md_modified = self._check_claude_md_modified()
        
        installed_languages = []
        config_version = None
        
        if standards_installed:
            installed_languages = self._get_installed_languages()
            
            # Try to read config version
            config_path = CLAUDE_STANDARDS_DIR / "config.json"
            if file_exists(config_path):
                try:
                    config = read_json_file(config_path)
                    config_version = config.get("version")
                except Exception:
                    pass
        
        # Get available languages from source
        available_languages = []
        if directory_exists(self.standards_source):
            available_languages = self._get_available_languages()
        
        return {
            'installed': standards_installed and claude_md_modified,
            'standards_installed': standards_installed,
            'claude_md_modified': claude_md_modified,
            'installed_languages': installed_languages,
            'installed_items': installed_languages,  # For compatibility with recommended installer
            'available_languages': available_languages,
            'config_version': config_version,
            'standards_dir': str(CLAUDE_STANDARDS_DIR)
        }
        
    def install(self) -> InstallationResult:
        """Install all available languages.
        
        Returns:
            InstallationResult indicating success/failure
        """
        available_languages = self._get_available_languages()
        installed_languages = self._get_installed_languages()
        
        results = []
        for language in available_languages:
            if language not in installed_languages:
                result = self.install_language(language)
                results.append((language, result))
        
        successful = [lang for lang, result in results if result.success]
        failed = [lang for lang, result in results if not result.success]
        
        if not results:
            return InstallationResult(
                True,
                "All language standards are already installed"
            )
        
        if failed:
            return InstallationResult(
                False,
                f"Installed {len(successful)} languages, {len(failed)} failed",
                {'successful': successful, 'failed': failed}
            )
        
        return InstallationResult(
            True,
            f"Successfully installed {len(successful)} language standards",
            {'installed': successful}
        )
        
    def install_language(self, language: str) -> InstallationResult:
        """Install code standards for a specific language.
        
        Args:
            language: Language name (e.g., 'go', 'python')
            
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            # Validate prerequisites
            prereq_result = self.validate_prerequisites()
            if not prereq_result.success:
                return prereq_result
                
            # Check if language exists in source
            language_source = self.standards_source / language
            if not language_source.exists():
                return InstallationResult(
                    False,
                    f"Language '{language}' not found in source directory"
                )
                
            # Create required directories
            self.create_required_directories()
            language_target = CLAUDE_STANDARDS_DIR / language
            ensure_directory(language_target)
            
            # Back up existing installation if present
            backup_created = False
            if language_target.exists() and any(language_target.iterdir()):
                backup_path = self.backup_manager.create_backup(
                    language_target,
                    f"code_standards_{language}"
                )
                if backup_path:
                    backup_created = True
            
            # Copy specific language files
            copy_files(language_source, language_target)
            
            # Ensure CLAUDE.md modification only once
            if not self._check_claude_md_modified():
                claude_md_result = self._modify_claude_md()
                if not claude_md_result.success:
                    # Rollback language installation if CLAUDE.md modification fails
                    if language_target.exists():
                        shutil.rmtree(language_target)
                    return claude_md_result
            
            details = {
                'language': language,
                'target_dir': str(language_target),
                'claude_md_modified': self._check_claude_md_modified()
            }
            
            if backup_created:
                details['backup_created'] = str(backup_path)
            
            return InstallationResult(
                True,
                f"Successfully installed {language} code standards",
                details
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to install {language} standards: {str(e)}"
            )
            
    def uninstall_language(self, language: str) -> InstallationResult:
        """Uninstall code standards for a specific language.
        
        Args:
            language: Language name (e.g., 'go', 'python')
            
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            language_target = CLAUDE_STANDARDS_DIR / language
            
            if not language_target.exists():
                return InstallationResult(
                    True,
                    f"{language} code standards are not installed"
                )
            
            # Back up before removal
            backup_path = None
            try:
                backup_path = self.backup_manager.create_backup(
                    language_target,
                    f"code_standards_{language}_uninstall"
                )
            except Exception:
                # Continue without backup if backup fails
                pass
            
            # Remove language directory
            shutil.rmtree(language_target)
            
            # Check if we should remove CLAUDE.md section
            remaining_languages = self._get_installed_languages()
            if not remaining_languages:
                # No languages left, remove CLAUDE.md section
                claude_md_result = self._remove_claude_md_section()
                if not claude_md_result.success:
                    # Continue anyway, language was removed
                    pass
            
            details = {
                'language': language,
                'backup_created': str(backup_path) if backup_path else None
            }
            
            return InstallationResult(
                True,
                f"Successfully uninstalled {language} code standards",
                details
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to uninstall {language} standards: {str(e)}"
            )
            
    def uninstall(self) -> InstallationResult:
        """Uninstall all installed languages.
        
        Returns:
            InstallationResult indicating success/failure
        """
        installed_languages = self._get_installed_languages()
        
        if not installed_languages:
            return InstallationResult(
                True,
                "No language standards are installed"
            )
        
        results = []
        for language in installed_languages:
            result = self.uninstall_language(language)
            results.append((language, result))
        
        successful = [lang for lang, result in results if result.success]
        failed = [lang for lang, result in results if not result.success]
        
        if failed:
            return InstallationResult(
                False,
                f"Uninstalled {len(successful)} languages, {len(failed)} failed",
                {'successful': successful, 'failed': failed}
            )
        
        return InstallationResult(
            True,
            f"Successfully uninstalled {len(successful)} language standards",
            {'uninstalled': successful}
        )
            
    def get_details(self) -> Dict[str, Any]:
        """Get detailed information about code standards.
        
        Returns:
            Dictionary with detailed installer information
        """
        status = self.check_status()
        
        # Get list of available languages from source
        available_languages = []
        if self.standards_source.exists():
            for item in self.standards_source.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    available_languages.append(item.name)
        
        # Load config if available
        config = self._load_config()
        
        return {
            'name': self.name,
            'description': self.description,
            'installed': status['installed'],
            'status': status,
            'paths': {
                'standards_source': str(self.standards_source),
                'standards_target': str(CLAUDE_STANDARDS_DIR),
                'claude_md': str(self.claude_md_path)
            },
            'available': {
                'languages': available_languages
            },
            'config': config,
            'section_markers': {
                'start': SECTION_START_MARKER,
                'end': SECTION_END_MARKER
            }
        }
        
    def validate_prerequisites(self) -> InstallationResult:
        """Validate prerequisites for code standards installation.
        
        Returns:
            InstallationResult indicating if prerequisites are met
        """
        # Check if source directory exists
        if not self.standards_source.exists():
            return InstallationResult(
                False,
                f"Standards source directory not found: {self.standards_source}"
            )
            
        # Check if we have any standards to install
        has_content = False
        for item in self.standards_source.iterdir():
            if item.is_dir() or item.name == "config.json":
                has_content = True
                break
                
        if not has_content:
            return InstallationResult(
                False,
                "No standard files found in source directory"
            )
            
        return InstallationResult(True, "Prerequisites met")
        
    def create_required_directories(self) -> None:
        """Create required directories for code standards."""
        super().create_required_directories()
        ensure_directory(CLAUDE_DIR)
        ensure_directory(CLAUDE_STANDARDS_DIR.parent)
        
    def _load_config(self) -> Optional[Dict[str, Any]]:
        """Load config.json from standards directory.
        
        Returns:
            Config dictionary or None if not found/invalid
        """
        config_path = CLAUDE_STANDARDS_DIR / "config.json"
        if file_exists(config_path):
            try:
                return read_json_file(config_path)
            except Exception:
                return None
        return None
        
    def _check_claude_md_modified(self) -> bool:
        """Check if CLAUDE.md contains ethPandaOps section.
        
        Returns:
            True if CLAUDE.md contains the section, False otherwise
        """
        if not file_exists(self.claude_md_path):
            return False
            
        try:
            content = read_text_file(self.claude_md_path)
            return SECTION_START_MARKER in content and SECTION_END_MARKER in content
        except Exception:
            return False
            
    def _modify_claude_md(self) -> InstallationResult:
        """Add ethPandaOps section to CLAUDE.md.
        
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            # Create CLAUDE.md if it doesn't exist
            if not file_exists(self.claude_md_path):
                ensure_directory(self.claude_md_path.parent)
                write_text_file(self.claude_md_path, "")
            
            # Back up existing CLAUDE.md
            backup_path = self.backup_manager.create_backup(
                self.claude_md_path,
                "CLAUDE_md"
            )
            
            # Read current content
            content = read_text_file(self.claude_md_path)
            
            # Check if section already exists
            if SECTION_START_MARKER in content and SECTION_END_MARKER in content:
                return InstallationResult(
                    True,
                    "CLAUDE.md already contains ethPandaOps section"
                )
            
            # Create the section content
            section_content = f"""

{SECTION_START_MARKER}
# ethpandaops

When making changes to supported file types, you MUST read the local coding standards from the ai-cookbook repository and apply them:
- **Go** (*.go, go.mod, go.sum): ~/.claude/ethpandaops/code-standards/go/CLAUDE.md
- **Python** (*.py): ~/.claude/ethpandaops/code-standards/python/CLAUDE.md
Use the Read tool to load these standards from ~/.claude/ethpandaops/code-standards/.
After loading the standards, you should briefly mention "Loaded 🐼 ethPandaOps 🐼 code standards for [language]"
{SECTION_END_MARKER}
"""
            
            # Append the section to the file
            write_text_file(self.claude_md_path, content + section_content)
            
            return InstallationResult(
                True,
                "CLAUDE.md modified successfully",
                {'backup_created': str(backup_path)}
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to modify CLAUDE.md: {str(e)}"
            )
            
    def _remove_claude_md_section(self) -> InstallationResult:
        """Remove ethPandaOps section from CLAUDE.md.
        
        Returns:
            InstallationResult indicating success/failure
        """
        try:
            if not file_exists(self.claude_md_path):
                return InstallationResult(
                    True,
                    "CLAUDE.md does not exist"
                )
            
            # Back up existing CLAUDE.md
            backup_path = self.backup_manager.create_backup(
                self.claude_md_path,
                "CLAUDE_md_uninstall"
            )
            
            # Read current content
            content = read_text_file(self.claude_md_path)
            
            # Remove the section using regex
            pattern = rf"{re.escape(SECTION_START_MARKER)}.*?{re.escape(SECTION_END_MARKER)}"
            new_content = re.sub(pattern, "", content, flags=re.DOTALL)
            
            # Clean up any extra newlines
            new_content = re.sub(r'\n{3,}', '\n\n', new_content).strip()
            
            # Write back the modified content
            write_text_file(self.claude_md_path, new_content)
            
            return InstallationResult(
                True,
                "CLAUDE.md section removed successfully",
                {'backup_created': str(backup_path)}
            )
            
        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to remove CLAUDE.md section: {str(e)}"
            )
            
    def _get_installed_languages(self) -> List[str]:
        """Get list of installed language standards.
        
        Returns:
            List of language names that have standards installed
        """
        languages = []
        if directory_exists(CLAUDE_STANDARDS_DIR):
            for item in CLAUDE_STANDARDS_DIR.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # Check if it contains CLAUDE.md
                    claude_md = item / "CLAUDE.md"
                    if file_exists(claude_md):
                        languages.append(item.name)
        return sorted(languages)
        
    def _get_available_languages(self) -> List[str]:
        """Get list of available language standards from source.
        
        Returns:
            List of language names that are available to install
        """
        languages = []
        if directory_exists(self.standards_source):
            for item in self.standards_source.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # Check if it contains CLAUDE.md
                    claude_md = item / "CLAUDE.md"
                    if file_exists(claude_md):
                        languages.append(item.name)
        return sorted(languages)