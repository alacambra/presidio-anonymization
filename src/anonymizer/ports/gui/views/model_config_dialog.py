"""Model configuration dialog view - humble Tkinter implementation with zero business logic."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict, Optional

from ..presenters.model_config_presenter import ModelConfigPresenter


class ModelConfigDialog:
    """
    Model configuration dialog view - humble object with zero business logic.

    All methods are simple UI operations. Business logic is in ModelConfigPresenter.
    """

    def __init__(self, parent: tk.Tk, on_saved: Optional[Callable[[str], None]] = None) -> None:
        """
        Initialize the dialog.

        Args:
            parent: Parent window
            on_saved: Optional callback called when config is saved
        """
        self._parent = parent
        self._on_saved = on_saved
        self._dialog: Optional[tk.Toplevel] = None
        self._saved = False

        # Create presenter
        self._presenter = ModelConfigPresenter(self)

        # UI state
        self._engine_type_var: Optional[tk.StringVar] = None
        self._spacy_model_vars: Dict[str, tk.StringVar] = {}
        self._transformers_model_vars: Dict[str, tk.StringVar] = {}
        self._pkg_status_label: Optional[tk.Label] = None
        self._pkg_install_btn: Optional[ttk.Button] = None
        self._transformers_status_labels: Dict[str, tk.Label] = {}
        self._transformers_download_btns: Dict[str, ttk.Button] = {}

    def show(self) -> bool:
        """
        Show the dialog and wait for user action.

        Returns:
            True if saved, False if cancelled
        """
        self._create_dialog()
        self._dialog.wait_window()
        return self._saved

    def update_spacy_model_status(self, lang_code: str, installed: bool) -> None:
        """Update spaCy model installation status display."""
        # This is handled via trace callbacks on the StringVars
        pass

    def update_transformers_status(self, lang_code: str, status_text: str, color: str) -> None:
        """Update transformers model status display."""
        label = self._transformers_status_labels.get(lang_code)
        if label:
            label.config(text=status_text, fg=color)

    def update_transformers_download_button(self, lang_code: str, enabled: bool) -> None:
        """Update transformers download button state."""
        btn = self._transformers_download_btns.get(lang_code)
        if btn:
            btn.config(state="normal" if enabled else "disabled")

    def update_package_status(self, status_text: str, color: str, install_enabled: bool) -> None:
        """Update package installation status display."""
        if self._pkg_status_label:
            self._pkg_status_label.config(text=status_text, fg=color)
        if self._pkg_install_btn:
            self._pkg_install_btn.config(state="normal" if install_enabled else "disabled")

    def show_error(self, title: str, message: str) -> None:
        """Show an error dialog."""
        messagebox.showerror(title, message)

    def show_info(self, title: str, message: str) -> None:
        """Show an info dialog."""
        messagebox.showinfo(title, message)

    def _create_dialog(self) -> None:
        """Create the dialog window and all widgets."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Configure Language Models")
        self._dialog.geometry("650x600")
        self._dialog.transient(self._parent)
        self._dialog.grab_set()

        # Main scrollable frame
        canvas = tk.Canvas(self._dialog)
        scrollbar = ttk.Scrollbar(self._dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        self._create_engine_section(scrollable_frame)
        self._create_spacy_section(scrollable_frame)
        self._create_transformers_section(scrollable_frame)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Button frame at bottom
        self._create_buttons_section()

    def _create_engine_section(self, parent: ttk.Frame) -> None:
        """Create engine type selection section."""
        engine_frame = ttk.LabelFrame(parent, text="NLP Engine Type", padding=10)
        engine_frame.pack(fill="x", padx=10, pady=10)

        self._engine_type_var = tk.StringVar(value=self._presenter.get_initial_engine_type())

        ttk.Radiobutton(
            engine_frame,
            text="spaCy (built-in NER models)",
            variable=self._engine_type_var,
            value="spacy",
        ).pack(anchor="w")

        ttk.Radiobutton(
            engine_frame,
            text="HuggingFace Transformers (custom NER models)",
            variable=self._engine_type_var,
            value="transformers",
        ).pack(anchor="w")

        ttk.Label(
            engine_frame,
            text="Note: Transformers requires 'spacy-huggingface-pipelines' package",
            font=("", 9, "italic"),
            foreground="gray",
        ).pack(anchor="w", pady=(5, 0))

    def _create_spacy_section(self, parent: ttk.Frame) -> None:
        """Create spaCy models selection section."""
        spacy_section = ttk.LabelFrame(parent, text="spaCy Models", padding=10)
        spacy_section.pack(fill="x", padx=10, pady=5)

        languages = self._presenter.get_available_languages()

        for lang_code, lang_name in languages.items():
            models = self._presenter.get_spacy_models_for_language(lang_code)
            current_model = self._presenter.get_current_spacy_model(lang_code)

            lang_frame = ttk.Frame(spacy_section)
            lang_frame.pack(fill="x", pady=2)

            ttk.Label(lang_frame, text=f"{lang_name}:", width=10).pack(side="left")

            model_var = tk.StringVar(value=current_model)
            self._spacy_model_vars[lang_code] = model_var

            model_combo = ttk.Combobox(
                lang_frame,
                textvariable=model_var,
                values=models,
                state="readonly",
                width=25,
            )
            model_combo.pack(side="left", padx=5)

            # Status label
            status_label = tk.Label(lang_frame, text="", width=12)
            status_label.pack(side="left")

            # Setup status update callback
            self._setup_spacy_status_callback(model_var, status_label)

    def _setup_spacy_status_callback(self, model_var: tk.StringVar, status_label: tk.Label) -> None:
        """Setup callback to update spaCy model status."""
        def update_status(*args) -> None:
            model_name = model_var.get()
            installed = self._presenter.is_spacy_model_installed(model_name)
            status_label.config(
                text="Installed" if installed else "Not installed",
                fg="green" if installed else "gray",
            )
        model_var.trace_add("write", update_status)
        update_status()

    def _create_transformers_section(self, parent: ttk.Frame) -> None:
        """Create transformers models selection section."""
        transformers_section = ttk.LabelFrame(
            parent, text="HuggingFace Transformer Models (for NER)", padding=10
        )
        transformers_section.pack(fill="x", padx=10, pady=5)

        # Package status
        pkg_status_frame = ttk.Frame(transformers_section)
        pkg_status_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(pkg_status_frame, text="Transformers support: ").pack(side="left")

        self._pkg_status_label = tk.Label(pkg_status_frame, text="", width=20)
        self._pkg_status_label.pack(side="left")

        self._pkg_install_btn = ttk.Button(
            pkg_status_frame, text="Install", width=10, command=self._handle_install_package
        )
        self._pkg_install_btn.pack(side="left", padx=5)

        self._update_package_status_display()

        # Language models
        languages = self._presenter.get_available_languages()

        for lang_code, lang_name in languages.items():
            models = self._presenter.get_transformers_models_for_language(lang_code)
            current_model = self._presenter.get_current_transformers_model(lang_code)

            lang_frame = ttk.Frame(transformers_section)
            lang_frame.pack(fill="x", pady=2)

            ttk.Label(lang_frame, text=f"{lang_name}:", width=10).pack(side="left")

            model_var = tk.StringVar(value=current_model)
            self._transformers_model_vars[lang_code] = model_var

            model_values = ["(none)"] + models
            model_combo = ttk.Combobox(
                lang_frame,
                textvariable=model_var,
                values=model_values,
                state="readonly",
                width=35,
            )
            model_combo.pack(side="left", padx=5)

            if not models:
                ttk.Label(lang_frame, text="(no models available)", foreground="gray").pack(
                    side="left"
                )
            else:
                # Status label
                status_label = tk.Label(lang_frame, text="", width=12)
                status_label.pack(side="left")
                self._transformers_status_labels[lang_code] = status_label

                # Download button
                download_btn = ttk.Button(lang_frame, text="Download", width=10)
                download_btn.pack(side="left", padx=5)
                self._transformers_download_btns[lang_code] = download_btn

                # Setup callbacks
                self._setup_transformers_callbacks(lang_code, model_var, status_label, download_btn)

        # Tip label
        desc_frame = ttk.Frame(transformers_section)
        desc_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(
            desc_frame,
            text="Tip: Medical de-id models (obi/deid_roberta_i2b2, StanfordAIMI) are optimized for healthcare data",
            font=("", 9, "italic"),
            foreground="gray",
        ).pack(anchor="w")

    def _setup_transformers_callbacks(
        self,
        lang_code: str,
        model_var: tk.StringVar,
        status_label: tk.Label,
        download_btn: ttk.Button
    ) -> None:
        """Setup callbacks for transformers model status and download."""
        def update_status(*args) -> None:
            model_name = model_var.get()
            if model_name == "(none)" or model_name == "":
                status_label.config(text="", fg="gray")
                download_btn.config(state="disabled")
            else:
                cached = self._presenter.is_transformers_model_cached(model_name)
                status_label.config(
                    text="Cached" if cached else "Not cached",
                    fg="green" if cached else "gray",
                )
                download_btn.config(state="disabled" if cached else "normal")

        def do_download() -> None:
            model_name = model_var.get()
            if model_name and model_name != "(none)":
                download_btn.config(state="disabled")
                status_label.config(text="Downloading...", fg="blue")

                def download_task() -> None:
                    success = self._presenter.download_transformers_model(model_name)
                    if self._dialog:
                        self._dialog.after(0, lambda: _on_download_complete(success))

                def _on_download_complete(success: bool) -> None:
                    if success:
                        status_label.config(text="Cached", fg="green")
                    else:
                        status_label.config(text="Failed", fg="red")
                        download_btn.config(state="normal")

                thread = threading.Thread(target=download_task, daemon=True)
                thread.start()

        model_var.trace_add("write", update_status)
        download_btn.config(command=do_download)
        update_status()

    def _create_buttons_section(self) -> None:
        """Create the dialog buttons."""
        button_frame = ttk.Frame(self._dialog)
        button_frame.pack(fill="x", pady=10, padx=10)

        ttk.Button(button_frame, text="Save", command=self._handle_save, width=10).pack(
            side="right", padx=5
        )
        ttk.Button(button_frame, text="Cancel", command=self._handle_cancel, width=10).pack(
            side="right", padx=5
        )

    def _update_package_status_display(self) -> None:
        """Update the package status display."""
        pkg_available = self._presenter.is_transformers_available()
        if pkg_available:
            self.update_package_status("Ready", "green", False)
        else:
            self.update_package_status("Not installed", "orange", True)

    # Event handlers
    def _handle_install_package(self) -> None:
        """Handle install package button click."""
        if self._pkg_install_btn:
            self._pkg_install_btn.config(state="disabled")
        if self._pkg_status_label:
            self._pkg_status_label.config(text="Installing...", fg="blue")

        def install_task() -> None:
            result = self._presenter.install_transformers_support()
            if self._dialog:
                self._dialog.after(0, lambda: _on_install_complete(result))

        def _on_install_complete(result: tuple[bool, str]) -> None:
            success, message = result
            if success:
                self.update_package_status("Ready", "green", False)
                self.show_info("Success", "Transformers support installed successfully.")
            else:
                self.update_package_status("Install failed", "red", True)
                self.show_error("Error", f"Installation failed:\n{message}")

        thread = threading.Thread(target=install_task, daemon=True)
        thread.start()

    def _handle_save(self) -> None:
        """Handle save button click."""
        engine_type = self._engine_type_var.get() if self._engine_type_var else "spacy"
        spacy_selections = {k: v.get() for k, v in self._spacy_model_vars.items()}
        transformers_selections = {k: v.get() for k, v in self._transformers_model_vars.items()}

        def progress_callback(title: str, message: str) -> bool:
            return self._run_with_progress(title, message)

        success, message = self._presenter.validate_and_save(
            engine_type,
            spacy_selections,
            transformers_selections,
            progress_callback
        )

        if success:
            self._saved = True
            if self._on_saved:
                self._on_saved(message)
            if self._dialog:
                self._dialog.destroy()
        else:
            self.show_error("Error", message)

    def _handle_cancel(self) -> None:
        """Handle cancel button click."""
        self._saved = False
        if self._dialog:
            self._dialog.destroy()

    def _run_with_progress(self, title: str, message: str) -> bool:
        """
        Run a background task with progress dialog.

        This is a simplified version that runs synchronously with a progress indicator.
        """
        if not self._dialog:
            return False

        # Create progress dialog
        progress_dialog = tk.Toplevel(self._dialog)
        progress_dialog.title(title)
        progress_dialog.geometry("400x120")
        progress_dialog.transient(self._dialog)
        progress_dialog.grab_set()
        progress_dialog.resizable(False, False)

        # Center the dialog
        progress_dialog.update_idletasks()
        x = self._dialog.winfo_x() + (self._dialog.winfo_width() - 400) // 2
        y = self._dialog.winfo_y() + (self._dialog.winfo_height() - 120) // 2
        progress_dialog.geometry(f"+{x}+{y}")

        # Message label
        msg_label = ttk.Label(
            progress_dialog,
            text=message,
            wraplength=380,
            justify="center"
        )
        msg_label.pack(pady=(20, 10), padx=10)

        # Progress bar
        progress_bar = ttk.Progressbar(
            progress_dialog,
            mode="indeterminate",
            length=350
        )
        progress_bar.pack(pady=10, padx=20)
        progress_bar.start(10)

        result = [False]

        def run_task() -> None:
            # Determine what task to run based on title
            if "Dependencies" in title:
                result[0] = self._presenter.install_transformers_support()[0]
            elif "Model" in title:
                # Extract model name from message
                model_name = message.split("Downloading: ")[1].split("\n")[0].split(" (")[0]
                result[0] = self._presenter.download_transformers_model(model_name)
            progress_dialog.after(0, progress_dialog.destroy)

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        self._dialog.wait_window(progress_dialog)
        return result[0]


def create_model_config_dialog(
    parent: tk.Tk,
    on_saved: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Factory function to create and show model config dialog.

    Args:
        parent: Parent window
        on_saved: Optional callback when config is saved

    Returns:
        True if saved, False if cancelled
    """
    dialog = ModelConfigDialog(parent, on_saved)
    return dialog.show()
