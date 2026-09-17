import re


def render_template(template: str, context: dict) -> str:
    result = template
    for key, value in context.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def extract_template_variables(template: str) -> list[str]:
    return re.findall(r"\{\{(\w+)\}\}", template)
