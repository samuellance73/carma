"""
Quick test: prints the full system prompt with all live context injected.
Run from the project root: nix-shell --run "python test_prompt.py"
"""

from src.prompts import get_system_prompt

if __name__ == "__main__":
    print("=" * 60)
    print("  SYSTEM PROMPT PREVIEW")
    print("=" * 60)
    print()
    prompt = get_system_prompt()
    print(prompt)
    print()
    print("=" * 60)
    print(f"  Total characters: {len(prompt)}")
    print("=" * 60)
