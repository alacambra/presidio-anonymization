"""Presenter for the Model Manager dialog - contains all business logic."""

import threading
from typing import TYPE_CHECKING, List, Tuple

from ....config import AVAILABLE_MODELS, LANGUAGE_NAMES
from ....model_storage import (
    delete_model,
    download_spacy_model,
    get_models_dir,
    is_model_downloaded,
)

if TYPE_CHECKING:
    from ..views.model_manager_dialog import ModelManagerDialog


class ModelManagerPresenter:
    """
    Presenter for the Model Manager dialog.

    Contains all business logic for model discovery, download, and deletion.
    """

    def __init__(self, view: "ModelManagerDialog") -> None:
        """Initialize the presenter."""
        self.view = view
        self._download_thread: threading.Thread | None = None
        self._cancel_download = False

    def get_models_directory(self) -> str:
        """Get the models storage directory path."""
        return str(get_models_dir())

    def get_models_by_language(self) -> List[Tuple[str, str, List[dict]]]:
        """
        Get all available models grouped by language.

        Returns:
            List of (lang_code, lang_name, models) tuples
            where models is a list of dicts with name, size_mb, description, downloaded
        """
        result = []

        for lang_code, models in AVAILABLE_MODELS.items():
            lang_name = LANGUAGE_NAMES.get(lang_code, lang_code)
            model_list = []

            for model in models:
                model_list.append(
                    {
                        "name": model.name,
                        "size_mb": model.size_mb,
                        "description": model.description,
                        "downloaded": is_model_downloaded(model.name),
                    }
                )

            result.append((lang_code, lang_name, model_list))

        return result

    def download_models(self, model_names: List[str]) -> None:
        """
        Download selected models in background thread.

        Args:
            model_names: List of model names to download
        """
        if self._download_thread and self._download_thread.is_alive():
            self.view.show_error("Error", "Download already in progress")
            return

        # Filter to only non-downloaded models
        to_download = [n for n in model_names if not is_model_downloaded(n)]
        if not to_download:
            self.view.show_info("Info", "Selected models are already downloaded")
            return

        self._cancel_download = False
        self.view.set_buttons_enabled(download=False, delete=False)
        self.view.show_progress(True)

        def download_task() -> None:
            for model_name in to_download:
                if self._cancel_download:
                    break

                # Get model size for progress estimation
                size_mb = self._get_model_size(model_name)

                def make_progress_callback(name: str, size: float):
                    def callback(downloaded: int, total: int) -> None:
                        downloaded_mb = downloaded / (1024 * 1024)
                        total_mb = total / (1024 * 1024) if total > 0 else size
                        self.view.schedule_ui_update(
                            lambda d=downloaded_mb, t=total_mb, n=name: self.view.update_progress(
                                d, t, n
                            )
                        )

                    return callback

                progress_callback = make_progress_callback(model_name, size_mb)

                self.view.schedule_ui_update(
                    lambda n=model_name: self.view.update_model_status(
                        n, "Downloading...", "downloading"
                    )
                )

                success, message = download_spacy_model(model_name, progress_callback)

                if success:
                    self.view.schedule_ui_update(
                        lambda n=model_name: self.view.update_model_status(
                            n, "✓ Downloaded", "downloaded"
                        )
                    )
                else:
                    self.view.schedule_ui_update(
                        lambda n=model_name, m=message: self._on_download_error(n, m)
                    )

            # Cleanup
            self.view.schedule_ui_update(self._on_download_complete)

        self._download_thread = threading.Thread(target=download_task, daemon=True)
        self._download_thread.start()

    def _on_download_error(self, model_name: str, message: str) -> None:
        """Handle download error for a model."""
        self.view.update_model_status(model_name, "Failed", "not_downloaded")
        self.view.show_error("Download Error", f"Failed to download {model_name}:\n{message}")

    def _on_download_complete(self) -> None:
        """Called when download completes."""
        self.view.show_progress(False)
        self.view.set_buttons_enabled(download=True, delete=True)
        self.view.refresh_tree()
        self.view.notify_models_changed()

    def _get_model_size(self, model_name: str) -> float:
        """Get the size in MB for a model."""
        for models in AVAILABLE_MODELS.values():
            for model in models:
                if model.name == model_name:
                    return float(model.size_mb)
        return 0.0

    def delete_models(self, model_names: List[str]) -> None:
        """
        Delete selected models.

        Args:
            model_names: List of model names to delete
        """
        # Filter to only downloaded models
        to_delete = [n for n in model_names if is_model_downloaded(n)]
        if not to_delete:
            self.view.show_info("Info", "Selected models are not downloaded")
            return

        deleted = []
        failed = []

        for model_name in to_delete:
            success, message = delete_model(model_name)
            if success:
                deleted.append(model_name)
            else:
                failed.append((model_name, message))

        # Refresh view
        self.view.refresh_tree()

        # Notify about model changes
        if deleted:
            self.view.notify_models_changed()

        # Show results
        if deleted:
            self.view.show_info("Success", f"Deleted {len(deleted)} model(s)")
        if failed:
            error_msg = "\n".join([f"{n}: {m}" for n, m in failed])
            self.view.show_error("Delete Error", f"Failed to delete:\n{error_msg}")

    def cancel_download(self) -> None:
        """Cancel any ongoing download."""
        self._cancel_download = True
