import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for

from . import config
from .task_manager import create_task, get_task, list_tasks
from .llm_handler import NOTE_STYLES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/")
def index():
    recent = list_tasks()[:10]
    return render_template("index.html", recent=recent, note_styles=NOTE_STYLES)


@app.route("/submit", methods=["POST"])
def submit():
    url = request.form.get("url", "").strip()
    note_style = request.form.get("note_style", "default")

    if not url:
        return render_template(
            "index.html", error="请输入 B 站视频链接",
            note_styles=NOTE_STYLES,
        )
    if "bilibili.com" not in url and "b23.tv" not in url:
        return render_template(
            "index.html", error="请输入有效的 B 站链接",
            note_styles=NOTE_STYLES,
        )
    if note_style not in NOTE_STYLES:
        note_style = "default"

    task_id = create_task(url, note_style=note_style)
    return redirect(url_for("processing", task_id=task_id))


@app.route("/processing/<task_id>")
def processing(task_id):
    task = get_task(task_id)
    if task is None:
        return redirect(url_for("index"))
    if task["status"] == "done":
        return redirect(url_for("result", task_id=task_id))
    if task["status"] == "error":
        return redirect(url_for("result", task_id=task_id))
    return render_template("processing.html", task_id=task_id)


@app.route("/status/<task_id>")
def status(task_id):
    task = get_task(task_id)
    if task is None:
        return jsonify({"status": "not_found"})
    return jsonify({
        "id": task["id"],
        "status": task["status"],
        "progress": task["progress"],
        "message": task["message"],
        "title": task.get("title", ""),
    })


@app.route("/result/<task_id>")
def result(task_id):
    task = get_task(task_id)
    if task is None:
        return redirect(url_for("index"))

    note_style_key = task.get("note_style", "default")
    note_style_label = NOTE_STYLES.get(note_style_key, {}).get("label", "")

    return render_template(
        "result.html",
        title=task.get("title", ""),
        status=task["status"],
        error=task.get("error", ""),
        segments=task.get("segments", []),
        full_text=task.get("full_text", ""),
        polished_text=task.get("polished_text", ""),
        notes=task.get("notes", ""),
        task_id=task_id,
        note_style_label=note_style_label,
    )


@app.route("/api/text/<task_id>")
def api_text(task_id):
    task = get_task(task_id)
    if task is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify({
        "full_text": task.get("full_text", ""),
        "polished_text": task.get("polished_text", ""),
        "notes": task.get("notes", ""),
    })


if __name__ == "__main__":
    logger.info("Starting BiliSum on %s:%s", config.HOST, config.PORT)
    app.run(host=config.HOST, port=config.PORT, debug=False)
