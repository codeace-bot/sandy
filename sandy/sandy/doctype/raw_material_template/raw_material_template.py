import frappe
from frappe.model.document import Document
from frappe.utils import flt

class RawMaterialTemplate(Document):
	pass

@frappe.whitelist()
def get_item_rate_for_bom(item_code, qty=1):
    """
    Fetch item rate using fallback logic:
    Valuation Rate -> Price List Rate -> Last Purchase Rate -> 0
    """
    from frappe.utils import flt
    qty = flt(qty)
    rate = 0

    # 1. Try Valuation Rate
    item = frappe.get_doc("Item", item_code)
    if item.valuation_rate:
        rate = item.valuation_rate
    else:
        # 2. Try Price List Rate
        price_list_rate = frappe.get_value(
            "Item Price",
            {"item_code": item_code, "price_list": "Standard Buying"},
            "price_list_rate"
        )
        if price_list_rate:
            rate = price_list_rate
        else:
            # 3. Try Last Purchase Rate
            last_purchase_rate = frappe.get_value("Item", item_code, "last_purchase_rate")
            if last_purchase_rate:
                rate = last_purchase_rate
            else:
                rate = 0  # fallback

    return flt(rate)


@frappe.whitelist()
def get_item_details_for_bom(item_code, bom_no=None, company=None, qty=1):
    from frappe.utils import flt
    item = frappe.get_doc("Item", item_code)

    # Fetch rate using fallback logic
    rate = item.valuation_rate or \
           frappe.get_value("Item Price", {"item_code": item_code, "price_list": "Standard Buying"}, "price_list_rate") or \
           frappe.get_value("Item", item_code, "last_purchase_rate") or 0

    amount = flt(rate) * flt(qty)

    return {
        "item_name": item.item_name,
        "description": item.description or item.item_name,
        "stock_uom": item.stock_uom,
        "uom": item.stock_uom,
        "conversion_factor": 1,
        "rate": rate,
        "amount": amount
    }