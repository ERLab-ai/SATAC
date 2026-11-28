"""P0 reference contract: inclusive astronomical years; not a production API."""
from dataclasses import dataclass
from enum import Enum


class Match(str, Enum):
    NONE = 'none'
    POSSIBLE = 'possible'
    CERTAIN = 'certain'
    UNDATED = 'undated'


@dataclass(frozen=True)
class Bound:
    kind: str
    low: int | None = None
    high: int | None = None

    def __post_init__(self):
        if self.kind == 'bounded':
            if type(self.low) is not int or type(self.high) is not int or self.low > self.high:
                raise ValueError('bounded endpoints require ordered integer years')
        elif self.kind not in ('open', 'unknown') or self.low is not None or self.high is not None:
            raise ValueError('open/unknown endpoints have no numeric bounds')

    def limits(self, start: bool):
        if self.kind == 'bounded':
            return self.low, self.high
        if self.kind == 'open':
            infinity = float('-inf') if start else float('inf')
            return infinity, infinity
        return float('-inf'), float('inf')


@dataclass(frozen=True)
class Extent:
    start: Bound
    end: Bound
    original_text: str
    calendar: str
    precision: str
    normalization_method: str

    def __post_init__(self):
        for value in (self.original_text, self.calendar, self.precision, self.normalization_method):
            if not isinstance(value, str) or not value.strip():
                raise ValueError('original dating metadata required')
        if self.start.limits(True)[0] > self.end.limits(False)[1]:
            raise ValueError('no feasible chronological ordering')

    def overlap(self, first: int, last: int) -> Match:
        if type(first) is not int or type(last) is not int or first > last:
            raise ValueError('query requires ordered integer years')
        if self.start.kind == self.end.kind == 'unknown':
            return Match.UNDATED
        sl, sh = self.start.limits(True)
        el, eh = self.end.limits(False)
        if sl > last or eh < first:
            return Match.NONE
        # Unknown endpoints are never presented as certain, even when constraints imply overlap.
        if 'unknown' not in (self.start.kind, self.end.kind) and min(sh, eh) <= last and max(el, sl) >= first:
            return Match.CERTAIN
        return Match.POSSIBLE

    def as_of(self, year: int) -> Match:
        return self.overlap(year, year)


def historical_year(year: int, era: str) -> int:
    if type(year) is not int or year <= 0 or era not in ('BCE', 'CE'):
        raise ValueError('historical display requires positive BCE/CE year')
    return 1 - year if era == 'BCE' else year


def display_year(year: int) -> tuple[int, str]:
    if type(year) is not int:
        raise ValueError('astronomical integer year required')
    return (1 - year, 'BCE') if year <= 0 else (year, 'CE')
