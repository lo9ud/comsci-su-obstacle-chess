import zipfile, os

print("Packing...\n")

with zipfile.ZipFile('obstacleChess.zip', mode='w') as package_zip:
    for filename in [fs for fs in os.listdir() if os.path.isfile(fs) and fs.endswith('.py') and fs != 'zip.py']:
        print(f"{filename.ljust(20)} -> obstacleChess.zip")
        package_zip.write(filename)

print("\nPacked!")