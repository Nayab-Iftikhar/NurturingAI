# Tools and Technologies Used in NurturingAI

This document outlines all the key technologies, frameworks, models, and tools utilized in the NurturingAI project.

## 1. Core Framework

### Backend Framework
- **Django (>=4.2)**: High-level Python web framework for rapid development
- **Django Ninja (>=0.22)**: Web framework for building APIs with Django and Python type hints, inspired by FastAPI
- **Uvicorn**: ASGI server for running the Django Ninja application

### Database
- **SQLite**: Lightweight, file-based relational database used for Django's ORM and general application data
- **Django ORM**: Object-Relational Mapping for database operations

## 2. Authentication & Security

### Authentication
- **PyJWT (==2.8.0)**: JSON Web Token (JWT) implementation for API authentication
- **python-jose[cryptography] (==3.3.0)**: Additional JWT utilities and cryptographic functions
- **bcrypt (==4.1.2)**: Strong password hashing function for user authentication
- **Django Session Authentication**: Used for frontend user sessions
- **Custom Mixed Authentication**: Supports both JWT and session-based authentication for API endpoints

### Security Features
- JWT token-based API authentication (mandatory for all endpoints)
- Password hashing with bcrypt
- CSRF protection for web forms
- Secure session management

## 3. Vector Store & Embeddings

### Vector Database
- **ChromaDB (==0.4.22)**: Open-source embedding database used to store:
  - Document RAG embeddings (brochure documents)
  - Vanna training data (DDL, documentation, SQL examples)

### Embedding Models
- **sentence-transformers (>=2.7.0)**: Library for generating embeddings
- **Embedding Model: `all-MiniLM-L6-v2`** (default, configurable via `EMBEDDING_MODEL`)
  - Dimensions: 384
  - Provider: Sentence Transformers
  - Use Case: Converting text chunks to vectors for semantic search
  - Alternative models can be used (e.g., `all-mpnet-base-v2`)

## 4. Document Processing

### Libraries
- **pypdf (==3.17.4)**: For extracting text from PDF documents
- **python-docx (==1.1.0)**: For extracting text from DOCX documents
- **unstructured (==0.11.8)**: For robust document parsing and text extraction
- **langchain-text-splitters (==0.3.0)**: Provides advanced text splitting strategies
  - **RecursiveCharacterTextSplitter**: Used for breaking documents into manageable chunks
    - Default chunk size: 1000 characters
    - Default chunk overlap: 200 characters

### Document Processing Pipeline
1. **File Upload**: Accepts PDF, DOCX, DOC, or TXT files
2. **Text Extraction**: Extracts raw text content from documents
3. **Chunking/Splitting**: Breaks text into overlapping chunks using RecursiveCharacterTextSplitter
4. **Embedding**: Converts chunks to 384-dimensional vectors using `all-MiniLM-L6-v2`
5. **Storage**: Stores vectors, chunks, and metadata in ChromaDB

## 5. Agent Orchestration & LLM Integration

### Agent Framework
- **LangGraph (==0.2.28)**: For building stateful, multi-actor applications with LLMs
  - **State Management**: Uses `AgentState` TypedDict for state management
  - **Graph Workflow**: Implements routing, tool execution, and response synthesis
  - **Class-Based Structure**: `RealEstateAgent` class manages the agent lifecycle

### LangChain Ecosystem
- **langchain (==0.3.0)**: Core library for developing applications powered by language models
- **langchain-community (==0.3.0)**: Community-contributed LangChain integrations
- **langchain-openai (==0.2.0)**: OpenAI integration for LangChain
- **langchain-chroma (==0.1.4)**: ChromaDB integration for LangChain
- **langchain-text-splitters (==0.3.0)**: Text splitting utilities

### LLM Models

#### Primary LLM Options (configurable via API keys)

**Option 1: OpenAI (Primary)**
- **Model**: `gpt-3.5-turbo` (default) or `gpt-4` (configurable)
- **Provider**: OpenAI
- **Library**: `langchain-openai`
- **Use Cases**: 
  - Agent routing decisions
  - Message generation
  - Text-to-SQL query generation
  - Document RAG response synthesis
- **Configuration**: Set `OPENAI_API_KEY` environment variable

**Option 2: Ollama (Fallback)**
- **Model**: `llama3.1:8b-instruct` (default, configurable)
- **Provider**: Ollama (local)
- **Library**: `langchain-community`
- **Use Cases**: Same as OpenAI (fallback if OpenAI not available or quota exceeded)
- **Configuration**: 
  - Set `OLLAMA_MODEL` environment variable (optional, defaults to `llama3.1:8b-instruct`)
  - Set `OLLAMA_BASE_URL` environment variable (optional, defaults to `http://localhost:11434`)
  - Ensure Ollama is running locally

