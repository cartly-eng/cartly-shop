import ast
import pathlib


def _tax_table():
    src = pathlib.Path(__file__).parents[1].joinpath("shop/roles/checkout.py").read_text()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "TAX_TABLE_V2":
            return ast.literal_eval(node.value)
    return {}


def test_every_catalog_currency_has_a_tax_rate():
    assert {"USD", "INR", "GBP", "EUR"} <= set(_tax_table())
