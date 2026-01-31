#!/usr/bin/env python3
"""
Odoo Code Assistant Agent
An autonomous agent for exploring Odoo codebase, fixing frontend issues, and testing modules.
"""
import anthropic
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Configuration
ODOO_PATH = Path("/home/as/ws/odoo")
ADDONS_PATH = ODOO_PATH / "addons"
CORE_ADDONS_PATH = ODOO_PATH / "odoo" / "addons"

# Initialize the Anthropic client
client = anthropic.Anthropic()

# System prompt for the Odoo agent
SYSTEM_PROMPT = """You are an expert Odoo developer assistant. Your role is to:

1. **Explore the Odoo codebase** - Navigate and understand the code structure
2. **Fix frontend issues** - Debug and fix OWL components, JavaScript, XML templates, and SCSS
3. **Test modules** - Run tests and verify module functionality

## Odoo Frontend Stack:
- **OWL Framework**: Odoo's reactive UI framework (similar to Vue/React)
- **QWeb Templates**: XML-based templates for rendering
- **SCSS/CSS**: Styling
- **JavaScript ES6+**: Component logic

## Key Directories:
- `/home/as/ws/odoo/addons/` - Custom addons (600+ modules)
- `/home/as/ws/odoo/odoo/addons/` - Core Odoo addons
- `/home/as/ws/odoo/addons/web/static/src/` - Main frontend code
- `*/static/src/` - Each addon's frontend assets

## Common Frontend Issues:
- OWL component lifecycle errors
- Template rendering issues (t-if, t-foreach, t-esc)
- RPC call failures
- Asset bundle errors
- Missing dependencies in manifest

## Testing:
- Use XML-RPC to test model operations
- Check browser console for JS errors
- Verify module installation via Odoo UI

When fixing issues:
1. First understand the current code
2. Identify the root cause
3. Make minimal, targeted changes
4. Suggest how to test the fix

Always explain your reasoning and provide actionable solutions."""

# Tool definitions
tools = [
    {
        "name": "read_file",
        "description": "Read the contents of a file in the Odoo codebase",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file (relative to /home/as/ws/odoo or absolute)"
                },
                "start_line": {
                    "type": "integer",
                    "description": "Start line number (optional, 1-indexed)"
                },
                "end_line": {
                    "type": "integer",
                    "description": "End line number (optional, 1-indexed)"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file in the Odoo codebase",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file (relative to /home/as/ws/odoo or absolute)"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file"
                }
            },
            "required": ["file_path", "content"]
        }
    },
    {
        "name": "edit_file",
        "description": "Edit a specific part of a file by replacing text",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file"
                },
                "old_text": {
                    "type": "string",
                    "description": "The exact text to find and replace"
                },
                "new_text": {
                    "type": "string",
                    "description": "The new text to replace with"
                }
            },
            "required": ["file_path", "old_text", "new_text"]
        }
    },
    {
        "name": "search_code",
        "description": "Search for code patterns in the Odoo codebase using ripgrep",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for"
                },
                "file_type": {
                    "type": "string",
                    "description": "File extension to filter (e.g., 'js', 'xml', 'py', 'scss')"
                },
                "path": {
                    "type": "string",
                    "description": "Subdirectory to search in (relative to Odoo root)"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 20)"
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "list_directory",
        "description": "List files and directories",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory path (relative to /home/as/ws/odoo or absolute)"
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter files (e.g., '*.js', '**/*.xml')"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to list recursively"
                }
            },
            "required": ["directory"]
        }
    },
    {
        "name": "find_files",
        "description": "Find files matching a pattern in the Odoo codebase",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Filename pattern (e.g., '*.js', 'manifest.py')"
                },
                "path": {
                    "type": "string",
                    "description": "Subdirectory to search in"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 50)"
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "run_odoo_command",
        "description": "Run Odoo CLI commands (scaffold, shell, test, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Odoo command to run (e.g., 'shell', 'test -m module_name')"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 120)"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "run_docker_command",
        "description": "Run commands inside the Odoo Docker container",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Command to run inside the container"
                },
                "service": {
                    "type": "string",
                    "description": "Docker service name (default: 'odoo')"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "test_module",
        "description": "Test an Odoo module via XML-RPC",
        "input_schema": {
            "type": "object",
            "properties": {
                "module_name": {
                    "type": "string",
                    "description": "Name of the module to test"
                },
                "test_type": {
                    "type": "string",
                    "enum": ["install", "upgrade", "check_models", "full"],
                    "description": "Type of test to run"
                }
            },
            "required": ["module_name"]
        }
    },
    {
        "name": "check_frontend_assets",
        "description": "Check frontend assets for a module (JS, XML templates, SCSS)",
        "input_schema": {
            "type": "object",
            "properties": {
                "module_name": {
                    "type": "string",
                    "description": "Name of the module to check"
                }
            },
            "required": ["module_name"]
        }
    },
    {
        "name": "analyze_owl_component",
        "description": "Analyze an OWL component for common issues",
        "input_schema": {
            "type": "object",
            "properties": {
                "component_path": {
                    "type": "string",
                    "description": "Path to the OWL component JS file"
                }
            },
            "required": ["component_path"]
        }
    },
    {
        "name": "get_module_info",
        "description": "Get information about an Odoo module from its manifest",
        "input_schema": {
            "type": "object",
            "properties": {
                "module_name": {
                    "type": "string",
                    "description": "Name of the module"
                }
            },
            "required": ["module_name"]
        }
    },
    {
        "name": "bash",
        "description": "Run a bash command (use with caution)",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Bash command to execute"
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory (default: /home/as/ws/odoo)"
                }
            },
            "required": ["command"]
        }
    }
]


