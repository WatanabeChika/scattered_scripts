import os
import subprocess
import argparse
from pathlib import Path

def find_rmvb_files(root_dir):
    """
    在指定目录及其子目录中查找所有.rmvb文件
    """
    rmvb_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.rmvb'):
                rmvb_files.append(os.path.join(root, file))
    return rmvb_files

def find_avi_files(root_dir):
    """
    在指定目录及其子目录中查找所有.avi文件
    """
    avi_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.avi'):
                avi_files.append(os.path.join(root, file))
    return avi_files

def convert_to_mp4(input_file, output_file=None, overwrite=False):
    """
    使用ffmpeg将RMVB/AVI文件转换为MP4格式
    """
    if output_file is None:
        output_file = os.path.splitext(input_file)[0] + '.mp4'
    
    # 检查输出文件是否已存在
    if os.path.exists(output_file) and not overwrite:
        print(f"跳过 {input_file} -> {output_file} (输出文件已存在)")
        return False
    
    # 构建ffmpeg命令
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-vcodec', 'hevc_nvenc',
        '-y' if overwrite else '-n',  # 根据overwrite参数决定是否覆盖
        output_file
    ]
    
    try:
        print(f"正在转换: {input_file} -> {output_file}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"转换完成: {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"转换失败: {input_file}")
        print(f"错误信息: {e.stderr}")
        return False
    except FileNotFoundError:
        print("错误: 未找到ffmpeg。请确保ffmpeg已安装并在系统PATH中。")
        return False

def main():
    parser = argparse.ArgumentParser(description='将指定文件夹中的RMVB/AVI文件转换为MP4格式')
    parser.add_argument('directory', help='要扫描的目录路径')
    parser.add_argument('-o', '--output', help='输出目录（默认为原文件所在目录）')
    parser.add_argument('-f', '--overwrite', action='store_true', 
                       help='覆盖已存在的MP4文件（默认不覆盖）')
    parser.add_argument('-r', '--remove-original', action='store_true',
                       help='转换成功后删除原始RMVB文件（请谨慎使用）')
    
    args = parser.parse_args()
    
    # 检查目录是否存在
    if not os.path.isdir(args.directory):
        print(f"错误: 目录 '{args.directory}' 不存在")
        return
    
    # 查找所有RMVB文件
    rmvb_files = find_rmvb_files(args.directory)
    
    if not rmvb_files:
        print("未找到任何RMVB文件")
        return
    
    print(f"找到 {len(rmvb_files)} 个RMVB文件")

    # 查找所有AVI文件
    avi_files = find_avi_files(args.directory)
    
    if not avi_files:
        print("未找到任何AVI文件")
        return
    
    print(f"找到 {len(avi_files)} 个AVI文件")
    
    # 转换每个文件
    successful_conversions = 0
    all_conversions = rmvb_files + avi_files
    for input_file in all_conversions:
        if args.output:
            # 保持原始目录结构
            rel_path = os.path.relpath(input_file, args.directory)
            output_file = os.path.join(args.output, os.path.splitext(rel_path)[0] + '.mp4')
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
        else:
            output_file = None
        
        if convert_to_mp4(input_file, output_file, args.overwrite):
            successful_conversions += 1
            # 如果设置了删除原文件选项且转换成功
            if args.remove_original:
                try:
                    os.remove(input_file)
                    print(f"已删除原始文件: {input_file}")
                except OSError as e:
                    print(f"警告: 无法删除原始文件 {input_file}: {e}")

    print(f"转换完成: {successful_conversions}/{len(all_conversions)} 个文件成功转换")

if __name__ == "__main__":
    main()