**LLM Usage in Components:**
- **Agent Routing**: Determines whether to use Text-to-SQL or Document RAG
- **Message Generation**: Creates hyper-personalized campaign messages
- **Text-to-SQL**: Converts natural language to SQL queries
- **Document RAG**: Synthesizes responses from retrieved document chunks

## 6. Text-to-SQL (T2SQL)

### Framework
- **Vanna (==0.5.5)**: Framework for generating SQL queries from natural language
  - Uses ChromaDB for storing training data (DDL, documentation, SQL examples)
  - Automatically seeds training data on first use
  - Supports SQLite syntax

### Training Data
- Database schema (DDL) for leads, campaigns, and campaign_leads tables
- Documentation about table structures and relationships
- SQL example queries for common operations

### Implementation
- **Class**: `TextToSQLTool` in `apps/agent/tools/text_to_sql.py`
- **Method**: `execute(query, project_name)` - Converts natural language to SQL and executes it

## 7. Document RAG (Retrieval-Augmented Generation)

### Implementation
- **Class**: `DocumentRAGTool` in `apps/agent/tools/document_rag.py`
- **Vector Store**: ChromaDB collection `brochures`
- **Embedding Model**: `all-MiniLM-L6-v2` (384 dimensions)
- **Retrieval**: Semantic search using cosine similarity
- **Generation**: LLM synthesizes responses from retrieved chunks

### RAG Pipeline
1. **Query Embedding**: Convert user query to vector
2. **Semantic Search**: Find top-k similar chunks in ChromaDB
3. **Context Building**: Combine retrieved chunks with metadata
4. **Response Generation**: LLM generates natural language response

## 8. Data Processing & Import

### Excel Processing
- **pandas (>=2.0.0)**: Data manipulation and analysis
- **openpyxl (>=3.0.0)**: Reading and writing Excel files (.xlsx)
- **Management Command**: `import_leads_excel` for bulk lead import

### Data Formats
- **JSON**: Lead data import/export
- **Excel (.xlsx)**: Lead data import
- **PDF, DOCX, DOC, TXT**: Document uploads

## 9. Email Service

### Email Backend
- **Django Email Backend**: 
  - Development: `django.core.mail.backends.console.EmailBackend` (console output)
  - Production: `django.core.mail.backends.smtp.EmailBackend` (SMTP)
- **SMTP Configuration**: Gmail SMTP (configurable)
- **Test Email**: All emails routed to `TEST_EMAIL` for testing/demo

### Email Features
- Personalized message generation using LLM
- Campaign message distribution
- Password reset emails

## 10. API Framework

### RESTful API
- **Django Ninja**: RESTful API framework
- **Resource Naming**: Plural nouns (e.g., `/api/leads`, `/api/campaigns`, `/api/agent/queries`)
- **HTTP Methods**: 
  - `GET`: Retrieve resources
  - `POST`: Create resources
  - `DELETE`: Remove resources
- **Status Codes**: 200, 201, 400, 401, 404, 500
- **Authentication**: JWT Bearer tokens (mandatory for all endpoints)

### API Endpoints

