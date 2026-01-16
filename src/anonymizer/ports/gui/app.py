"""Composition root - wires all dependencies for the GUI application."""

from ...config import set_model_for_language
from .presenters.anonymizer_presenter import AnonymizerPresenter
from .views.entity_selection_dialog import create_entity_selection_dialog
from .views.main_window import AnonymizerView
from .views.model_manager_dialog import create_model_manager_dialog


def create_application() -> AnonymizerView:
    """
    Create and wire the GUI application.

    This is the composition root that creates all components and wires
    their dependencies together.

    Returns:
        Configured AnonymizerView ready to run
    """
    # Create view
    view = AnonymizerView()

    # Create presenter with view
    presenter = AnonymizerPresenter(view)

    # Wire callbacks from view to presenter
    view.set_on_anonymize(presenter.handle_anonymize)
    view.set_on_view_mapping(presenter.handle_view_mapping)

    # Wire language change callback to update model info
    def on_language_changed(language: str) -> None:
        model_info = presenter.get_model_info_for_language(language)
        view.set_model_info_text(model_info)

    view.set_on_language_changed(on_language_changed)

    # Wire model change callback to update config
    def on_model_changed(lang_code: str, model_name: str) -> None:
        set_model_for_language(lang_code, model_name)

    view.set_on_model_changed(on_model_changed)

    # Set dialog factories
    view.set_entity_dialog_factory(create_entity_selection_dialog)

    # Wire Model Manager menu
    def on_model_manager() -> None:
        def on_models_changed() -> None:
            view.refresh_available_languages()
            # Update model info display for current language
            language = view.selected_language
            model_info = presenter.get_model_info_for_language(language)
            view.set_model_info_text(model_info)

        create_model_manager_dialog(view.root, on_models_changed)

    view.set_on_model_manager(on_model_manager)

    # Initialize model info display (will be set when model is auto-selected)
    initial_language = view.selected_language
    if initial_language:
        model_info = presenter.get_model_info_for_language(initial_language)
        view.set_model_info_text(model_info)

    return view


def main() -> None:
    """Entry point for GUI."""
    app = create_application()
    app.run()


if __name__ == "__main__":
    main()
