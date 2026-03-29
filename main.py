import sys


def main():
    import logging

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    log = logging.getLogger("main")
    log.info("Starting HotKey Translator...")

    from src.app import TranslatorApp

    app = TranslatorApp()
    log.info("App initialized. Press Ctrl+Shift+T in any text field to translate.")
    sys.exit(app.run())


if __name__ == "__main__":
    main()
