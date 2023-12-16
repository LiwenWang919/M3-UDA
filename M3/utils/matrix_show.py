from PIL import Image
import numpy as np


def show_m(matrix,name):
    tensor_np = matrix.cpu().numpy()

    if name == 'M':
        tensor_np = tensor_np*100

    # 缩放张量到 [0, 255] 范围，并将其转换为 8 位无符号整数
    scaled_tensor = (tensor_np * 255).astype(np.uint8)

    # 创建一个 Pillow 图像对象
    image = Image.fromarray(scaled_tensor, mode='L')  # 'L' 表示灰度图像

    # 保存图像或显示图像
    image.save(name+'.png')  # 保存为图像文件