"""
Reusable UI components for the PandaOps Cookbook
"""

from typing import Optional, List, Literal
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.prompt import Confirm
from rich.text import Text
from rich.align import Align

from ..config.settings import COLORS


class StatusIndicator:
    """Visual status indicators with colored symbols"""
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize StatusIndicator
        
        Args:
            console: Rich Console instance (creates new if not provided)
        """
        self.console = console or Console()
        self._indicators = {
            "success": ("✓", COLORS["success"]),
            "error": ("✗", COLORS["error"]),
            "warning": ("⚠", COLORS["warning"]),
            "info": ("ℹ", COLORS["info"]),
            "pending": ("⋯", COLORS["muted"]),
            "running": ("⟳", COLORS["primary"]),
        }
    
    def show(self, status: Literal["success", "error", "warning", "info", "pending", "running"], 
             message: str, prefix: str = "") -> None:
        """
        Display a status message with indicator
        
        Args:
            status: Status type
            message: Message to display
            prefix: Optional prefix before indicator
        """
        symbol, color = self._indicators.get(status, ("•", "white"))
        
        if prefix:
            self.console.print(f"{prefix} [{color}]{symbol}[/{color}] {message}")
        else:
            self.console.print(f"[{color}]{symbol}[/{color}] {message}")
    
    def success(self, message: str, prefix: str = "") -> None:
        """Show success status"""
        self.show("success", message, prefix)
    
    def error(self, message: str, prefix: str = "") -> None:
        """Show error status"""
        self.show("error", message, prefix)
    
    def warning(self, message: str, prefix: str = "") -> None:
        """Show warning status"""
        self.show("warning", message, prefix)
    
    def info(self, message: str, prefix: str = "") -> None:
        """Show info status"""
        self.show("info", message, prefix)
    
    def pending(self, message: str, prefix: str = "") -> None:
        """Show pending status"""
        self.show("pending", message, prefix)
    
    def running(self, message: str, prefix: str = "") -> None:
        """Show running status"""
        self.show("running", message, prefix)


class ProgressBar:
    """Simple progress bar for long-running operations"""
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize ProgressBar
        
        Args:
            console: Rich Console instance (creates new if not provided)
        """
        self.console = console or Console()
        self._progress = None
        self._task = None
    
    def start(self, total: int, description: str = "Processing") -> None:
        """
        Start a new progress bar
        
        Args:
            total: Total number of steps
            description: Description of the operation
        """
        self._progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            TimeRemainingColumn(),
            console=self.console,
        )
        self._progress.start()
        self._task = self._progress.add_task(description, total=total)
    
    def update(self, advance: int = 1, description: Optional[str] = None) -> None:
        """
        Update progress bar
        
        Args:
            advance: Number of steps to advance
            description: Optional new description
        """
        if self._progress and self._task is not None:
            if description:
                self._progress.update(self._task, description=description)
            self._progress.update(self._task, advance=advance)
    
    def finish(self) -> None:
        """Stop and clean up the progress bar"""
        if self._progress:
            self._progress.stop()
            self._progress = None
            self._task = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.finish()


class MessageBox:
    """Display messages and confirmations in styled boxes"""
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize MessageBox
        
        Args:
            console: Rich Console instance (creates new if not provided)
        """
        self.console = console or Console()
    
    def show(self, message: str, title: Optional[str] = None, 
             style: Literal["info", "success", "warning", "error"] = "info",
             width: Optional[int] = None) -> None:
        """
        Display a message in a styled box
        
        Args:
            message: Message content
            title: Optional box title
            style: Box style (determines color)
            width: Optional box width
        """
        color = COLORS.get(style, COLORS["info"])
        
        # Create text with appropriate styling
        text = Text(message, style=f"{color}")
        
        # Create panel with title if provided
        panel = Panel(
            text,
            title=title,
            title_align="left",
            border_style=color,
            width=width,
            padding=(1, 2),
        )
        
        self.console.print(panel)
    
    def confirm(self, message: str, default: bool = False) -> bool:
        """
        Show a confirmation prompt
        
        Args:
            message: Confirmation message
            default: Default response if user presses Enter
            
        Returns:
            User's confirmation response
        """
        return Confirm.ask(
            f"[{COLORS['primary']}]{message}[/{COLORS['primary']}]",
            default=default,
            console=self.console
        )
    
    def info(self, message: str, title: Optional[str] = None) -> None:
        """Show info message"""
        self.show(message, title, "info")
    
    def success(self, message: str, title: Optional[str] = None) -> None:
        """Show success message"""
        self.show(message, title, "success")
    
    def warning(self, message: str, title: Optional[str] = None) -> None:
        """Show warning message"""
        self.show(message, title, "warning")
    
    def error(self, message: str, title: Optional[str] = None) -> None:
        """Show error message"""
        self.show(message, title, "error")