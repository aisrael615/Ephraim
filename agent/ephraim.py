import argparse
import inspect
import json
import os
import threading
import time
import logging

from dotenv import load_dotenv
from langdetect import detect
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel

from consts import API_KEY_ENV_VAR_NAME, DATABASE_FILE_NAME, MODEL_NAME
from helpers import error, is_error, broken_rule_in_plan
from prompts import basic_rules, response_rules, response_format, tool_decider_rules
from tools import PharmacyTools


class Ephraim:
    """Real-time conversational AI agent for pharmacy tasks using LLM."""

    def __init__(self) -> None:
        """Initialize the agent: load API key, database, tools, and rules."""

        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        )
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        self.api_key: str = os.getenv(API_KEY_ENV_VAR_NAME)
        if not self.api_key:
            raise ValueError("API key not found. Set OPENAI_API_KEY in .env file.")

        self.client: OpenAI = OpenAI(api_key=self.api_key)
        self.console: Console = Console()


        with open(DATABASE_FILE_NAME, "r") as f:
            self.data: dict = json.load(f)
        self.tools: PharmacyTools = PharmacyTools(data=self.data, console=self.console, logger=self.logger)
        self.tool_map: dict = self._generate_tool_map()

        self.basic_rules: str = basic_rules
        self.response_rules: str = response_rules
        self.console.print(Panel(
            "Hi! I'm EphrAIm, your AI pharmacy assistant. How may I help you?",
            title="[bold green]Ephraim[/bold green]",
            border_style="green",
            expand=False
        )
        )

    def _generate_tool_map(self) -> dict:
        """Collect all public methods from the tools class as a dict of {name: description}."""
        tool_map: dict = {}
        for name, func in inspect.getmembers(self.tools.__class__, predicate=inspect.isfunction):
            if not name.startswith("_"):
                description = func.__doc__ or "No description provided"
                tool_map[name] = description.strip()
        return tool_map

    def _generate_tool_decider_system_prompt(self) -> str:
        """Generate the system prompt used to decide which tool(s) to call."""
        lines = tool_decider_rules
        lines.append("\nAvailable tools:\n")
        for tool_name, description in self.tool_map.items():
            lines.append(f"- {tool_name}: {description}")
        lines.extend(response_format)
        return "\n".join(lines)

    def _decide_tool(self, user_message: str) -> dict:
        """
        Ask the LLM to produce a tool execution plan and a human-readable explanation.
        The explanation is printed asynchronously while the plan is processed.
        """

        messages = [
            {
                "role": "system",
                "content": (
                        self._generate_tool_decider_system_prompt()
                        + "\n\nReturn your response in the following exact format:\n"
                          "---EXPLANATION---\n"
                          "<polite, concise explanation in the user's language. Do not add additional information beyond the steps of the plan>\n\n"
                          "---PLAN---\n"
                          "<JSON only>"
                )
            },
            {"role": "user", "content": user_message}
        ]

        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages
        )

        content: str = response.choices[0].message.content or ""

        # -------- Split explanation and plan --------
        try:
            explanation_part, plan_part = content.split("---PLAN---", 1)
            explanation = explanation_part.replace("---EXPLANATION---", "").strip()
            self.tools.language = detect(explanation)
            plan_json = plan_part.strip()
        except ValueError:
            return error(message="LLM response did not contain explanation and plan sections",
                         code="INVALID_LLM_FORMAT")

        # -------- Parse plan immediately --------
        try:
            plan = json.loads(plan_json)
            self.logger.debug(f"Plan: {plan}")
        except json.JSONDecodeError:
            return error(message="Unable to parse JSON plan produced by LLM", code="INVALID_JSON")

        # -------- Background thread: streaming print --------
        def stream_print(text: str, delay: float = 0.02) -> None:
            self.console.print("[bold green]Ephraim: [/]", end="")
            for char in text:
                self.console.print(char, end="")
                time.sleep(delay)
            self.console.print()  # newline at end

        if explanation and not broken_rule_in_plan(plan):
            self.tools.explanation_thread = threading.Thread(
                target=stream_print,
                args=(explanation,),
                daemon=True
            )
            self.tools.explanation_thread.start()

        return plan

    def _execute_tool(self, plan: dict) -> str:
        """
        Execute a plan produced by the AI agent.

        Args:
            plan (dict): A dict with key "plan", which is a list of tool steps.

        Returns:
            str: Execution summary of all tool outputs.
        """
        saved_outputs: dict = {}
        execution_summary: list = []

        for step in plan.get("plan", []):
            tool_name: str = step["tool"]
            args: dict = step.get("args", {})
            save_as: str | None = step.get("save_as")
            foreach_key: str | None = step.get("foreach")

            iterable = saved_outputs.get(foreach_key, []) if foreach_key else [None]

            results: list = []

            for item in iterable:
                actual_args: dict = {}
                for k, v in args.items():
                    actual_args[k] = item if v == "$item" else v

                # Execute tool
                result = getattr(self.tools, tool_name)(**actual_args)

                if is_error(result):
                    return "\n".join(f"{k}: {v}" for k, v in result.items())
                results.append(result)

                execution_summary.append(f"TOOL OUTPUT: {tool_name}")
                execution_summary.append(f"ARGS: {json.dumps(actual_args)}")
                execution_summary.append(f"RESULT: {json.dumps(result)}\n")

            if save_as:
                saved_outputs[save_as] = results if foreach_key else results[0]

        self.tools.explanation_thread = None
        return "\n".join(execution_summary)

    def _stream_response(self, user_content: str, execution_summary: str) -> None:
        system_instructions: str = "\n".join([
            self.basic_rules,
            self.response_rules,
            "Relevant data:",
            json.dumps(execution_summary, indent=2)
        ])

        messages = [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_content},
        ]

        with self.client.chat.completions.stream(
                model=MODEL_NAME,
                messages=messages,
        ) as stream:
            self.console.print("[bold green]Ephraim: [/]", end="")
            for event in stream:
                if event.type == "content.delta":
                    self.console.print(event.delta, end="")
            self.console.print("\n")

    def handle_user_message(self, user_message: str) -> None:
        """Full pipeline: decide which tool(s) to call, execute them, and stream the result."""
        decision: dict = self._decide_tool(user_message)
        result: str = self._execute_tool(decision)
        self._stream_response(user_message, result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    cmd_args = parser.parse_args()

    e = Ephraim()

    if cmd_args.debug:
        import logging

        e.logger.setLevel(logging.DEBUG)  # assuming you attach a logger to Ephraim

    while True:
        try:
            user_msg = e.console.input("[bold blue]You:[/bold blue] ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if user_msg.lower() in ["exit", "quit"]:
            break
        else:
            e.handle_user_message(user_msg)
