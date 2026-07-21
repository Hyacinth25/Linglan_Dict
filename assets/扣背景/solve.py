import os
from PIL import Image

def remove_green_screen(folder_path):
    # 目标绿色的 RGB 值 (#22B14C)
    # 22 -> 34, B1 -> 177, 4C -> 76
    target_green = (34, 177, 76)
    threshold = 5  # 容差（允许颜色有一点点偏差，防止边缘抠不干净）

    # 遍历文件夹
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.png'):
            file_path = os.path.join(folder_path, filename)
            temp_path = os.path.join(folder_path, f"temp_{filename}")

            print(f"正在处理: {filename} ✨")

            # 打开图片并转为 RGBA 模式
            # （RGBA：红、绿、蓝 + Alpha透明度通道）
            img = Image.open(file_path).convert("RGBA")
            datas = img.getdata()

            new_data = []
            for item in datas:
                # 计算当前像素与目标绿色的距离
                # 如果颜色足够接近，就把它变透明 (Alpha 设为 0)
                if (abs(item[0] - target_green[0]) < threshold and
                    abs(item[1] - target_green[1]) < threshold and
                    abs(item[2] - target_green[2]) < threshold):
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)

            img.putdata(new_data)
            
            # 先存为临时文件
            img.save(temp_path, "PNG")
            
            # 关闭图片流以便删除原文件
            img.close()

            # 核心替换操作：删除旧的，重命名新的
            os.remove(file_path)
            os.rename(temp_path, file_path)
            
            print(f"完成！已替换 {filename}")

# 使用方法：把 '.' 换成你的文件夹路径
if __name__ == "__main__":
    remove_green_screen('.')