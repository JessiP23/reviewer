import sys
from pathlib import Path

from reviewer.api.graphql import schema


def main() -> None:
    destination = Path(sys.argv[1] if len(sys.argv) > 1 else "schema.graphql")
    destination.write_text(schema.as_str(), encoding="utf-8")


if __name__ == "__main__":
    main()
