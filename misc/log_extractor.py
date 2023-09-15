import os, re

log_files = [f for f in os.listdir(".") if os.path.isfile(f) and f.endswith('.log')]

expected_re = re.compile(
    r"(?:Expected:)\n(?P<expected>([\.pPnNbBrRqQkK_|MDOX]+\n)+.*)(?:\nFound:\n)(?P<found>([\.pPnNbBrRqQkK_|MDX]+\n)+.*)?\n(?:Test:)"
)
all_match:dict[str, list[dict[str,str]]] = {}
for file in log_files:
    with open(file, 'r') as f:
        matches = [{"ex":match.group("expected"), "fd":match.group("found")} for match in expected_re.finditer(f.read())]
    all_match[file] = matches
    
for file, matches in all_match.items():
    print(file)
    for i, match in enumerate(matches):
        print(f"\nMatch {i+1}:")
        print("Expected:")
        print(match["ex"])
        with open(f"./log_output/{file[:-4]}_match_{i+1}.txt", 'w') as f:
            f.write(match["ex"])
            if match["fd"]:
                print("Found:")
                print(match["fd"])
                f.write("%Found:\n")
                for line in match["fd"].split("\n"):
                    f.write(f"%{line}")
    print()
    print()