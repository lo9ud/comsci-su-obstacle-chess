import zipfile, os

print("Packing...\n")
skips = ["zip.py"]
with zipfile.ZipFile("obstacleChess.zip", mode="w") as package_zip:
    for filename in [
        potential
        for potential in os.listdir()
        if os.path.isfile(potential)
        and potential.endswith(".py")
        and potential not in skips
    ]:
        print(f"{filename.ljust(20)} -> obstacleChess.zip")
        package_zip.write(filename)

print("\nPacked!")
