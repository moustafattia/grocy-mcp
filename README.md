# grocy-mcp

MCP server and CLI for Grocy — control stock, shopping lists, recipes and chores via AI agents.

## Features

- **30 MCP tools** covering stock, shopping lists, recipes, chores, and system management
- **Full CLI** with subcommand groups mirroring every MCP tool
- **Name-based lookups** — pass product/recipe/chore names instead of numeric IDs
- **Dual transport** — stdio (for Claude Desktop / Claude Code) and streamable-http
- **Grocy v4.4.1+** compatible

## Installation

```bash
pip install grocy-mcp
```

Run without installing using `uvx`:

```bash
uvx grocy-mcp --transport stdio
```

## Configuration

grocy-mcp reads configuration from (in priority order):

1. Environment variables
2. TOML config file

### Environment variables

```bash
export GROCY_URL="https://grocy.example.com"
export GROCY_API_KEY="your-api-key-here"
```

### TOML config file

Create `~/.config/grocy-mcp/config.toml` (Linux/macOS) or the platform equivalent:

```toml
[grocy]
url = "https://grocy.example.com"
api_key = "your-api-key-here"
```

## Usage

### MCP server — stdio (Claude Desktop / Claude Code)

```bash
grocy-mcp --transport stdio
```

### MCP server — streamable-http

```bash
grocy-mcp --transport streamable-http --port 8000
```

### Claude Code configuration

Add to your `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "grocy": {
      "command": "grocy-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "GROCY_URL": "https://grocy.example.com",
        "GROCY_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### CLI examples

```bash
# Stock
grocy stock overview
grocy stock expiring
grocy stock add Milk 2
grocy stock consume "Oat Milk" 1
grocy stock search milk
grocy stock barcode 5000112637922

# Shopping list
grocy shopping view
grocy shopping add Butter --amount 3
grocy shopping add "Oat Milk" --amount 2 --list-id 2 --note "for breakfast"
grocy shopping clear

# Recipes
grocy recipes list
grocy recipes details "Spaghetti Bolognese"
grocy recipes fulfillment "Spaghetti Bolognese"
grocy recipes consume "Spaghetti Bolognese"
grocy recipes add-to-shopping "Spaghetti Bolognese"

# Chores
grocy chores list
grocy chores overdue
grocy chores execute "Vacuum living room"
grocy chores execute "Vacuum living room" --done-by 1
grocy chores undo "Vacuum living room"

# System
grocy system info
grocy entity list products
grocy entity manage products create --data '{"name": "Oat Milk"}'
```

## Development

```bash
git clone https://github.com/moustafattia/grocy-mcp
cd grocy-mcp
pip install -e ".[dev]"
pytest -v
```

## License

MIT
