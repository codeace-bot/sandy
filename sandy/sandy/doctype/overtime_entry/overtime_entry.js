frappe.ui.form.on('Overtime Entry', {
    employee(frm) {
        if (!frm.doc.employee) return;

        frappe.call({
            method: 'sandy.sandy.doctype.overtime_entry.overtime_entry.get_employee_salary_details',
            args: { employee: frm.doc.employee, overtime_date: frm.doc.overtime_date },
            callback(r) {
                if (!r.message) return;

                frm.set_value('base_salary', r.message.base_salary);
                frm.set_value('standard_working_hours', r.message.standard_hours);
                frm.set_value('standard_working_days', r.message.standard_days);
                frm.set_value('base_salary_per_hour', r.message.per_hour);
                frm.set_value('base_salary_per_minute', r.message.per_minute);
                frm.set_value('salary_structure', r.message.salary_structure);

                if (r.message.salary_structure) {
                    if (!r.message.is_over_time_in_structure) {
                        frm.set_value('overwrite_salary_structure_amount', 0);
                        frm.set_df_property('overwrite_salary_structure_amount', 'disabled', 1);
                    } else {
                        frm.set_df_property('overwrite_salary_structure_amount', 'disabled', 0);
                    }
                }

                calculate_overtime(frm);
            }
        });
    },

    overtime_date(frm) {
        if (frm.doc.employee) {
            frappe.call({
                method: 'sandy.sandy.doctype.overtime_entry.overtime_entry.get_employee_salary_details',
                args: { employee: frm.doc.employee, overtime_date: frm.doc.overtime_date },
                callback(r) {
                    if (!r.message) return;
                    frm.set_value('standard_working_days', r.message.standard_days);
                    frm.set_value('base_salary_per_hour', r.message.per_hour);
                    frm.set_value('base_salary_per_minute', r.message.per_minute);
                    calculate_overtime(frm);
                }
            });
        }
    },

    overtime_type(frm) {
        calculate_overtime(frm);
    },

    overtime_time(frm) {
        calculate_overtime(frm);
    },

    adjust_amount(frm) {
        calculate_overtime(frm);
    }
});

function calculate_overtime(frm) {
    if (!frm.doc.overtime_time || !frm.doc.base_salary || !frm.doc.overtime_type) return;

    const rate = frm.doc.overtime_type === "Hourly"
        ? frm.doc.base_salary_per_hour
        : frm.doc.base_salary_per_minute;

    const amount = flt(frm.doc.overtime_time) * flt(rate) * 1.5;
    frm.set_value('overtime_amount', amount);
    frm.set_value('final_amount', amount + flt(frm.doc.adjust_amount));
}
