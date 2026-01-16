"""Model Manager dialog view - humble Tkinter implementation with zero business logic."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict, List, Optional


class ModelManagerDialog:
    """
    Model Manager dialog view - humble object with zero business logic.

    All methods are simple UI operations. Business logic is in ModelManagerPresenter.
    """

    def __init__(self, parent: tk.Tk) -> None:
        """Initialize the dialog."""
        self._parent = parent
        self._dialog: Optional[tk.Toplevel] = None
        self._tree: Optional[ttk.Treeview] = None
        self._progress_frame: Optional[ttk.Frame] = None
        self._progress_bar: Optional[ttk.Progressbar] = None
        self._progress_label: Optional[ttk.Label] = None
        self._download_btn: Optional[ttk.Button] = None
        self._delete_btn: Optional[ttk.Button] = None

        # Checkbox state tracking: model_name -> BooleanVar
        self._check_vars: Dict[str, tk.BooleanVar] = {}

        # Item ID tracking: model_name -> tree item ID
        self._item_ids: Dict[str, str] = {}

        # Callback when models are downloaded/deleted
        self._on_models_changed: Optional[Callable[[], None]] = None

        # Track if dialog is destroyed (for safe UI updates during download)
        self._is_destroyed = False

        # Create presenter (lazy import to avoid circular dependency)
        from ..presenters.model_manager_presenter import ModelManagerPresenter

        self._presenter = ModelManagerPresenter(self)

    def set_on_models_changed(self, callback: Optional[Callable[[], None]]) -> None:
        """Set callback for when models are downloaded or deleted."""
        self._on_models_changed = callback

    def notify_models_changed(self) -> None:
        """Notify that models have been downloaded or deleted."""
        if self._on_models_changed:
            self._on_models_changed()

    def show(self) -> None:
        """Show the dialog."""
        self._create_dialog()
        self._populate_tree()
        if self._dialog:
            self._dialog.wait_window()

    # View methods called by presenter

    def update_model_status(self, model_name: str, status: str, color: str) -> None:
        """Update the status display for a model."""
        if self._is_destroyed:
            return
        if self._tree and model_name in self._item_ids:
            try:
                item_id = self._item_ids[model_name]
                values = self._tree.item(item_id)["values"]
                if values:
                    # Update status column (index 2)
                    new_values = (values[0], values[1], status)
                    self._tree.item(item_id, values=new_values, tags=(color,))
            except tk.TclError:
                self._is_destroyed = True

    def show_progress(self, visible: bool) -> None:
        """Show or hide the progress frame."""
        if self._is_destroyed:
            return
        if self._progress_frame:
            try:
                if visible:
                    self._progress_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
                    if self._progress_bar:
                        self._progress_bar["value"] = 0
                else:
                    self._progress_frame.grid_remove()
            except tk.TclError:
                self._is_destroyed = True

    def update_progress(self, downloaded_mb: float, total_mb: float, model_name: str) -> None:
        """Update progress bar and label."""
        if self._is_destroyed:
            return
        if self._progress_bar and self._progress_label:
            try:
                if total_mb > 0:
                    progress = (downloaded_mb / total_mb) * 100
                    self._progress_bar["value"] = progress
                self._progress_label.config(
                    text=f"Downloading {model_name}: {downloaded_mb:.1f} MB / {total_mb:.1f} MB"
                )
            except tk.TclError:
                self._is_destroyed = True

    def set_buttons_enabled(self, download: bool, delete: bool) -> None:
        """Enable/disable action buttons."""
        if self._is_destroyed:
            return
        try:
            if self._download_btn:
                self._download_btn.config(state="normal" if download else "disabled")
            if self._delete_btn:
                self._delete_btn.config(state="normal" if delete else "disabled")
        except tk.TclError:
            self._is_destroyed = True

    def show_error(self, title: str, message: str) -> None:
        """Show an error dialog."""
        parent = self._dialog if self._dialog else self._parent
        messagebox.showerror(title, message, parent=parent)

    def show_info(self, title: str, message: str) -> None:
        """Show an info dialog."""
        parent = self._dialog if self._dialog else self._parent
        messagebox.showinfo(title, message, parent=parent)

    def refresh_tree(self) -> None:
        """Refresh the tree view with current data."""
        if self._is_destroyed:
            return
        if self._tree:
            try:
                # Clear existing items
                for item in self._tree.get_children():
                    self._tree.delete(item)
                self._check_vars.clear()
                self._item_ids.clear()
                self._populate_tree()
            except tk.TclError:
                self._is_destroyed = True

    def schedule_ui_update(self, callback: Callable[[], None]) -> None:
        """Schedule a callback on the UI thread."""
        if self._dialog and not self._is_destroyed:
            try:
                self._dialog.after(0, callback)
            except tk.TclError:
                # Dialog was destroyed between check and call
                self._is_destroyed = True

    def get_selected_models(self) -> List[str]:
        """Get list of checked model names."""
        return [name for name, var in self._check_vars.items() if var.get()]

    def _create_dialog(self) -> None:
        """Create the dialog window and all widgets."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Model Manager")
        self._dialog.geometry("700x500")
        self._dialog.transient(self._parent)
        self._dialog.grab_set()

        # Make dialog resizable
        self._dialog.columnconfigure(0, weight=1)
        self._dialog.rowconfigure(1, weight=1)

        # Header frame
        header_frame = ttk.Frame(self._dialog)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header_frame.columnconfigure(0, weight=1)

        ttk.Label(
            header_frame, text="Manage spaCy Language Models", font=("", 12, "bold")
        ).grid(row=0, column=0, sticky="w")

        models_dir = self._presenter.get_models_directory()
        ttk.Label(
            header_frame, text=f"Storage: {models_dir}", font=("", 9), foreground="gray"
        ).grid(row=1, column=0, sticky="w")

        # Treeview frame
        tree_frame = ttk.Frame(self._dialog)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # Create treeview with columns
        columns = ("model", "size", "status")
        self._tree = ttk.Treeview(
            tree_frame, columns=columns, show="tree headings", selectmode="extended"
        )

        self._tree.heading("#0", text="Select")
        self._tree.heading("model", text="Model")
        self._tree.heading("size", text="Size (MB)")
        self._tree.heading("status", text="Status")

        self._tree.column("#0", width=60, stretch=False)
        self._tree.column("model", width=200, minwidth=150)
        self._tree.column("size", width=80, anchor="center", stretch=False)
        self._tree.column("status", width=120, anchor="center", stretch=False)

        # Tags for status colors
        self._tree.tag_configure("downloaded", foreground="green")
        self._tree.tag_configure("not_downloaded", foreground="gray")
        self._tree.tag_configure("downloading", foreground="blue")

        # Scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # Bind double-click to toggle checkbox
        self._tree.bind("<Double-1>", self._handle_tree_double_click)
        self._tree.bind("<Button-1>", self._handle_tree_click)

        # Progress frame (hidden by default)
        self._progress_frame = ttk.Frame(self._dialog)

        self._progress_label = ttk.Label(self._progress_frame, text="")
        self._progress_label.pack(fill="x")

        self._progress_bar = ttk.Progressbar(
            self._progress_frame, mode="determinate", length=400
        )
        self._progress_bar.pack(fill="x", pady=5)

        # Button frame
        button_frame = ttk.Frame(self._dialog)
        button_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)

        self._download_btn = ttk.Button(
            button_frame, text="Download Selected", command=self._handle_download
        )
        self._download_btn.pack(side="left", padx=5)

        self._delete_btn = ttk.Button(
            button_frame, text="Delete Selected", command=self._handle_delete
        )
        self._delete_btn.pack(side="left", padx=5)

        ttk.Button(button_frame, text="Close", command=self._handle_close).pack(
            side="right", padx=5
        )

    def _populate_tree(self) -> None:
        """Populate the tree with model data."""
        if not self._tree:
            return

        model_data = self._presenter.get_models_by_language()

        for lang_code, lang_name, models in model_data:
            # Insert language parent (not selectable)
            lang_id = self._tree.insert("", "end", text=lang_name, open=True)

            for model in models:
                model_name = model["name"]

                # Create checkbox variable
                check_var = tk.BooleanVar(value=False)
                self._check_vars[model_name] = check_var

                # Determine tag, status and checkbox text
                if model["downloaded"]:
                    tag = "downloaded"
                    status = "✓ Downloaded"
                    checkbox_text = "[ ]"
                else:
                    tag = "not_downloaded"
                    status = "Not downloaded"
                    checkbox_text = "[ ]"

                # Insert model item
                item_id = self._tree.insert(
                    lang_id,
                    "end",
                    text=checkbox_text,
                    values=(model_name, model["size_mb"], status),
                    tags=(tag,),
                )

                # Track item ID
                self._item_ids[model_name] = item_id

    def _handle_tree_click(self, event: tk.Event) -> None:
        """Handle click on tree - toggle checkbox if clicking on tree column."""
        if not self._tree:
            return

        region = self._tree.identify_region(event.x, event.y)
        column = self._tree.identify_column(event.x)

        # Only toggle if clicking on the tree column (#0) which shows checkbox
        if region == "tree" and column == "#0":
            item = self._tree.identify_row(event.y)
            if item:
                self._toggle_item_checkbox(item)

    def _handle_tree_double_click(self, event: tk.Event) -> None:
        """Handle double-click on tree to toggle checkbox."""
        if not self._tree:
            return

        item = self._tree.identify_row(event.y)
        if item:
            self._toggle_item_checkbox(item)

    def _toggle_item_checkbox(self, item: str) -> None:
        """Toggle the checkbox for a tree item."""
        if not self._tree:
            return

        values = self._tree.item(item)["values"]
        if not values:
            # This is a parent (language) item, not a model
            return

        model_name = values[0]
        if model_name in self._check_vars:
            var = self._check_vars[model_name]
            var.set(not var.get())

            # Update visual indicator
            new_text = "[X]" if var.get() else "[ ]"
            self._tree.item(item, text=new_text)

    # Event handlers

    def _handle_download(self) -> None:
        """Handle download button click."""
        selected = self.get_selected_models()
        if not selected:
            self.show_info("Info", "Please select models to download")
            return
        self._presenter.download_models(selected)

    def _handle_delete(self) -> None:
        """Handle delete button click."""
        selected = self.get_selected_models()
        if not selected:
            self.show_info("Info", "Please select models to delete")
            return
        self._presenter.delete_models(selected)

    def _handle_close(self) -> None:
        """Handle close button click."""
        self._is_destroyed = True
        self._presenter.cancel_download()
        if self._dialog:
            self._dialog.destroy()


def create_model_manager_dialog(
    parent: tk.Tk,
    on_models_changed: Optional[Callable[[], None]] = None,
) -> None:
    """
    Factory function to create and show model manager dialog.

    Args:
        parent: Parent window
        on_models_changed: Optional callback when models are downloaded/deleted
    """
    dialog = ModelManagerDialog(parent)
    dialog.set_on_models_changed(on_models_changed)
    dialog.show()
