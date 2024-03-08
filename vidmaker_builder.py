import os

print("Enter the name of the generator you want to create: ")
generator_name = input()

os.makedirs("./generators", generator_name, exist_ok=True)
print("Done, now execute run_all_instances.bat to run the generator.")