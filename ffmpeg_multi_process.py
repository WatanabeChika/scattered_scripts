import os
import glob
import subprocess
import argparse
import re
import sys

# SETTINGS
INPUT_FILE_FORMAT  = 'mkv'
OUTPUT_FILE_FORMAT = 'mp4'
SUBTITLE_FORMAT    = 'ass'

SUBTITLE_LANGUAGE  = 'chs'     # 语言代码，例如：'.zh-cn.mkv'
SUBTITLE_PREFIX    = ''     # 字幕文件前缀，例如：'.[sub]1080p.'
BASENAME_SUFFIX    = ''     # 基础文件名后缀，用于删除以匹配字幕文件名

SUBTITLE_NUM       = 0

SILENT_RUNNING     = True 

    
def run_ffmpeg_silent(cmd):
    """使用进度信息过滤"""
    process = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,  # 屏蔽标准输出
        encoding='utf-8',  # 显式指定编码为utf-8
        errors='replace',  # 替换无法解码的字符
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    # 实时过滤进度信息
    error_output = []
    while True:
        line = process.stderr.readline()
        if not line:
            if process.poll() is not None:
                break
            continue
        line = line.strip()
        error_output.append(line)
        
        # 匹配进度信息（示例格式：frame= 1234 fps=246 q=31.0 size=   12345kB）
        if re.match(r'frame\s*=\s*\d+', line):
            # 清理控制字符后输出
            clean_line = re.sub(r'.*\r', '', line)
            sys.stdout.write(f'\r{clean_line}')
            sys.stdout.flush()

    # 输出最终状态
    sys.stdout.write('\n')
    return process.wait(), error_output

def escape_special_chars(path):
    """转义文件路径中的特殊字符[和]"""
    return path.replace('[', '\\[').replace(']', '\\]')

def process_videos_outside_sub(input_dir, output_dir):
    # 记录原始工作目录
    original_cwd = os.getcwd()
    # 使用绝对路径
    abs_input = os.path.abspath(input_dir)
    abs_output = os.path.abspath(output_dir)
    
    try:
        # 切换到输入目录
        os.chdir(abs_input)
        
        # 创建输出目录
        os.makedirs(abs_output, exist_ok=True)

        # 遍历当前目录（即input_dir）中的mkv文件
        for mkv_file in glob.glob(f"*.{INPUT_FILE_FORMAT}"):
            base_name = os.path.splitext(mkv_file)[0]

            if BASENAME_SUFFIX:
                # 删除基础文件名后缀
                base_name_for_find_subs = base_name.replace(BASENAME_SUFFIX, '')
            else:
                base_name_for_find_subs = base_name
            
            # 查找匹配的字幕文件（相对路径）
            subs_found = glob.glob(f"{glob.escape(base_name_for_find_subs)}*{SUBTITLE_PREFIX}*{SUBTITLE_LANGUAGE}*.{SUBTITLE_FORMAT}")

            if not subs_found:
                print(f"Found no subtitle. Skip file: {mkv_file}")
                continue

            sub_file = subs_found[0]
            if len(subs_found) > 1:
                print(f"Found more than one subtitles. Choose the first one: {sub_file}")
            
            # 构建ffmpeg命令（使用相对路径）
            cmd = [
                "ffmpeg",
                "-y",
                "-i", mkv_file,
                "-c", "copy",
                "-vf", f"ass={escape_special_chars(sub_file)}",
                "-vcodec", "hevc_nvenc",
                os.path.join(abs_output, f"{base_name}.{OUTPUT_FILE_FORMAT}")
            ]

            print(f"Now processing: {mkv_file}")
            if SILENT_RUNNING:
                return_code, error = run_ffmpeg_silent(cmd)
                if return_code != 0:
                    error_msg = "\n".join(error)
                    raise RuntimeError(f"Process failed: {mkv_file}. Error: {error_msg}")
            else:
                try:
                    subprocess.run(cmd, check=True, stderr=subprocess.PIPE)
                except subprocess.CalledProcessError as error:
                    print(f"Process failed: {mkv_file}. Error: {error}")

    finally:
        # 恢复原始工作目录
        os.chdir(original_cwd)

def process_videos_inside_sub(input_dir, output_dir):
    # 记录原始工作目录
    original_cwd = os.getcwd()
    # 使用绝对路径
    abs_input = os.path.abspath(input_dir)
    abs_output = os.path.abspath(output_dir)
    
    try:
        # 切换到输入目录
        os.chdir(abs_input)
        
        # 创建输出目录
        os.makedirs(abs_output, exist_ok=True)

        # 遍历当前目录（即input_dir）中的mkv文件
        for mkv_file in glob.glob(f"*.{INPUT_FILE_FORMAT}"):
            base_name = os.path.splitext(mkv_file)[0]
            
            # 构建ffmpeg命令（使用相对路径）
            cmd = [
                "ffmpeg",
                "-y",
                "-i", mkv_file,
                "-map", "0:v:0",  # 默认视频流
                "-map", "0:a:0",  # 默认音频流
                "-vf", f"subtitles={escape_special_chars(mkv_file)}:si={SUBTITLE_NUM}", # 第SUBTITLE_NUM个字幕流
                "-vcodec", "hevc_nvenc",
                os.path.join(abs_output, f"{base_name}.{OUTPUT_FILE_FORMAT}")
            ]

            print(f"Now processing: {mkv_file}")
            if SILENT_RUNNING:
                return_code, error = run_ffmpeg_silent(cmd)
                if return_code != 0:
                    error_msg = "\n".join(error)
                    raise RuntimeError(f"Process failed: {mkv_file}. Error: {error_msg}")
            else:
                try:
                    subprocess.run(cmd, check=True, stderr=subprocess.PIPE)
                except subprocess.CalledProcessError as error:
                    print(f"Process failed: {mkv_file}. Error: {error}")

    finally:
        # 恢复原始工作目录
        os.chdir(original_cwd)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video subtitle hardcoding tool")
    parser.add_argument("input_dir", help="Input directory (contains videos and subtitles)")
    parser.add_argument("output_dir", help="Output directory (saves generated files)")
    parser.add_argument("--inside_sub", action="store_true", help="Process videos with subtitles inside the video file")
    
    args = parser.parse_args()
    
    if args.inside_sub:
        process_videos_inside_sub(args.input_dir, args.output_dir)
    else:
        process_videos_outside_sub(args.input_dir, args.output_dir)