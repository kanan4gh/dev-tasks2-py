"""Reject metered LLM headless invocations from active project surfaces."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import json
from pathlib import Path
import re
import shlex
import sys
from typing import Any

DEFAULT_POLICY = Path(__file__).with_name("metered_automation_policy.json")
EXECUTION_CALLS = {
    "os.system",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "subprocess.run",
}
PROTECTED_EXCLUDES = {".git", ".steering", ".venv", "docs/ideas"}


class PolicyError(ValueError):
    """Raised when a metered automation policy is unsafe or malformed."""


@dataclass(frozen=True)
class Signature:
    policy_id: str
    command: str
    arguments: tuple[str, ...]

    @property
    def tokens(self) -> tuple[str, ...]:
        return (self.command, *self.arguments)


@dataclass(frozen=True)
class Policy:
    signatures: tuple[Signature, ...]
    include_paths: tuple[Path, ...]
    exclude_paths: tuple[Path, ...]
    extensions: frozenset[str]


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    policy_id: str


def _require_string_list(raw: dict[str, Any], key: str) -> list[str]:
    value = raw.get(key)
    if not isinstance(value, list) or not value:
        raise PolicyError(f"{key} must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise PolicyError(f"{key} must contain non-empty strings")
    return value


def _safe_relative_path(value: str, key: str) -> Path:
    path = Path(value)
    if path.is_absolute() or value in {"", ".", "/"} or ".." in path.parts:
        raise PolicyError(f"unsafe {key}: {value!r}")
    return path


def load_policy(path: Path) -> Policy:
    try:
        raw_object: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PolicyError(f"cannot read policy: {exc}") from exc
    if not isinstance(raw_object, dict):
        raise PolicyError("policy root must be an object")
    raw: dict[str, Any] = raw_object
    if raw.get("version") != 1:
        raise PolicyError("unsupported policy version")

    signature_data = raw.get("signatures")
    if not isinstance(signature_data, list) or not signature_data:
        raise PolicyError("signatures must be a non-empty list")
    signatures: list[Signature] = []
    seen_ids: set[str] = set()
    for item in signature_data:
        if not isinstance(item, dict):
            raise PolicyError("each signature must be an object")
        policy_id = item.get("id")
        command = item.get("command")
        arguments = item.get("arguments")
        if not isinstance(policy_id, str) or not policy_id.strip() or policy_id in seen_ids:
            raise PolicyError("signature id must be non-empty and unique")
        if not isinstance(command, str) or not command.strip():
            raise PolicyError(f"{policy_id}: command must be non-empty")
        if (
            not isinstance(arguments, list)
            or not arguments
            or any(not isinstance(arg, str) or not arg.strip() for arg in arguments)
        ):
            raise PolicyError(f"{policy_id}: arguments must contain non-empty strings")
        seen_ids.add(policy_id)
        signatures.append(Signature(policy_id, command, tuple(arguments)))

    include_paths = tuple(
        _safe_relative_path(item, "include path")
        for item in _require_string_list(raw, "include_paths")
    )
    exclude_paths = tuple(
        _safe_relative_path(item, "exclude path")
        for item in _require_string_list(raw, "exclude_paths")
    )
    overlap = set(include_paths) & set(exclude_paths)
    if overlap:
        raise PolicyError(f"paths cannot be both included and excluded: {sorted(map(str, overlap))}")
    for path_item in exclude_paths:
        if len(path_item.parts) == 1 and str(path_item) not in PROTECTED_EXCLUDES:
            if not str(path_item).startswith(".") and str(path_item) != "__pycache__":
                raise PolicyError(f"overly broad exclude path: {path_item}")

    extensions = frozenset(_require_string_list(raw, "extensions"))
    if any(not extension.startswith(".") for extension in extensions):
        raise PolicyError("extensions must start with a dot")
    return Policy(tuple(signatures), include_paths, exclude_paths, extensions)


def _is_excluded(relative_path: Path, excludes: tuple[Path, ...]) -> bool:
    return any(relative_path == excluded or excluded in relative_path.parents for excluded in excludes)


def iter_target_files(root: Path, policy: Policy) -> list[Path]:
    if not root.is_dir():
        raise PolicyError(f"project root is not a directory: {root}")
    files: set[Path] = set()
    for include in policy.include_paths:
        target = root / include
        if not target.exists():
            raise PolicyError(f"include path does not exist: {include}")
        candidates = [target] if target.is_file() else target.rglob("*")
        for candidate in candidates:
            if not candidate.is_file() or candidate.suffix not in policy.extensions:
                continue
            relative = candidate.relative_to(root)
            if not _is_excluded(relative, policy.exclude_paths):
                files.add(candidate)
    return sorted(files)


def _normalized_tokens(text: str) -> list[tuple[str, int]]:
    tokens: list[tuple[str, int]] = []
    for match in re.finditer(r"[A-Za-z0-9_./-]+", text):
        tokens.append((match.group(0), text.count("\n", 0, match.start()) + 1))
    return tokens


def _matches_signature(tokens: list[str], signature: Signature) -> bool:
    expected = list(signature.tokens)
    for start in range(len(tokens) - len(expected) + 1):
        candidate = tokens[start : start + len(expected)]
        if Path(candidate[0]).name == expected[0] and candidate[1:] == expected[1:]:
            return True
    return False


def scan_text(path: Path, text: str, signatures: tuple[Signature, ...]) -> list[Violation]:
    positioned = _normalized_tokens(text)
    values = [token for token, _line in positioned]
    violations: list[Violation] = []
    for signature in signatures:
        expected = list(signature.tokens)
        for start in range(len(values) - len(expected) + 1):
            candidate = values[start : start + len(expected)]
            if Path(candidate[0]).name == expected[0] and candidate[1:] == expected[1:]:
                violations.append(Violation(path, positioned[start][1], signature.policy_id))
    return violations


def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _constant_value(node: ast.expr, constants: dict[str, object]) -> object | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        values = [_constant_value(element, constants) for element in node.elts]
        return values if all(value is not None for value in values) else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _constant_value(node.left, constants)
        right = _constant_value(node.right, constants)
        if isinstance(left, str) and isinstance(right, str):
            return left + right
        if isinstance(left, list) and isinstance(right, list):
            return [*left, *right]
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    return None


def _command_tokens(value: object) -> list[str]:
    if isinstance(value, str):
        try:
            return shlex.split(value)
        except ValueError:
            return value.split()
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return [item for item in value if isinstance(item, str)]
    return []


class ExecutionVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, signatures: tuple[Signature, ...]) -> None:
        self.path = path
        self.signatures = signatures
        self.constants: dict[str, object] = {}
        self.violations: list[Violation] = []

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        value = _constant_value(node.value, self.constants)
        if value is not None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.constants[target.id] = value
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if _call_name(node.func) in EXECUTION_CALLS:
            argument: ast.expr | None = node.args[0] if node.args else None
            if argument is None:
                argument = next((kw.value for kw in node.keywords if kw.arg == "args"), None)
            if argument is not None:
                tokens = _command_tokens(_constant_value(argument, self.constants))
                for signature in self.signatures:
                    if _matches_signature(tokens, signature):
                        self.violations.append(
                            Violation(self.path, node.lineno, signature.policy_id)
                        )
        self.generic_visit(node)


def scan_python(path: Path, text: str, signatures: tuple[Signature, ...]) -> list[Violation]:
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        raise PolicyError(f"cannot parse Python file {path}:{exc.lineno}: {exc.msg}") from exc
    visitor = ExecutionVisitor(path, signatures)
    visitor.visit(tree)
    return visitor.violations


def scan_repository(root: Path, policy: Policy) -> list[Violation]:
    violations: set[Violation] = set()
    for path in iter_target_files(root, policy):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise PolicyError(f"cannot read {path.relative_to(root)}: {exc}") from exc
        relative = path.relative_to(root)
        violations.update(scan_text(relative, text, policy.signatures))
        if path.suffix == ".py":
            violations.update(scan_python(relative, text, policy.signatures))
    return sorted(violations, key=lambda item: (str(item.path), item.line, item.policy_id))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        policy = load_policy(args.policy.resolve())
        violations = scan_repository(args.root.resolve(), policy)
    except Exception as exc:
        print(f"metered automation lint: inspection failed: {exc}", file=sys.stderr)
        return 1
    if violations:
        print(f"metered automation lint: {len(violations)} violation(s)", file=sys.stderr)
        for violation in violations:
            print(f"  [{violation.policy_id}] {violation.path}:{violation.line}", file=sys.stderr)
        return 1
    print("metered automation lint: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
