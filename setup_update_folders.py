import os
import shutil
import configparser

if __name__ == "__main__":
    generators = [f for f in os.listdir("generators") if os.path.isdir(os.path.join("generators", f))]
    instance_folder = "__INSTANCE__"

    print("Updating video generators assets...")

    def update_config(config, default_config):
        # Add missing elements
        for section in default_config.sections():
            if not config.has_section(section):
                config.add_section(section)

            for option, value in default_config.items(section):
                if not config.has_option(section, option):
                    config.set(section, option, value)

        # Remove superfluous options
        for section in config.sections():
            if section not in default_config.sections():
                config.remove_section(section)
        return config

    for generator in generators:
        print("Updating assets and actions for generator: " + generator)
        assets_folders_to_ignore = ["gameplay", "music"]
        
        # Construct paths for source (__INSTANCE__) and destination (generator folder)
        source_path = os.path.join(instance_folder, '')
        destination_path = os.path.join('./generators', generator, '')
        
        # Create the destination folder if it doesn't exist
        os.makedirs(destination_path, exist_ok=True)
        
        # Function to filter out folders to ignore
        def ignore_folders(dirs):
            return [d for d in dirs if d in assets_folders_to_ignore and os.path.isdir(os.path.join(source_path, d))]
        
        # Recursively copy the contents from the source to the destination, excluding specified folders
        for root, dirs, files in os.walk(source_path):
            dirs_to_ignore = ignore_folders(dirs)
            dirs[:] = [d for d in dirs if d not in dirs_to_ignore]
            
            for file in files:
                #check if folder is in ignore list
                if os.path.basename(root) in assets_folders_to_ignore:
                    continue

                src_file = os.path.join(root, file)
                dest_file = os.path.join(destination_path, os.path.relpath(src_file, source_path))
                # make sure all folders exist
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)

                # copy src_file to dest_file and overwrite if it already exists
                shutil.copyfile(src_file, dest_file)

        if not os.path.isfile(os.path.join(destination_path, "config.ini")):
            shutil.copyfile(os.path.join("default_config.ini"), os.path.join(destination_path, "config.ini"))

        default_config = configparser.ConfigParser()
        default_config.read(os.path.join("default_config.ini"), encoding='utf-8')

        config = configparser.ConfigParser()
        config.read(os.path.join(destination_path, "config.ini"), encoding='utf-8')

        config = update_config(config, default_config)

        # Save the updated configuration
        with open(os.path.join(destination_path, "config.ini"), 'w', encoding='utf-8') as config_file:
            config.write(config_file)

        # edit the bat file by replacing %id% by the generator name
        with open(os.path.join(destination_path, "app.bat"), "r") as bat_file:
            bat_file_content = bat_file.read()
            bat_file_content = bat_file_content.replace("%id%", generator)
            with open(os.path.join(destination_path, "app.bat"), "w") as bat_file:
                bat_file.write(bat_file_content)
            
        print("Generator done updating: " + generator)
        #os.system("start cmd /c \"cd " + destination_path + " && app.bat\"")