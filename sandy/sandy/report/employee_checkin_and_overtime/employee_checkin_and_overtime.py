import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt, getdate
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "employee",
            "label": _("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120,
        },
        {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "department",
            "label": _("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "width": 120,
        },
        {
            "fieldname": "date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "fieldname": "first_in",
            "label": _("First IN"),
            "fieldtype": "Datetime",
            "width": 150,
        },
        {
            "fieldname": "last_out",
            "label": _("Last OUT"),
            "fieldtype": "Datetime",
            "width": 150,
        },
        {
            "fieldname": "working_hours",
            "label": _("Working Hours"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 120,
        },
        {
            "fieldname": "actual_overtime",
            "label": _("Actual Overtime"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 130,
        },
        {
            "fieldname": "late_hours",
            "label": _("Late Hours"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 100,
        },
        {
            "fieldname": "late_amount",
            "label": _("Late Amount"),
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "width": 140,
        },
        {
            "fieldname": "overtime_hours",
            "label": _("Overtime Hours"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 120,
        },
        {
            "fieldname": "overtime_amount",
            "label": _("Overtime Amount"),
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "width": 140,
        },
        {
            "fieldname": "overtime_entry",
            "label": _("Overtime Entry"),
            "fieldtype": "Link",
            "options": "Overtime Entry",
            "width": 150,
        },

    ]


def get_data(filters):
    conditions = []
    params = {}

    if filters.get("from_date"):
        conditions.append("DATE(ec.time) >= %(from_date)s")
        params["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("DATE(ec.time) <= %(to_date)s")
        params["to_date"] = filters["to_date"]

    if filters.get("employee"):
        conditions.append("ec.employee = %(employee)s")
        params["employee"] = filters["employee"]

    if filters.get("department"):
        conditions.append("emp.department = %(department)s")
        params["department"] = filters["department"]

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    data = frappe.db.sql(
        f"""
        SELECT
            ec.employee,
            emp.employee_name,
            emp.department,
            emp.company,
            emp.gender,
            DATE(ec.time) AS date,
            MIN(CASE WHEN ec.log_type = 'IN' THEN ec.time END) AS first_in,
            MAX(CASE WHEN ec.log_type = 'OUT' THEN ec.time END) AS last_out,
            MIN(CASE WHEN ec.log_type = 'IN' THEN ec.shift_start END) AS shift_start,
            TIME_TO_SEC(
                TIMEDIFF(
                    MAX(CASE WHEN ec.log_type = 'OUT' THEN ec.time END),
                    MIN(CASE WHEN ec.log_type = 'IN' THEN ec.time END)
                )
            ) / 3600 AS working_hours,
            oe.overtime_time AS overtime_hours,
            oe.overtime_amount,
            oe.name AS overtime_entry,
            GREATEST(
                TIME_TO_SEC(
                    TIMEDIFF(
                        MAX(CASE WHEN ec.log_type = 'OUT' THEN ec.time END),
                        MIN(CASE WHEN ec.log_type = 'IN' THEN ec.time END)
                    )
                ) / 3600 - (CASE WHEN emp.gender = 'Male' THEN 9.0 ELSE 8.5 END),
                0
            ) AS actual_overtime
        FROM
            `tabEmployee Checkin` ec
        INNER JOIN
            `tabEmployee` emp ON emp.name = ec.employee
        LEFT JOIN
            `tabOvertime Entry` oe
                ON oe.employee = ec.employee
                AND oe.overtime_date = DATE(ec.time)
                AND oe.docstatus = 1
        WHERE
            {where_clause}
        GROUP BY
            ec.employee, DATE(ec.time)
        ORDER BY
            ec.employee, DATE(ec.time) DESC
        """,
        params,
        as_dict=True,
    )

    employee_salary_cache = {}
    for row in data:
        row.working_hours = flt(row.working_hours, 2)
        row.overtime_hours = flt(row.overtime_hours, 2) if row.overtime_hours else 0
        row.overtime_amount = flt(row.overtime_amount, 2) if row.overtime_amount else 0
        row.actual_overtime = flt(row.actual_overtime, 2)

        late_hours = 0.0
        if row.first_in and row.shift_start:
            diff_seconds = (row.first_in - row.shift_start).total_seconds()
            late_hours = max(0, diff_seconds / 3600.0)
        row.late_hours = flt(late_hours, 2)

        late_amount = 0.0
        if late_hours and row.employee:
            per_hour = get_employee_per_hour_rate(
                row.employee, row.date, row.gender, employee_salary_cache
            )
            late_amount = -(late_hours * per_hour)
        row.late_amount = flt(late_amount, 2)

    return data


def get_employee_per_hour_rate(employee, date, gender, cache):
    key = employee
    if key not in cache:
        base = frappe.db.get_value(
            "Salary Structure Assignment",
            {"employee": employee, "docstatus": 1},
            "base",
            order_by="from_date desc",
        )
        base = flt(base)
        std_hours = 9.0 if gender == "Male" else 8.5
        std_days = get_working_days_in_month(employee, date)
        monthly_hours = std_days * std_hours
        cache[key] = base / monthly_hours if monthly_hours else 0
    return cache[key]


def get_working_days_in_month(employee, date):
    date = getdate(date)
    start_date = date.replace(day=1)
    end_date = start_date.replace(day=28) + __import__("datetime").timedelta(days=4)
    end_date = end_date - __import__("datetime").timedelta(days=end_date.day)

    total_days = date_diff(end_date, start_date) + 1

    payroll_settings = frappe.get_cached_value(
        "Payroll Settings", None, "include_holidays_in_total_working_days"
    )

    if cint(payroll_settings):
        return total_days

    holiday_list = get_holiday_list_for_employee(employee, raise_exception=False)
    if not holiday_list:
        return total_days

    holidays = frappe.get_all(
        "Holiday",
        fields=["holiday_date"],
        filters={"parent": holiday_list, "holiday_date": ["between", [start_date, end_date]]},
        pluck="holiday_date",
    )

    return total_days - len(holidays)
