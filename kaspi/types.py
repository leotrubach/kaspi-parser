import dataclasses
import datetime
from decimal import Decimal
from itertools import groupby
from typing import NamedTuple, List

from pdfminer.layout import LTRect


class Period(NamedTuple):
    start_date: datetime.date
    end_date: datetime.date


class Transaction(NamedTuple):
    tx_date: datetime.date
    amount: Decimal
    kind: str
    description: str


class Box(NamedTuple):
    x1: float
    y1: float
    x2: float
    y2: float

    def contains(self, b: 'Box'):
        return self.x1 <= b.x1 and self.y1 <= b.y1 and self.x2 >= b.x2 and self.y2 >= b.y2

    def overlaps(self, b: "Box"):
        return not(
            self.x1 > b.x2 or
            self.x2 < b.x1 or
            self.y1 > b.y2 or
            self.y2 < b.y1
        )

    def intersection_area(self, b: "Box"):
        dx = max(0.0, min(self.x2, b.x2) - max(self.x1, b.x1))
        dy = max(0.0, min(self.y2, b.y2) - max(self.x1, b.x1))
        return dx * dy

    def merge(self, b: 'Box'):
        return Box(
            min(b.x1, self.x1),
            min(b.y1, self.y1),
            max(b.x2, self.x2),
            max(b.y2, self.y2),
        )


@dataclasses.dataclass
class Cell:
    b: Box
    row: int | None = None
    column: int | None = None
    contents: str = ""

    @property
    def c(self):
        return -self.b.y1, self.b.x1


class Table:
    def __init__(self, cells: List[Cell]=None, b: Box=None):
        self.cells: List[Cell] = cells if cells else []
        self.b: Box = b

    def __repr__(self):
        return f"Table({self.b.x1},{self.b.y1},{self.b.x2},{self.b.y2})"

    def can_add(self, e: LTRect):
        b = Box(*e.bbox)
        if self.b.x1 - b.x2 > 1:
            return False
        if b.x1 - self.b.x2 > 1:
            return False
        if self.b.y1 - b.y2 > 1:
            return False
        if b.y1 - self.b.y2 > 1:
            return False
        return True

    def sort(self):
        self.cells.sort(key=lambda cell: cell.c)
        for row, (_, group) in enumerate(groupby(self.cells, key=lambda cell: cell.b.y1)):
            for column, cell in enumerate(group):
                cell.column = column
                cell.row = row

    def add_element(self, e: LTRect):
        b = Box(*e.bbox)
        if not self.cells:
            self.b = Box(*b)
        else:
            self.b = self.b.merge(b)
        self.cells.append(Cell(b=b))


class TableFinder:
    def __init__(self):
        self.tables: List[Table] = []

    def can_merge(self, g1: Table, g2: Table):
        if g1.b.x1 - g2.b.x2 > 1:
            return False
        if g2.b.x1 - g1.b.x2 > 1:
            return False
        if g1.b.y1 - g2.b.y2 > 1:
            return False
        if g2.b.y1 - g1.b.y1 > 1:
            return False
        return True

    def merge(self, g1: Table, g2: Table) -> Table:
        return Table(
            cells=[*g1.cells, *g2.cells],
            b=g1.b.merge(g2.b)
        )

    def sort_tables(self):
        for g in self.tables:
            g.sort()

    def check_and_merge_groups(self, j):
        other_groups = [*self.tables[:j], *self.tables[j + 1:]]
        group = self.tables[j]
        for i, g in enumerate(other_groups):
            if self.can_merge(g, group):
                new_group = self.merge(g, group)
                self.tables[i] = new_group
                break

    def add_bbox(self, e: LTRect):
        for i, group in enumerate(self.tables):
            if group.can_add(e):
                group.add_element(e)
                self.check_and_merge_groups(i)
                break
        else:
            bg = Table()
            bg.add_element(e)
            self.tables.append(bg)
