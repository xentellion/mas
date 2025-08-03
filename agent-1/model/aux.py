def achtung_print(warning, text=None):
    if text:
        print(f"\033[1;31m{warning}:\033[0m {text}")
    else:
        print(f"\033[1;31m{warning}:\033[0m")
