"""Bedrock AgentCore entrypoint."""

from vendorops_agent.agent import agent, app, invoke

__all__ = ["agent", "app", "invoke"]

if __name__ == "__main__":
    app.run()
