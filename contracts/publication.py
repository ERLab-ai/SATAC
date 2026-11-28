"""P0 executable policy reference, in memory; not an authenticated API or database."""
from dataclasses import dataclass, replace, asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Optional

REGISTRY = json.loads((Path(__file__).resolve().parents[1] / "ontology/predicates.json").read_text())
REVIEW_STATES = {"unreviewed", "review_required", "disputed"}


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Reference:
    source_version_id: str
    locator: Optional[str] = None


@dataclass(frozen=True)
class Claim:
    claim_id: str
    version_id: str
    subject_id: str
    predicate: str
    object_id: str
    verification_status: str = "unreviewed"
    epistemic_status: str = "uncertain"
    references: tuple[Reference, ...] = ()
    scientific_note: Optional[str] = None
    justification: Optional[str] = None
    synthetic: bool = False
    restricted: bool = False
    correction_status: str = "none"
    conflict_group_id: Optional[str] = None


@dataclass(frozen=True)
class Release:
    release_id: str
    members: tuple[str, ...]
    manifest_sha256: str


@dataclass(frozen=True)
class Correction:
    previous: Claim
    replacement: Claim
    reason: str
    basis: str
    actor: str
    recorded_at: str


class PolicyStore:
    """Role strings simulate a trusted service boundary; they are NOT authentication."""

    def __init__(self, entities, sources):
        self._entities = dict(entities)
        self._sources = dict(sources)  # only public bibliographic titles; never raw sources
        if any(not nonblank(k) or v not in REGISTRY["entity_types"] for k, v in self._entities.items()):
            raise ValueError("invalid entity catalog")
        if any(not nonblank(k) or not nonblank(v) for k, v in self._sources.items()):
            raise ValueError("invalid source catalog")
        self._versions = {}
        self._latest = {}
        self._releases = {}
        self._suppressed = set()
        self._corrections = []
        self._tasks = {}
        self._current = None

    def _validate(self, c):
        if not isinstance(c, Claim) or not all(nonblank(v) for v in (c.claim_id, c.version_id, c.subject_id, c.predicate, c.object_id)):
            raise ValueError("invalid claim identity")
        rule = REGISTRY["predicates"].get(c.predicate)
        if rule is None or c.subject_id not in self._entities or c.object_id not in self._entities:
            raise ValueError("unknown predicate or entity")
        for entity, side in ((c.subject_id, "domain"), (c.object_id, "range")):
            if "*" not in rule[side] and self._entities[entity] not in rule[side]:
                raise ValueError("invalid relation types")
        if rule.get("requires_justification") and not nonblank(c.justification):
            raise ValueError("influence requires justification")
        for field in ("verification_status", "epistemic_status", "correction_status"):
            if getattr(c, field) not in REGISTRY[field]:
                raise ValueError("invalid " + field)
        if type(c.synthetic) is not bool or type(c.restricted) is not bool:
            raise ValueError("invalid visibility")
        if not isinstance(c.references, tuple) or any(not isinstance(r, Reference) or r.source_version_id not in self._sources or (r.locator is not None and not nonblank(r.locator)) for r in c.references):
            raise ValueError("invalid source reference")
        if c.conflict_group_id is not None and not nonblank(c.conflict_group_id):
            raise ValueError("invalid conflict group")
        if any(v is not None and not nonblank(v) for v in (c.scientific_note, c.justification)):
            raise ValueError("invalid text")

    def _followup(self, c):
        reasons = set()
        if not c.references or any(r.locator is None for r in c.references):
            reasons.add("documentation")
        if c.verification_status in REVIEW_STATES:
            reasons.add("review")
        if c.verification_status == "known_incorrect" or c.correction_status == "pending":
            reasons.add("correction")
        self._tasks[c.version_id] = frozenset(reasons)

    def stage(self, c):
        self._validate(c)
        if c.version_id in self._versions or c.claim_id in self._latest:
            raise ValueError("existing claim: use correction or revision")
        self._versions[c.version_id] = c
        self._latest[c.claim_id] = c.version_id
        self._followup(c)

    def tasks(self, *, role):
        self._require(role, "curator")
        return {v: tuple(sorted(self._tasks[v])) for v in self._latest.values() if self._tasks[v]}

    @staticmethod
    def _require(role, expected):
        if role != expected:
            raise PermissionError("service role required")

    def _eligible(self, c):
        return not (c.synthetic or c.restricted or c.verification_status == "known_incorrect" or c.version_id in self._suppressed)

    def _projection(self, c):
        result = {"claim_id": c.claim_id, "version_id": c.version_id, "subject_id": c.subject_id,
                  "predicate": c.predicate, "object_id": c.object_id}
        if c.conflict_group_id is not None:
            result["conflict_group_id"] = c.conflict_group_id
        if c.scientific_note is not None:
            result["scientific_note"] = c.scientific_note
        if c.references:
            result["references"] = [
                dict(source_version_id=r.source_version_id, title=self._sources[r.source_version_id],
                     **({"locator": r.locator} if r.locator is not None else {}))
                for r in c.references]
        return result

    def publish(self, release_id, members, *, role):
        self._require(role, "publication_service")
        if not nonblank(release_id) or release_id in self._releases:
            raise ValueError("invalid or reused release ID")
        ids = tuple(sorted(members))
        if len(set(ids)) != len(ids) or any(v not in self._versions for v in ids):
            raise ValueError("invalid release membership")
        records = [self._versions[v] for v in ids]
        if len({c.claim_id for c in records}) != len(records):
            raise ValueError("multiple versions of one claim")
        if any(not self._eligible(c) or self._latest[c.claim_id] != c.version_id for c in records):
            raise ValueError("ineligible or superseded member")
        # Explicit editorial groups only; coincident subject/predicate is not evidence of conflict.
        groups = {}
        for c in records:
            if c.conflict_group_id is not None:
                scope = (c.subject_id, c.predicate)
                if groups.setdefault(c.conflict_group_id, scope) != scope:
                    raise ValueError("conflict group mixes subjects or predicates")
        release = Release(release_id, ids, digest([self._projection(c) for c in records]))
        self._releases[release_id] = release
        self._current = release_id
        return release

    def read(self, release_id=None):
        release = self._releases[release_id if release_id is not None else self._current]
        return {"release_id": release.release_id, "claims": [
            self._projection(self._versions[v]) for v in release.members if self._eligible(self._versions[v])
        ]}

    def read_conflicts(self, release_id=None):
        """Release-scoped alternatives, using only the currently public projection.

        Group IDs are explicitly assigned in staging, not inferred from differing
        values or review status. A group with fewer than two visible claims is
        not presented as a conflict. No winner, confidence score, or merging.
        """
        public = self.read(release_id)
        groups = {}
        for claim in public["claims"]:
            group = claim.get("conflict_group_id")
            if group is not None:
                groups.setdefault(group, []).append(claim)
        return {"release_id": public["release_id"], "conflicts": [
            {"group_id": group, "alternatives": claims}
            for group, claims in sorted(groups.items()) if len(claims) >= 2
        ]}

    def manifest(self, release_id, *, role):
        self._require(role, "curator")
        return self._releases[release_id]

    def flag_incorrect(self, version_id, *, role):
        self._require(role, "curator")
        if version_id not in self._versions:
            raise ValueError("unknown version")
        self._suppressed.add(version_id)
        self._tasks[version_id] = self._tasks[version_id] | {"correction"}

    def correct(self, version_id, replacement, *, reason, basis, actor, role, release_id=None):
        self._require(role, "publication_service")
        old = self._versions[version_id]
        self._validate(replacement)
        if (self._latest[old.claim_id] != version_id or replacement.claim_id != old.claim_id
                or replacement.version_id in self._versions or not all(nonblank(v) for v in (reason, basis, actor))
                or replacement.verification_status == "known_incorrect" or replacement.synthetic != old.synthetic
                or replacement.restricted != old.restricted):
            raise ValueError("invalid or unsubstantiated correction")
        new = replace(replacement, correction_status="corrected")
        if (old.subject_id, old.predicate, old.object_id) == (new.subject_id, new.predicate, new.object_id):
            raise ValueError("no corrected relation value")
        # Check all foreseeable failures before changing the store.
        current = self._releases.get(self._current)
        active = current is not None and version_id in current.members
        if active:
            if not nonblank(release_id) or release_id in self._releases or not self._eligible(new):
                raise ValueError("eligible replacement and fresh release ID required")
            members = tuple(new.version_id if v == version_id else v for v in current.members
                            if v == version_id or self._eligible(self._versions[v]))
            if any(v != new.version_id and self._latest[self._versions[v].claim_id] != v for v in members):
                raise ValueError("current release contains another superseded record")
        elif release_id is not None:
            raise ValueError("release ID only for active published correction")
        if active and new.conflict_group_id is not None:
            for member in members:
                if member == new.version_id:
                    continue
                other = self._versions[member]
                if (other.conflict_group_id == new.conflict_group_id and
                        (other.subject_id, other.predicate) != (new.subject_id, new.predicate)):
                    raise ValueError("conflict group mixes subjects or predicates")
        self._versions[new.version_id] = new
        self._latest[new.claim_id] = new.version_id
        self._suppressed.add(version_id)
        self._followup(new)
        self._corrections.append(Correction(old, new, reason, basis, actor, datetime.now(timezone.utc).isoformat()))
        return self.publish(release_id, members, role=role) if active else new

    def correction_log(self, *, role):
        self._require(role, "curator")
        return tuple(self._corrections)
