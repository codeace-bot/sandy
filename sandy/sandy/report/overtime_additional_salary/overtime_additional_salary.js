frappe.query_reports["Overtime Additional Salary"] = {
    filters: [
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee"
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department"
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: ["", "Pending", "Salary Created"]
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date"
        }
    ],

    onload(report) {
        report.page.add_inner_button(__("Create Additional Salary"), () => {
            const rows = report.datatable?.getCheckedRows() || [];
            if (!rows.length) {
                frappe.msgprint(__("Please select rows to create Additional Salary"));
                return;
            }

            const selected = rows.map(idx => report.data[idx]);

            frappe.confirm(
                __("Create Additional Salary for {0} selected overtime entries?", [selected.length]),
                () => {
                    frappe.call({
                        method: "sandy.sandy.doctype.overtime_entry.overtime_entry.create_additional_salary",
                        args: {
                            entries: selected.map(d => ({ name: d.name }))
                        },
                        callback(r) {
                            if (r.message && r.message.length) {
                                frappe.msgprint(
                                    __("Created {0} Additional Salary records: {1}",
                                        [r.message.length, r.message.join(", ")]
                                    )
                                );
                                report.refresh();
                            }
                        }
                    });
                }
            );
        });

        frappe.db.get_list("Overtime Entry", {
            filters: { status: "Pending" },
            limit: 1
        }).then(result => {
            if (result.length === 0) {
                frappe.msgprint({
                    title: __("Info"),
                    message: __("No pending overtime entries found."),
                    indicator: "orange"
                });
            }
        });
    },

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "status") {
            if (data?.status === "Pending") {
                value = `<span class="indicator-pill red">${value}</span>`;
            } else if (data?.status === "Salary Created") {
                value = `<span class="indicator-pill green">${value}</span>`;
            }
        }

        if (column.fieldname === "overtime_amount" && data?.overtime_amount > 0 && data?.status === "Pending") {
            value = `<strong>${value}</strong>`;
        }

        return value;
    }
};
