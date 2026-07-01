import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "name",
            "label": _("Overtime Entry ID"),
            "fieldtype": "Link",
            "options": "Overtime Entry",
            "width": 150
        },
        {
            "fieldname": "employee",
            "label": _("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120
        },
        {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "gender",
            "label": _("Gender"),
            "fieldtype": "Data",
            "width": 80
        },
        {
            "fieldname": "company",
            "label": _("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "width": 120
        },
        {
            "fieldname": "department",
            "label": _("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "width": 120
        },
        {
            "fieldname": "overtime_date",
            "label": _("Overtime Date"),
            "fieldtype": "Date",
            "width": 110
        },
        {
            "fieldname": "overtime_type",
            "label": _("Type"),
            "fieldtype": "Data",
            "width": 90
        },
        {
            "fieldname": "overtime_time",
            "label": _("Time"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 90
        },
        {
            "fieldname": "base_salary",
            "label": _("Base Salary"),
            "fieldtype": "Currency",
            "options": "company:default_currency",
            "width": 120
        },
        {
            "fieldname": "overtime_amount",
            "label": _("Overtime Amount"),
            "fieldtype": "Currency",
            "options": "company:default_currency",
            "width": 140
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "additional_salary_ref",
            "label": _("Additional Salary"),
            "fieldtype": "Link",
            "options": "Additional Salary",
            "width": 150
        }
    ]


def get_data(filters):
    conditions = []

    if filters and filters.get("employee"):
        conditions.append(f"oe.employee = '{frappe.db.escape(filters['employee'])}'")

    if filters and filters.get("department"):
        conditions.append(f"oe.department = '{frappe.db.escape(filters['department'])}'")

    if filters and filters.get("status"):
        conditions.append(f"oe.status = '{frappe.db.escape(filters['status'])}'")

    if filters and filters.get("from_date"):
        conditions.append(f"oe.overtime_date >= '{filters['from_date']}'")

    if filters and filters.get("to_date"):
        conditions.append(f"oe.overtime_date <= '{filters['to_date']}'")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    data = frappe.db.sql(f"""
        SELECT
            oe.name,
            oe.employee,
            oe.employee_name,
            oe.gender,
            oe.company,
            oe.department,
            oe.overtime_date,
            oe.overtime_type,
            oe.overtime_time,
            oe.base_salary,
            oe.overtime_amount,
            oe.status,
            oe.additional_salary_ref
        FROM
            `tabOvertime Entry` oe
        WHERE
            {where_clause}
        ORDER BY
            oe.overtime_date DESC, oe.creation DESC
    """, as_dict=True)

    return data
