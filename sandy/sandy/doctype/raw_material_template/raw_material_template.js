
frappe.ui.form.on('Raw Material Template', {
    refresh: function(frm) {
        // nothing needed here
    }
});

frappe.ui.form.on('BOM Item', {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.item_code) return;

        // Fetch Item Details (UOM, Description)
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Item",
                name: row.item_code
            },
            callback: function(r) {
                if (r.message) {
                    frappe.model.set_value(cdt, cdn, "uom", r.message.stock_uom);
                    frappe.model.set_value(cdt, cdn, "description", r.message.description || r.message.item_name);

                    if (!row.qty) {
                        frappe.model.set_value(cdt, cdn, "qty", 1);
                    }
                }
            }
        });

        // Fetch Buying Rate from Item Price
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Item Price",
                filters: {
                    item_code: row.item_code,
                    buying: 1
                },
                fields: ["price_list_rate"],
                limit: 1
            },
            callback: function(r) {
                if (r.message?.length) {
                    frappe.model.set_value(cdt, cdn, "rate", r.message[0].price_list_rate);
                    frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(r.message[0].price_list_rate));
                } else {
                    // Fallback to Valuation Rate
                    frappe.call({
                        method: "frappe.client.get_value",
                        args: {
                            doctype: "Item",
                            filters: { name: row.item_code },
                            fieldname: "valuation_rate"
                        },
                        callback(val) {
                            let rate = val.message?.valuation_rate || 0;
                            frappe.model.set_value(cdt, cdn, "rate", rate);
                            frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(rate));
                        }
                    });
                }
            }
        });
    },

    qty(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
    },

    rate(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
    }
});


