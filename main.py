import argparse
from itertools import groupby

from kaspi.types import Transaction, Box, TableFinder
from kaspi.utils import parse_date, parse_amount
from pdfminer.layout import LAParams, LTRect, LTTextBoxHorizontal
from pdfminer.high_level import extract_pages





def find_tables(elements):
    added = set()
    tf = TableFinder()

    for element in elements:
        if isinstance(element, LTRect):
            key = str(element.bbox)
            if key not in added:
                tf.add_bbox(element)
                added.add(key)

    tf.sort_tables()
    return tf


def fill_values(tf, elements):
    for element in elements:
        if isinstance(element, LTTextBoxHorizontal):
            text = element.get_text().strip()
            for table in tf.tables:
                b = Box(*element.bbox)
                if table.b.contains(b):
                    for cell in table.cells:
                        if cell.b.overlaps(b):
                            cell.contents += text
                            break
                    break


def process_page(page_layout):
    raw_data = []
    elements = list(page_layout)
    tf = find_tables(elements)
    fill_values(tf, elements)
    table = tf.tables[-1]
    for _, group in groupby(table.cells, lambda cell: cell.row):
        row = list(group)
        sdate, samount, kind, description, *tail = map(lambda o: o.contents, row)
        raw_data.append([sdate, samount, kind, description])
    return raw_data


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_file")
    parser.add_argument("tsv_file")
    return parser.parse_args()

def main():
    args = parse_args()
    pages = list(extract_pages(args.pdf_file, laparams=LAParams()))
    raw_data = []
    for page_layout in pages:
        raw_data.extend(process_page(page_layout))

    data = []
    for sdate, samount, kind, _ in raw_data[1:]:
        kind, description = kind.split("       ")
        data.append(
            Transaction(
                tx_date=parse_date(sdate),
                amount=parse_amount(samount),
                kind=kind,
                description=description,
            )
        )
    received = [d for d in data if d.kind == "Deposit received"]
    with open(args.tsv_file, "w") as out_file:
        for d in received:
            print(f"{d.tx_date}\t{d.amount}", file=out_file)


if __name__ == '__main__':
    main()