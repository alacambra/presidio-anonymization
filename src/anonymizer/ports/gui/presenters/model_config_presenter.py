"""Presenter for the model configuration dialog - contains configuration logic."""

from typing import Callable, Dict, List, Optional, Tuple

from ....config import (
    AVAILABLE_MODELS,
    AVAILABLE_TRANSFORMERS_MODELS,
    LANGUAGE_NAMES,
    SELECTED_TRANSFORMERS_MODEL,
    SUPPORTED_LANGUAGES,
    download_transformers_model,
    get_nlp_engine_type,
    install_huggingface_pipelines,
    is_huggingface_pipelines_available,
    is_model_installed,
    is_transformers_model_cached,
    set_model_for_language,
    set_nlp_engine_type,
    set_transformers_model_for_language,
)


class ModelConfigPresenter:
    """
    Presenter for the model configuration dialog.

    Contains all business logic for model selection, validation,
    installation, and saving configuration.
    """

    def __init__(self, view: "ModelConfigDialog") -> None:  # type: ignore[name-defined]
        """
        Initialize the presenter with a view.

        Args:
            view: The ModelConfigDialog instance (concrete class)
        """
        self.view = view
        self._engine_type: str = get_nlp_engine_type()
        self._spacy_selections: Dict[str, str] = {}
        self._transformers_selections: Dict[str, str] = {}

    def get_initial_engine_type(self) -> str:
        """Get the currently configured engine type."""
        return get_nlp_engine_type()

    def get_available_languages(self) -> Dict[str, str]:
        """Get available languages with their display names."""
        return LANGUAGE_NAMES.copy()

    def get_spacy_models_for_language(self, lang_code: str) -> List[str]:
        """Get available spaCy models for a language."""
        models = AVAILABLE_MODELS.get(lang_code, [])
        return [m.name for m in models]

    def get_current_spacy_model(self, lang_code: str) -> str:
        """Get currently selected spaCy model for a language."""
        return SUPPORTED_LANGUAGES.get(lang_code, "")

    def get_transformers_models_for_language(self, lang_code: str) -> List[str]:
        """Get available transformer models for a language."""
        models = AVAILABLE_TRANSFORMERS_MODELS.get(lang_code, [])
        return [m.name for m in models]

    def get_current_transformers_model(self, lang_code: str) -> str:
        """Get currently selected transformers model for a language."""
        return SELECTED_TRANSFORMERS_MODEL.get(lang_code, "") or ""

    def is_spacy_model_installed(self, model_name: str) -> bool:
        """Check if a spaCy model is installed."""
        return is_model_installed(model_name)

    def is_transformers_available(self) -> bool:
        """Check if HuggingFace pipelines package is installed."""
        return is_huggingface_pipelines_available()

    def is_transformers_model_cached(self, model_name: str) -> bool:
        """Check if a transformers model is cached locally."""
        if not model_name or model_name == "(none)":
            return False
        return is_transformers_model_cached(model_name)

    def get_transformers_model_size(self, lang_code: str, model_name: str) -> Optional[int]:
        """Get the size in MB of a transformers model."""
        models = AVAILABLE_TRANSFORMERS_MODELS.get(lang_code, [])
        for m in models:
            if m.name == model_name:
                return m.size_mb
        return None

    def install_transformers_support(self) -> Tuple[bool, str]:
        """
        Install the HuggingFace pipelines package.

        Returns:
            Tuple of (success, message)
        """
        return install_huggingface_pipelines()

    def download_transformers_model(self, model_name: str) -> bool:
        """
        Download a transformers model.

        Args:
            model_name: Name of the model to download

        Returns:
            True if download succeeded
        """
        return download_transformers_model(model_name)

    def set_engine_type(self, engine_type: str) -> None:
        """Set the selected engine type (not saved until save_configuration)."""
        self._engine_type = engine_type

    def set_spacy_model(self, lang_code: str, model_name: str) -> None:
        """Set a spaCy model selection (not saved until save_configuration)."""
        self._spacy_selections[lang_code] = model_name

    def set_transformers_model(self, lang_code: str, model_name: str) -> None:
        """Set a transformers model selection (not saved until save_configuration)."""
        self._transformers_selections[lang_code] = model_name

    def validate_and_save(
        self,
        engine_type: str,
        spacy_selections: Dict[str, str],
        transformers_selections: Dict[str, str],
        progress_callback: Optional[Callable[[str, str], bool]] = None
    ) -> Tuple[bool, str]:
        """
        Validate selections and save configuration.

        Args:
            engine_type: Selected engine type ("spacy" or "transformers")
            spacy_selections: Dict of lang_code -> model_name for spaCy
            transformers_selections: Dict of lang_code -> model_name for transformers
            progress_callback: Optional callback for running tasks with progress
                              Signature: (title, message) -> bool (success)

        Returns:
            Tuple of (success, message)
        """
        # If transformers engine selected, ensure package is installed
        if engine_type == "transformers":
            if not is_huggingface_pipelines_available():
                if progress_callback:
                    success = progress_callback(
                        "Installing Dependencies",
                        "Installing transformers support package...\nThis may take a few minutes."
                    )
                    if not success:
                        return False, "Failed to install transformers support."
                else:
                    success, msg = install_huggingface_pipelines()
                    if not success:
                        return False, f"Failed to install transformers support: {msg}"

            # Download any uncached transformers models
            for lang_code, model_name in transformers_selections.items():
                if model_name and model_name != "(none)" and model_name != "":
                    if not is_transformers_model_cached(model_name):
                        model_size = self.get_transformers_model_size(lang_code, model_name)
                        size_str = f" (~{model_size} MB)" if model_size else ""

                        if progress_callback:
                            success = progress_callback(
                                "Downloading Model",
                                f"Downloading: {model_name}{size_str}\n\n"
                                "This may take several minutes depending on your connection."
                            )
                            if not success:
                                return False, f"Failed to download model: {model_name}"
                        else:
                            if not download_transformers_model(model_name):
                                return False, f"Failed to download model: {model_name}"

        # Save engine type
        set_nlp_engine_type(engine_type)

        # Save spaCy models
        for lang_code, model_name in spacy_selections.items():
            if model_name:
                set_model_for_language(lang_code, model_name)

        # Save transformers models
        for lang_code, model_name in transformers_selections.items():
            if model_name == "(none)" or model_name == "":
                set_transformers_model_for_language(lang_code, None)
            else:
                set_transformers_model_for_language(lang_code, model_name)

        return True, f"Model configuration updated. Engine: {engine_type}"
