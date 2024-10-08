import PyInstaller.__main__
from pathlib import Path

HERE = Path(__file__).parent.absolute()
path_to_main = str(HERE / "../../pyinstaller_entry_point.py")

def main():
	PyInstaller.__main__.run([path_to_main, '--onefile', '--windowed', '--distpath', 'flump', '--name', 'flump'])

if __name__ == '__main__':
	main()