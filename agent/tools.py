import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from helpers import error, log_method_call


class PharmacyTools:
    """
    Name:
        PharmacyTools

    Purpose:
        Collection of domain-specific tools for a pharmacy conversational agent.
        Handles user validation, inventory queries, and prescription data access.

    Inputs:
        data (dict): In-memory database containing users, inventory, and logs.

    Output Schema:
        Tool-specific outputs.

    Error Handling:
        All methods return standardized error dicts instead of raising exceptions.

    Fallback Behavior:
        Prompts for missing user inputs and returns safe defaults where possible.
    """

    def __init__(self, data: Dict[str, Any], console, logger) -> None:
        self.data = data
        self.console = console
        self.explanation_thread = None
        self.language = "en"
        self.logger = logger

    def _stream_text(self, text, style, delay):
        """Function to be run in a thread"""
        self.console.print(f"[bold {style}]Ephraim: [/]", end="")
        for char in text:
            self.console.print(char, end="")
            time.sleep(delay)
        self.console.print()  # Newline at the end

    def _validate_user_name_and_dob(
            self,
            user_name: Optional[str] = None,
            user_dob: Optional[str] = None,
    ) -> Union[Dict[str, Any], Dict[str, Any]]:
        """
        Purpose:
            Validate a user's identity using name and date of birth.

        Inputs:
            user_name (str | None): User's name (case-insensitive).
            user_dob (str | None): DOB in YYYY-MM-DD format.

        Output Schema:
            On success:
                user (dict)

            On failure:
                standardized error dict

        Error Handling:
            - USER_NOT_FOUND
            - INVALID_DOB
            - INCORRECT_DOB

        Fallback Behavior:
            Prompts for missing inputs.
        """
        if self.explanation_thread:
            self.explanation_thread.join()

        users_dict = {user["name"].lower(): user for user in self.data["users"]}

        if not user_name:
            self.console.print("[bold green]Ephraim: [/]", end="")
            if self.language == "en":
                self.console.print("Please enter your name:")
            elif self.language == "he":
                self.console.print("אנא הזן את שמך:")
            self.console.print("[bold blue]You: [/]", end="")
            user_name = input().strip()
        user_name_lower = user_name.lower()

        if user_name_lower not in users_dict:
            return error(message=f"User '{user_name}' not found", code="USER_NOT_FOUND",
                         details={"user_name": user_name})

        if not user_dob:
            self.console.print("[bold green]Ephraim: [/]", end="")
            if self.language == "en":
                self.console.print("Please enter your date of birth (YYYY-MM-DD):")
            elif self.language == "he":
                self.console.print("אנא הזן את תאריך הלידה שלך (YYYY-MM-DD):")
            self.console.print("[bold blue]You: [/]", end="")
            user_dob = input().strip()

        try:
            datetime.strptime(user_dob, "%Y-%m-%d")
        except ValueError:
            return error(message="Invalid DOB format", code="INVALID_DOB", details={"user_dob": user_dob})

        if user_dob != users_dict[user_name_lower]["dob"]:
            return error(message="Incorrect DOB", code="INCORRECT_DOB", details={"user_dob": user_dob})

        return users_dict[user_name_lower]

    @log_method_call
    def get_medication_details_by_name(self, name: str) -> Dict[str, Any]:
        """
        Purpose:
            Retrieve detailed medication information from inventory.

        Inputs:
            name (str): Medication name (case-insensitive).

        Output Schema:
            On success:
                medication dict

            On failure:
                standardized error dict

        Error Handling:
            - MEDICATION_NOT_FOUND

        Fallback Behavior:
            Returns error without raising exceptions.
        """
        for med in self.data["pharmacy_inventory"]:
            if med["name"].lower() == name.lower():
                return med

        return error(message=f"Medication '{name}' not found", code="MEDICATION_NOT_FOUND",
                     details={"medication_name": name})

    @log_method_call
    def get_user_prescription_names(
            self,
            user_name: Optional[str] = None,
            user_dob: Optional[str] = None
    ) -> Union[List[str], Dict[str, Any]]:
        """
        Purpose:
            Retrieve prescription medication names for a validated user.

        Inputs:
            user_name (str | None): User's name.
            user_dob (str | None): User's DOB.

        Output Schema:
            On success:
                list[str]

            On failure:
                standardized error dict

        Error Handling:
            Identity validation errors via helper.

        Fallback Behavior:
            Prompts for missing identity fields.
        """
        user = self._validate_user_name_and_dob(user_name, user_dob)

        if "error" in user:
            return user

        return user.get("prescriptions", ["No Current Medications"])

    @log_method_call
    def check_inventory_status(self) -> Union[List[str], Dict[str, Any]]:
        """
        Purpose:
            List medications that are not out of stock.

        Inputs:
            None

        Output Schema:
            On success:
                list[str]

            On failure:
                standardized error dict

        Error Handling:
            INVENTORY_ERROR on unexpected failures.

        Fallback Behavior:
            Returns friendly message if no inventory is available.
        """

        try:
            available = [
                med["name"]
                for med in self.data["pharmacy_inventory"]
                if med.get("availability") != "Out of stock"
            ]
            return available if available else ["No medications currently in stock"]
        except Exception as e:
            return error(message="Failed to retrieve inventory status", code="INVENTORY_ERROR",
                         details={"exception": str(e)})

    @log_method_call
    def report_broken_rule(self, rule: str) -> Dict[str, Any]:
        """
        Purpose:
            Notify the user that their request violates service rules.

        Inputs:
            rule (str): Description of violated rule.

        Output Schema:
            standardized error dict with RULE_VIOLATION code

        Error Handling:
            This tool cannot fail.

        Fallback Behavior:
            Acts as a terminal response.
        """
        return error(message="I cannot complete your request because it violates a service rule.",
                     code="RULE_VIOLATION", details={"rule": rule})

    @log_method_call
    def get_user_prescription_history(
            self,
            user_name: Optional[str] = None,
            user_dob: Optional[str] = None
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Purpose:
            Retrieve a user's historical prescription fill records.

        Inputs:
            user_name (str | None): User's name.
            user_dob (str | None): User's DOB.

        Output Schema:
            On success:
                list[{
                    medication: str,
                    date_filled: str,
                    quantity: int,
                    status: str
                }]

            On failure:
                standardized error dict

        Error Handling:
            - Identity validation errors
            - NO_PRESCRIPTIONS if no history exists

        Fallback Behavior:
            Prompts for missing identity fields.
        """
        user = self._validate_user_name_and_dob(user_name, user_dob)

        if "error" in user:
            return user

        logs = [
            {
                "medication": log["medication"],
                "date_filled": log["date_filled"],
                "quantity": log["quantity"],
                "status": log["status"]
            }
            for log in self.data.get("prescription_logs", [])
            if log["user_name"].lower() == user["name"].lower()
        ]

        if not logs:
            return error(message="No prescriptions found", code="NO_PRESCRIPTIONS", details={"user_name": user["name"]})

        return logs
