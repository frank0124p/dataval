#!/usr/bin/env python3
"""Every declarative checking verb gets one passing and one failing example."""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval.model import Column, Table
from dataval.skills.markdown_skill import _eval, _parse_check, _table_matches


def c(name: str, raw: str = "String", base: str = "string", *,
      nullable: bool = False, comment: str | None = "ok") -> Column:
    return Column(name=name, raw_type=raw, base_type=base,
                  nullable=nullable, comment=comment)


def t(name: str = "good_table", columns: list[Column] | None = None, **kwargs) -> Table:
    return Table(name=name, columns=columns or [], **kwargs)


class CheckingVerbTest(unittest.TestCase):
    def assert_verb(self, line: str, good: Table, bad: Table,
                    glossary: dict | None = None):
        with self.subTest(line=line):
            applies, requires, unparsed = _parse_check([line])
            self.assertEqual({}, applies)
            self.assertEqual([], unparsed)
            self.assertEqual(1, len(requires))
            good_ok, good_detail = _eval(good, requires[0], glossary)
            bad_ok, bad_detail = _eval(bad, requires[0], glossary)
            self.assertTrue(good_ok, good_detail)
            self.assertFalse(bad_ok, line)
            self.assertTrue(bad_detail.get("msg"), line)

    def test_all_require_verbs(self):
        glossary = {
            "banned_terms": {"cust": "customer"},
            "aliases": {"client": "customer"},
            "standard_terms": ["customer", "email"],
        }
        cases = [
            ("require: has_column id",
             t(columns=[c("id")]), t()),
            ("require: column_type amount decimal",
             t(columns=[c("amount", "Decimal(18,2)", "decimal")]),
             t(columns=[c("amount", "Float64", "float")])),
            ("require: not_nullable id",
             t(columns=[c("id")]), t(columns=[c("id", nullable=True)])),
            ("require: columns_not_both email amount",
             t(columns=[c("email")]), t(columns=[c("email"), c("amount")])),
            ("require: name_matches BadName [a-z_]+",
             t(), t(columns=[c("BadName")])),
            ("require: column_commented id",
             t(columns=[c("id")]), t(columns=[c("id", comment=None)])),
            ("require: all_columns_commented",
             t(columns=[c("id")]), t(columns=[c("id", comment=None)])),
            ("require: has_primary_key",
             t(columns=[c("id")], primary_key=["id"]),
             t(columns=[c("id")], sorting_key=["id"])),
            ("require: has_business_key",
             t(columns=[c("customer_id")], business_key=["customer_id"]),
             t(columns=[c("customer_id")], sorting_key=["customer_id"])),
            ("require: has_order_by",
             t(columns=[c("id")], sorting_key=["id"]), t(columns=[c("id")])),
            ("require: no_nullable_in_key",
             t(columns=[c("id")], sorting_key=["id"]),
             t(columns=[c("id", nullable=True)], sorting_key=["id"])),
            ("require: engine_matches MergeTree",
             t(engine="ReplacingMergeTree"), t(engine="Log")),
            ("require: table_name_matches [a-z_]+",
             t(name="good_table"), t(name="BadTable")),
            ("require: type_not_used Float",
             t(columns=[c("value", "Decimal(9,2)", "decimal")]),
             t(columns=[c("value", "Float64", "float")])),
            ("require: lowcardinality_when_present status",
             t(columns=[c("status", "LowCardinality(String)")]),
             t(columns=[c("status", "String")])),
            ("require: no_banned_term",
             t(columns=[c("customer_name")]), t(columns=[c("cust_name")]), glossary),
            ("require: no_alias_term",
             t(columns=[c("customer_name")]), t(columns=[c("client_name")]), glossary),
            ("require: term_in_glossary",
             t(columns=[c("customer_email")]), t(columns=[c("mystery_value")]), glossary),
            ("require: all_columns_name_match [a-z][a-z0-9_]*",
             t(columns=[c("good_name")]), t(columns=[c("BadName")])),
            ("require: type_not_for_matching .*(amount|price).* float",
             t(columns=[c("amount", "Decimal(18,2)", "decimal")]),
             t(columns=[c("amount", "Float64", "float")])),
            ("require: datetime_with_timezone",
             t(columns=[c("created_at", "DateTime('UTC')", "datetime")]),
             t(columns=[c("created_at", "DateTime", "datetime", comment=None)])),
            ("require: identifier_max_length 10",
             t(name="short", columns=[c("id")]), t(name="this_name_is_too_long")),
            ("require: pk_ends_with _id",
             t(columns=[c("customer_id")], business_key=["customer_id"]),
             t(columns=[c("customer_key")], business_key=["customer_key"])),
            ("require: columns_not_named select,from,where",
             t(columns=[c("customer_id")]), t(columns=[c("select")])),
        ]
        for case in cases:
            self.assert_verb(*case)

    def test_applies_to_verbs(self):
        applies, requires, unparsed = _parse_check([
            'applies_to: name_matches ".*customer.*"',
            "require: has_column customer_id",
        ])
        self.assertFalse(unparsed)
        self.assertTrue(_table_matches(t(name="dim_customer"), applies))
        self.assertFalse(_table_matches(t(name="dim_product"), applies))
        self.assertEqual(1, len(requires))

        applies, _, unparsed = _parse_check(["applies_to: has_column customer_id"])
        self.assertFalse(unparsed)
        self.assertTrue(_table_matches(t(columns=[c("customer_id")]), applies))
        self.assertFalse(_table_matches(t(columns=[c("product_id")]), applies))


if __name__ == "__main__":
    unittest.main()
