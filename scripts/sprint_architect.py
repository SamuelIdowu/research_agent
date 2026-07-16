import argparse
import os
import shutil
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SPRINTS_DIR = PROJECT_ROOT / "docs" / "sprints"
TEMPLATE_PATH = SPRINTS_DIR / "templates" / "00_sprint_template.md"
PROMPTS_PATH = SPRINTS_DIR / "sprint_prompts.md"

def scaffold_sprint(sprint_num: str, sprint_title: str):
    # Format sprint number to always be two digits (e.g., "12")
    sprint_num_formatted = str(sprint_num).zfill(2)
    sprint_name_slug = sprint_title.lower().replace(" ", "_").replace("-", "_")
    filename = f"{sprint_num_formatted}_{sprint_name_slug}.md"
    new_sprint_path = SPRINTS_DIR / filename
    
    # Check if template exists
    if not TEMPLATE_PATH.exists():
        print(f"Error: Template not found at {TEMPLATE_PATH}")
        return
        
    if new_sprint_path.exists():
        print(f"Error: Sprint file already exists at {new_sprint_path}")
        return

    # 1. Create the new sprint document from template
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template_content = f.read()
        
    new_content = template_content.replace(
        "# Sprint XX: [Sprint Title]", 
        f"# Sprint {sprint_num_formatted}: {sprint_title}"
    )
    
    with open(new_sprint_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print(f"Created new sprint file: {new_sprint_path}")
    
    # 2. Append to sprint_prompts.md
    if not PROMPTS_PATH.exists():
        print(f"Warning: {PROMPTS_PATH} not found. Skipping prompt generation.")
        return
        
    prompt_content = f"""
## Sprint {sprint_num_formatted}: {sprint_title}

**1. Initiate & Plan**
```text
Please read `docs/sprints/{filename}`. We are building {sprint_title}. Please draft a comprehensive implementation plan. Stop and wait for my approval before coding.
```

**2. Develop**
```text
I approve the plan for Sprint {sprint_num_formatted}. Please implement the features exactly as detailed in the checklist.
```

**3. Validate**
```text
Please run the validation steps outlined in the Sprint {sprint_num_formatted} doc. Run the test suite and fix any bugs that arise.
```

**4. Review**
```text
Act as a senior architect. Review the Sprint {sprint_num_formatted} implementation. Verify that all requirements were met, security concerns addressed, and quality standards upheld.
```

---
"""
    with open(PROMPTS_PATH, "a", encoding="utf-8") as f:
        f.write(prompt_content)
        
    print(f"Appended prompts for Sprint {sprint_num_formatted} to {PROMPTS_PATH}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scaffold a new sprint document and prompt sequence.")
    parser.add_argument("number", type=str, help="The sprint number (e.g. 12)")
    parser.add_argument("title", type=str, help="The sprint title (e.g. 'Advanced Analytics')")
    
    args = parser.parse_args()
    scaffold_sprint(args.number, args.title)
