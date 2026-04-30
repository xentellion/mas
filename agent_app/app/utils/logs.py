import os
import logging


def delete_oldest_logs(path: str = "logs", logs_count: int = 10):
    files = []
    for filename in os.listdir(path):
        filepath = os.path.join(path, filename)
        if os.path.isfile(filepath):
            files.append(filepath)
    if not files:
        return
    if len(files) < logs_count:
        return
    files.sort(key=os.path.getctime, reverse=True)
    for file in files[logs_count - 1 : -2]:
        try:
            os.remove(file)
            logging.info(f"Oldest log cleared: {file}")
        except OSError as e:
            logging.error(f"Error deleting file {file}: {e}")
