import os
import pkg_resources
import sys
import chardet

def get_dependencies():
    try:
        with open('requirements.txt', 'rb') as f:
            result = chardet.detect(f.read())  # or readline if the file is large
            charenc = result['encoding']
        with open('requirements.txt', 'r', encoding=charenc) as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print("requirements.txt not found. Consider generating one using 'pip freeze > requirements.txt'")
        return []

def get_project_name():
    return os.path.basename(os.getcwd())

def get_python_version():
    return f"{sys.version_info.major}.{sys.version_info.minor}"

def get_project_structure():
    structure = []
    for root, dirs, files in os.walk('.'):
        level = root.replace('.', '').count(os.sep)
        indent = ' ' * 4 * (level)
        structure.append('{}{}/'.format(indent, os.path.basename(root)))
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            structure.append('{}{}'.format(subindent, f))
    return structure

def generate_readme():
    project_name = get_project_name()
    python_version = get_python_version()
    dependencies = get_dependencies()
    project_structure = get_project_structure()

    dependency_list = "\n".join(f"- {dep}" for dep in dependencies) if dependencies else "No dependencies listed"
    readme_content = f"""# {project_name}

    ## Description
    This is a Space Invaders game implemented in Python using Pygame.
    
    ## Requirements
    - Python {python_version}
    - Pygame
    
    ## Dependencies
    {dependency_list}

    ## Installation
        1. Clone this repository:
           ```
           git clone https://github.com/udivak/Space-Invaders-Pro.git
           cd Space-Invaders-Pro
           ```
        2. Install the required dependencies:
           ```
           pip install pygame
           ```
    ## Game Controls
    - Player 1:
      - Arrow keys to move
      - 'L' key to shoot
    - Player 2 (if applicable):
      - W, A, S, D keys to move
      - 'G' key to shoot

    ## Features
    - Single and Two-player modes
    - Multiple enemy types
    - Power-ups
    - Boss battles
    - Score tracking

    ## Contributing
    Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
    """

    with open('README.md', 'w') as f:
        f.write(readme_content)


    print("README.md has been generated successfully!")

generate_readme()