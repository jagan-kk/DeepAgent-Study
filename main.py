from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
import os
from dotenv import load_dotenv
load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY")




agent= create_deep_agent(
    model="ollama:qwen3:8b",
    tools=[],
    memory=["./AGENTS.md"],
    system_prompt="""You are a helpful file-management assistant.

        You are working in a virtual filesystem. The project root is /.

        Rules:

        Treat tool results as the source of truth.
        When the ls tool returns paths such as /.env, /main.py, or /.git/,
        those are entries inside the current project directory /.
        Never say a directory is empty if the ls tool returned one or more entries.
        Clearly separate files and directories in your response.
        If a tool call fails, explain the error and try a reasonable relative path such as . or /.

        CRITICAL: At the end of every task, or when a new project rule/issue is discovered, you must use your file editing tools to update ./AGENTS.md with the current state, progress, and plans. Do not exit without logging your state here.
        """,
        backend=LocalShellBackend(
        root_dir=r"C:\Users\USER\Documents\Task\DeepAgent",
        virtual_mode=True,
        env=os.environ.copy()
)
    )


result=agent.invoke(
    {"messages":[{"role":"user","content":"hey, can you give me a list of all the files and directories in the current project directory /?"}]}
)
print(result["messages"][-1].content)