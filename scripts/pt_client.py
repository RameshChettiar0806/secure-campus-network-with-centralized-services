"""Client for the local Packet Tracer bridge and its Qt-style JSON arrays."""

import argparse
import json
from pathlib import Path
import urllib.request

BASE = Path(__file__).resolve().parents[1]
BRIDGE_URL = 'http://127.0.0.1:7532/call'


def normalize(value):
    """Convert dense serialized Qt arrays, preserving ordinary JSON objects."""
    if isinstance(value, dict):
        if 'length' in value and all(k == 'length' or k.isdigit() for k in value):
            length = value['length']
            if (type(length) is not int or length < 0 or len(value) != length + 1
                    or any(str(i) not in value for i in range(length))):
                raise ValueError('Malformed Packet Tracer array')
            return [normalize(value[str(i)]) for i in range(length)]
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def call(name, args=None):
    request = urllib.request.Request(
        BRIDGE_URL,
        json.dumps({'name': name, 'arguments': args or {}}).encode('utf-8'),
        {'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.load(response)
    while isinstance(data, dict) and 'code' in data and 'result' in data:
        data = data['result']
    return normalize(data)


def evidence_path(name):
    """Constrain CLI output to the project's evidence directory."""
    root = (BASE / 'evidence').resolve()
    target = (root / name).resolve()
    if target == root or not target.is_relative_to(root):
        raise ValueError('Output must be a file inside the evidence directory')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', help='Bridge tool name')
    parser.add_argument('arguments', nargs='?', default='{}', type=json.loads)
    parser.add_argument('output', nargs='?', help='Output path relative to evidence/')
    args = parser.parse_args()
    if not isinstance(args.arguments, dict):
        parser.error('arguments must be a JSON object')
    # Check the destination before invoking a potentially mutating simulator tool.
    target = evidence_path(args.output) if args.output else None
    text = json.dumps(call(args.name, args.arguments), indent=2)
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + '\n', encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
