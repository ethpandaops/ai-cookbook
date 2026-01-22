"""Claude skills installer for PandaOps Cookbook."""

from pathlib import Path
from typing import Dict, Any, List
import shutil

from ..installers.base import BaseInstaller, InstallationResult
from ..utils.file_operations import (
    ensure_directory, directory_exists, remove_directory
)
from ..config.settings import CLAUDE_DIR, CLAUDE_SKILLS_DIR, SKILLS_SOURCE


class SkillsInstaller(BaseInstaller):
    """Installer for Claude skills integration."""

    def __init__(self) -> None:
        """Initialize skills installer."""
        super().__init__(
            name="Claude Skills",
            description="Install Claude Code skills with frontmatter, arguments, and supporting files"
        )
        self.skills_source = SKILLS_SOURCE

        # Initialize update detector
        self.initialize_update_detector(self.skills_source, CLAUDE_SKILLS_DIR)

    def check_status(self) -> Dict[str, Any]:
        """Check installation status of Claude skills.

        Returns:
            Dictionary with status information:
            - installed: Whether any skills are installed
            - installed_skills: List of installed skill names
            - available_skills: List of available skills from source
        """
        skills_installed = CLAUDE_SKILLS_DIR.exists() and \
                          len(list(CLAUDE_SKILLS_DIR.glob("*/SKILL.md"))) > 0

        installed_skills = []
        if skills_installed:
            # List skill directories that contain SKILL.md
            for skill_dir in CLAUDE_SKILLS_DIR.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    installed_skills.append(skill_dir.name)

        # Get available skills from source
        available_skills = []
        if directory_exists(self.skills_source):
            for skill_dir in self.skills_source.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    available_skills.append(skill_dir.name)

        return {
            'installed': skills_installed,
            'installed_skills': installed_skills,
            'installed_items': installed_skills,  # For compatibility with recommended installer
            'available_skills': available_skills,
            'skills_dir': str(CLAUDE_SKILLS_DIR)
        }

    def install(self) -> InstallationResult:
        """Install all available skills.

        Returns:
            InstallationResult indicating success/failure
        """
        status = self.check_status()
        available_skills = status.get('available_skills', [])
        installed_skills = status.get('installed_skills', [])

        results = []
        for skill in available_skills:
            if skill not in installed_skills:
                result = self.install_skill(skill)
                results.append((skill, result))

        successful = [skill for skill, result in results if result.success]
        failed = [skill for skill, result in results if not result.success]

        if not results:
            return InstallationResult(
                True,
                "All skills are already installed"
            )

        if failed:
            return InstallationResult(
                False,
                f"Installed {len(successful)} skills, {len(failed)} failed",
                {'successful': successful, 'failed': failed}
            )

        return InstallationResult(
            True,
            f"Successfully installed {len(successful)} skills",
            {'installed': successful}
        )

    def install_skill(self, skill_name: str) -> InstallationResult:
        """Install a specific Claude skill.

        Args:
            skill_name: Name of the skill directory (e.g., 'eip')

        Returns:
            InstallationResult indicating success/failure
        """
        try:
            # Check if skill exists in source
            skill_source_dir = self.skills_source / skill_name
            skill_file = skill_source_dir / "SKILL.md"

            if not skill_source_dir.exists() or not skill_file.exists():
                return InstallationResult(
                    False,
                    f"Skill '{skill_name}' not found in source directory"
                )

            # Create required directories
            self.create_required_directories()
            ensure_directory(CLAUDE_SKILLS_DIR)
            skill_target_dir = CLAUDE_SKILLS_DIR / skill_name
            ensure_directory(skill_target_dir)

            # Back up existing skill if present
            backup_created = False
            skill_target_file = skill_target_dir / "SKILL.md"
            if skill_target_file.exists():
                backup_path = self.backup_manager.create_backup(
                    skill_target_file,
                    f"skill_{skill_name}"
                )
                if backup_path:
                    backup_created = True

            # Copy all files in the skill directory (SKILL.md and supporting files)
            copied_files = []
            for source_file in skill_source_dir.iterdir():
                if source_file.is_file():
                    target_file = skill_target_dir / source_file.name
                    shutil.copy2(source_file, target_file)
                    copied_files.append(source_file.name)

            # Update metadata for the SKILL.md file
            if self.update_detector:
                metadata_key = f"{skill_name}/SKILL.md"
                self.update_detector.update_metadata(metadata_key, skill_file)

            details = {
                'skill': skill_name,
                'target_path': str(skill_target_dir),
                'files_copied': copied_files
            }

            if backup_created:
                details['backup_created'] = str(backup_path)

            return InstallationResult(
                True,
                f"Successfully installed skill: {skill_name}",
                details
            )

        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to install skill {skill_name}: {str(e)}"
            )

    def uninstall_skill(self, skill_name: str) -> InstallationResult:
        """Uninstall a specific Claude skill.

        Args:
            skill_name: Name of the skill directory (e.g., 'eip')

        Returns:
            InstallationResult indicating success/failure
        """
        try:
            skill_target_dir = CLAUDE_SKILLS_DIR / skill_name

            if not skill_target_dir.exists():
                return InstallationResult(
                    True,
                    f"Skill '{skill_name}' is not installed"
                )

            # Remove skill directory
            shutil.rmtree(skill_target_dir)

            # Remove metadata
            if self.update_detector:
                metadata_key = f"{skill_name}/SKILL.md"
                self.update_detector.remove_metadata(metadata_key)

            details = {
                'skill': skill_name
            }

            return InstallationResult(
                True,
                f"Successfully uninstalled skill: {skill_name}",
                details
            )

        except Exception as e:
            return InstallationResult(
                False,
                f"Failed to uninstall skill {skill_name}: {str(e)}"
            )

    def uninstall(self) -> InstallationResult:
        """Uninstall all Claude skills.

        Returns:
            InstallationResult indicating success/failure
        """
        try:
            if not directory_exists(CLAUDE_SKILLS_DIR):
                return InstallationResult(
                    True,
                    "No Claude skills were installed"
                )

            # Get list of installed skills
            status = self.check_status()
            installed_skills = status.get('installed_skills', [])

            if not installed_skills:
                return InstallationResult(
                    True,
                    "No Claude skills were installed"
                )

            # Remove each skill directory
            for skill in installed_skills:
                skill_dir = CLAUDE_SKILLS_DIR / skill
                if skill_dir.exists():
                    shutil.rmtree(skill_dir)

            details = {
                'removed': installed_skills
            }

            return InstallationResult(
                True,
                f"Successfully uninstalled {len(installed_skills)} skills",
                details
            )

        except Exception as e:
            return InstallationResult(
                False,
                f"Uninstallation failed: {str(e)}"
            )

    def get_details(self) -> Dict[str, Any]:
        """Get detailed information about Claude skills.

        Returns:
            Dictionary with detailed installer information
        """
        status = self.check_status()

        # Get details about each available skill
        available_skills_details = {}
        if self.skills_source.exists():
            for skill_dir in self.skills_source.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        # Read skill metadata from frontmatter
                        try:
                            with open(skill_file, 'r') as f:
                                content = f.read()
                                if content.startswith('---'):
                                    # Extract frontmatter
                                    end_idx = content.find('---', 3)
                                    if end_idx > 0:
                                        frontmatter = content[3:end_idx].strip()
                                        # Simple parsing of key fields
                                        skill_info = {'name': skill_dir.name}
                                        for line in frontmatter.split('\n'):
                                            if ':' in line:
                                                key, value = line.split(':', 1)
                                                skill_info[key.strip()] = value.strip()
                                        available_skills_details[skill_dir.name] = skill_info
                        except Exception:
                            available_skills_details[skill_dir.name] = {'name': skill_dir.name}

        return {
            'name': self.name,
            'description': self.description,
            'installed': status['installed'],
            'status': status,
            'paths': {
                'skills_source': str(self.skills_source),
                'skills_target': str(CLAUDE_SKILLS_DIR)
            },
            'available_skills': available_skills_details
        }

    def list_available_skills(self) -> List[str]:
        """List all available Claude skills.

        Returns:
            List of available skill names
        """
        if not self.skills_source.exists():
            return []

        skills = []
        for skill_dir in self.skills_source.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skills.append(skill_dir.name)

        return skills

    def validate_prerequisites(self) -> InstallationResult:
        """Validate prerequisites for Claude skills installation.

        Returns:
            InstallationResult indicating if prerequisites are met
        """
        # Check if source directory exists
        if not self.skills_source.exists():
            return InstallationResult(
                False,
                f"Skills source directory not found: {self.skills_source}"
            )

        # Check if we have any skills to install
        skills = self.list_available_skills()
        if not skills:
            return InstallationResult(
                False,
                "No skill directories found in source directory"
            )

        return InstallationResult(True, "Prerequisites met")

    def create_required_directories(self) -> None:
        """Create required directories for Claude skills."""
        super().create_required_directories()
        ensure_directory(CLAUDE_DIR)
        ensure_directory(CLAUDE_SKILLS_DIR)
