"""Tkinter GUI interface for document anonymization."""

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict, List, Optional, Tuple

from ..config import (
    AVAILABLE_MODELS,
    AVAILABLE_TRANSFORMERS_MODELS,
    DEFAULT_LANGUAGE,
    LANGUAGE_NAMES,
    SELECTED_TRANSFORMERS_MODEL,
    SUPPORTED_ENTITIES,
    SUPPORTED_FILE_EXTENSIONS,
    SUPPORTED_LANGUAGES,
    download_transformers_model,
    get_nlp_engine_type,
    get_transformers_model_for_language,
    install_huggingface_pipelines,
    is_huggingface_pipelines_available,
    is_model_installed,
    is_transformers_model_cached,
    set_model_for_language,
    set_nlp_engine_type,
    set_transformers_model_for_language,
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
        self.model_info_label: Optional[ttk.Label] = None

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

        lang_frame = ttk.Frame(parent)
        lang_frame.grid(row=2, column=1, sticky="ew", pady=5)

        language_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.selected_language,
            values=[f"{code} - {name}" for code, name in LANGUAGE_NAMES.items()],
            state="readonly",
            width=20,
        )
        language_combo.pack(side="left")
        language_combo.set(f"{DEFAULT_LANGUAGE} - {LANGUAGE_NAMES[DEFAULT_LANGUAGE]}")

        language_combo.bind("<<ComboboxSelected>>", self._on_language_selected)

        # Model info label
        self.model_info_label = ttk.Label(lang_frame, text="", foreground="gray")
        self.model_info_label.pack(side="left", padx=(15, 0))
        self._update_model_info_label()

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

        ttk.Button(
            button_frame,
            text="Configure Models...",
            command=self._show_model_selection_dialog,
            width=15,
        ).grid(row=0, column=2, padx=10)

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
        self._update_model_info_label()

    def _get_current_model_info(self, language: str) -> str:
        """Get a description of the currently configured model for a language."""
        engine_type = get_nlp_engine_type()

        if engine_type == "transformers":
            transformers_model = get_transformers_model_for_language(language)
            if transformers_model is not None:
                # Shorten the model name for display
                short_name = transformers_model.name.split("/")[-1]
                return f"Model: {short_name} (transformers)"

        # Default to spaCy
        spacy_model = SUPPORTED_LANGUAGES.get(language, "")
        if spacy_model:
            return f"Model: {spacy_model} (spaCy)"
        return "Model: not configured"

    def _update_model_info_label(self) -> None:
        """Update the model info label with current configuration."""
        if self.model_info_label is None:
            return

        language = self.selected_language.get().split(" - ")[0]
        model_info = self._get_current_model_info(language)
        self.model_info_label.config(text=model_info)

    def _run_with_progress(
        self,
        parent: tk.Toplevel,
        title: str,
        message: str,
        task: Callable[[], bool],
    ) -> bool:
        """
        Run a task in a background thread with a progress dialog.

        Args:
            parent: Parent window for the dialog
            title: Dialog title
            message: Message to display
            task: Function to run (returns True on success, False on failure)

        Returns:
            True if task succeeded, False otherwise
        """
        result: List[bool] = [False]  # Use list to allow modification in nested function
        error_msg: List[str] = [""]

        # Create progress dialog
        progress_dialog = tk.Toplevel(parent)
        progress_dialog.title(title)
        progress_dialog.geometry("400x120")
        progress_dialog.transient(parent)
        progress_dialog.grab_set()
        progress_dialog.resizable(False, False)

        # Center the dialog
        progress_dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 120) // 2
        progress_dialog.geometry(f"+{x}+{y}")

        # Message label
        msg_label = ttk.Label(
            progress_dialog,
            text=message,
            wraplength=380,
            justify="center"
        )
        msg_label.pack(pady=(20, 10), padx=10)

        # Progress bar (indeterminate mode)
        progress_bar = ttk.Progressbar(
            progress_dialog,
            mode="indeterminate",
            length=350
        )
        progress_bar.pack(pady=10, padx=20)
        progress_bar.start(10)

        def run_task() -> None:
            try:
                result[0] = task()
            except Exception as e:
                result[0] = False
                error_msg[0] = str(e)
            finally:
                # Schedule dialog close on main thread
                progress_dialog.after(0, progress_dialog.destroy)

        # Start task in background thread
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        # Wait for dialog to close
        parent.wait_window(progress_dialog)

        return result[0]

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

    def _show_model_selection_dialog(self) -> None:
        """Show dialog for selecting NLP engine and models."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Configure Language Models")
        dialog.geometry("650x600")
        dialog.transient(self.root)
        dialog.grab_set()

        # Track selected models
        spacy_model_vars: Dict[str, tk.StringVar] = {}
        transformers_model_vars: Dict[str, tk.StringVar] = {}

        # Engine type variable
        engine_type_var = tk.StringVar(value=get_nlp_engine_type())

        # Main scrollable frame
        canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Engine type selection
        engine_frame = ttk.LabelFrame(
            scrollable_frame, text="NLP Engine Type", padding=10
        )
        engine_frame.pack(fill="x", padx=10, pady=10)

        ttk.Radiobutton(
            engine_frame,
            text="spaCy (built-in NER models)",
            variable=engine_type_var,
            value="spacy",
        ).pack(anchor="w")

        ttk.Radiobutton(
            engine_frame,
            text="HuggingFace Transformers (custom NER models)",
            variable=engine_type_var,
            value="transformers",
        ).pack(anchor="w")

        ttk.Label(
            engine_frame,
            text="Note: Transformers requires 'spacy-huggingface-pipelines' package",
            font=("", 9, "italic"),
            foreground="gray",
        ).pack(anchor="w", pady=(5, 0))

        # spaCy models section
        spacy_section = ttk.LabelFrame(
            scrollable_frame, text="spaCy Models", padding=10
        )
        spacy_section.pack(fill="x", padx=10, pady=5)

        for lang_code, models in AVAILABLE_MODELS.items():
            lang_name = LANGUAGE_NAMES.get(lang_code, lang_code)
            current_model = SUPPORTED_LANGUAGES.get(lang_code, "")

            lang_frame = ttk.Frame(spacy_section)
            lang_frame.pack(fill="x", pady=2)

            ttk.Label(lang_frame, text=f"{lang_name}:", width=10).pack(side="left")

            model_var = tk.StringVar(value=current_model)
            spacy_model_vars[lang_code] = model_var

            model_combo = ttk.Combobox(
                lang_frame,
                textvariable=model_var,
                values=[m.name for m in models],
                state="readonly",
                width=25,
            )
            model_combo.pack(side="left", padx=5)

            # Show install status
            def make_status_label(lf: ttk.Frame, mv: tk.StringVar) -> tk.Label:
                label = tk.Label(lf, text="", width=12)
                label.pack(side="left")

                def update_status(*args: object) -> None:
                    installed = is_model_installed(mv.get())
                    label.config(
                        text="Installed" if installed else "Not installed",
                        fg="green" if installed else "gray",
                    )

                mv.trace_add("write", update_status)
                update_status()
                return label

            make_status_label(lang_frame, model_var)

        # Transformers models section
        transformers_section = ttk.LabelFrame(
            scrollable_frame, text="HuggingFace Transformer Models (for NER)", padding=10
        )
        transformers_section.pack(fill="x", padx=10, pady=5)

        # Show package availability status with install button
        pkg_status_frame = ttk.Frame(transformers_section)
        pkg_status_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(pkg_status_frame, text="Transformers support: ").pack(side="left")

        pkg_status_label = tk.Label(pkg_status_frame, text="", width=20)
        pkg_status_label.pack(side="left")

        pkg_install_btn = ttk.Button(pkg_status_frame, text="Install", width=10)
        pkg_install_btn.pack(side="left", padx=5)

        def update_pkg_status() -> None:
            pkg_available = is_huggingface_pipelines_available()
            if pkg_available:
                pkg_status_label.config(text="Ready", fg="green")
                pkg_install_btn.config(state="disabled")
            else:
                pkg_status_label.config(text="Not installed", fg="orange")
                pkg_install_btn.config(state="normal")

        def do_install_pkg() -> None:
            pkg_install_btn.config(state="disabled")
            pkg_status_label.config(text="Installing...", fg="blue")
            dialog.update()

            success, message = install_huggingface_pipelines()

            if success:
                pkg_status_label.config(text="Ready", fg="green")
                messagebox.showinfo("Success", "Transformers support installed successfully.")
            else:
                pkg_status_label.config(text="Install failed", fg="red")
                pkg_install_btn.config(state="normal")
                messagebox.showerror("Error", f"Installation failed:\n{message}")

        pkg_install_btn.config(command=do_install_pkg)
        update_pkg_status()

        # Store status labels and download buttons for updates
        transformers_status_labels: Dict[str, tk.Label] = {}
        transformers_download_btns: Dict[str, ttk.Button] = {}

        for lang_code in LANGUAGE_NAMES.keys():
            lang_name = LANGUAGE_NAMES.get(lang_code, lang_code)
            available_models = AVAILABLE_TRANSFORMERS_MODELS.get(lang_code, [])
            current_model = SELECTED_TRANSFORMERS_MODEL.get(lang_code, "") or ""

            lang_frame = ttk.Frame(transformers_section)
            lang_frame.pack(fill="x", pady=2)

            ttk.Label(lang_frame, text=f"{lang_name}:", width=10).pack(side="left")

            model_var = tk.StringVar(value=current_model)
            transformers_model_vars[lang_code] = model_var

            model_values = ["(none)"] + [m.name for m in available_models]
            model_combo = ttk.Combobox(
                lang_frame,
                textvariable=model_var,
                values=model_values,
                state="readonly",
                width=35,
            )
            model_combo.pack(side="left", padx=5)

            if not available_models:
                ttk.Label(lang_frame, text="(no models available)", foreground="gray").pack(
                    side="left"
                )
            else:
                # Status label for cached/not cached
                status_label = tk.Label(lang_frame, text="", width=12)
                status_label.pack(side="left")
                transformers_status_labels[lang_code] = status_label

                # Download button
                download_btn = ttk.Button(lang_frame, text="Download", width=10)
                download_btn.pack(side="left", padx=5)
                transformers_download_btns[lang_code] = download_btn

                def make_update_status(
                    _lc: str, mv: tk.StringVar, sl: tk.Label, db: ttk.Button
                ) -> None:
                    def update_status(*_args: object) -> None:
                        model_name = mv.get()
                        if model_name == "(none)" or model_name == "":
                            sl.config(text="", fg="gray")
                            db.config(state="disabled")
                        else:
                            cached = is_transformers_model_cached(model_name)
                            sl.config(
                                text="Cached" if cached else "Not cached",
                                fg="green" if cached else "gray",
                            )
                            db.config(state="disabled" if cached else "normal")

                    def do_download() -> None:
                        model_name = mv.get()
                        if model_name and model_name != "(none)":
                            db.config(state="disabled")
                            sl.config(text="Downloading...", fg="blue")
                            dialog.update()
                            success = download_transformers_model(model_name)
                            if success:
                                sl.config(text="Cached", fg="green")
                            else:
                                sl.config(text="Failed", fg="red")
                                db.config(state="normal")

                    mv.trace_add("write", update_status)
                    db.config(command=do_download)
                    update_status()

                make_update_status(
                    lang_code, model_var, status_label, download_btn
                )

        # Description of selected transformers model
        desc_frame = ttk.Frame(transformers_section)
        desc_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(
            desc_frame,
            text="Tip: Medical de-id models (obi/deid_roberta_i2b2, StanfordAIMI) are optimized for healthcare data",
            font=("", 9, "italic"),
            foreground="gray",
        ).pack(anchor="w")

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Button frame at bottom
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", pady=10, padx=10)

        def save_selection() -> None:
            """Save the selected models and engine type."""
            # Check if transformers engine selected and collect models to download
            engine = engine_type_var.get()
            models_to_download: List[Tuple[str, str, tk.Label, ttk.Button]] = []

            if engine == "transformers":
                # First check if spacy-huggingface-pipelines is installed
                if not is_huggingface_pipelines_available():
                    # Install it with progress dialog
                    pkg_install_btn.config(state="disabled")

                    success = self._run_with_progress(
                        dialog,
                        "Installing Dependencies",
                        "Installing transformers support package...\n"
                        "This may take a few minutes.",
                        lambda: install_huggingface_pipelines()[0]
                    )

                    if success:
                        pkg_status_label.config(text="Ready", fg="green")
                    else:
                        pkg_status_label.config(text="Install failed", fg="red")
                        pkg_install_btn.config(state="normal")
                        messagebox.showerror(
                            "Error",
                            "Failed to install transformers support.\n\n"
                            "Please check your internet connection and try again."
                        )
                        return

                # Collect transformers models that need downloading
                for lang_code, var in transformers_model_vars.items():
                    selected = var.get()
                    if selected and selected != "(none)" and selected != "":
                        if not is_transformers_model_cached(selected):
                            status_label = transformers_status_labels.get(lang_code)
                            download_btn = transformers_download_btns.get(lang_code)
                            if status_label and download_btn:
                                models_to_download.append(
                                    (lang_code, selected, status_label, download_btn)
                                )

            # Download any missing models with progress dialog
            if models_to_download:
                for lang_code, model_name, status_label, download_btn in models_to_download:
                    download_btn.config(state="disabled")
                    dialog.update()

                    # Get model size for display
                    model_size = ""
                    available = AVAILABLE_TRANSFORMERS_MODELS.get(lang_code, [])
                    for m in available:
                        if m.name == model_name:
                            model_size = f" (~{m.size_mb} MB)"
                            break

                    success = self._run_with_progress(
                        dialog,
                        "Downloading Model",
                        f"Downloading: {model_name}{model_size}\n\n"
                        "This may take several minutes depending on your connection.",
                        lambda mn=model_name: download_transformers_model(mn)
                    )

                    if success:
                        status_label.config(text="Cached", fg="green")
                    else:
                        status_label.config(text="Failed", fg="red")
                        download_btn.config(state="normal")
                        messagebox.showerror(
                            "Error",
                            f"Failed to download model: {model_name}\n\n"
                            "Please check your internet connection and try again."
                        )
                        return

            # Save engine type
            set_nlp_engine_type(engine)

            # Save spaCy models
            for lang_code, var in spacy_model_vars.items():
                selected = var.get()
                if selected:
                    set_model_for_language(lang_code, selected)

            # Save transformers models
            for lang_code, var in transformers_model_vars.items():
                selected = var.get()
                if selected == "(none)" or selected == "":
                    set_transformers_model_for_language(lang_code, None)
                else:
                    set_transformers_model_for_language(lang_code, selected)

            self._log_status(f"Model configuration updated. Engine: {engine}")
            self._update_model_info_label()
            dialog.destroy()

        def cancel() -> None:
            """Close without saving."""
            dialog.destroy()

        ttk.Button(button_frame, text="Save", command=save_selection, width=10).pack(
            side="right", padx=5
        )
        ttk.Button(button_frame, text="Cancel", command=cancel, width=10).pack(
            side="right", padx=5
        )

        # Wait for dialog
        dialog.wait_window()

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

        model_info = self._get_current_model_info(language)
        self._log_status("Starting anonymization...")
        self._log_status(f"Language: {language}")
        self._log_status(model_info)
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
