import os
from flask import Flask, render_template

app = Flask(__name__, template_folder="views")
app.debug = True

@app.route("/configs/<config>")
def host_file(config: str):
    if config.endswith(".RPfile"):
        with open(f"rpository/{config}", "r", encoding="utf-8") as _f:
            return _f.read()
    else:
        with open(f"rpository/{config}.RPfile", "r", encoding="utf-8") as _f:
            return _f.read()

@app.route("/configs/")
def list_files():
    return os.listdir("rpository")

@app.route("/volumes")
def send_volumes():
    with open("db/file1.yaml", "r", encoding="utf-8") as _f:
        return _f.read()
