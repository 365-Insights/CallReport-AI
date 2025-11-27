# Voice Bot - AI-Powered Conversational Assistant

An intelligent voice-enabled bot built on Azure Functions that processes voice input, manages contact information, and leverages AI to provide natural conversational interactions for CRM/call report management.

## Overview

This Voice Bot is an Azure Functions-based application that combines speech recognition, natural language processing, and AI agents to automate contact management and call reporting. The bot can understand user speech, extract structured information, enrich data from the internet, and generate natural responses.

## Key Features

- **Voice Recognition**: Supports multi-language speech-to-text using Azure Cognitive Services
- **Natural Language Understanding**: Classifies user intents and extracts structured information from conversational input
- **Contact Management**: Creates and updates contact records with automatic field extraction
- **Internet Data Enrichment**: Automatically searches for company and personal information using AI agents
- **Call Report Management**: Creates call reports and manages follow-ups
- **Interest Tracking**: Extracts and manages user interests from conversations
- **Conversational AI**: Generates contextual responses based on chat history
- **Multi-language Support**: Handles German (de-DE) and English (en-US) by default

## Architecture

### Core Components

#### 1. **VoiceBot** (`services/voice_bot.py`)
Main orchestrator that handles:
- User message classification
- Contact creation and updates
- Information extraction from text
- Internet data enrichment via AI agents
- Response generation
- State management

#### 2. **OpenAI Client** (`services/openai_client.py`)
Manages interactions with Azure OpenAI:
- Async API calls
- Response generation
- Text processing
- Retry logic with backoff

#### 3. **Search Agent** (`services/ai_agent.py`)
AI-powered agent for web searches:
- Person information lookup (LinkedIn, professional profiles)
- Company information retrieval
- Website and imprint extraction
- Google search integration

#### 4. **Voice Services** (`services/voice.py`)
Handles speech processing:
- Speech-to-text conversion
- Text-to-speech synthesis
- Multi-language support
- Fast transcription API

#### 5. **User State** (`services/user_state.py`)
Manages session state:
- Chat history tracking
- User context preservation
- Contact information caching

## Installation

### Prerequisites

- Python 3.11+
- Azure account with:
  - Azure Functions
  - Azure Cognitive Services (Speech)
  - Azure OpenAI Service
  - Azure AI Projects
  - Azure Key Vault

### Configuration

This application uses Azure Key Vault for secure secrets management.

#### 1. Setup Azure Key Vault

Create a Key Vault and add the following secrets:

```bash
az keyvault secret set --vault-name your-kv --name "openai-endpoint" --value "your-endpoint"
az keyvault secret set --vault-name your-kv --name "openai-key" --value "your-key"
az keyvault secret set --vault-name your-kv --name "llm-model" --value "gpt-4"
az keyvault secret set --vault-name your-kv --name "openai-api-version" --value "2024-02-15-preview"
az keyvault secret set --vault-name your-kv --name "best-model" --value "gpt-4"
az keyvault secret set --vault-name your-kv --name "speech-service-region" --value "westeurope"
az keyvault secret set --vault-name your-kv --name "speech-service-key" --value "your-key"
az keyvault secret set --vault-name your-kv --name "speech-service-endpoint" --value "https://westeurope.api.cognitive.microsoft.com/"
az keyvault secret set --vault-name your-kv --name "PROJECT-CONNECTION-STRING" --value "your-connection"
az keyvault secret set --vault-name your-kv --name "ai-agent-id" --value "your-agent-id"
az keyvault secret set --vault-name your-kv --name "BING-CONNECTION-NAME" --value "your-bing-connection"
az keyvault secret set --vault-name your-kv --name "search-agent-llm" --value "gpt-4"
az keyvault secret set --vault-name your-kv --name "app-insights-connection-string" --value "your-connection-string"
```

#### 2. Set Environment Variable

Create a `.env` file with:

```
AZURE_KEY_VAULT_URL=https://your-keyvault.vault.azure.net/
```

#### 3. Grant Access

For local development:
```bash
az login
```

For Azure Functions (Production):
- Enable System-assigned Managed Identity
- Grant Key Vault access:
```bash
az keyvault set-policy \
  --name your-kv \
  --object-id <managed-identity-principal-id> \
  --secret-permissions get list
```

#### 4. Install Dependencies

