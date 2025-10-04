# YouTube AI Finance Content Generator

An automated pipeline for creating finance-focused YouTube videos using AI-generated content, voice synthesis, and media composition.

## Features

- **News Ingestion**: RSS feed collection and keyword extraction
- **AI Script Writing**: LLM-powered 60-second video scripts with hooks and CTAs
- **Voice Synthesis**: High-quality TTS using ElevenLabs
- **Media Composition**: Vertical video (1080×1920) with B-roll and subtitles
- **Thumbnail Generation**: AI-generated thumbnails
- **YouTube Upload**: Automated upload with duplicate detection

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

3. Set up YouTube OAuth:
- Place your `client_secret.json` in `yt_oauth/` directory
- Run the pipeline once to generate `token.json`

4. Configure settings in `config.yaml`

## Usage

```bash
python run_pipeline.py
```

## Project Structure

```
yt-ai-finance/
├── README.md
├── requirements.txt
├── .env.example
├── config.yaml
├── run_pipeline.py
├── data/
│   ├── workitems/              # Generation queue (summary/script JSON)
│   ├── outputs/                # Daily outputs (audio/video/thumbnail/meta)
│   └── logs/                   # Logs (JSONL)
├── src/
│   ├── utils/                  # Utility modules
│   ├── ingest/                 # News feed ingestion
│   ├── author/                 # Script generation
│   ├── voice/                  # Text-to-speech
│   ├── media/                  # Video composition
│   └── publish/                # YouTube upload
└── yt_oauth/                   # YouTube OAuth credentials
```

## Configuration

- **config.yaml**: Main configuration file
- **.env**: Environment variables and API keys
- **yt_oauth/**: YouTube API credentials

## Dependencies

- OpenAI API for script generation
- ElevenLabs API for voice synthesis
- Pexels API for B-roll footage
- YouTube Data API for uploads
- MoviePy for video composition

