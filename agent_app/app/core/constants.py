import os


GRAPH_PATH = "data/graph.bin"
LOG_PROMPTS = os.getenv("LOG_PROMPTS") == "True"
STEP = 1
TPS = 1 / float(os.environ["TPS"])
