"""
该脚本不与游戏一起运行，仅作为工具脚本，用于将gif分开成多张png（如有需要）
"""
import sys
import os
from PIL import Image

def extract_gif_frames(gif_path):
    gif_path = os.path.abspath(gif_path)
    gif_dir = os.path.dirname(gif_path)
    gif_name = os.path.splitext(os.path.basename(gif_path))[0]

    with Image.open(gif_path) as im:
        frame_count = im.n_frames
        print(f"提取 {frame_count} 帧...")

        # 用于还原每一帧完整图像
        previous_frame = im.convert("RGBA")

        for i in range(frame_count):
            im.seek(i)
            current_frame = im.convert("RGBA")

            # 创建一张完整大小的画布
            new_frame = Image.new("RGBA", im.size)
            new_frame.paste(current_frame, (0, 0), current_frame)

            output_path = os.path.join(gif_dir, f"{gif_name}_frame_{i:03d}.png")
            new_frame.save(output_path)
            print(f"保存帧 {i} 到：{output_path}")

            previous_frame = new_frame

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("请将 GIF 文件路径拖入此脚本，或在命令行中输入路径。")
    else:
        gif_path = sys.argv[1]
        extract_gif_frames(gif_path)