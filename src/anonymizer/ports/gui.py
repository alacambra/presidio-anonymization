"""Tkinter GUI interface for document anonymization."""

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from ..config import (
    DEFAULT_LANGUAGE,
    SUPPORTED_ENTITIES,
    SUPPORTED_FILE_EXTENSIONS,
    SUPPORTED_LANGUAGES,
)
from ..core.anonymizer_service import AnonymizerService
from ..core.models import DocumentResult, PIIEntity


class AnonymizerGUI:
    """
    Cross-platform GUI for document anonymization.

    Provides file/folder selection, language selection, and status display.
    """

    def __init__(self) -> None:
        """Initialize the GUI application."""
        self.root = tk.Tk()
        self.root.title("Document Anonymizer")
        self.root.geometry("600x700")
        self.root.minsize(500, 600)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.selected_language = tk.StringVar(value=DEFAULT_LANGUAGE)
        self.confidence_threshold: Optional[tk.DoubleVar] = None
        self.threshold_label: Optional[ttk.Label] = None
        self.last_mapping_path: Optional[str] = None
        self.entity_vars: Dict[str, tk.BooleanVar] = {}

        # Watch for manual changes to input path (typed or pasted)
        self.input_path.trace_add("write", self._on_input_path_changed)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the user interface."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        self._create_input_section(main_frame)
        self._create_output_section(main_frame)
        self._create_language_section(main_frame)
        self._create_threshold_section(main_frame)
        self._create_entities_section(main_frame)
        self._create_status_section(main_frame)
        self._create_buttons_section(main_frame)

    def _create_input_section(self, parent: ttk.Frame) -> None:
        """Create the input file/folder selection section."""
        ttk.Label(parent, text="Input:").grid(row=0, column=0, sticky="w", pady=5)

        input_frame = ttk.Frame(parent)
        input_frame.grid(row=0, column=1, sticky="ew", pady=5)
        input_frame.columnconfigure(0, weight=1)

        ttk.Entry(input_frame, textvariable=self.input_path).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )

        ttk.Button(input_frame, text="File...", command=self._browse_input_file).grid(
            row=0, column=1, padx=2
        )

    def _create_output_section(self, parent: ttk.Frame) -> None:
        """Create the output location selection section."""
        ttk.Label(parent, text="Output:").grid(row=1, column=0, sticky="w", pady=5)

        output_frame = ttk.Frame(parent)
        output_frame.grid(row=1, column=1, sticky="ew", pady=5)
        output_frame.columnconfigure(0, weight=1)

        ttk.Entry(output_frame, textvariable=self.output_path).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )

        ttk.Button(output_frame, text="Browse...", command=self._browse_output).grid(
            row=0, column=1
        )

    def _create_language_section(self, parent: ttk.Frame) -> None:
        """Create the language selection section."""
        ttk.Label(parent, text="Language:").grid(row=2, column=0, sticky="w", pady=5)

        language_names = {
            "en": "English",
            "es": "Spanish",
            "de": "German",
            "ca": "Catalan",
        }

        language_combo = ttk.Combobox(
            parent,
            textvariable=self.selected_language,
            values=[f"{code} - {name}" for code, name in language_names.items()],
            state="readonly",
            width=20,
        )
        language_combo.grid(row=2, column=1, sticky="w", pady=5)
        language_combo.set(f"{DEFAULT_LANGUAGE} - {language_names[DEFAULT_LANGUAGE]}")

        language_combo.bind("<<ComboboxSelected>>", self._on_language_selected)

    def _create_threshold_section(self, parent: ttk.Frame) -> None:
        """Create confidence threshold slider section."""
        ttk.Label(parent, text="Confidence:").grid(row=3, column=0, sticky="w", pady=5)

        threshold_frame = ttk.Frame(parent)
        threshold_frame.grid(row=3, column=1, sticky="ew", pady=5)

        # Slider variable (0.5 to 0.95 range)
        self.confidence_threshold = tk.DoubleVar(value=0.7)

        # Slider widget
        slider = ttk.Scale(
            threshold_frame,
            from_=0.5,
            to=0.95,
            variable=self.confidence_threshold,
            orient="horizontal",
            length=200,
            command=self._on_threshold_change
        )
        slider.grid(row=0, column=0, padx=(0, 10))

        # Display current value label
        self.threshold_label = ttk.Label(threshold_frame, text="0.70")
        self.threshold_label.grid(row=0, column=1)

    def _on_threshold_change(self, value: str) -> None:
        """Update label when threshold slider changes."""
        threshold = float(value)
        if self.threshold_label:
            self.threshold_label.config(text=f"{threshold:.2f}")

    def _create_entities_section(self, parent: ttk.Frame) -> None:
        """Create the entity type selection section with checkboxes."""
        ttk.Label(parent, text="Entities:").grid(row=4, column=0, sticky="nw", pady=5)

        entities_frame = ttk.LabelFrame(parent, text="Select entity types to anonymize")
        entities_frame.grid(row=4, column=1, sticky="ew", pady=5)

        # Human-readable names for entity types
        entity_labels = {
            "PERSON": "Person names",
            "EMAIL_ADDRESS": "Email addresses",
            "PHONE_NUMBER": "Phone numbers",
            "CREDIT_CARD": "Credit cards",
            "IBAN_CODE": "IBAN codes",
            "LOCATION": "Locations",
            "DATE_TIME": "Dates & times",
            "NRP": "National IDs (NRP)",
        }

        # Create checkboxes in a grid layout (2 columns)
        for idx, entity_type in enumerate(SUPPORTED_ENTITIES):
            var = tk.BooleanVar(value=True)  # All selected by default
            self.entity_vars[entity_type] = var

            label = entity_labels.get(entity_type, entity_type)
            cb = ttk.Checkbutton(entities_frame, text=label, variable=var)
            row = idx // 2
            col = idx % 2
            cb.grid(row=row, column=col, sticky="w", padx=10, pady=2)

        # Select All / Deselect All buttons
        btn_frame = ttk.Frame(entities_frame)
        btn_frame.grid(row=(len(SUPPORTED_ENTITIES) // 2) + 1, column=0, columnspan=2, pady=5)

        ttk.Button(btn_frame, text="Select All", command=self._select_all_entities).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(btn_frame, text="Deselect All", command=self._deselect_all_entities).grid(
            row=0, column=1, padx=5
        )

    def _select_all_entities(self) -> None:
        """Select all entity checkboxes."""
        for var in self.entity_vars.values():
            var.set(True)

    def _deselect_all_entities(self) -> None:
        """Deselect all entity checkboxes."""
        for var in self.entity_vars.values():
            var.set(False)

    def _get_selected_entities(self) -> List[str]:
        """Get list of currently selected entity types."""
        return [
            entity_type
            for entity_type, var in self.entity_vars.items()
            if var.get()
        ]

    def _create_status_section(self, parent: ttk.Frame) -> None:
        """Create the status display section."""
        ttk.Label(parent, text="Status:").grid(row=5, column=0, sticky="nw", pady=5)

        status_frame = ttk.Frame(parent)
        status_frame.grid(row=5, column=1, sticky="nsew", pady=5)
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        parent.rowconfigure(5, weight=1)

        self.status_text = tk.Text(
            status_frame,
            height=10,
            width=50,
            state="disabled",
            wrap="word",
        )
        self.status_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(status_frame, command=self.status_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.status_text.config(yscrollcommand=scrollbar.set)

        self._log_status("Ready. Select a file to anonymize.")

    def _create_buttons_section(self, parent: ttk.Frame) -> None:
        """Create the action buttons section."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=6, column=0, columnspan=2, pady=15)

        ttk.Button(
            button_frame,
            text="Anonymize",
            command=self._on_anonymize_click,
            width=15,
        ).grid(row=0, column=0, padx=10)

        self.view_mapping_btn = ttk.Button(
            button_frame,
            text="View Mapping",
            command=self._on_view_mapping_click,
            width=15,
            state="disabled",
        )
        self.view_mapping_btn.grid(row=0, column=1, padx=10)

    def _browse_input_file(self) -> None:
        """Open file dialog for input file selection."""
        # Build supported files pattern from config
        supported_patterns = " ".join(f"*{ext}" for ext in SUPPORTED_FILE_EXTENSIONS)

        filetypes = [
            ("Supported files", supported_patterns),
            ("Text files", "*.txt"),
            ("Markdown files", "*.md"),
            ("Word documents", "*.docx"),
            ("PDF files", "*.pdf"),
            ("All files", "*.*"),
        ]

        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self.input_path.set(path)
            self._suggest_output_path(Path(path))

    def _browse_output(self) -> None:
        """Open dialog for output location selection."""
        input_val = self.input_path.get()

        if input_val and Path(input_val).is_file():
            path = filedialog.asksaveasfilename(
                defaultextension=Path(input_val).suffix,
                filetypes=[("Same as input", f"*{Path(input_val).suffix}")],
            )
        else:
            path = filedialog.askdirectory()

        if path:
            self.output_path.set(path)

    def _suggest_output_path(self, input_path: Path) -> None:
        """Suggest an output path based on input path."""
        stem = input_path.stem
        suffix = input_path.suffix
        suggested = input_path.parent / f"{stem}.anonym{suffix}"
        self.output_path.set(str(suggested))

    def _on_input_path_changed(self, *args) -> None:  # type: ignore[no-untyped-def]
        """Called when input path changes (typed or pasted)."""
        input_val = self.input_path.get()
        if input_val and Path(input_val).exists() and Path(input_val).is_file():
            self._suggest_output_path(Path(input_val))

    def _on_language_selected(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Handle language selection change."""
        selection = self.selected_language.get()
        language_code = selection.split(" - ")[0]
        self.selected_language.set(language_code)

    def _extract_context(self, text: str, entity: PIIEntity, context_length: int = 50) -> str:
        """
        Extract surrounding context for an entity.

        Args:
            text: Full document text
            entity: Entity to extract context for
            context_length: Number of characters to show before/after

        Returns:
            Context string with entity highlighted
        """
        start = max(0, entity.start - context_length)
        end = min(len(text), entity.end + context_length)

        context = text[start:end]

        # Add ellipsis if truncated
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."

        # Replace newlines/tabs with spaces for display
        context = " ".join(context.split())

        return context

    def _show_entity_selection_dialog(
        self,
        entities: List[PIIEntity],
        text: str,
        threshold: float
    ) -> Optional[List[PIIEntity]]:
        """
        Show dialog for user to select which entities to anonymize.

        Args:
            entities: List of detected entities above threshold
            text: Original document text for context extraction
            threshold: Current confidence threshold

        Returns:
            List of selected entities, or None if cancelled
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Entities to Anonymize")
        dialog.geometry("900x600")
        dialog.transient(self.root)
        dialog.grab_set()

        # Result variable
        selected_entities: Optional[List[PIIEntity]] = None

        # Header frame
        header_frame = ttk.Frame(dialog)
        header_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(
            header_frame,
            text=f"Found {len(entities)} entities with confidence >= {threshold:.2f}",
            font=("", 10, "bold")
        ).pack(side="left")

        # Create treeview with scrollbars
        tree_frame = ttk.Frame(dialog)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Treeview columns
        columns = ("select", "text", "type", "score", "context")
        tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="extended"
        )

        # Column headers
        tree.heading("select", text="Select")
        tree.heading("text", text="Entity Text")
        tree.heading("type", text="Type")
        tree.heading("score", text="Score")
        tree.heading("context", text="Context")

        # Column widths
        tree.column("select", width=60, anchor="center")
        tree.column("text", width=150)
        tree.column("type", width=120)
        tree.column("score", width=80, anchor="center")
        tree.column("context", width=400)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # Track selection state per item
        selection_state: Dict[str, bool] = {}

        # Populate treeview
        for idx, entity in enumerate(entities):
            item_id = str(idx)
            context = self._extract_context(text, entity, context_length=50)

            tree.insert(
                "",
                "end",
                iid=item_id,
                values=(
                    "✓",  # Default checked
                    entity.text,
                    entity.entity_type,
                    f"{entity.score:.3f}",
                    context
                ),
                tags=("checked",)
            )
            selection_state[item_id] = True

        # Configure tag colors
        tree.tag_configure("checked", background="#d4edda")
        tree.tag_configure("unchecked", background="#f8d7da")

        # Toggle selection on double-click
        def toggle_selection(event: tk.Event) -> None:  # type: ignore[type-arg]
            item = tree.identify_row(event.y)
            if item:
                current_state = selection_state[item]
                new_state = not current_state
                selection_state[item] = new_state

                # Update visual
                check_mark = "✓" if new_state else "✗"
                tag = "checked" if new_state else "unchecked"

                values = tree.item(item)["values"]
                tree.item(item, values=(check_mark, *values[1:]), tags=(tag,))

        tree.bind("<Double-1>", toggle_selection)

        # Button frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=10, pady=10)

        def select_all_above_threshold() -> None:
            """Select all entities with score >= threshold."""
            for idx, entity in enumerate(entities):
                item_id = str(idx)
                if entity.score >= threshold:
                    selection_state[item_id] = True
                    values = tree.item(item_id)["values"]
                    tree.item(item_id, values=("✓", *values[1:]), tags=("checked",))

        def deselect_all() -> None:
            """Deselect all entities."""
            for item_id in selection_state:
                selection_state[item_id] = False
                values = tree.item(item_id)["values"]
                tree.item(item_id, values=("✗", *values[1:]), tags=("unchecked",))

        def confirm() -> None:
            """Confirm selection and close dialog."""
            nonlocal selected_entities
            selected_entities = [
                entities[int(item_id)]
                for item_id, is_selected in selection_state.items()
                if is_selected
            ]
            dialog.destroy()

        def cancel() -> None:
            """Cancel and close dialog."""
            nonlocal selected_entities
            selected_entities = None
            dialog.destroy()

        # Buttons
        ttk.Button(
            button_frame,
            text="Select All Above Threshold",
            command=select_all_above_threshold
        ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="Deselect All",
            command=deselect_all
        ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="Anonymize Selected",
            command=confirm
        ).pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="Cancel",
            command=cancel
        ).pack(side="right", padx=5)

        # Wait for dialog to close
        dialog.wait_window()

        return selected_entities

    def _on_anonymize_click(self) -> None:
        """Handle anonymize button click."""
        input_val = self.input_path.get()
        output_val = self.output_path.get()

        if not input_val:
            messagebox.showerror("Error", "Please select an input file.")
            return

        if not output_val:
            messagebox.showerror("Error", "Please select an output location.")
            return

        selected_entities = self._get_selected_entities()
        if not selected_entities:
            messagebox.showerror("Error", "Please select at least one entity type to anonymize.")
            return

        input_path = Path(input_val)

        # Validate input is a file (not folder)
        if not input_path.is_file():
            messagebox.showerror("Error", "Please select a file (folder mode removed).")
            return

        language = self.selected_language.get().split(" - ")[0]
        threshold = self.confidence_threshold.get() if self.confidence_threshold else 0.7

        self._log_status("Starting anonymization...")
        self._log_status(f"Language: {language}")
        self._log_status(f"Confidence threshold: {threshold:.2f}")
        self._log_status(f"Entity types: {', '.join(selected_entities)}")
        self.root.update()

        try:
            service = AnonymizerService(
                language=language,
                selected_entities=selected_entities,
                min_confidence=threshold
            )

            # Show selection dialog for file
            result = service.anonymize_file_with_selection(
                input_path,
                Path(output_val),
                selection_callback=lambda entities, text:
                    self._show_entity_selection_dialog(entities, text, threshold)
            )

            if result is None:
                # User cancelled
                self._log_status("Anonymization cancelled by user.")
                return

            self._handle_file_result(result)
            self.view_mapping_btn.config(state="normal")
            messagebox.showinfo("Success", "Anonymization complete!")

        except Exception as e:
            self._log_status(f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))

    def _handle_file_result(self, result: DocumentResult) -> None:
        """Handle result from single file anonymization."""
        self._log_status(f"Output: {result.output_path}")
        self._log_status(f"Mapping: {result.mapping_path}")
        self._log_status(f"Entities anonymized: {result.entities_count}")
        self.last_mapping_path = result.mapping_path

    def _on_view_mapping_click(self) -> None:
        """Handle view mapping button click."""
        if not self.last_mapping_path:
            messagebox.showinfo("Info", "No mapping file available.")
            return

        try:
            with open(self.last_mapping_path, "r", encoding="utf-8") as f:
                mapping_data = json.load(f)

            self._show_mapping_window(mapping_data)

        except Exception as e:
            messagebox.showerror("Error", f"Could not load mapping: {e}")

    def _show_mapping_window(self, mapping_data: dict) -> None:  # type: ignore[type-arg]
        """Show mapping data in a new window."""
        window = tk.Toplevel(self.root)
        window.title("Anonymization Mapping")
        window.geometry("500x400")

        text = tk.Text(window, wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)

        formatted = json.dumps(mapping_data, indent=2, ensure_ascii=False)
        text.insert("1.0", formatted)
        text.config(state="disabled")

    def _log_status(self, message: str) -> None:
        """Add a message to the status display."""
        self.status_text.config(state="normal")
        self.status_text.insert("end", f"{message}\n")
        self.status_text.see("end")
        self.status_text.config(state="disabled")

    def run(self) -> None:
        """Start the GUI application."""
        self.root.mainloop()


def main() -> None:
    """Entry point for GUI."""
    app = AnonymizerGUI()
    app.run()


if __name__ == "__main__":
    main()
