"""Tkinter GUI interface for document anonymization.

This module redirects to the MVP-structured GUI implementation.
The original monolithic implementation has been refactored to use
the Model-View-Presenter pattern.

Structure:
- views/: Humble view implementations (zero business logic)
- presenters/: Business logic extracted from original GUI
- app.py: Composition root that wires dependencies
"""

from .gui.app import main

__all__ = ["main"]

if __name__ == "__main__":
    main()
