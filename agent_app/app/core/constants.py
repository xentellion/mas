import os


GRAPH_PATH = "data/graph.bin"
LOG_PROMPTS = os.getenv("LOG_PROMPTS") == "True"
STEP = 1
TPS = int(os.environ["TPS"])