def resolve_path(path: str) -> Path:
    """Resolve a path relative to Odoo root or as absolute."""
    p = Path(path)
    if p.is_absolute():
        return p
    return ODOO_PATH / path


def read_file(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """Read a file and return its contents."""
    try:
        path = resolve_path(file_path)
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if start_line is not None or end_line is not None:
            start = (start_line or 1) - 1
            end = end_line or len(lines)
            lines = lines[start:end]
            # Add line numbers
            numbered_lines = []
            for i, line in enumerate(lines, start=start + 1):
                numbered_lines.append(f"{i:4d} | {line.rstrip()}")
            return "\n".join(numbered_lines)

        return "".join(lines)
    except FileNotFoundError:
        return f"Error: File not found at {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


def write_file(file_path: str, content: str) -> str:
    """Write content to a file."""
    try:
        path = resolve_path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


def edit_file(file_path: str, old_text: str, new_text: str) -> str:
    """Edit a file by replacing text."""
    try:
        path = resolve_path(file_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if old_text not in content:
            return f"Error: Could not find the specified text in {file_path}"

        count = content.count(old_text)
        if count > 1:
            return f"Warning: Found {count} occurrences of the text. Please provide more context to make it unique."

        new_content = content.replace(old_text, new_text)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return f"Successfully edited {path}"
    except Exception as e:
        return f"Error editing file: {str(e)}"


def search_code(pattern: str, file_type: Optional[str] = None, path: Optional[str] = None, max_results: int = 20) -> str:
    """Search for code patterns using ripgrep."""
    try:
        search_path = resolve_path(path) if path else ODOO_PATH
        cmd = ["rg", "--line-number", "--max-count", str(max_results)]

        if file_type:
            cmd.extend(["--type", file_type])

        cmd.extend([pattern, str(search_path)])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return result.stdout[:10000]  # Limit output
        elif result.returncode == 1:
            return "No matches found"
        else:
            return f"Search error: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Search timed out"
    except FileNotFoundError:
        # Fallback to grep if rg not available
        try:
            search_path = resolve_path(path) if path else ODOO_PATH
            cmd = ["grep", "-rn", "--include", f"*.{file_type}" if file_type else "*", pattern, str(search_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.stdout[:10000] if result.stdout else "No matches found"
        except Exception as e:
            return f"Error: {str(e)}"


def list_directory(directory: str, pattern: Optional[str] = None, recursive: bool = False) -> str:
    """List files in a directory."""
    try:
        dir_path = resolve_path(directory)
        if not dir_path.exists():
            return f"Error: Directory not found at {directory}"

        if pattern and recursive:
            files = list(dir_path.rglob(pattern))[:100]
        elif pattern:
            files = list(dir_path.glob(pattern))[:100]
        elif recursive:
            files = list(dir_path.rglob("*"))[:100]
        else:
            files = list(dir_path.iterdir())[:100]

        result = []
        for f in sorted(files):
            rel_path = f.relative_to(dir_path) if f.is_relative_to(dir_path) else f
            marker = "/" if f.is_dir() else ""
            result.append(f"{rel_path}{marker}")

        return "\n".join(result) if result else "Directory is empty"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


def find_files(pattern: str, path: Optional[str] = None, max_results: int = 50) -> str:
    """Find files matching a pattern."""
    try:
        search_path = resolve_path(path) if path else ODOO_PATH
        files = list(search_path.rglob(pattern))[:max_results]

        result = []
        for f in sorted(files):
            try:
                rel_path = f.relative_to(ODOO_PATH)
            except ValueError:
                rel_path = f
            result.append(str(rel_path))

        return "\n".join(result) if result else "No files found"
    except Exception as e:
        return f"Error finding files: {str(e)}"


def run_odoo_command(command: str, timeout: int = 120) -> str:
    """Run Odoo CLI command via docker-compose."""
    try:
        full_cmd = f"docker-compose exec -T odoo python3 odoo-bin {command}"
        result = subprocess.run(
            full_cmd,
            shell=True,
            cwd=ODOO_PATH,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = result.stdout + result.stderr
        return output[:5000] if output else "Command completed with no output"
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error running command: {str(e)}"


def run_docker_command(command: str, service: str = "odoo") -> str:
    """Run command inside Docker container."""
    try:
        full_cmd = f"docker-compose exec -T {service} {command}"
        result = subprocess.run(
            full_cmd,
            shell=True,
            cwd=ODOO_PATH,
            capture_output=True,
            text=True,
            timeout=60
        )
        output = result.stdout + result.stderr
        return output[:5000] if output else "Command completed with no output"
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error running docker command: {str(e)}"


def test_module(module_name: str, test_type: str = "check_models") -> str:
    """Test an Odoo module via XML-RPC."""
    import xmlrpc.client

    url = "http://localhost:8069"
    db = "odoo"
    username = "admin"
    password = "admin"

    results = []

    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})

        if not uid:
            return "Error: Authentication failed. Is Odoo running?"

        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        results.append(f"✓ Connected to Odoo (UID: {uid})")

        # Check if module is installed
        module_ids = models.execute_kw(
            db, uid, password,
            'ir.module.module', 'search',
            [[['name', '=', module_name]]]
        )

        if not module_ids:
            return f"Module '{module_name}' not found"

        module_info = models.execute_kw(
            db, uid, password,
            'ir.module.module', 'read',
            [module_ids],
            {'fields': ['name', 'state', 'shortdesc', 'author']}
        )[0]

        results.append(f"Module: {module_info['shortdesc']} ({module_info['name']})")
        results.append(f"State: {module_info['state']}")

        if test_type == "install" and module_info['state'] != 'installed':
            models.execute_kw(
                db, uid, password,
                'ir.module.module', 'button_immediate_install',
                [module_ids]
            )
            results.append("✓ Module installed successfully")

        elif test_type == "upgrade":
            models.execute_kw(
                db, uid, password,
                'ir.module.module', 'button_immediate_upgrade',
                [module_ids]
            )
            results.append("✓ Module upgraded successfully")

        elif test_type in ["check_models", "full"]:
            # Get models defined by this module
            model_ids = models.execute_kw(
                db, uid, password,
                'ir.model', 'search',
                [[['modules', 'ilike', module_name]]]
            )

            model_names = models.execute_kw(
                db, uid, password,
                'ir.model', 'read',
                [model_ids],
                {'fields': ['model', 'name']}
            )

            results.append(f"\nModels ({len(model_names)}):")
            for m in model_names[:20]:
                results.append(f"  - {m['model']}: {m['name']}")

        return "\n".join(results)

    except Exception as e:
        return f"Error testing module: {str(e)}"


def check_frontend_assets(module_name: str) -> str:
    """Check frontend assets for a module."""
    results = []

    # Find module path
    module_path = None
    for addons_dir in [ADDONS_PATH, CORE_ADDONS_PATH]:
        potential_path = addons_dir / module_name
        if potential_path.exists():
            module_path = potential_path
            break

    if not module_path:
        return f"Module '{module_name}' not found"

    results.append(f"Module path: {module_path}")

    static_src = module_path / "static" / "src"
    if not static_src.exists():
        results.append("No static/src directory found")
        return "\n".join(results)

    # Count files by type
    js_files = list(static_src.rglob("*.js"))
    xml_files = list(static_src.rglob("*.xml"))
    scss_files = list(static_src.rglob("*.scss"))
    css_files = list(static_src.rglob("*.css"))

    results.append(f"\nFrontend Assets:")
    results.append(f"  JavaScript files: {len(js_files)}")
    results.append(f"  XML templates: {len(xml_files)}")
    results.append(f"  SCSS files: {len(scss_files)}")
    results.append(f"  CSS files: {len(css_files)}")

    # List JS files
    if js_files:
        results.append(f"\nJavaScript files:")
        for f in js_files[:15]:
            rel_path = f.relative_to(module_path)
            results.append(f"  - {rel_path}")

    # Check manifest for assets
    manifest_path = module_path / "__manifest__.py"
    if manifest_path.exists():
        with open(manifest_path, 'r') as f:
            content = f.read()

        if "'assets'" in content or '"assets"' in content:
            results.append("\n✓ Assets defined in manifest")
            # Extract assets section
            match = re.search(r"['\"]assets['\"]\s*:\s*\{([^}]+)\}", content, re.DOTALL)
            if match:
                results.append(f"Assets config preview:\n{match.group(0)[:500]}")
        else:
            results.append("\n⚠ No assets defined in manifest")

    return "\n".join(results)


def analyze_owl_component(component_path: str) -> str:
    """Analyze an OWL component for common issues."""
    results = []

    try:
        path = resolve_path(component_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        results.append(f"Analyzing: {path.name}")
        results.append("=" * 50)

        # Check for OWL imports
        owl_imports = re.findall(r"from\s+['\"]@odoo/owl['\"]\s+import\s+\{([^}]+)\}", content)
        web_imports = re.findall(r"from\s+['\"]@web/[^'\"]+['\"]\s+import\s+\{([^}]+)\}", content)

        if owl_imports:
            results.append(f"OWL imports: {', '.join(owl_imports)}")
        if web_imports:
            results.append(f"Web imports: {len(web_imports)} modules")

        # Check for Component class
        components = re.findall(r"class\s+(\w+)\s+extends\s+Component", content)
        if components:
            results.append(f"\nComponents defined: {', '.join(components)}")

        # Check for template
        templates = re.findall(r"static\s+template\s*=\s*['\"]([^'\"]+)['\"]", content)
        if templates:
            results.append(f"Templates: {', '.join(templates)}")
        else:
            results.append("⚠ No static template defined")

        # Check for props
        props = re.findall(r"static\s+props\s*=\s*\{([^}]+)\}", content, re.DOTALL)
        if props:
            results.append("✓ Props defined")

        # Check for setup function
        if "setup()" in content:
            results.append("✓ setup() method found")

            # Check for hooks
            hooks = []
            if "useState" in content:
                hooks.append("useState")
            if "useRef" in content:
                hooks.append("useRef")
            if "useEffect" in content:
                hooks.append("useEffect")
            if "onMounted" in content:
                hooks.append("onMounted")
            if "onWillStart" in content:
                hooks.append("onWillStart")
            if "useService" in content:
                hooks.append("useService")

            if hooks:
                results.append(f"Hooks used: {', '.join(hooks)}")

        # Common issues check
        issues = []

        if "this.state" in content and "useState" not in content:
            issues.append("⚠ Using this.state without useState hook")

        if "this.props" in content and "static props" not in content:
            issues.append("⚠ Accessing props without prop validation")

        if "async" in content and "await" in content:
            if "onWillStart" not in content and "useEffect" not in content:
                issues.append("⚠ Async code might need onWillStart or useEffect")

        if issues:
            results.append("\nPotential Issues:")
            results.extend(issues)
        else:
            results.append("\n✓ No obvious issues found")

        return "\n".join(results)

    except FileNotFoundError:
        return f"Error: Component file not found at {component_path}"
    except Exception as e:
        return f"Error analyzing component: {str(e)}"


def get_module_info(module_name: str) -> str:
    """Get information about an Odoo module from its manifest."""
    results = []

    # Find module path
    module_path = None
    for addons_dir in [ADDONS_PATH, CORE_ADDONS_PATH]:
        potential_path = addons_dir / module_name
        if potential_path.exists():
            module_path = potential_path
            break

    if not module_path:
        return f"Module '{module_name}' not found"

    manifest_path = module_path / "__manifest__.py"
    if not manifest_path.exists():
        return f"No manifest found for module '{module_name}'"

    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse manifest (safely)
        manifest = eval(content)

        results.append(f"Module: {module_name}")
        results.append(f"Path: {module_path}")
        results.append("=" * 50)

        for key in ['name', 'version', 'category', 'summary', 'description', 'author', 'depends', 'data', 'assets']:
            if key in manifest:
                value = manifest[key]
                if isinstance(value, list):
                    if len(value) > 10:
                        results.append(f"{key}: {value[:10]} ... ({len(value)} items)")
                    else:
                        results.append(f"{key}: {value}")
                elif isinstance(value, dict):
                    results.append(f"{key}: {json.dumps(value, indent=2)[:500]}")
                else:
                    results.append(f"{key}: {value}")

        return "\n".join(results)

    except Exception as e:
        return f"Error reading manifest: {str(e)}"


def bash(command: str, working_dir: Optional[str] = None) -> str:
    """Run a bash command."""
    try:
        cwd = resolve_path(working_dir) if working_dir else ODOO_PATH
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60
        )
        output = result.stdout + result.stderr
        return output[:5000] if output else "Command completed with no output"
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error running command: {str(e)}"


def process_tool_call(tool_name: str, tool_input: dict) -> str:
    """Process a tool call and return the result."""
    tool_functions = {
        "read_file": read_file,
        "write_file": write_file,
        "edit_file": edit_file,
        "search_code": search_code,
        "list_directory": list_directory,
        "find_files": find_files,
        "run_odoo_command": run_odoo_command,
        "run_docker_command": run_docker_command,
        "test_module": test_module,
        "check_frontend_assets": check_frontend_assets,
        "analyze_owl_component": analyze_owl_component,
        "get_module_info": get_module_info,
        "bash": bash,
    }

    if tool_name in tool_functions:
        return tool_functions[tool_name](**tool_input)
    else:
        return f"Unknown tool: {tool_name}"


def run_agent(user_message: str, verbose: bool = True):
    """Run the Odoo agent with the given user message."""
    print(f"\n{'='*60}")
    print(f"User: {user_message}")
    print(f"{'='*60}\n")

    messages = [
        {"role": "user", "content": user_message}
    ]

    iteration = 0
    max_iterations = 30

    while iteration < max_iterations:
        iteration += 1

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "tool_use":
            tool_calls = [block for block in response.content if block.type == "tool_use"]
            text_blocks = [block for block in response.content if block.type == "text"]

            # Print any text output
            for block in text_blocks:
                if verbose and block.text.strip():
                    print(f"Agent: {block.text}\n")

            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for tool_call in tool_calls:
                if verbose:
                    print(f"🔧 Calling: {tool_call.name}")
                    print(f"   Input: {json.dumps(tool_call.input, indent=2)[:200]}")

                result = process_tool_call(tool_call.name, tool_call.input)

                if verbose:
                    preview = result[:300] + "..." if len(result) > 300 else result
                    print(f"   Result: {preview}\n")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": result
                })

            messages.append({"role": "user", "content": tool_results})

        else:
            # Final response
            final_response = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_response = block.text
                    break

            print(f"\n{'='*60}")
            print(f"Agent Response:\n{final_response}")
            print(f"{'='*60}\n")
            return final_response

    return "Max iterations reached"


def interactive_mode():
    """Run the agent in interactive mode."""
    print("\n" + "="*60)
    print("  Odoo Code Assistant Agent")
    print("  Type 'exit' or 'quit' to stop")
    print("="*60 + "\n")

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break

            run_agent(user_input)

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run with command line argument
        user_message = " ".join(sys.argv[1:])
        run_agent(user_message)
    else:
        # Interactive mode
        interactive_mode()
