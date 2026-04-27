from string import Template


# Pattern: define each prompt as a Template so callers can substitute variables.
#
# Example:
#   SUMMARIZE_PROMPT = Template("""
#   You are a summarization assistant.
#   Summarize the following content about $topic:
#   $content
#   """)
#
# Usage:
#   prompt = SUMMARIZE_PROMPT.substitute(topic="LLM Agents", content=raw_text)


# TODO: add project prompts below
