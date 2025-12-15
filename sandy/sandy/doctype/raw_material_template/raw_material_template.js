frappe.ui.form.on('Raw Material Template', {
    refresh(frm) { }
});

frappe.ui.form.on('BOM Item', {
    item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.item_code) return;

        // STEP 1: Fetch basic item details
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Item",
                name: row.item_code
            },
            callback(r) {
                if (!r.message) return;

                let item = r.message;

                frappe.model.set_value(cdt, cdn, "item_name", item.item_name);
                frappe.model.set_value(cdt, cdn, "description", item.description || item.item_name);
                frappe.model.set_value(cdt, cdn, "stock_uom", item.stock_uom);
                frappe.model.set_value(cdt, cdn, "uom", item.stock_uom);
                frappe.model.set_value(cdt, cdn, "conversion_factor", 1);

                if (!row.qty) {
                    frappe.model.set_value(cdt, cdn, "qty", 1);
                }

                // STEP 2: Fetch rate based on BOM's Rate of Materials setting
                frappe.call({
                    method: "sandy.sandy.doctype.raw_material_template.raw_material_template.get_item_rate_for_bom",
                    args: {
                        item_code: row.item_code,
                        qty: row.qty || 1
                    },
                    callback(r) {
                        let rate = r.message || 0;
                        frappe.model.set_value(cdt, cdn, "rate", rate);
                        frappe.model.set_value(cdt, cdn, "amount", flt(rate) * flt(row.qty || 1));
                    }
                });
            }
        });
    },

    // Recalculate amount if qty or rate changes
    qty(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
    },

    rate(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
    }
});
