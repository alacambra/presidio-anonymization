"""Entry point for PyInstaller executable."""
import multiprocessing

if __name__ == "__main__":
    # CRITICAL: Must be called before any other code in frozen apps.
    # This prevents child processes from re-executing the GUI when
    # third-party libraries (spaCy, Presidio) use multiprocessing internally.
    # No-op in non-frozen environments, so safe for development mode.
    multiprocessing.freeze_support()

    from anonymizer.ports.gui.app import main
    main()
