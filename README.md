# Ephraim

**Ephraim** is a real-time conversational AI agent designed to assist with pharmacy-related tasks. It combines a Large Language Model (LLM) with modular tools to intelligently decide which actions to perform and provides human-readable explanations in real-time.

---

## Table of Contents
- [Architecture](#architecture)
- [Overall Workflow](#overall-workflow)
- [Installation](#installation)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Architecture:
Ephraim is designed as a tool-driven conversational agent. The system cleanly separates reasoning, decision-making, and execution to ensure reliability, extensibility, and transparency.

At a high level, Ephraim follows this flow:

### User Input -> LLM Tool Decision -> Structured Execution Plan (JSON) -> PharmacyTools Execution -> Streamed Explanation + Final Response

A core design principle was such that the LLM would not be given the entire database and simply read from it.
This would both be a security/privacy issue, and also could lead to inaccurate results due to hallucination.

Rather, the LLM decides which tool to use, Ephraim executes the tool locally on the data, and then provides the LLM with the output to help craft an answer.
This of course requires two separate prompts of the LLM which is why it is important that Ephraim streams responses, giving users output as soon as it is available.

Ephraim is made up of three main methods plus its Toolbox. The Toolbox is a separate class that is created and stored within Ephraim during construction of the Class.

### Toolbox:
Here are the key aspects of the Toolbox:
1. Standardized error JSONs in order to handle errors in clear and safe manner
2. Tool: `get_medication_details_from_name`
3. Tool: `check_inventory_status`
4. Tool: `get_user_prescription_names`
5. Tool: `get_user_prescription_history`

Note: The list of tools is dynamically inspected by Ephraim such that the LLM will know what tools can be used based on their docstring descriptions
This means tools can be added to the Toolbox and Ephraim with automatically know to access them


### `_decide_tool` 

Responsible for understanding the user’s intent and converting it into a **structured execution plan**.

At this stage, Ephraim:

- Sends the user’s message to the LLM along with:
  - A dynamically generated catalog of available tools
  - Strict formatting and response rules
- Instructs the LLM to return:
  - A concise, human-readable explanation (for the user)
  - A machine-readable JSON execution plan (for the system)

The LLM response is split into two parallel paths:

- **Explanation**
  - Streamed asynchronously to the user
  - Provides immediate feedback while execution is prepared
- **Plan**
  - Parsed and validated immediately
  - Execution proceeds only if valid JSON is produced

---

### `_execute_tool` 

Responsible for executing the structured plan produced by `_decide_tool` in a **fully deterministic** manner.

This method:

- Iterates through each step in the execution plan
- Dynamically invokes the specified `PharmacyTools` method
- Supports:
  - Sequential tool execution
  - Saving intermediate results (`save_as`)
  - Iterative execution over prior outputs (`foreach`)
- Immediately halts execution on any standardized error

During execution, Ephraim builds a structured **execution summary** that records:

- Tool names
- Arguments used
- Tool outputs

This summary becomes the sole source of truth for the final response.

---

### `_stream_response`

Responsible for generating the final user-facing response.

At this stage, Ephraim:

- Combines:
  - System response rules
  - The original user request
  - The execution summary produced by `_execute_tool`
- Streams the response token-by-token to the terminal

Because responses are grounded in actual tool outputs, the LLM is constrained to:

- Summarize results
- Explain outcomes
- Communicate errors clearly

No new decisions or actions occur during this phase.

---


## Overall Workflow:
### 1. **Setup**:
- Running program will begin infinite loop conversation with Ephraim
  - If given command line argument --debug, logs will be posted in chat as well
- Ephraim will be instantiated and in its constructor it will:
  - Create and save its Toolbox object
  - Dynamically store the names and descriptions of its tools based on the Toolbox
  - Send a welcome message to the user

### 2. **User Input**: 
- User will be prompted to input a question for Ephraim. 
- Ephraim will read and process input

### 3. **Decide Tool**:
- Takes the predefined system prompt (including rules, available tools, and response format) together with the user prompt and sends to model to decide which tool to use
- Model responds with two parts:
  - a JSON of its plan to answer the user request
  - a textual version of that plan in order to explain plan to user
- A plan JSON has the following format:

```json
{
  "plan": [
    {
      "tool": "get_user_prescription_names",
      "args": {
        "user_name": "Alice",
        "user_dob": "1995-04-12"
      },
      "save_as": "prescriptions"
    },
    {
      "tool": "get_medication_details_by_name",
      "foreach": "prescriptions",
      "args": {
        "name": "$item"
      }
    }
  ]
}
```
- Plans allow Ephraim to complete both single-tool requests and ones that require multiple, sequential tasks
- Streams the textual version of the plan to the user in a background thread
- Meanwhile, passes the JSON plan to his tool executer

### 4. **Execution**:
- Steps through each tool needed in the plan and executes them sequentially
- Saves any outputs that must be used by later tools in appropriate variables
- Runs tool multiple times if based on previous tool output that has multiple values
  - Ex: If the user asks "What are my prescriptions and who manufactures them?", Ephraim will find the details of EVERY prescription the user has
- Returns summary of plan execution

### 5. **Response**
- Combines rules, execution summary, and format into system instructions
- Prompts LLM with user request and system instructions to answer user's question
- Streams response in Rich textual format as LLM produces chunks
 



## Installation

These instructions guide you through running the **Ephraim agent** using Docker

---

## 1. Clone the repository

Open PowerShell / Terminal and run:

```powershell
git clone https://github.com/aisrael615/Ephraim
cd Ephraim
```

---

## 2. Create a `.env` file

Create a file named `.env` in the root of the repo. This file stores environment variables needed by Ephraim (like API keys or secrets).

Example `.env`:

```env
OPENAI_API_KEY=your_api_key_here
```

> **Important:** `.env` is ignored by Git and should **never be committed**.

---

## 3. Verify project structure

Your project should look like this:

```
Ephraim/
├── Dockerfile
├── requirements.txt
├── .gitignore
└── agent/
    ├── ephraim.py
    ├── database.json
    └── other files...
```

* `agent/` contains the Python code and `database.json`
* `.env` is in the root folder

---

## 4. Build the Docker image

```powershell
docker build --no-cache -t ephraim-agent .
```

* `--no-cache` ensures all files are copied fresh
* `-t ephraim-agent` tags the Docker image

---

## 5. Run Ephraim interactively

```powershell
docker run -it --rm --env-file .env ephraim-agent
```

### Explanation:

* `-i` → interactive mode, keeps STDIN open
* `-t` → allocates a terminal for proper output
* `--rm` → removes the container after exit
* `--env-file .env` → loads your environment variables

You can now **chat with Ephraim** in real time:

Type `exit` or `quit` to close the container.

---



## License

This project is licensed under the MIT License.

---

## Acknowledgments

* [OpenAI](https://openai.com/) for the GPT models.
* [Rich](https://github.com/Textualize/rich) for terminal formatting.
* [Langdetect](https://pypi.org/project/langdetect/) for language detection.
* Original inspiration and modular tool architecture from the Ephraim project structure.
