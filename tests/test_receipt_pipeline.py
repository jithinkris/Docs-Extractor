import json
import unittest
from unittest.mock import patch

from app.pipeline import run_pipeline
from app.schemas import Invoice


RECEIPT_TEXT = """THE NEST RESTAURANT

Swamy Vivekananda Road,
Prashanth Layout, Whitefield,
Mob!8281361601
mae
Name:

LSE

i OS A

Date. 03/10/26 Dine In: 3
23:01 sig
Cashier: biller Bill No.: 14680
LAO
Item Oty. Price Amount
a7 as
Kerala Porotta 5 20.00 100.00
Chicken Bba 1180.00 180.0
Ai-faham (qtr) 1\u00b0150.00 150.00
LADUE R LBBB
Total Oty: 7 SubTotal 430.00
Grand Total * 430.00
Paid va UPI
veo TANK YOU...

a

"""

EXTRACTED_RECEIPT = {
    "vendor_name": "THE NEST RESTAURANT",
    "invoice_number": "14680",
    "invoice_date": "2026-10-03",
    "due_date": None,
    "currency": None,
    "line_items": [
        {"description": "Kerala Porotta", "quantity": 5, "unit_price": 20, "amount": 100},
        {"description": "Chicken Bba", "quantity": 1, "unit_price": 180, "amount": 180},
        {"description": "Ai-faham (qtr)", "quantity": 1, "unit_price": 150, "amount": 150},
    ],
    "subtotal": 430,
    "tax": None,
    "total": 430,
}


class ReceiptPipelineTests(unittest.TestCase):
    def test_receipt_fields_missing_from_document_can_remain_empty(self):
        invoice = Invoice.model_validate_json(
            '{"vendor_name":"Shop","subtotal":"8.50","total":"8.50"}'
        )

        self.assertIsNone(invoice.invoice_number)
        self.assertIsNone(invoice.invoice_date)
        self.assertIsNone(invoice.currency)
        self.assertEqual(invoice.line_items, [])

    @patch("app.llm._ask", return_value=json.dumps(EXTRACTED_RECEIPT))
    @patch("app.llm.classify", return_value="receipt")
    @patch(
        "app.processing.extract_text",
        return_value=(RECEIPT_TEXT, 0.70, []),
    )
    def test_receipt_is_extracted_instead_of_marked_unsupported(
        self, _extract_text, _classify, ask
    ):
        record = run_pipeline(b"image bytes", "bill.jpg")

        _extract_text.assert_called_once_with(b"image bytes", "bill.jpg")
        _classify.assert_called_once_with(RECEIPT_TEXT)
        self.assertEqual(record["doc_type"], "receipt")
        self.assertEqual(record["data"]["vendor_name"], "THE NEST RESTAURANT")
        self.assertEqual(record["data"]["invoice_number"], "14680")
        self.assertEqual(record["data"]["total"], "430")
        self.assertEqual(len(record["data"]["line_items"]), 3)
        self.assertNotIn("unsupported_doc_type", record["quality"]["flags"])
        self.assertIn("bill/receipt number", ask.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
