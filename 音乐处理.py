import os
import shutil
from mutagen import File
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import logging

# 支持的音频格式
SUPPORTED_FORMATS = [".mp3", ".flac", ".wav", ".aac", ".ogg"]

# 目标文件夹名称
DUPLICATE_FOLDER_NAME = "重复音乐"


def get_music_files(directory):
    """递归获取目录及其子目录下的所有音乐文件"""
    music_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if os.path.splitext(file)[1].lower() in SUPPORTED_FORMATS:
                music_files.append(os.path.join(root, file))
    return music_files


def get_metadata(file_path):
    """获取音频文件的标签数据（歌手和标题）"""
    try:
        audio = File(file_path, easy=True)
        if audio is None:
            return None, None
        artist = audio.get('artist', [None])[0]
        title = audio.get('title', [None])[0]
        return artist, title
    except Exception as e:
        logging.error(f"无法读取文件标签: {file_path}, 错误: {str(e)}")
        return None, None


def get_file_details(file_path):
    """获取文件的格式、大小、比特率、采样率等信息"""
    try:
        if file_path.lower().endswith('.mp3'):
            audio = MP3(file_path)
            file_size = os.path.getsize(file_path)
            bitrate = audio.info.bitrate if audio.info.bitrate else 0  # 默认比特率为 0
            sample_rate = audio.info.sample_rate if audio.info.sample_rate else 0  # 默认采样率为 0
            return file_size, bitrate, sample_rate
        else:
            # 对于非 MP3 文件，返回文件大小，默认比特率和采样率为 0
            return os.path.getsize(file_path), 0, 0
    except Exception as e:
        logging.error(f"无法读取文件信息: {file_path}, 错误: {str(e)}")
        return os.path.getsize(file_path), 0, 0  # 返回文件大小，默认比特率和采样率为 0


def handle_duplicates(duplicate_files, duplicate_folder, log_file):
    """根据规则筛选重复音乐，保留最优文件，其他文件移动到重复文件夹"""
    if not os.path.exists(duplicate_folder):
        os.makedirs(duplicate_folder)

    # 排序规则：优先保留非MP3文件 -> 文件大小 -> 比特率 -> 采样率
    duplicate_files.sort(key=lambda file: (
        os.path.splitext(file)[1].lower() == ".mp3",  # MP3优先删除
        -os.path.getsize(file),  # 文件大小较大优先
        -get_file_details(file)[1],  # 比特率较高优先
        -get_file_details(file)[2]  # 采样率较高优先
    ))

    # 保留第一首，其他文件移动到重复音乐文件夹
    best_file = duplicate_files[0]
    moved_files = []

    for file in duplicate_files[1:]:
        file_name = os.path.basename(file)
        new_path = os.path.join(duplicate_folder, file_name)
        shutil.move(file, new_path)
        moved_files.append(file)

    # 写入日志
    with open(log_file, 'a', encoding='utf-8') as log:
        log.write(f"\n重复歌曲: {os.path.basename(best_file)}\n")
        log.write(f"保留文件: {best_file}\n")
        if moved_files:
            log.write("移动文件:\n")
            for moved_file in moved_files:
                log.write(f"  {moved_file}\n")


def find_duplicates(music_files):
    """查找重复的音乐文件"""
    music_map = {}
    for file in music_files:
        artist, title = get_metadata(file)
        if artist and title:
            key = (artist.lower(), title.lower())
            if key not in music_map:
                music_map[key] = []
            music_map[key].append(file)
        else:
            logging.warning(f"文件标签不完整或无法读取: {file}")

    return {key: files for key, files in music_map.items() if len(files) > 1}


def main(directory):
    # 获取所有音乐文件
    music_files = get_music_files(directory)
    logging.info(f"扫描到的音乐文件数量: {len(music_files)}")

    # 查找重复音乐
    duplicates = find_duplicates(music_files)
    logging.info(f"发现重复的音乐数量: {len(duplicates)}")

    # 处理重复音乐
    duplicate_folder = os.path.join(directory, DUPLICATE_FOLDER_NAME)
    log_file = os.path.join(duplicate_folder, "重复音乐日志.txt")

    for key, files in duplicates.items():
        artist, title = key
        logging.info(f"处理重复音乐: {artist} - {title}")
        handle_duplicates(files, duplicate_folder, log_file)


if __name__ == "__main__":
    music_directory = input("请输入要扫描的音乐文件夹路径: ")
    if os.path.isdir(music_directory):
        main(music_directory)
    else:
        print("输入的路径无效，请检查后重试。")