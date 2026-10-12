# PostgreSQL MCP Server with Safety Layer

A Model Context Protocol (MCP) server that provides read-only access to PostgreSQL with configurable table access restrictions.

## Features

- **Read-only access**: All queries are validated to prevent data modification
- **Table whitelisting**: Only specified tables can be accessed
- **Schema restrictions**: Access limited to a single schema
- **Query limits**: Configurable row limits and statement timeouts
- **LLM integration**: Works with Gemini to create a natural language database assistant

## Setup

### 1. Create Virtual Environment

```bash
python -m venv .venv
```

### 2. Activate Virtual Environment

**Windows:**
```bash
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and add your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
DATABASE_URL=postgresql://mcp_readonly:your_password@localhost:5432/your_database
MAX_ROWS=100
STATEMENT_TIMEOUT_MS=10000
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

### 3. Configure Allowed Tables

Copy the example config file and customize for your database:

```bash
cp mcp-server/config.example.json mcp-server/config.json
```

Edit `mcp-server/config.json`:
```json
{
  "allowed_schema": "public",
  "allowed_tables": [
    "departments",
    "modules",
    "module_department",
    "form_systems",
    "form_fields"
  ]
}
```

### 4. Set Up Database User (Optional)

For additional security, create a read-only database user:

```bash
psql -U postgres -d your_database -f database/setup_readonly.sql
```

Update the password in the SQL file and your `.env` accordingly.

## Usage

### Running the MCP Server

```bash
python -m mcp_server.server
```

### Running the Agent

```bash
python agent.py
```

The agent will start an interactive session where you can ask questions about your database in natural language.

## MCP Tools

The server provides three tools:

1. **get_database_schema**: Returns column information for all allowed tables
2. **get_table_schema**: Returns column information for a specific table
3. **read_query**: Executes a read-only SQL query (SELECT/WITH only)

## Security Features

- SQL injection protection via parameterized queries
- Read-only transactions enforced at database level
- Statement timeouts to prevent long-running queries
- Row limits to prevent excessive data retrieval
- Table access whitelist enforcement
- Schema access restrictions
- Regex-based SQL validation to block write operations

## Project Structure

```
.
├── agent.py                          # LLM agent client
├── llm/
│   └── gemini.py                     # Gemini LLM integration
├── mcp_server/
│   ├── server.py                     # MCP server implementation
│   ├── config.json                   # Security configuration (gitignored)
│   └── config.example.json           # Example configuration
├── database/
│   └── setup_readonly.sql            # Database user setup script
├── .env                              # Environment variables (gitignored)
├── .env.example                      # Example environment file
└── requirements.txt                 # Python dependencies
```
