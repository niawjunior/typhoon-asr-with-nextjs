# Typhoon ASR Demo

A Next.js and FastAPI demo application for Typhoon ASR - Thai speech recognition in real-time.

## Features

- Upload audio files for transcription
- Record audio directly from your microphone
- Real-time Thai speech recognition
- Word-level timestamp visualization
- Support for multiple audio formats (.wav, .mp3, .flac, .ogg, .opus)
- Two operation modes:
  - API mode (using Typhoon's cloud service)
  - Local mode (self-hosted, requires typhoon-asr package)
- Modern UI with Next.js frontend
- FastAPI backend for audio processing

## Project Structure

- `/web` - Next.js frontend
- `/api.py` - FastAPI backend for audio transcription
- `/main.py` - Entry point for the application

## Installation

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- npm or yarn
- uv (Python package manager)

### Backend Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/typhoon-asr.git
cd typhoon-asr
```

2. Create and activate a virtual environment using uv (recommended):
```bash
uv venv
source .venv/bin/activate
```

3. Install Python dependencies using uv:
```bash
uv pip install -r requirements.txt
```

4. (Optional) If you want to use the local model:
```bash
uv pip install typhoon-asr
```

### Frontend Setup

1. Navigate to the web directory:
```bash
cd web
```

2. Install Node.js dependencies:
```bash
npm install
# or
yarn install
```

3. Create a `.env.local` file in the web directory with your API key (optional):
```
NEXT_PUBLIC_API_KEY=your-typhoon-api-key
```

## Usage

1. Start the FastAPI backend:
```bash
python main.py
```

2. In a separate terminal, start the Next.js frontend:
```bash
cd web
npm run dev
# or
yarn dev
```

3. Open your browser and navigate to http://localhost:3000

4. Choose your preferred transcription mode:
   - API mode: Uses Typhoon's cloud service (requires API key)
   - Local mode: Processes audio on your device (requires typhoon-asr package)

5. Upload an audio file or record audio using your microphone.

6. Click "Transcribe" to get the Thai speech transcription.

## API Key Configuration

You can configure the API key in two ways:

1. **Environment Variable**: Add your API key to the `.env.local` file in the web directory:
   ```
   NEXT_PUBLIC_API_KEY=your-typhoon-api-key
   ```

2. **UI Input**: Enter your API key directly in the configuration panel of the web interface

Get your API key from the [Typhoon Web Playground](https://opentyphoon.ai/)

## API Documentation

The FastAPI backend provides the following endpoints:

- `GET /` - Root endpoint, returns a welcome message
- `GET /health` - Health check endpoint
- `POST /transcribe` - Transcribe audio file

API documentation is available at http://localhost:8000/docs when the backend is running.

## Troubleshooting

### CORS Issues

If you encounter CORS issues when connecting the frontend to the backend, make sure:

1. The backend is running on http://localhost:8000
2. The frontend is making requests to the correct backend URL

### API Key Issues

If transcription fails with API mode:

1. Verify your API key is correct
2. Check that you have sufficient quota/credits with Typhoon ASR

### Local Model Issues

If using the local model:

1. Ensure the typhoon-asr package is installed correctly
2. Check if your system meets the requirements for running the model

## About Typhoon ASR

Typhoon ASR is a Thai speech recognition model developed by SCB 10X. It provides accurate real-time transcription of Thai speech.

### Model Information

- Model ID: typhoon-asr-realtime
- Size: 114M
- Rate Limits: 100 requests/minute
- Release Date: 2025-09-08

## License

This demo application is provided as-is without any warranty. Use at your own risk.

## Credits

- [Typhoon ASR](https://opentyphoon.ai/) - Thai speech recognition model
- [Next.js](https://nextjs.org/) - Frontend framework
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [OpenAI](https://openai.com/) - API client library
- [shadcn/ui](https://ui.shadcn.com/) - UI components
