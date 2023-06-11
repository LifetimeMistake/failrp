import os
from flask import Flask, render_template

app = Flask(__name__, template_folder="views")
app.debug = True

@app.route("/configs/<config>")
def host_file(config: str):
    with open(f"rpository/{config}", "r", encoding="utf-8") as _f:
        return _f.read()
    
@app.route("/configs/")
def list_files():
    return os.listdir("rpository")

@app.route("/labels/<label_file>")
def host_label(label_file: str):
    with open(f"partition_labels/{label_file}", "r", encoding="utf-8") as _f:
        return _f.read()

@app.route("/labels/")
def send_labels():
    return os.listdir("partition_labels")