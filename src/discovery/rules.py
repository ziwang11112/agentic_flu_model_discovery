from __future__ import annotations

from dataclasses import dataclass


STRUCTURE_TEMPLATES = {
    "SIR": {
        "compartments": ("S", "I", "R"),
        "edges": (("S", "I"), ("I", "R")),
        "infectious": ("I",),
    },
    "SEIR": {
        "compartments": ("S", "E", "I", "R"),
        "edges": (("S", "E"), ("E", "I"), ("I", "R")),
        "infectious": ("I",),
    },
    "SEIRS": {
        "compartments": ("S", "E", "I", "R"),
        "edges": (("S", "E"), ("E", "I"), ("I", "R"), ("R", "S")),
        "infectious": ("I",),
    },
    "SEIHR": {
        "compartments": ("S", "E", "I", "H", "R"),
        "edges": (("S", "E"), ("E", "I"), ("I", "H"), ("H", "R")),
        "infectious": ("I",),
    },
    "SEIAR": {
        "compartments": ("S", "E", "I", "A", "R"),
        "edges": (("S", "E"), ("E", "I"), ("E", "A"), ("I", "R"), ("A", "R")),
        "infectious": ("I", "A"),
    },
}


@dataclass(frozen=True)
class StructureSpec:
    """One candidate in the constrained discovery space."""

    structure_name: str
    fractional: bool = False
    observation_map: str = "I"

    @property
    def spec_key(self) -> str:
        return f"{self.structure_name}|fractional={int(self.fractional)}|obs={self.observation_map}"

    @property
    def slug(self) -> str:
        return (
            self.spec_key.replace("|", "__")
            .replace("=", "-")
            .replace("+", "plus")
            .replace("/", "_")
        )


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    reason: str


def structure_template(spec: StructureSpec | str) -> dict[str, tuple[str, ...]]:
    name = spec if isinstance(spec, str) else spec.structure_name
    if name not in STRUCTURE_TEMPLATES:
        raise KeyError(f"Unknown structure {name}")
    return STRUCTURE_TEMPLATES[name]


def _reaches_target(edges: tuple[tuple[str, str], ...], start: str, target: str) -> bool:
    adjacency: dict[str, list[str]] = {}
    for source, destination in edges:
        adjacency.setdefault(source, []).append(destination)
    stack = [start]
    seen = set()
    while stack:
        node = stack.pop()
        if node == target:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(adjacency.get(node, []))
    return False


def validate_structure(spec: StructureSpec) -> ValidationResult:
    """Validate one constrained candidate structure."""
    if spec.structure_name not in STRUCTURE_TEMPLATES:
        return ValidationResult(False, "structure_not_allowed")

    template = structure_template(spec)
    compartments = template["compartments"]
    edges = template["edges"]
    infectious = template["infectious"]

    if len(compartments) > 5:
        return ValidationResult(False, "too_many_compartments")

    if any(source == destination for source, destination in edges):
        return ValidationResult(False, "self_loop_detected")

    outgoing_from_s = [destination for source, destination in edges if source == "S"]
    if len(outgoing_from_s) != 1 or outgoing_from_s[0] not in {"E", "I"}:
        return ValidationResult(False, "infection_must_start_from_s")

    for infectious_compartment in infectious:
        if not _reaches_target(edges, infectious_compartment, "R"):
            return ValidationResult(False, f"infectious_compartment_{infectious_compartment}_does_not_reach_r")

    for compartment in compartments:
        degree = sum(1 for source, target in edges if source == compartment or target == compartment)
        if degree == 0:
            return ValidationResult(False, f"isolated_compartment_{compartment}")

    if spec.observation_map == "I+H" and "H" not in compartments:
        return ValidationResult(False, "observation_map_requires_h")
    if spec.observation_map not in {"I", "I+H"}:
        return ValidationResult(False, "invalid_observation_map")

    return ValidationResult(True, "ok")


def generate_neighbors(spec: StructureSpec) -> list[StructureSpec]:
    """Generate 1-hop neighbors under the constrained edit grammar."""
    neighbors: set[StructureSpec] = set()

    neighbors.add(
        StructureSpec(
            structure_name=spec.structure_name,
            fractional=not spec.fractional,
            observation_map=spec.observation_map,
        )
    )

    if spec.structure_name == "SEIR":
        neighbors.update(
            {
                StructureSpec("SIR", spec.fractional, "I"),
                StructureSpec("SEIRS", spec.fractional, "I"),
                StructureSpec("SEIHR", spec.fractional, "I"),
                StructureSpec("SEIAR", spec.fractional, "I"),
            }
        )
    elif spec.structure_name == "SIR":
        neighbors.add(StructureSpec("SEIR", spec.fractional, "I"))
    elif spec.structure_name == "SEIRS":
        neighbors.add(StructureSpec("SEIR", spec.fractional, "I"))
    elif spec.structure_name == "SEIHR":
        neighbors.add(StructureSpec("SEIR", spec.fractional, "I"))
        alternate = "I+H" if spec.observation_map == "I" else "I"
        neighbors.add(StructureSpec("SEIHR", spec.fractional, alternate))
    elif spec.structure_name == "SEIAR":
        neighbors.add(StructureSpec("SEIR", spec.fractional, "I"))

    valid_neighbors = [neighbor for neighbor in neighbors if validate_structure(neighbor).valid]
    return sorted(valid_neighbors, key=lambda candidate: candidate.spec_key)
