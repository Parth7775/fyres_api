try:
    import app
    print("Successfully imported app.")
    print("Routes:")
    print(app.app.url_map)
except ImportError as e:
    print(f"Import Error: {e}")
except Exception as e:
    print(f"Error: {e}")
