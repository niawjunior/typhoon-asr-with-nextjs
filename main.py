import uvicorn
from api import app

def main():
    """Entry point for the Typhoon ASR application."""
    print("Starting Typhoon ASR API server...")
    print("API documentation available at: http://localhost:8000/docs")
    print("Frontend available at: http://localhost:3000")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
