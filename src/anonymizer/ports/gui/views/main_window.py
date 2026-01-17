"""Main window view - humble Tkinter implementation with zero business logic."""

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict, List, Optional

from ....config import (
    AVAILABLE_MODELS,
    DEFAULT_LANGUAGE,
    LANGUAGE_NAMES,
    SUPPORTED_ENTITIES,
    SUPPORTED_FILE_EXTENSIONS,
    set_model_for_language,
)
from ....core.models import PIIEntity
from ....model_storage import is_model_downloaded


class AnonymizerView:
    """
    Main window view - humble object with zero business logic.

    All methods are simple UI operations. Business logic is in AnonymizerPresenter.
    """

    def __init__(self) -> None:
        """Initialize the view."""
        self.root = tk.Tk()
        self.root.title("Document Anonymizer")
        self.root.geometry("600x700")
        self.root.minsize(500, 600)

        self._input_path = tk.StringVar()
        self._output_path = tk.StringVar()
        self._selected_language = tk.StringVar(value=DEFAULT_LANGUAGE)
        self._confidence_threshold: Optional[tk.DoubleVar] = None
        self._threshold_label: Optional[ttk.Label] = None
        self._entity_vars: Dict[str, tk.BooleanVar] = {}
        self._model_info_label: Optional[ttk.Label] = None
        self._view_mapping_btn: Optional[ttk.Button] = None
        self._status_text: Optional[tk.Text] = None

        # Model selection menu widgets
        self._model_menu_btn: Optional[tk.Menubutton] = None
        self._model_menu: Optional[tk.Menu] = None
        self._selected_model: Optional[str] = None

        # Callbacks set by presenter
        self._on_anonymize: Optional[Callable[[], None]] = None
        self._on_view_mapping: Optional[Callable[[], None]] = None
        self._on_language_changed: Optional[Callable[[str], None]] = None
        self._on_model_changed: Optional[Callable[[str, str], None]] = None
        self._on_model_manager: Optional[Callable[[], None]] = None

        # Dialog factories set by composition root
        self._entity_dialog_factory: Optional[Callable] = None

        # Watch for input path changes
        self._input_path.trace_add("write", self._handle_input_path_change)

        self._setup_ui()

    # Properties for presenter access
    @property
    def input_path(self) -> str:
        """Get the input path value."""
        return self._input_path.get()

    @property
    def output_path(self) -> str:
        """Get the output path value."""
        return self._output_path.get()

    @property
    def selected_language(self) -> str:
        """Get the selected language value."""
        return self._selected_language.get()

    @property
    def confidence_threshold(self) -> float:
        """Get the confidence threshold value."""
        return self._confidence_threshold.get() if self._confidence_threshold else 0.7

    @property
    def selected_model(self) -> Optional[str]:
        """Get the currently selected model name."""
        return self._selected_model

    # Setter methods for presenter
    def set_input_path(self, path: str) -> None:
        """Set the input path value."""
        self._input_path.set(path)

    def set_output_path(self, path: str) -> None:
        """Set the output path value."""
        self._output_path.set(path)

    # Callback registration
    def set_on_anonymize(self, callback: Callable[[], None]) -> None:
        """Set the anonymize button callback."""
        self._on_anonymize = callback

    def set_on_view_mapping(self, callback: Callable[[], None]) -> None:
        """Set the view mapping button callback."""
        self._on_view_mapping = callback

    def set_on_language_changed(self, callback: Callable[[str], None]) -> None:
        """Set the language changed callback."""
        self._on_language_changed = callback

    def set_on_model_changed(self, callback: Callable[[str, str], None]) -> None:
        """Set the model changed callback (lang_code, model_name)."""
        self._on_model_changed = callback

    def set_on_model_manager(self, callback: Callable[[], None]) -> None:
        """Set the model manager menu callback."""
        self._on_model_manager = callback

    def set_entity_dialog_factory(self, factory: Callable) -> None:
        """Set the entity selection dialog factory."""
        self._entity_dialog_factory = factory

    # View methods for presenter
    def get_selected_entities(self) -> List[str]:
        """Get list of currently selected entity types."""
        return [
            entity_type
            for entity_type, var in self._entity_vars.items()
            if var.get()
        ]

    def show_error(self, title: str, message: str) -> None:
        """Show an error dialog."""
        messagebox.showerror(title, message)

    def show_success(self, title: str, message: str) -> None:
        """Show a success dialog."""
        messagebox.showinfo(title, message)

    def show_info(self, title: str, message: str) -> None:
        """Show an info dialog."""
        messagebox.showinfo(title, message)

    def log_status(self, message: str) -> None:
        """Add a message to the status display."""
        if self._status_text:
            self._status_text.config(state="normal")
            self._status_text.insert("end", f"{message}\n")
            self._status_text.see("end")
            self._status_text.config(state="disabled")

    def set_mapping_button_enabled(self, enabled: bool) -> None:
        """Enable or disable the view mapping button."""
        if self._view_mapping_btn:
            self._view_mapping_btn.config(state="normal" if enabled else "disabled")

    def set_model_info_text(self, text: str) -> None:
        """Set the model info label text."""
        if self._model_info_label:
            self._model_info_label.config(text=text)

    def refresh_available_languages(self) -> None:
        """Refresh the model menu based on downloaded models."""
        self._populate_model_menu()

    def show_mapping_window(self, mapping_data: dict) -> None:
        """Show mapping data in a new window."""
        window = tk.Toplevel(self.root)
        window.title("Anonymization Mapping")
        window.geometry("500x400")

        text = tk.Text(window, wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)

        formatted = json.dumps(mapping_data, indent=2, ensure_ascii=False)
        text.insert("1.0", formatted)
        text.config(state="disabled")

    def show_entity_selection_dialog(
        self,
        entities: List[PIIEntity],
        text: str,
        threshold: float
    ) -> Optional[List[PIIEntity]]:
        """Show the entity selection dialog."""
        if self._entity_dialog_factory:
            return self._entity_dialog_factory(self.root, entities, text, threshold)
        return None

    def update_display(self) -> None:
        """Force UI update."""
        self.root.update()

    def run(self) -> None:
        """Start the GUI application."""
        self.root.mainloop()

    # UI Setup methods (pure UI creation, no logic)
    def _setup_ui(self) -> None:
        """Build the user interface."""
        # Create menu bar first
        self._create_menu_bar()

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

    def _create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)

        file_menu.add_command(
            label="Model Manager...", command=self._handle_model_manager_click
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

    def _handle_model_manager_click(self) -> None:
        """Handle Model Manager menu click."""
        if self._on_model_manager:
            self._on_model_manager()

    def _create_input_section(self, parent: ttk.Frame) -> None:
        """Create the input file selection section."""
        ttk.Label(parent, text="Input:").grid(row=0, column=0, sticky="w", pady=5)

        input_frame = ttk.Frame(parent)
        input_frame.grid(row=0, column=1, sticky="ew", pady=5)
        input_frame.columnconfigure(0, weight=1)

        ttk.Entry(input_frame, textvariable=self._input_path).grid(
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

        ttk.Entry(output_frame, textvariable=self._output_path).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )

        ttk.Button(output_frame, text="Browse...", command=self._browse_output).grid(
            row=0, column=1
        )

    def _create_language_section(self, parent: ttk.Frame) -> None:
        """Create hierarchical model selection with cascading menu."""
        ttk.Label(parent, text="Model:").grid(row=2, column=0, sticky="w", pady=5)

        model_frame = ttk.Frame(parent)
        model_frame.grid(row=2, column=1, sticky="ew", pady=5)

        # Menu button showing current selection
        self._model_menu_btn = tk.Menubutton(
            model_frame,
            text="Select Model...",
            relief="raised",
            width=35,
        )
        self._model_menu_btn.pack(side="left")

        # Build hierarchical menu
        self._model_menu = tk.Menu(self._model_menu_btn, tearoff=0)
        self._model_menu_btn["menu"] = self._model_menu
        self._populate_model_menu()

        # Model info label
        self._model_info_label = ttk.Label(model_frame, text="", foreground="gray")
        self._model_info_label.pack(side="left", padx=(15, 0))

    def _populate_model_menu(self) -> None:
        """Build cascading menu with downloaded models by language."""
        if not self._model_menu:
            return

        self._model_menu.delete(0, "end")
        has_any_models = False
        first_model_info: Optional[tuple[str, str]] = None

        for lang_code, lang_name in LANGUAGE_NAMES.items():
            # Get downloaded models for this language
            models = AVAILABLE_MODELS.get(lang_code, [])
            downloaded = [m for m in models if is_model_downloaded(m.name)]

            if not downloaded:
                continue  # Skip languages with no downloaded models

            has_any_models = True

            # Create submenu for this language
            lang_menu = tk.Menu(self._model_menu, tearoff=0)
            self._model_menu.add_cascade(label=lang_name, menu=lang_menu)

            for model in downloaded:
                label = f"{model.name} ({model.size_mb} MB - {model.description})"
                # Use default argument to capture current values
                lang_menu.add_command(
                    label=label,
                    command=lambda lc=lang_code, mn=model.name: self._select_model(lc, mn),
                )

                # Track first model for auto-selection
                if first_model_info is None:
                    first_model_info = (lang_code, model.name)

        if not has_any_models:
            self._model_menu.add_command(
                label="No models downloaded",
                state="disabled",
            )
            self._model_menu.add_separator()
            self._model_menu.add_command(
                label="Use File > Model Manager to download",
                state="disabled",
            )
            if self._model_menu_btn:
                self._model_menu_btn.config(text="No models - use Model Manager")
        elif self._selected_model is None and first_model_info:
            # Auto-select first available model on initial load
            self._select_model(first_model_info[0], first_model_info[1])

    def _select_model(self, lang_code: str, model_name: str) -> None:
        """Handle model selection from menu."""
        self._selected_language.set(lang_code)
        self._selected_model = model_name

        # Update config immediately (important for initialization before callbacks are wired)
        set_model_for_language(lang_code, model_name)

        # Update button text
        lang_name = LANGUAGE_NAMES.get(lang_code, lang_code)
        if self._model_menu_btn:
            self._model_menu_btn.config(text=f"{lang_name}: {model_name}")

        # Notify callbacks
        if self._on_language_changed:
            self._on_language_changed(lang_code)
        if self._on_model_changed:
            self._on_model_changed(lang_code, model_name)

    def _create_threshold_section(self, parent: ttk.Frame) -> None:
        """Create confidence threshold slider section."""
        ttk.Label(parent, text="Confidence:").grid(row=3, column=0, sticky="w", pady=5)

        threshold_frame = ttk.Frame(parent)
        threshold_frame.grid(row=3, column=1, sticky="ew", pady=5)

        self._confidence_threshold = tk.DoubleVar(value=0.7)

        slider = ttk.Scale(
            threshold_frame,
            from_=0.5,
            to=0.95,
            variable=self._confidence_threshold,
            orient="horizontal",
            length=200,
            command=self._handle_threshold_change
        )
        slider.grid(row=0, column=0, padx=(0, 10))

        self._threshold_label = ttk.Label(threshold_frame, text="0.70")
        self._threshold_label.grid(row=0, column=1)

    def _create_entities_section(self, parent: ttk.Frame) -> None:
        """Create the entity type selection section with checkboxes."""
        ttk.Label(parent, text="Entities:").grid(row=4, column=0, sticky="nw", pady=5)

        entities_frame = ttk.LabelFrame(parent, text="Select entity types to anonymize")
        entities_frame.grid(row=4, column=1, sticky="ew", pady=5)

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

        for idx, entity_type in enumerate(SUPPORTED_ENTITIES):
            var = tk.BooleanVar(value=True)
            self._entity_vars[entity_type] = var

            label = entity_labels.get(entity_type, entity_type)
            cb = ttk.Checkbutton(entities_frame, text=label, variable=var)
            row = idx // 2
            col = idx % 2
            cb.grid(row=row, column=col, sticky="w", padx=10, pady=2)

        btn_frame = ttk.Frame(entities_frame)
        btn_frame.grid(row=(len(SUPPORTED_ENTITIES) // 2) + 1, column=0, columnspan=2, pady=5)

        ttk.Button(btn_frame, text="Select All", command=self._select_all_entities).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(btn_frame, text="Deselect All", command=self._deselect_all_entities).grid(
            row=0, column=1, padx=5
        )

    def _create_status_section(self, parent: ttk.Frame) -> None:
        """Create the status display section."""
        ttk.Label(parent, text="Status:").grid(row=5, column=0, sticky="nw", pady=5)

        status_frame = ttk.Frame(parent)
        status_frame.grid(row=5, column=1, sticky="nsew", pady=5)
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        parent.rowconfigure(5, weight=1)

        self._status_text = tk.Text(
            status_frame,
            height=10,
            width=50,
            state="disabled",
            wrap="word",
        )
        self._status_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(status_frame, command=self._status_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._status_text.config(yscrollcommand=scrollbar.set)

        self.log_status("Ready. Select a file to anonymize.")

    def _create_buttons_section(self, parent: ttk.Frame) -> None:
        """Create the action buttons section."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=6, column=0, columnspan=2, pady=15)

        ttk.Button(
            button_frame,
            text="Anonymize",
            command=self._handle_anonymize_click,
            width=15,
        ).grid(row=0, column=0, padx=10)

        self._view_mapping_btn = ttk.Button(
            button_frame,
            text="View Mapping",
            command=self._handle_view_mapping_click,
            width=15,
            state="disabled",
        )
        self._view_mapping_btn.grid(row=0, column=1, padx=10)

    # Event handlers (simple delegation, no logic)
    def _handle_anonymize_click(self) -> None:
        """Handle anonymize button click - delegate to callback."""
        if self._on_anonymize:
            self._on_anonymize()

    def _handle_view_mapping_click(self) -> None:
        """Handle view mapping button click - delegate to callback."""
        if self._on_view_mapping:
            self._on_view_mapping()

    def _handle_threshold_change(self, value: str) -> None:
        """Update label when threshold slider changes."""
        threshold = float(value)
        if self._threshold_label:
            self._threshold_label.config(text=f"{threshold:.2f}")

    def _handle_input_path_change(self, *args) -> None:
        """Called when input path changes - suggest output path."""
        input_val = self._input_path.get()
        if input_val and Path(input_val).exists() and Path(input_val).is_file():
            self._suggest_output_path(Path(input_val))

    def _notify_model_config_saved(self, message: str) -> None:
        """Called when model config is saved."""
        self.log_status(message)
        if self._on_language_changed:
            language = self._selected_language.get().split(" - ")[0]
            self._on_language_changed(language)

    # File browser helpers (pure UI operations)
    def _browse_input_file(self) -> None:
        """Open file dialog for input file selection."""
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
            self._input_path.set(path)
            self._suggest_output_path(Path(path))

    def _browse_output(self) -> None:
        """Open dialog for output location selection."""
        input_val = self._input_path.get()

        if input_val and Path(input_val).is_file():
            path = filedialog.asksaveasfilename(
                defaultextension=Path(input_val).suffix,
                filetypes=[("Same as input", f"*{Path(input_val).suffix}")],
            )
        else:
            path = filedialog.askdirectory()

        if path:
            self._output_path.set(path)

    def _suggest_output_path(self, input_path: Path) -> None:
        """Suggest an output path based on input path."""
        stem = input_path.stem
        suffix = input_path.suffix
        suggested = input_path.parent / f"{stem}.anonym{suffix}"
        self._output_path.set(str(suggested))

    def _select_all_entities(self) -> None:
        """Select all entity checkboxes."""
        for var in self._entity_vars.values():
            var.set(True)

    def _deselect_all_entities(self) -> None:
        """Deselect all entity checkboxes."""
        for var in self._entity_vars.values():
            var.set(False)
