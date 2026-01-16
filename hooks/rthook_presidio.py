"""Runtime hook to fix presidio_analyzer conf path resolution in frozen apps."""
import sys
from pathlib import Path


def _register_spacy_transformers():
    """
    Import spacy-curated-transformers to register the curated_transformer factory.

    NOTE: In PyInstaller frozen builds, these packages are excluded because
    TorchScript requires .py source files which PyInstaller doesn't preserve.
    Transformer models (*_trf) are not supported in the packaged app.
    Basic spaCy models (sm/md/lg) work fine.
    """
    # Skip in frozen apps - transformer packages are excluded from the bundle
    if getattr(sys, 'frozen', False):
        print("[rthook] Frozen app - transformer packages excluded (TorchScript limitation)")
        print("[rthook] Use basic spaCy models (sm/md/lg) instead of transformer models (*_trf)")
        return

    # Import the specific module that registers the curated_transformer factory
    # (the package __init__.py doesn't import it automatically)
    try:
        from spacy_curated_transformers.pipeline import transformer  # noqa: F401
        print("[rthook] spacy_curated_transformers.pipeline.transformer imported")

        # Verify the factory was registered
        try:
            from spacy.language import Language
            factories = list(Language.factories.keys()) if hasattr(Language, 'factories') else []
            if 'curated_transformer' in factories:
                print("[rthook] curated_transformer factory IS registered")
            else:
                print(f"[rthook] WARNING: curated_transformer NOT in factories: {factories[:10]}...")
        except Exception as e:
            print(f"[rthook] could not verify factory registration: {e}")

    except ImportError as e:
        print(f"[rthook] spacy_curated_transformers import failed: {e}")
    except Exception as e:
        print(f"[rthook] spacy_curated_transformers unexpected error: {e}")

    # Also import spacy_transformers (registers transformer factory, used by some models)
    try:
        import spacy_transformers  # noqa: F401
        print(f"[rthook] spacy_transformers imported: {spacy_transformers.__version__}")
    except ImportError as e:
        print(f"[rthook] spacy_transformers import failed: {e}")
    except Exception as e:
        print(f"[rthook] spacy_transformers unexpected error: {e}")


def _patch_presidio_conf_paths():
    """Patch presidio_analyzer to find conf files in frozen app."""
    if not getattr(sys, 'frozen', False):
        return  # Not frozen, skip patching

    # Get PyInstaller's extraction directory
    meipass = Path(sys._MEIPASS)
    conf_dir = meipass / 'presidio_analyzer' / 'conf'

    if not conf_dir.exists():
        return  # Conf dir not found, skip

    # Patch RecognizerConfigurationLoader._get_full_conf_path
    try:
        from presidio_analyzer.recognizer_registry import recognizers_loader_utils

        @staticmethod
        def patched_recognizer_conf(default_conf_file="default_recognizers.yaml"):
            return conf_dir / default_conf_file

        recognizers_loader_utils.RecognizerConfigurationLoader._get_full_conf_path = patched_recognizer_conf
    except (ImportError, AttributeError):
        pass

    # Patch NlpEngineProvider._get_full_conf_path
    try:
        from presidio_analyzer.nlp_engine import nlp_engine_provider

        @staticmethod
        def patched_nlp_conf(default_conf_file="default.yaml"):
            return conf_dir / default_conf_file

        nlp_engine_provider.NlpEngineProvider._get_full_conf_path = patched_nlp_conf
    except (ImportError, AttributeError):
        pass

    # Patch AnalyzerEngineProvider._get_full_conf_path
    try:
        from presidio_analyzer import analyzer_engine_provider

        @staticmethod
        def patched_analyzer_conf(default_conf_file="default_analyzer.yaml"):
            return conf_dir / default_conf_file

        analyzer_engine_provider.AnalyzerEngineProvider._get_full_conf_path = patched_analyzer_conf
    except (ImportError, AttributeError):
        pass


print("[rthook] Runtime hook starting...")

# Register spacy-transformers factory first (needed for *_trf models)
_register_spacy_transformers()

# Then patch presidio conf paths
_patch_presidio_conf_paths()

print("[rthook] Runtime hook complete.")
