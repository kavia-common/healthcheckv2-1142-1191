from app import app  # type: ignore

if __name__ == "__main__":
    # Flask app retained (not used by healthcheck CLI). This allows
    # container to start for smoke tests if needed.
    app.run()