#### Authentication (`/api/auth`)
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/forgot-password` - Password reset request
- `POST /api/auth/reset-password` - Password reset

#### Documents (`/api/documents`)
- `POST /api/documents/upload` - Upload and process documents
- `GET /api/documents/stats` - Get document statistics
- `DELETE /api/documents/project/{project_name}` - Delete project documents

#### Leads (`/api/leads`)
- `POST /api/leads/filter` - Filter leads by criteria
- `GET /api/leads/projects` - Get unique project names
- `GET /api/leads/unit-types` - Get unique unit types
- `GET /api/leads/statuses` - Get unique lead statuses

#### Campaigns (`/api/campaigns`)
- `POST /api/campaigns/create` - Create a new campaign
- `GET /api/campaigns/list` - List all campaigns
- `GET /api/campaigns/{id}` - Get campaign details
- `POST /api/campaigns/{id}/generate-messages` - Generate and send campaign messages

#### Agent (`/api/agent`)
- `POST /api/agent/queries` - Submit a new query to the agent (Text-to-SQL or Document RAG)
- `GET /api/agent/queries` - List agent query conversations
- `GET /api/agent/queries/{id}` - Get a specific conversation

## 11. Testing & Evaluation

### Testing Framework
- **pytest (>=7.0.0)**: Testing framework
- **pytest-django (>=4.5.0)**: Django integration for pytest
- **pytest-cov (>=4.0.0)**: Coverage reporting
- **pytest-mock (>=3.10.0)**: Mocking utilities
- **reportlab (>=4.0.0)**: PDF generation for test fixtures

### Evaluation Framework
- **DeepEval (>=0.17.0)**: Agent evaluation framework
  - **Metrics**:
    - Answer Relevancy: Measures relevance of agent responses
    - Faithfulness: Measures accuracy to source documents
    - Contextual Relevancy: Measures use of provided context
  - **Results Storage**: `agent_evaluation_scores.json`

## 12. Utilities & Dependencies

### Data Validation
- **Pydantic (>=2.0.0)**: Data validation and serialization (used by Django Ninja)
- **python-multipart (==0.0.6)**: For handling `multipart/form-data` in API requests

### HTTP & Networking
- **httpx (==0.25.2)**: Modern HTTP client
- **requests**: HTTP library (dependency of various packages)

### Environment Management
- **python-dotenv (==1.0.0)**: For loading environment variables from `.env` file

### Templating
- **Jinja2**: Templating engine (used by Django and various packages)

## 13. Architecture Overview

### Class-Based Structure

#### Agent Components

**RealEstateAgent** (`apps/agent/langgraph_agent.py`):
- `__init__()`: Initialize agent with tools and LLM
- `_build_graph()`: Build LangGraph workflow
- `_route_query()`: Route query to determine tool choice
- `_should_use_sql()`: Conditional edge function for routing
- `_execute_text_to_sql()`: Execute Text-to-SQL tool
- `_execute_document_rag()`: Execute Document RAG tool
- `_synthesize_response()`: Synthesize final response
- `query()`: Main method to process queries through the agent

**TextToSQLTool** (`apps/agent/tools/text_to_sql.py`):
- `__init__()`: Initialize tool and ensure training data exists
- `_ensure_training_data()`: Check and seed training data if needed
- `_seed_training_data()`: Seed initial training data (DDL, docs, SQL examples)
- `execute()`: Execute natural language query using Text-to-SQL

**DocumentRAGTool** (`apps/agent/tools/document_rag.py`):
- `__init__()`: Initialize tool with ChromaDB service
- `execute()`: Execute RAG query against brochure documents

**AgentState** (TypedDict in `apps/agent/langgraph_agent.py`):
- `query`: User's natural language query
- `project_name`: Project name for context
- `tool_choice`: Selected tool ('text_to_sql' or 'document_rag')
- `result`: Tool execution result
- `response`: Final synthesized response

#### Service Classes

**ChromaDBService** (`services/chromadb_service.py`):
- `__init__()`: Initialize ChromaDB client and embedding model
- `add_documents()`: Add documents with embeddings to ChromaDB
- `query_documents()`: Query documents using semantic search
- `get_collection_stats()`: Get statistics about stored documents
- `delete_documents_by_project()`: Delete documents by project name

**VannaChromaDBService** (`services/vanna_service.py`):
- `__init__()`: Initialize ChromaDB client for Vanna training data
- `add_training_data()`: Add training data (DDL, documentation, SQL examples)
- `get_similar_training_data()`: Get similar training data for a query
- `get_training_data()`: Get all training data

**Document Processing Functions** (`services/document_processor.py`):
- `extract_text_from_file()`: Extract text from PDF, DOCX, DOC, or TXT files
- `chunk_text()`: Split text into chunks using RecursiveCharacterTextSplitter
- `process_document()`: Complete document processing pipeline (extract, chunk, embed, store)

**Message Generation** (`services/message_generator.py`):
- `generate_personalized_message()`: Generate hyper-personalized messages using LLM

**Email Service** (`services/email_service.py`):
- `send_personalized_email()`: Send personalized emails to leads

#### Models (Django ORM)

**Lead Model** (`leads/models.py`):
- `lead_id`: Unique identifier (CharField, max_length=20)
- `name`: Lead name (CharField, max_length=255)
- `email`: Email address (EmailField)
- `country_code`: Country code (CharField, max_length=5)
- `phone`: Phone number (CharField, max_length=32)
- `project_name`: Project name (CharField, max_length=255)
- `unit_type`: Unit type preference (CharField, max_length=255)
- `budget_min`: Minimum budget (DecimalField, nullable)
- `budget_max`: Maximum budget (DecimalField, nullable)
- `status`: Lead status (CharField, max_length=64)
- `last_conversation_date`: Last conversation date (DateField, nullable)
- `last_conversation_summary`: Conversation summary (TextField)
- `created_at`: Creation timestamp (DateTimeField, auto_now_add)
- `updated_at`: Last update timestamp (DateTimeField, auto_now)

**Campaign Model** (`campaigns/models.py`):
- `name`: Campaign name (CharField, max_length=255, optional)
- `project_name`: Project name (CharField, max_length=255)
- `channel`: Communication channel - 'email' or 'whatsapp' (CharField, choices)
- `offer_details`: Sales offer details (TextField, optional)
- `created_by`: Foreign key to User (ForeignKey)
- `created_at`: Creation timestamp (DateTimeField, auto_now_add)
- `updated_at`: Last update timestamp (DateTimeField, auto_now)
- `is_active`: Active status (BooleanField, default=True)

**CampaignLead Model** (`campaigns/models.py`):
- `campaign`: Foreign key to Campaign (ForeignKey)
- `lead`: Foreign key to Lead (ForeignKey)
- `message_sent`: Message sent status (BooleanField, default=False)
- `message_sent_at`: Message sent timestamp (DateTimeField, nullable)
- `personalized_message`: Generated personalized message (TextField, optional)
- `created_at`: Creation timestamp (DateTimeField, auto_now_add)
- Unique constraint: (campaign, lead)

**Conversation Model** (`campaigns/models.py`):
- `campaign_lead`: Foreign key to CampaignLead (ForeignKey)
- `sender`: Sender type - 'customer' or 'agent' (CharField, choices)
- `message`: Message content (TextField)
- `agent_tool_used`: Tool used by agent - 'text_to_sql' or 'document_rag' (CharField, optional)
- `created_at`: Creation timestamp (DateTimeField, auto_now_add)

**User Model** (Django built-in):
- Standard Django User model for authentication
- Extended with custom fields if needed

#### API Schemas (Pydantic)

**Authentication Schemas** (`authentication/api.py`):
- `RegisterSchema`: User registration request
- `LoginSchema`: User login request
- `TokenResponse`: JWT token response
- `ForgotPasswordSchema`: Password reset request
- `ResetPasswordSchema`: Password reset with token
- `MessageResponse`: Generic message response

**Lead Schemas** (`leads/schemas.py`):
- `LeadFilterSchema`: Lead filtering criteria
- `LeadResponseSchema`: Lead data response
- `LeadFilterResponseSchema`: Filtered leads response with count

**Campaign Schemas** (`campaigns/schemas.py`):
- `CreateCampaignSchema`: Campaign creation request
- `CampaignResponseSchema`: Campaign data response
- `CampaignDetailResponseSchema`: Detailed campaign with leads
- `GenerateMessagesSchema`: Message generation request

**Agent Schemas** (`apps/agent/api.py`):
- `AgentQueryRequestSchema`: Agent query submission request
- `AgentQueryResponseSchema`: Agent query response with tool used

**Document Schemas** (`documents/api.py`):
- `DocumentUploadSchema`: Document upload request
- `DocumentUploadResponse`: Document upload response with processing results
- `DocumentStatsResponse`: Document collection statistics

#### Authentication Classes

**JWTAuth** (`authentication/jwt_auth.py`):
- `create_access_token()`: Create JWT access token
- `JWTAuth`: Custom JWT authentication class for Django Ninja
- `jwt_auth`: Instance of JWTAuth for use in API endpoints

**SessionAuth** (`authentication/session_auth.py`):
- `SessionAuth`: Custom authentication class for Django session-based auth

**MixedAuth** (`authentication/mixed_auth.py`):
- `MixedAuth`: Custom authentication class supporting both JWT and session auth

### State Management
- **LangGraph StateGraph**: Manages agent workflow state
- **AgentState TypedDict**: Defines state structure (query, project_name, tool_choice, result, response)

### Workflow
1. **Query Submission**: User submits query via `POST /api/agent/queries`
2. **Authentication**: JWT token validated
3. **Agent Routing**: LangGraph routes to appropriate tool (Text-to-SQL or Document RAG)
4. **Tool Execution**: Selected tool processes the query
5. **Response Synthesis**: Agent synthesizes final response
6. **Storage**: Conversation stored in database
7. **Response**: JSON response returned to client

## 14. Configuration

### Environment Variables
See `.env.example` for all required configuration:
- Django settings (SECRET_KEY, DEBUG, ALLOWED_HOSTS)
- JWT configuration
- Email settings
- LLM API keys (OPENAI_API_KEY or OLLAMA_BASE_URL for local Ollama)
- Embedding model selection
- Test email address

### ChromaDB Configuration
- **Persistence Directory**: `data/chromadb/` (configurable via `CHROMA_PERSIST_DIRECTORY`)
- **Collections**:
  - `brochures`: Document RAG embeddings
  - `vanna_training`: Text-to-SQL training data

## 15. File Structure

```
NurturingAI/
├── apps/
│   └── agent/
│       ├── api.py              # Agent API endpoints (RESTful)
│       ├── langgraph_agent.py  # LangGraph agent class
│       └── tools/
│           ├── text_to_sql.py  # Text-to-SQL tool class
│           └── document_rag.py # Document RAG tool class
├── services/
│   ├── chromadb_service.py     # ChromaDB service class
│   ├── vanna_service.py        # Vanna service class
│   ├── document_processor.py   # Document processing utilities
│   ├── message_generator.py    # LLM-based message generation
│   └── email_service.py        # Email sending service
├── campaigns/                  # Campaign management app
├── leads/                      # Lead management app
├── documents/                  # Document upload app
├── authentication/             # Authentication app
├── tests/                      # Test suite
└── config/                     # Django configuration
```

## 16. Key Features

### Agent Capabilities
- **Intelligent Routing**: Automatically determines Text-to-SQL vs Document RAG
- **State Management**: LangGraph manages complex agent workflows
- **Tool Integration**: Seamless integration of multiple tools
- **Conversation History**: Stores all customer-agent interactions

### Document Processing
- **Multi-format Support**: PDF, DOCX, DOC, TXT
- **Intelligent Chunking**: Recursive text splitting with overlap
- **Semantic Search**: Vector-based similarity search
- **Metadata Tracking**: Project name, source file, chunk index

### Lead Management
- **Advanced Filtering**: Multiple criteria with validation
- **Bulk Import**: Excel and JSON import support
- **Campaign Targeting**: Link leads to campaigns

### Campaign Management
- **Personalized Messages**: LLM-generated hyper-personalized content
- **Multi-channel**: Email and WhatsApp support
- **Message Tracking**: Track sent messages and responses

## 17. Performance Considerations

### Embedding Model
- **all-MiniLM-L6-v2**: Fast, efficient 384-dimensional embeddings
- **Local Execution**: No API calls needed for embeddings
- **Batch Processing**: Efficient batch embedding generation

### LLM Selection
- **OpenAI**: High quality, reliable (recommended for production)
- **Ollama**: Local inference (recommended for development/testing)
- **Fallback Logic**: Automatic fallback from OpenAI to Ollama if OpenAI unavailable or quota exceeded

### ChromaDB
- **Local Persistence**: No external service required
- **Efficient Queries**: Optimized vector similarity search
- **Scalable**: Handles large document collections

## 18. Security

### Authentication
- **JWT Tokens**: Secure, stateless authentication
- **Token Expiration**: Configurable expiration time
- **Password Hashing**: bcrypt with salt

### API Security
- **Mandatory Authentication**: All endpoints require JWT
- **Input Validation**: Pydantic schema validation
- **Error Handling**: Secure error messages (no sensitive data leakage)

## 19. Development Tools

### Code Quality
- **Pytest**: Comprehensive test suite
- **Coverage Reports**: HTML and JSON coverage reports
- **Linting**: Python code quality checks

### Evaluation
- **DeepEval**: Automated agent evaluation
- **Reproducible**: Single command evaluation (`python tests/run_eval.py`)
- **Metrics Tracking**: JSON-based results storage

## 20. Deployment Considerations

### Requirements
- Python 3.9+
- SQLite (or PostgreSQL for production)
- ChromaDB (local or remote)
- LLM API access (OpenAI) or local Ollama installation

### Environment Setup
1. Copy `.env.example` to `.env`
2. Configure all required environment variables
3. Run migrations: `python manage.py migrate`
4. Import leads: `python manage.py import_leads_excel --reset`
5. Start server: `python manage.py runserver`

### Production Checklist
- Set `DEBUG=False`
- Configure proper `SECRET_KEY` and `JWT_SECRET_KEY`
- Set up SMTP email backend
- Configure `ALLOWED_HOSTS`
- Use PostgreSQL for database
- Set up proper logging
- Configure SSL/HTTPS
- Set up monitoring and error tracking
