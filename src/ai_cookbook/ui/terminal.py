"""Terminal utilities and ANSI handling for interactive UI."""

import sys
import termios
import tty
import os
from typing import Optional, Tuple


class TerminalController:
    """Handle terminal operations and ANSI escape sequences."""
    
    def __init__(self):
        """Initialize terminal controller."""
        self.original_settings = None
        self._is_tty = sys.stdin.isatty() and sys.stdout.isatty()
        
    def setup_terminal(self) -> None:
        """Configure terminal for interactive use."""
        if not self._is_tty:
            return
            
        try:
            # Save original terminal settings
            self.original_settings = termios.tcgetattr(sys.stdin)
            
            # Set terminal to raw mode for character input
            tty.setraw(sys.stdin.fileno())
            
            # Hide cursor
            self.hide_cursor()
        except Exception:
            # Silently fail if terminal operations not supported
            pass
            
    def restore_terminal(self) -> None:
        """Restore original terminal settings."""
        if not self._is_tty or not self.original_settings:
            return
            
        try:
            # Show cursor
            self.show_cursor()
            
            # Restore original settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_settings)
            self.original_settings = None
        except Exception:
            # Silently fail if terminal operations not supported
            pass
            
    def get_terminal_size(self) -> Tuple[int, int]:
        """Get terminal dimensions (rows, columns)."""
        try:
            size = os.get_terminal_size()
            return (size.lines, size.columns)
        except Exception:
            # Return default size if unable to determine
            return (24, 80)
            
    def clear_screen(self) -> None:
        """Clear terminal screen."""
        if not self._is_tty:
            return
            
        # Use ANSI escape sequence to clear screen and move cursor to top
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.flush()
        
    def move_cursor(self, row: int, col: int) -> None:
        """Move cursor to specified position (1-indexed)."""
        if not self._is_tty:
            return
            
        # ANSI escape sequence for cursor positioning
        sys.stdout.write(f'\033[{row};{col}H')
        sys.stdout.flush()
        
    def hide_cursor(self) -> None:
        """Hide terminal cursor."""
        if not self._is_tty:
            return
            
        sys.stdout.write('\033[?25l')
        sys.stdout.flush()
        
    def show_cursor(self) -> None:
        """Show terminal cursor."""
        if not self._is_tty:
            return
            
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()
        
    def getch(self) -> str:
        """Get single character input from terminal."""
        if not self._is_tty:
            # Fallback to line input if not a TTY
            return sys.stdin.read(1)
            
        try:
            return sys.stdin.read(1)
        except Exception:
            return ''
            
    def get_key(self) -> str:
        """Get key input handling special keys like arrows."""
        ch = self.getch()
        
        if ch == '\x1b':  # ESC sequence
            # Read the next two characters
            seq1 = self.getch()
            seq2 = self.getch()
            
            if seq1 == '[':  # CSI sequence
                if seq2 == 'A':
                    return 'UP'
                elif seq2 == 'B':
                    return 'DOWN'
                elif seq2 == 'C':
                    return 'RIGHT'
                elif seq2 == 'D':
                    return 'LEFT'
                elif seq2 == 'H':
                    return 'HOME'
                elif seq2 == 'F':
                    return 'END'
                elif seq2.isdigit():
                    # Handle extended sequences like Page Up/Down
                    seq3 = self.getch()
                    if seq2 == '5' and seq3 == '~':
                        return 'PGUP'
                    elif seq2 == '6' and seq3 == '~':
                        return 'PGDN'
                    
            # Return ESC if sequence not recognized
            return 'ESC'
            
        elif ch == '\r' or ch == '\n':
            return 'ENTER'
        elif ch == '\t':
            return 'TAB'
        elif ch == '\x7f' or ch == '\x08':  # DEL or backspace
            return 'BACKSPACE'
        elif ch == '\x03':  # Ctrl+C
            return 'CTRL+C'
        elif ch == '\x04':  # Ctrl+D
            return 'CTRL+D'
        elif ch == '\x1a':  # Ctrl+Z
            return 'CTRL+Z'
        else:
            # Return the character as-is
            return ch
            
    def clear_line(self) -> None:
        """Clear current line."""
        if not self._is_tty:
            return
            
        sys.stdout.write('\r\033[K')
        sys.stdout.flush()
        
    def save_cursor_position(self) -> None:
        """Save current cursor position."""
        if not self._is_tty:
            return
            
        sys.stdout.write('\033[s')
        sys.stdout.flush()
        
    def restore_cursor_position(self) -> None:
        """Restore saved cursor position."""
        if not self._is_tty:
            return
            
        sys.stdout.write('\033[u')
        sys.stdout.flush()
        
    def write(self, text: str) -> None:
        """Write text to terminal."""
        sys.stdout.write(text)
        sys.stdout.flush()
        
    def writeln(self, text: str = '') -> None:
        """Write text followed by newline."""
        sys.stdout.write(text + '\n')
        sys.stdout.flush()