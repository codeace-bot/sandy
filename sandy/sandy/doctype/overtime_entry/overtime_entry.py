import math

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, date_diff, getdate, flt
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee


class OvertimeEntry(Document):
    def validate(self):
        self.calculate_overtime_amount()
        self.validate_salary_structure()

    def before_save(self):
        self.set_standard_working_hours()
        self.set_standard_working_days()
        self.calculate_overtime_amount()

    def on_submit(self):
        if self.status == "Salary Created":
            return

        additional_salary = frappe.get_doc({
            "doctype": "Additional Salary",
            "employee": self.employee,
            "salary_component": "Over Time",
            "amount": self.final_amount or self.overtime_amount,
            "payroll_date": self.overtime_date,
            "company": self.company,
            "custom_overtime_entry": self.name,
            "overwrite_salary_structure_amount": self.overwrite_salary_structure_amount,
            "notes": f"Overtime Entry: {self.name} - {self.overtime_time} {self.overtime_type}(s)",
        })
        additional_salary.insert()
        additional_salary.submit()

        self.db_set("status", "Salary Created")
        self.db_set("additional_salary_ref", additional_salary.name)

    def set_standard_working_hours(self):
        if not self.gender:
            return
        self.standard_working_hours = 9.0 if self.gender == "Male" else 8.5

    def set_standard_working_days(self):
        if not self.overtime_date:
            return
        self.standard_working_days = get_working_days_in_month(
            self.employee, self.overtime_date
        )

    def validate_salary_structure(self):
        if not self.employee:
            return

        salary_structure = frappe.db.get_value(
            "Salary Structure Assignment",
            {
                "employee": self.employee,
                "docstatus": 1,
            },
            "salary_structure",
            order_by="from_date desc",
        )

        if salary_structure:
            self.salary_structure = salary_structure

        if self.overwrite_salary_structure_amount and salary_structure:
            is_component_in_structure = frappe.db.get_value(
                "Salary Detail",
                {
                    "parenttype": "Salary Structure",
                    "parent": salary_structure,
                    "salary_component": "Over Time",
                },
            )

            if not is_component_in_structure:
                self.overwrite_salary_structure_amount = 0
                frappe.msgprint(
                    _(
                        "Overwrite Salary Structure Amount is disabled as the Salary Component: {0} not part of the Salary Structure: {1}"
                    ).format("Over Time", salary_structure)
                )

    def calculate_overtime_amount(self):
        if not self.overtime_time or not self.base_salary or not self.overtime_type:
            return

        rate_field = "base_salary_per_hour" if self.overtime_type == "Hourly" else "base_salary_per_minute"
        rate = flt(self.get(rate_field))

        if rate:
            self.overtime_amount = math.ceil(flt(self.overtime_time) * rate * 2)
            self.final_amount = self.overtime_amount + flt(self.adjust_amount)


def get_working_days_in_month(employee, overtime_date):
    date = getdate(overtime_date)
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


@frappe.whitelist()
def get_employee_salary_details(employee, overtime_date=None):
    if not employee:
        return {}

    gender = frappe.get_value("Employee", employee, "gender")
    if not gender:
        frappe.msgprint(frappe._("Gender not set for Employee {0}").format(employee))
        return {}

    standard_hours = 9.0 if gender == "Male" else 8.5

    if overtime_date:
        standard_days = get_working_days_in_month(employee, overtime_date)
    else:
        standard_days = cint(
            frappe.get_meta("Overtime Entry").get_field("standard_working_days").default or 0
        )

    salary_structure_data = frappe.db.get_value(
        "Salary Structure Assignment",
        {"employee": employee, "docstatus": 1},
        ["base", "salary_structure"],
        order_by="from_date desc",
        as_dict=True
    )

    base_salary = salary_structure_data.base if salary_structure_data else 0
    salary_structure = salary_structure_data.salary_structure if salary_structure_data else None

    is_component_in_structure = False
    if salary_structure:
        is_component_in_structure = frappe.db.get_value(
            "Salary Detail",
            {
                "parenttype": "Salary Structure",
                "parent": salary_structure,
                "salary_component": "Over Time",
            },
        )

    monthly_hours = standard_days * standard_hours
    per_hour = flt(base_salary) / monthly_hours if monthly_hours else 0
    per_minute = per_hour / 60 if per_hour else 0

    return {
        "base_salary": flt(base_salary),
        "standard_hours": standard_hours,
        "standard_days": standard_days,
        "per_hour": flt(per_hour, 4),
        "per_minute": flt(per_minute, 4),
        "gender": gender,
        "salary_structure": salary_structure,
        "is_over_time_in_structure": is_component_in_structure
    }


@frappe.whitelist()
def create_additional_salary(entries):
    import json

    if isinstance(entries, str):
        entries = json.loads(entries)

    created = []
    for entry in entries:
        doc = frappe.get_doc("Overtime Entry", entry.get("name"))
        if doc.status == "Salary Created":
            continue

        additional_salary = frappe.get_doc({
            "doctype": "Additional Salary",
            "employee": doc.employee,
            "salary_component": "Over Time",
            "amount": doc.overtime_amount,
            "payroll_date": doc.overtime_date,
            "company": doc.company,
            "custom_overtime_entry": doc.name,
            "overwrite_salary_structure_amount": doc.overwrite_salary_structure_amount,
            "notes": f"Overtime Entry: {doc.name} - {doc.overtime_time} {doc.overtime_type}(s)"
        })
        additional_salary.insert()
        additional_salary.submit()

        doc.db_set("status", "Salary Created")
        created.append(additional_salary.name)

    return created
