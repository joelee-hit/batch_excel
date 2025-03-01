import subprocess
import sys
import shutil
import os

exe_name = "batch_excel"
exe_dir_path = "batch_excel"

def run_pyinstaller():
    # 定义 PyInstaller 命令的参数列表
    command = [
        sys.executable,
        '-m',
        'PyInstaller',
        '--strip',
        '--noconsole',
        '-i',
        'R/icon.ico',
        '--add-data',
        'R:me_R',
        '--add-data',
        'config:me_config',
        '--name', exe_name, 
        '--distpath', "dist", 
        'main.py'
    ]
    try:
        # 执行命令并捕获输出
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print("package succcess!")
        print("stdout:")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("package succcess!")
        print("stderr:")
        print(e.stderr)
        return False

def rm_dir_file():
    # 删除 dist、build 目录和 main.spec 文件
    directories_to_remove = [os.path.join(os.getcwd(), path) for path in ['dist', 'build']]
    files_to_remove = [os.path.join(os.getcwd(), path) for path in ['main.spec']]

    for directory in directories_to_remove:
        if os.path.exists(directory):
            try:
                shutil.rmtree(directory)
                print(f"rm: {directory}")
            except Exception as e:
                print(f"rm {directory} fail: {e}")

    for file in files_to_remove:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"rm: {file}")
            except Exception as e:
                print(f"rm {file} fail: {e}")


def move_folders():
    # 获取打包后可执行文件所在的目录，默认是 dist 目录
    dist_dir = os.path.join(os.getcwd(), 'dist', exe_dir_path)
    # _internal 目录路径
    internal_dir = os.path.join(dist_dir, '_internal')

    # 要移动的文件夹列表
    folders_to_move = {
        'me_config': "config",
        'me_R': "R"
    }

    for folder1, folder2 in folders_to_move.items():
        source_folder = os.path.join(internal_dir, folder1)
        destination_folder = os.path.join(dist_dir, folder2)

        if os.path.exists(source_folder):
            try:
                # 移动文件夹
                shutil.move(source_folder, destination_folder)
                print(f"mv {source_folder} to {destination_folder}")
            except FileExistsError:
                print(f"{destination_folder} already exists")
            except Exception as e:
                print(f"mv {source_folder} fail: {e}")
        else:
            print(f"{source_folder} not exists")

if __name__ == "__main__":
    rm_dir_file()
    if run_pyinstaller():
        move_folders()
