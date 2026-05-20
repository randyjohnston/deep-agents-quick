from dotenv import load_dotenv

load_dotenv(override=True)

from agent import agent

def main():
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What are the latest LangChain releases?"}]},
        config={"configurable": {"thread_id": "1"}},
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
