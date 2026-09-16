"""
AfferentBus — D0/PR0 topology only.

Sees physical device ids. Parks or reserves identity. Never Stimulus.
Not a Sensor. Virtual never rides this bus.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Set

import yaml


APPROVED = frozenset({"human", "hi", "auto_return"})
DISPOSITIONS = frozenset(
    {"parked_unmapped", "parked_site_occupied", "reserved"}
)


class DeviceEnumerator(Protocol):
    def enumerate(self) -> List[str]:
        ...


class FakeDeviceEnumerator:
    """In-process probe. Opaque device_id strings. Not I2C-only."""

    def __init__(self, present: Optional[List[str]] = None) -> None:
        self.present: List[str] = list(present or [])

    def enumerate(self) -> List[str]:
        return list(self.present)


class FixturePadBus:
    """PR1 fixture: unit [0, 1] already. Same read_all() shape as Pad-Read. Not a chip."""

    def __init__(
        self,
        device_id: str,
        enumerator: DeviceEnumerator,
        unit: float = 0.0,
    ) -> None:
        self.device_id = str(device_id)
        self.enumerator = enumerator
        self.unit = float(unit)

    @property
    def connected(self) -> bool:
        try:
            return self.device_id in set(self.enumerator.enumerate() or [])
        except Exception:
            return False

    def read_all(self) -> Dict[str, Any]:
        u = max(0.0, min(1.0, float(self.unit)))
        return {"fsr": [u, 0.0, 0.0, 0.0]}


@dataclass
class MapEntry:
    device_id: str
    organ_class: Optional[str] = None
    stub_id: Optional[str] = None
    body_site: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    notes: str = ""

    @classmethod
    def from_dict(cls, raw: MappingLike) -> Optional["MapEntry"]:
        if not isinstance(raw, dict):
            return None
        did = str(raw.get("device_id") or "").strip()
        if not did:
            return None
        return cls(
            device_id=did,
            organ_class=_opt_str(raw.get("organ_class")),
            stub_id=_opt_str(raw.get("stub_id")),
            body_site=_opt_str(raw.get("body_site")),
            approved_by=_opt_str(raw.get("approved_by")),
            approved_at=_opt_str(raw.get("approved_at")),
            notes=str(raw.get("notes") or ""),
        )


MappingLike = Dict[str, Any]


def _opt_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


@dataclass
class TopologyEvent:
    kind: str
    device_id: str
    claimed_type: Optional[str] = None
    disposition: Optional[str] = None
    body_site: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "device_id": self.device_id,
            "claimed_type": self.claimed_type,
            "disposition": self.disposition,
            "body_site": self.body_site,
        }


def load_organ_map(path: Optional[Path], *, fail_open: bool = True) -> List[MapEntry]:
    if path is None:
        return []
    try:
        if not path.is_file():
            return []
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        raw_entries = data.get("entries") or []
        if not isinstance(raw_entries, list):
            return []
        out: List[MapEntry] = []
        for row in raw_entries:
            ent = MapEntry.from_dict(row)
            if ent is not None:
                out.append(ent)
        return out
    except Exception:
        if not fail_open:
            raise
        return []


class AfferentBus:
    """Topology watcher. poll() returns events, never Stimulus."""

    def __init__(
        self,
        map_path: Optional[str | Path] = None,
        enumerator: Optional[DeviceEnumerator] = None,
        fail_open: bool = True,
        log: Optional[Callable[[TopologyEvent], None]] = None,
    ) -> None:
        self.map_path = Path(map_path) if map_path else None
        self.enumerator = enumerator or FakeDeviceEnumerator()
        self.fail_open = bool(fail_open)
        self._log = log
        self.entries: List[MapEntry] = []
        self.events: List[TopologyEvent] = []
        self._seen: Set[str] = set()
        self._reserved: Dict[str, str] = {}  # device_id -> body_site
        self._disp: Dict[str, str] = {}  # device_id -> last disposition
        self.fixture_units: Dict[str, float] = {}
        self._reload_map()

    def _reload_map(self) -> None:
        self.entries = load_organ_map(self.map_path, fail_open=self.fail_open)

    def entry_for(self, device_id: str) -> Optional[MapEntry]:
        for e in self.entries:
            if e.device_id == device_id:
                return e
        return None

    def site_holder(self, body_site: str) -> Optional[str]:
        for did, site in self._reserved.items():
            if site == body_site:
                return did
        return None

    def _emit(self, ev: TopologyEvent) -> TopologyEvent:
        self.events.append(ev)
        if self._log is not None:
            try:
                self._log(ev)
            except Exception:
                if not self.fail_open:
                    raise
        return ev

    def _dispose(self, device_id: str) -> tuple[str, Optional[str]]:
        ent = self.entry_for(device_id)
        if ent is None:
            return "parked_unmapped", None
        site = ent.body_site
        if not site:
            # Mapped but no site: still identity-only reserve without occupying a site
            self._reserved[device_id] = ""
            return "reserved", None
        holder = self.site_holder(site)
        if holder is not None and holder != device_id:
            return "parked_site_occupied", site
        # auto_return / human / hi: map row exists → reserved if site free or we already hold it
        self._reserved[device_id] = site
        return "reserved", site

    def poll(self) -> List[TopologyEvent]:
        """Compare enumerator to last seen. Identity only. Never Stimulus."""
        try:
            now = {str(x) for x in (self.enumerator.enumerate() or []) if str(x).strip()}
        except Exception:
            if not self.fail_open:
                raise
            now = set()
        out: List[TopologyEvent] = []
        appeared = now - self._seen
        gone = self._seen - now
        stayed = now & self._seen
        for did in sorted(appeared):
            disp, site = self._dispose(did)
            self._disp[did] = disp
            out.append(
                self._emit(
                    TopologyEvent(
                        kind="appeared",
                        device_id=did,
                        disposition=disp,
                        body_site=site,
                    )
                )
            )
        for did in sorted(stayed):
            ent = self.entry_for(did)
            site = self._reserved.get(did) or (ent.body_site if ent else None)
            out.append(
                self._emit(
                    TopologyEvent(
                        kind="heartbeat_ok",
                        device_id=did,
                        disposition=self._disp.get(did),
                        body_site=site if site else None,
                    )
                )
            )
        for did in sorted(gone):
            ent = self.entry_for(did)
            site = self._reserved.pop(did, None) or (ent.body_site if ent else None)
            self._disp.pop(did, None)
            out.append(
                self._emit(
                    TopologyEvent(
                        kind="heartbeat_lost",
                        device_id=did,
                        body_site=site if site else None,
                    )
                )
            )
            out.append(
                self._emit(
                    TopologyEvent(
                        kind="gone",
                        device_id=did,
                        body_site=site if site else None,
                    )
                )
            )
        self._seen = now
        return out

    def site_map_owned(self, body_site: str) -> bool:
        """Human/HI approved row owns this site, whether or not the device is present."""
        site = str(body_site or "")
        if not site:
            return False
        for e in self.entries:
            if e.body_site == site and (e.approved_by or "") in ("human", "hi"):
                return True
        return False

    def wrap_reader(self, stub_id: str = "hardware_pad") -> Optional[FixturePadBus]:
        """PR1 wrap: existing seat backend when map-owned device is present. Never Sensation."""
        want = str(stub_id or "hardware_pad")
        for did, site in self._reserved.items():
            ent = self.entry_for(did)
            if ent is None:
                continue
            if (ent.stub_id or "") != want:
                continue
            if (ent.organ_class or "") != "touch":
                continue
            if (ent.approved_by or "") not in ("human", "hi"):
                continue
            if did not in self._seen:
                continue
            unit = float(self.fixture_units.get(did, 0.0))
            return FixturePadBus(did, self.enumerator, unit=unit)
        return None
