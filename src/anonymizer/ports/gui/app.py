"""Composition root - wires all dependencies for the GUI application."""

from .presenters.anonymizer_presenter import AnonymizerPresenter
from .views.entity_selection_dialog import create_entity_selection_dialog
from .views.main_window import AnonymizerView
from .views.model_config_dialog import create_model_config_dialog


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
    view.set_on_configure_models(presenter.handle_configure_models)

    # Wire language change callback to update model info
    def on_language_changed(language: str) -> None:
        model_info = presenter.get_model_info_for_language(language)
        view.set_model_info_text(model_info)

    view.set_on_language_changed(on_language_changed)

    # Set dialog factories
    view.set_entity_dialog_factory(create_entity_selection_dialog)
    view.set_model_config_dialog_factory(create_model_config_dialog)

    # Initialize model info display
    initial_language = view.selected_language.split(" - ")[0]
    model_info = presenter.get_model_info_for_language(initial_language)
    view.set_model_info_text(model_info)

    return view


def main() -> None:
    """Entry point for GUI."""
    app = create_application()
    app.run()


if __name__ == "__main__":
    main()
