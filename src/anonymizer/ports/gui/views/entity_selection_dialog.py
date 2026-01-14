"""Entity selection dialog view - humble Tkinter implementation with zero business logic."""

import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from ....core.models import PIIEntity
from ..presenters.entity_selection_presenter import EntitySelectionPresenter


class EntitySelectionDialog:
    """
    Entity selection dialog view - humble object with zero business logic.

    All methods are simple UI operations. Business logic is in EntitySelectionPresenter.
    """

    def __init__(
        self,
        parent: tk.Tk,
        entities: List[PIIEntity],
        text: str,
        threshold: float
    ) -> None:
        """
        Initialize the dialog.

        Args:
            parent: Parent window
            entities: List of detected PII entities
            text: Original document text for context extraction
            threshold: Confidence threshold
        """
        self._parent = parent
        self._dialog: Optional[tk.Toplevel] = None
        self._tree: Optional[ttk.Treeview] = None

        # Create presenter and initialize
        self._presenter = EntitySelectionPresenter(self)
        self._presenter.initialize(entities, text, threshold)

    def show(self) -> Optional[List[PIIEntity]]:
        """
        Show the dialog and wait for user action.

        Returns:
            List of selected entities, or None if cancelled
        """
        self._create_dialog()
        self._populate_tree()
        self._dialog.wait_window()
        return self._presenter.get_result()

    def update_item_selection(self, item_id: str, selected: bool) -> None:
        """Update the visual selection state of an item."""
        if self._tree:
            check_mark = "✓" if selected else "✗"
            tag = "checked" if selected else "unchecked"
            values = self._tree.item(item_id)["values"]
            self._tree.item(item_id, values=(check_mark, *values[1:]), tags=(tag,))

    def _create_dialog(self) -> None:
        """Create the dialog window and all widgets."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Select Entities to Anonymize")
        self._dialog.geometry("900x600")
        self._dialog.transient(self._parent)
        self._dialog.grab_set()

        # Header frame
        header_frame = ttk.Frame(self._dialog)
        header_frame.pack(fill="x", padx=10, pady=10)

        entity_count = self._presenter.get_entity_count()
        threshold = self._presenter.get_threshold()
        ttk.Label(
            header_frame,
            text=f"Found {entity_count} entities with confidence >= {threshold:.2f}",
            font=("", 10, "bold")
        ).pack(side="left")

        # Create treeview with scrollbars
        tree_frame = ttk.Frame(self._dialog)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        columns = ("select", "text", "type", "score", "context")
        self._tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="extended"
        )

        # Column headers
        self._tree.heading("select", text="Select")
        self._tree.heading("text", text="Entity Text")
        self._tree.heading("type", text="Type")
        self._tree.heading("score", text="Score")
        self._tree.heading("context", text="Context")

        # Column widths
        self._tree.column("select", width=60, anchor="center")
        self._tree.column("text", width=150)
        self._tree.column("type", width=120)
        self._tree.column("score", width=80, anchor="center")
        self._tree.column("context", width=400)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # Configure tag colors (with explicit foreground for readability)
        self._tree.tag_configure("checked", background="#d4edda", foreground="#000000")
        self._tree.tag_configure("unchecked", background="#f8d7da", foreground="#000000")

        # Bind double-click
        self._tree.bind("<Double-1>", self._handle_double_click)

        # Button frame
        button_frame = ttk.Frame(self._dialog)
        button_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(
            button_frame,
            text="Select All Above Threshold",
            command=self._handle_select_all_above_threshold
        ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="Deselect All",
            command=self._handle_deselect_all
        ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="Anonymize Selected",
            command=self._handle_confirm
        ).pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._handle_cancel
        ).pack(side="right", padx=5)

    def _populate_tree(self) -> None:
        """Populate the treeview with entity data."""
        if not self._tree:
            return

        display_data = self._presenter.get_entity_display_data()
        for item in display_data:
            self._tree.insert(
                "",
                "end",
                iid=str(item["id"]),
                values=(
                    "✓" if item["selected"] else "✗",
                    item["text"],
                    item["entity_type"],
                    f"{item['score']:.3f}",
                    item["context"]
                ),
                tags=("checked" if item["selected"] else "unchecked",)
            )

    # Event handlers (simple delegation to presenter)
    def _handle_double_click(self, event: tk.Event) -> None:
        """Handle double-click on tree item."""
        if not self._tree:
            return
        item = self._tree.identify_row(event.y)
        if item:
            new_state = self._presenter.toggle_selection(int(item))
            self.update_item_selection(item, new_state)

    def _handle_select_all_above_threshold(self) -> None:
        """Handle select all above threshold button."""
        selected_ids = self._presenter.select_all_above_threshold()
        for entity_id in selected_ids:
            self.update_item_selection(str(entity_id), True)

    def _handle_deselect_all(self) -> None:
        """Handle deselect all button."""
        deselected_ids = self._presenter.deselect_all()
        for entity_id in deselected_ids:
            self.update_item_selection(str(entity_id), False)

    def _handle_confirm(self) -> None:
        """Handle confirm button."""
        self._presenter.confirm_selection()
        if self._dialog:
            self._dialog.destroy()

    def _handle_cancel(self) -> None:
        """Handle cancel button."""
        self._presenter.cancel()
        if self._dialog:
            self._dialog.destroy()


def create_entity_selection_dialog(
    parent: tk.Tk,
    entities: List[PIIEntity],
    text: str,
    threshold: float
) -> Optional[List[PIIEntity]]:
    """
    Factory function to create and show entity selection dialog.

    Args:
        parent: Parent window
        entities: List of detected PII entities
        text: Original document text
        threshold: Confidence threshold

    Returns:
        List of selected entities, or None if cancelled
    """
    dialog = EntitySelectionDialog(parent, entities, text, threshold)
    return dialog.show()
