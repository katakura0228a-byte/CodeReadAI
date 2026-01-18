from dataclasses import dataclass, field
from pathlib import Path
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript
import tree_sitter_java
import tree_sitter_go
import tree_sitter_rust
import tree_sitter_c
import tree_sitter_cpp
from tree_sitter import Language, Parser, Node


@dataclass
class CodeUnitInfo:
    """Extracted code unit information."""
    type: str  # 'function', 'class', 'method'
    name: str
    start_line: int
    end_line: int
    signature: str
    source_code: str
    children: list["CodeUnitInfo"] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ParseResult:
    """Result of parsing a file."""
    language: str
    code_units: list[CodeUnitInfo]
    line_count: int


class ParserService:
    """Service for parsing source code using tree-sitter."""

    # Language extension mappings
    EXTENSION_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".hpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
    }

    # Tree-sitter language modules
    LANGUAGE_MODULES = {
        "python": tree_sitter_python,
        "javascript": tree_sitter_javascript,
        "typescript": tree_sitter_typescript,
        "java": tree_sitter_java,
        "go": tree_sitter_go,
        "rust": tree_sitter_rust,
        "c": tree_sitter_c,
        "cpp": tree_sitter_cpp,
    }

    # Node types to extract for each language
    EXTRACT_TYPES = {
        "python": {
            "function": ["function_definition"],
            "class": ["class_definition"],
        },
        "javascript": {
            "function": ["function_declaration", "arrow_function", "function"],
            "class": ["class_declaration"],
        },
        "typescript": {
            "function": ["function_declaration", "arrow_function", "function"],
            "class": ["class_declaration", "interface_declaration"],
        },
        "java": {
            "function": ["method_declaration", "constructor_declaration"],
            "class": ["class_declaration", "interface_declaration"],
        },
        "go": {
            "function": ["function_declaration", "method_declaration"],
            "class": ["type_declaration"],
        },
        "rust": {
            "function": ["function_item"],
            "class": ["struct_item", "impl_item", "trait_item"],
        },
        "c": {
            "function": ["function_definition"],
            "class": ["struct_specifier"],
        },
        "cpp": {
            "function": ["function_definition"],
            "class": ["class_specifier", "struct_specifier"],
        },
    }

    def __init__(self):
        self._parsers: dict[str, Parser] = {}

    def _get_parser(self, language: str) -> Parser | None:
        """Get or create parser for a language."""
        if language not in self._parsers:
            module = self.LANGUAGE_MODULES.get(language)
            if not module:
                return None
            lang = Language(module.language())
            parser = Parser(lang)
            self._parsers[language] = parser
        return self._parsers[language]

    def detect_language(self, file_path: str) -> str | None:
        """Detect language from file extension."""
        ext = Path(file_path).suffix.lower()
        return self.EXTENSION_MAP.get(ext)

    def parse_file(self, file_path: str, content: str) -> ParseResult | None:
        """Parse a source file and extract code units."""
        language = self.detect_language(file_path)
        if not language:
            return None

        parser = self._get_parser(language)
        if not parser:
            return None

        tree = parser.parse(bytes(content, "utf-8"))
        code_units = self._extract_code_units(tree.root_node, content, language)
        line_count = content.count("\n") + 1

        return ParseResult(
            language=language,
            code_units=code_units,
            line_count=line_count,
        )

    def _extract_code_units(
        self, node: Node, content: str, language: str, parent_class: str | None = None
    ) -> list[CodeUnitInfo]:
        """Recursively extract code units from AST."""
        units = []
        extract_types = self.EXTRACT_TYPES.get(language, {})

        for child in node.children:
            unit = None

            # Check if this is a function
            if child.type in extract_types.get("function", []):
                unit = self._extract_function(child, content, language, parent_class)

            # Check if this is a class
            elif child.type in extract_types.get("class", []):
                unit = self._extract_class(child, content, language)
                if unit:
                    # Extract methods from class
                    unit.children = self._extract_code_units(
                        child, content, language, parent_class=unit.name
                    )

            if unit:
                units.append(unit)
            else:
                # Recurse into other nodes
                units.extend(self._extract_code_units(child, content, language, parent_class))

        return units

    def _extract_function(
        self, node: Node, content: str, language: str, parent_class: str | None
    ) -> CodeUnitInfo | None:
        """Extract function information from AST node."""
        name = self._get_name(node, language)
        if not name:
            return None

        source_code = content[node.start_byte:node.end_byte]
        signature = self._extract_signature(node, content, language)

        return CodeUnitInfo(
            type="method" if parent_class else "function",
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            signature=signature,
            source_code=source_code,
            metadata={"parent_class": parent_class} if parent_class else {},
        )

    def _extract_class(self, node: Node, content: str, language: str) -> CodeUnitInfo | None:
        """Extract class information from AST node."""
        name = self._get_name(node, language)
        if not name:
            return None

        source_code = content[node.start_byte:node.end_byte]
        signature = self._extract_signature(node, content, language)

        return CodeUnitInfo(
            type="class",
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            signature=signature,
            source_code=source_code,
        )

    def _get_name(self, node: Node, language: str) -> str | None:
        """Extract name from AST node."""
        # Look for name/identifier child
        name_types = ["name", "identifier", "declarator", "type_identifier"]
        for child in node.children:
            if child.type in name_types:
                return child.text.decode("utf-8")
            # For C/C++ function declarators
            if child.type == "function_declarator":
                for subchild in child.children:
                    if subchild.type == "identifier":
                        return subchild.text.decode("utf-8")
        return None

    def _extract_signature(self, node: Node, content: str, language: str) -> str:
        """Extract signature (first line or definition) from node."""
        source = content[node.start_byte:node.end_byte]
        lines = source.split("\n")

        # For Python, include decorators and def line
        if language == "python":
            sig_lines = []
            for line in lines:
                sig_lines.append(line)
                if line.strip().endswith(":"):
                    break
            return "\n".join(sig_lines)

        # For other languages, take first line up to {
        first_line = lines[0]
        if "{" in first_line:
            return first_line.split("{")[0].strip()
        return first_line.strip()
