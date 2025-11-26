"""Tkinter GUI interface for document anonymization."""

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from ..config import DEFAULT_LANGUAGE, SUPPORTED_ENTITIES, SUPPORTED_LANGUAGES
from ..core.anonymizer_service import AnonymizerService
from ..core.models import DocumentResult


class AnonymizerGUI:
    """
    Cross-platform GUI for document anonymization.

    Provides file/folder selection, language selection, and status display.
    """

    def __init__(self) -> None:
        """Initialize the GUI application."""
        self.root = tk.Tk()
        self.root.title("Document Anonymizer")
        self.root.geometry("600x650")
        self.root.minsize(500, 550)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.selected_language = tk.StringVar(value=DEFAULT_LANGUAGE)
        self.last_mapping_path: Optional[str] = None
        self.entity_vars: Dict[str, tk.BooleanVar] = {}

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
        ttk.Button(input_frame, text="Folder...", command=self._browse_input_folder).grid(
            row=0, column=2
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

    def _create_entities_section(self, parent: ttk.Frame) -> None:
        """Create the entity type selection section with checkboxes."""
        ttk.Label(parent, text="Entities:").grid(row=3, column=0, sticky="nw", pady=5)

        entities_frame = ttk.LabelFrame(parent, text="Select entity types to anonymize")
        entities_frame.grid(row=3, column=1, sticky="ew", pady=5)

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
        ttk.Label(parent, text="Status:").grid(row=4, column=0, sticky="nw", pady=5)

        status_frame = ttk.Frame(parent)
        status_frame.grid(row=4, column=1, sticky="nsew", pady=5)
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        parent.rowconfigure(4, weight=1)

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

        self._log_status("Ready. Select a file or folder to anonymize.")

    def _create_buttons_section(self, parent: ttk.Frame) -> None:
        """Create the action buttons section."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=5, column=0, columnspan=2, pady=15)

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
        filetypes = [
            ("Supported files", "*.txt *.docx *.pdf"),
            ("Text files", "*.txt"),
            ("Word documents", "*.docx"),
            ("PDF files", "*.pdf"),
            ("All files", "*.*"),
        ]

        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self.input_path.set(path)
            self._suggest_output_path(Path(path))

    def _browse_input_folder(self) -> None:
        """Open folder dialog for input folder selection."""
        path = filedialog.askdirectory()
        if path:
            self.input_path.set(path)
            self.output_path.set(f"{path}_anonymized")

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
        suggested = input_path.parent / f"{stem}_anonymized{suffix}"
        self.output_path.set(str(suggested))

    def _on_language_selected(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Handle language selection change."""
        selection = self.selected_language.get()
        language_code = selection.split(" - ")[0]
        self.selected_language.set(language_code)

    def _on_anonymize_click(self) -> None:
        """Handle anonymize button click."""
        input_val = self.input_path.get()
        output_val = self.output_path.get()

        if not input_val:
            messagebox.showerror("Error", "Please select an input file or folder.")
            return

        if not output_val:
            messagebox.showerror("Error", "Please select an output location.")
            return

        selected_entities = self._get_selected_entities()
        if not selected_entities:
            messagebox.showerror("Error", "Please select at least one entity type to anonymize.")
            return

        input_path = Path(input_val)
        language = self.selected_language.get().split(" - ")[0]

        self._log_status("Starting anonymization...")
        self._log_status(f"Language: {language}")
        self._log_status(f"Entities: {', '.join(selected_entities)}")
        self.root.update()

        try:
            service = AnonymizerService(language=language, selected_entities=selected_entities)

            if input_path.is_file():
                result = service.anonymize_file(input_path, Path(output_val))
                self._handle_file_result(result)
            else:
                results = service.anonymize_directory(input_path, Path(output_val))
                self._handle_directory_results(results)

            self.view_mapping_btn.config(state="normal")
            messagebox.showinfo("Success", "Anonymization complete!")

        except Exception as e:
            self._log_status(f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))

    def _handle_file_result(self, result: DocumentResult) -> None:
        """Handle result from single file anonymization."""
        self._log_status(f"Output: {result.output_path}")
        self._log_status(f"Mapping: {result.mapping_path}")
        self._log_status(f"Entities found: {result.entities_count}")
        self.last_mapping_path = result.mapping_path

    def _handle_directory_results(self, results: list[DocumentResult]) -> None:
        """Handle results from directory anonymization."""
        self._log_status(f"Files processed: {len(results)}")

        total_entities = sum(r.entities_count for r in results)
        self._log_status(f"Total entities: {total_entities}")

        for result in results:
            self._log_status(f"  - {result.input_path}")

        if results:
            self.last_mapping_path = results[0].mapping_path

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
