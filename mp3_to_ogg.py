import os
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor

def convert_single_mp3(mp3_path, ogg_path):
    """转换单个 MP3 文件为 OGG 文件"""
    audio = AudioSegment.from_mp3(mp3_path)
    audio.export(ogg_path, format="ogg")
    print(f"Converted: {mp3_path} -> {ogg_path}")

def convert_mp3_to_ogg(source_folder, destination_folder):
    # 确保目标文件夹存在
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    # 获取所有 MP3 文件
    mp3_files = [f for f in os.listdir(source_folder) if f.endswith(".mp3")]

    # 使用线程池并行处理文件
    with ThreadPoolExecutor() as executor:
        futures = []
        for filename in mp3_files:
            mp3_path = os.path.join(source_folder, filename)
            ogg_path = os.path.join(destination_folder, os.path.splitext(filename)[0] + ".ogg")
            futures.append(executor.submit(convert_single_mp3, mp3_path, ogg_path))

        # 等待所有任务完成
        for future in futures:
            future.result()

def convert_single_ogg(ogg_path, mp3_path):
    """转换单个 OGG 文件为 MP3 文件"""
    audio = AudioSegment.from_ogg(ogg_path)
    audio.export(mp3_path, format="mp3")
    print(f"Converted: {ogg_path} -> {mp3_path}")

def convert_ogg_to_mp3(source_folder, destination_folder):
    # 确保目标文件夹存在
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    # 获取所有 OGG 文件
    ogg_files = [f for f in os.listdir(source_folder) if f.endswith(".ogg")]

    # 使用线程池并行处理文件
    with ThreadPoolExecutor() as executor:
        futures = []
        for filename in ogg_files:
            ogg_path = os.path.join(source_folder, filename)
            mp3_path = os.path.join(destination_folder, os.path.splitext(filename)[0] + ".mp3")
            futures.append(executor.submit(convert_single_ogg, ogg_path, mp3_path))

        # 等待所有任务完成
        for future in futures:
            future.result()

if __name__ == "__main__":
    source_folder = input("Enter the source folder path: ").strip()
    destination_folder = input("Enter the destination folder path: ").strip()
    conversion_choice = input("Enter '1' to convert MP3 to OGG or '2' to convert OGG to MP3: ").strip()

    if conversion_choice == '1':
        convert_mp3_to_ogg(source_folder, destination_folder)
    elif conversion_choice == '2':
        convert_ogg_to_mp3(source_folder, destination_folder)
    else:
        print("Invalid choice. Please enter '1' or '2'.")