```bash
pip install -r requirements.txt
```
## Usage

### API Endpoint

**POST** `/api/req`

### Request Body

```json
{
  "formData": "<json-string-of-contact-forms>",
  "sessionID": "<session-identifier>",
  "callreportID": "<call-report-id>",
  "value": "<audio-data-or-text>",
  "language": "de-DE"
}
```

### Response

```json
{
  "commands": [
    {
      "name": "playBotVoice",
      "value": "<base64-audio>",
      "order": 1,
      "duration": 3500
    },
    {
      "name": "createContact",
      "value": { "GeneralInformation": {...}, "BusinessInformation": {...} },
      "order": 2
    }
  ],
  "sessionID": "<session-id>"
}
```

## Command Types

The bot supports the following command types:

| Command | Description |
|---------|-------------|
| `playBotVoice` | Plays synthesized voice response |
| `createContact` | Creates a new contact record |
| `updateCurrentContact` | Updates existing contact information |
| `fillInterests` | Fills in user interests |
| `addFollowUpds` | Adds follow-up tasks |
| `giveListContactFields` | Provides list of contact fields |
| `giveListInterests` | Provides list of interests |
| `saveCurrentDocument` | Saves the current document |
| `cancel` | Cancels the current operation |

## Message Classification

The bot classifies user messages into the following intents:

- **Create report**: User wants to create a new call report
- **Create contact**: User wants to add a new contact
- **Update info**: User wants to update contact information
- **Fill interests**: User wants to record interests
- **Add follow-ups**: User wants to add follow-up tasks
- **Save**: User wants to save the current state
- **Cancel**: User wants to cancel the operation
- **None**: General conversation

## Data Enrichment

The bot automatically enriches contact information by:

1. **Personal Information**: Searches LinkedIn and professional networks for:
   - Job title and department
   - Professional background
   - Contact details
   - LinkedIn profile URL

2. **Company Information**: Retrieves from official websites and LinkedIn:
   - Full company address
   - Contact information (phone, email)
   - Industry type
   - Company website
   - Imprint information

## Docker Deployment

Build and deploy using Docker:

```bash
# Build the image
docker build -t voice-bot .

# Run the container
docker run -p 8080:80 --env-file .env voice-bot
```

## Project Structure

```
voice_bot/
├── constants/              # Constants and singleton patterns
│   ├── constants.py
│   └── singleton.py
├── services/              # Core business logic
│   ├── ai_agent.py       # AI search agent
│   ├── commands.py       # Command definitions
│   ├── llm_prompts.py    # LLM prompt templates
│   ├── openai_client.py  # OpenAI API client
│   ├── user_state.py     # User session management
│   ├── voice.py          # Speech services
│   └── voice_bot.py      # Main bot logic
├── utils/                 # Utility functions
│   ├── logger.py
│   └── utils.py
├── tests/                 # Test files
├── function_app.py        # Azure Functions entry point
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
└── README.md             # This file
```

## Key Technologies

- **Azure Functions**: Serverless compute platform
- **Azure OpenAI**: GPT models for natural language understanding
- **Azure Cognitive Services**: Speech-to-text and text-to-speech
- **Azure AI Projects**: AI agent orchestration
- **Python AsyncIO**: Asynchronous processing for performance
- **Docker**: Containerization for deployment

## Required Fields

The bot validates the following required contact fields:
- FirstName
- LastName
- Company
- BusinessEmail

## Language Support

Currently supported languages:
- German (`de-DE`) - Default
- English (`en-US`)

Speech synthesis voices:
- German: `de-DE-KatjaNeural`
- English: `en-US-AvaMultilingualNeural`

## Performance Optimizations

- Async/await patterns for concurrent operations
- Parallel task execution using `asyncio.TaskGroup`
- Caching of user sessions and contact data
- Fast speech recognition API for quick transcription

## Error Handling

The bot includes comprehensive error handling:
- Graceful fallbacks for API failures
- Retry logic for transient errors
- User-friendly error messages
- Detailed logging for debugging


### Code Structure

- Use `@timing()` decorator to track function performance
- Follow async/await patterns for I/O operations
- Maintain session state in `UserData` objects
- Validate all commands before returning to client

## Run locally
### To run locally you can use test_server.py file and use examples from test_clean.ipynb