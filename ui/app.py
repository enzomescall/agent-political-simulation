from flask import Flask, render_template, request, send_from_directory, jsonify
import subprocess
import os
import json
import tempfile
from pathlib import Path
import glob

app = Flask(__name__, template_folder="templates", static_folder="static")

EXAMPLES_DIR = Path("examples")
OUTPUT_DIR = Path("visualizations")
WORK_DIR = Path(__file__).parent.parent


@app.route("/")
def index():
    examples = []
    for d in (WORK_DIR / "examples").iterdir():
        if d.is_dir() and (d / "world.toml").exists():
            examples.append(d.name)
    return render_template("index.html", examples=examples)


@app.route("/api/examples")
def list_examples():
    examples = []
    for d in EXAMPLES_DIR.iterdir():
        if d.is_dir() and (d / "world.toml").exists():
            examples.append(d.name)
    return jsonify(examples)


@app.route("/api/run", methods=["POST"])
def run_simulation():
    data = request.json
    example = data.get("example")
    command = data.get("command", "from-config")  # "from-config" or "generate"
    turns = data.get("turns", 10)
    seed = data.get("seed", 42)
    visualize = data.get("visualize", True)
    viz_nums = data.get("viz_nums", [])

    if command == "generate":
        profile = data.get("profile", "local")
        args = [
            str(WORK_DIR / ".venv" / "bin" / "python"),
            "sim_test.py",
            "generate",
            "--profile",
            profile,
            "--turns",
            str(turns),
            "--seed",
            str(seed),
            "--summary",
            "short",
        ]
    else:
        config_path = WORK_DIR / "examples" / example
        args = [
            str(WORK_DIR / ".venv" / "bin" / "python"),
            "sim_test.py",
            "from-config",
            "--config",
            str(config_path),
            "--turns",
            str(turns),
            "--seed",
            str(seed),
            "--summary",
            "short",
        ]

    if visualize:
        if viz_nums:
            if len(viz_nums) == 1:
                args.extend(["-v", str(viz_nums[0])])
            else:
                args.append("-v")
        else:
            args.append("-v")

    print(f"Running: {' '.join(args)}")
    result = subprocess.run(args, capture_output=True, text=True, cwd=str(WORK_DIR))

    viz_pattern = "*"
    if example:
        viz_pattern = f"{example}_*"
    viz_dirs = sorted(
        (WORK_DIR / "visualizations").glob(viz_pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    latest_viz_dir = str(viz_dirs[0]) if viz_dirs else None

    return jsonify(
        {
            "success": result.returncode == 0,
            "output": result.stdout[-2000:]
            if len(result.stdout) > 2000
            else result.stdout,
            "error": result.stderr[-1000:]
            if len(result.stderr) > 1000
            else result.stderr,
            "viz_dir": latest_viz_dir,
            "debug": {"args": args, "cwd": str(WORK_DIR)},
        }
    )


@app.route("/viz/<path:filepath>")
def serve_viz(filepath):
    return send_from_directory(str(WORK_DIR / "visualizations"), filepath)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
