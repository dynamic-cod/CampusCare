"""
train_urgency_model.py
Entry point to train the CampusCare urgency classifier model.
Executes retrain_urgency_model.py.
"""
import os
import sys

if __name__ == "__main__":
    script_path = os.path.join(os.path.dirname(__file__), "retrain_urgency_model.py")
    with open(script_path) as f:
        code = compile(f.read(), script_path, "exec")
        exec(code, globals(), locals())
